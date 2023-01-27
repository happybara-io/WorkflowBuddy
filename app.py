import contextlib
import copy
import json
import logging
import os
import pprint
import re
import traceback as tb
from datetime import datetime, timedelta, timezone
from typing import Tuple

import buddy.constants as c

import slack_sdk
from flask import Flask, jsonify, request
from slack_bolt import Ack, App, Respond
from slack_bolt.adapter.flask import SlackRequestHandler
from slack_bolt.workflows.step import Complete, Configure, Fail, Update, WorkflowStep
from slack_sdk.models.views import View

import buddy
import buddy.errors
import buddy.utils as utils
from buddy.sqlalchemy_ear import SQLAlchemyInstallationStore
from slack_sdk.oauth.state_store.sqlalchemy import SQLAlchemyOAuthStateStore
from slack_sdk.oauth import OAuthStateUtils
from slack_bolt import App, Ack, Respond, BoltContext
from slack_bolt.oauth.oauth_settings import OAuthSettings
import sqlalchemy
from sqlalchemy.engine import Engine

# attempting and failing to silence DEBUG loggers
logger = logging.getLogger(__name__).setLevel(logging.INFO)
logging.basicConfig(level=logging.INFO)
logging.getLogger("sqlalchemy.engine").setLevel(logging.INFO)
logging.getLogger("slack_bolt").setLevel(logging.INFO)
logging.getLogger("slack_sdk").setLevel(logging.INFO)

ENV = os.environ.get("ENV", "DEV")
slack_client_id = os.environ["SLACK_CLIENT_ID"]
encryption_key = os.environ.get("SECRET_ENCRYPTION_KEY")
ignore_encryption_warning = os.environ.get("IGNORE_ENCRYPTION", False)
if not encryption_key and not ignore_encryption_warning:
    logging.warning(
        "[!] Starting server without an encryption key...data will not be encrypted at rest by this application."
    )

# TODO: Sett up SQLALChemy Engine
LOCAL_SQLITE_DB = "workflow_buddy.db"
if ENV == "PROD":
    LOCAL_SQLITE_DB = f"/usr/app/data/{LOCAL_SQLITE_DB}"
LOCAL_SQLITE_CONN_STR = f"sqlite:///{LOCAL_SQLITE_DB}"
# TODO: if an alternative connection string is provided
conn_str = os.environ.get("SQL_CONN_STR", LOCAL_SQLITE_CONN_STR)
logging.info(f"Starting SQLAlchemy connected to: {conn_str}")
engine: Engine = sqlalchemy.create_engine(conn_str)


installation_store = SQLAlchemyInstallationStore(
    engine=engine,
    client_id=slack_client_id,
    encryption_key=encryption_key,
    logger=logger,
)
oauth_state_store = SQLAlchemyOAuthStateStore(
    engine=engine,
    expiration_seconds=OAuthStateUtils.default_expiration_seconds,
    logger=logger,
)
try:
    engine.execute("select count(*) from slack_bots")
except Exception as e:
    installation_store.metadata.create_all(engine)
    oauth_state_store.metadata.create_all(engine)

slack_app = App(
    signing_secret=os.environ["SLACK_SIGNING_SECRET"],
    oauth_settings=OAuthSettings(
        client_id=slack_client_id,
        client_secret=os.environ["SLACK_CLIENT_SECRET"],
        scopes=c.SCOPES,
        user_scopes=c.USER_SCOPES,
        installation_store=installation_store,
        state_store=oauth_state_store,
    ),
)

# TODO: this only works if we have a single process, not good! Tech debt!
DEBUG_STEP_DATA_CACHE = {}


@slack_app.middleware  # or app.use(log_request)
def log_request(logger: logging.Logger, body: dict, next):
    logger.debug(body)
    return next()


def build_scheduled_message_modal(client: slack_sdk.WebClient) -> dict:
    # https://api.slack.com/methods/chat.scheduledMessages.list
    # TODO: error handling
    resp = client.chat_scheduledMessages_list()
    blocks = [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "Messages scheduled to be sent from this bot.",
            },
        },
        {"type": "divider"},
    ]
    if resp["ok"]:
        # TODO: add stuff for pagination? etc? Average user will have <10 I'd bet,
        # so fine to leave off for now.
        messages_list = resp["scheduled_messages"]
        if len(messages_list) < 1:
            blocks.append(
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"🤷 Nothing scheduled currently.",
                    },
                }
            )
        for sm in messages_list:
            text = sm["text"]
            blocks.append(
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*To:* <#{sm['channel_id']}> *At:* `{sm['post_at']}` *Text:*\n```{text[:100]}{'...' if len(text) > 100 else ''}```",
                    },
                    "accessory": {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "Delete", "emoji": True},
                        "style": "danger",
                        "value": f"{sm['channel_id']}-{sm['id']}",
                        "action_id": "scheduled_message_delete_clicked",
                    },
                }
            )
    else:
        blocks.extend(
            [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"❌ Failed to list scheduled messages, err: {resp.get('error')}",
                    },
                }
            ]
        )

    sm_modal = {
        "type": "modal",
        "title": {
            "type": "plain_text",
            "text": "Manage Scheduled Msgs",
            "emoji": True,
        },
        "close": {"type": "plain_text", "text": "Close", "emoji": True},
        "blocks": blocks,
    }
    return sm_modal


def build_manual_complete_modal(client: slack_sdk.WebClient) -> dict:
    blocks = [
        {
            "type": "input",
            "block_id": "execution_id_input",
            "element": {
                "type": "plain_text_input",
                "action_id": "execution_id_value",
                "placeholder": {
                    "type": "plain_text",
                    "text": "11111111111.11111111111",
                },
            },
            "label": {"type": "plain_text", "text": "Execution ID", "emoji": True},
        },
        {
            "type": "input",
            "optional": True,
            "block_id": "block_checkboxes",
            "element": {
                "type": "checkboxes",
                "options": [
                    {
                        "text": {"type": "mrkdwn", "text": "*🥵❌ Mark Step as Failed*"},
                        "description": {
                            "type": "mrkdwn",
                            "text": "_Mark Step as a failure and halt the workflow with error message._",
                        },
                        "value": "value_checkboxes",
                    }
                ],
                "action_id": "action_checkboxes",
            },
            "label": {"type": "plain_text", "text": " ", "emoji": True},
        },
        {
            "type": "input",
            "block_id": "error_message_input",
            "optional": True,
            "element": {"type": "plain_text_input", "action_id": "error_message_value"},
            "label": {"type": "plain_text", "text": "Error Message", "emoji": True},
            "hint": {
                "type": "plain_text",
                "text": "Sadly Markdown won't work in the error message.",
            },
        },
    ]
    mc_modal = {
        "type": "modal",
        "callback_id": "manual_complete_submission",
        "title": {
            "type": "plain_text",
            "text": "Manual Finish Step",
            "emoji": True,
        },
        "submit": {"type": "plain_text", "text": "Finish Step", "emoji": True},
        "close": {"type": "plain_text", "text": "Close", "emoji": True},
        "blocks": blocks,
    }
    return mc_modal


@slack_app.shortcut("message_details")
def shortcut_message_details(ack: Ack, shortcut: dict, client: slack_sdk.WebClient):
    ack()

    blocks = [
        {"type": "section", "text": {"type": "mrkdwn", "text": "Message details:"}},
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"```{json.dumps(shortcut, indent=2)}```",
            },
        },
    ]
    client.views_open(
        trigger_id=shortcut["trigger_id"],
        view={
            "type": "modal",
            "title": {"type": "plain_text", "text": "Inspect Message"},
            "close": {"type": "plain_text", "text": "Close"},
            "blocks": blocks,
        },
    )


@slack_app.action(re.compile("(manual_complete-continue|manual_complete-stop)"))
def manual_complete_button_clicked(
    ack: Ack,
    body: dict,
    logger: logging.Logger,
    client: slack_sdk.WebClient,
    respond: Respond,
):
    ack()
    actions_payload = body["actions"][0]
    action_id = actions_payload["action_id"]
    action_user_id = body["user"]["id"]
    action_user_name = body["user"].get("name")
    try:
        workflow_step_execute_id, workflow_name = actions_payload["value"].split(
            c.BUDDY_VALUE_DELIMITER
        )
    except ValueError:
        workflow_step_execute_id = actions_payload["value"]
        workflow_name = "the Workflow"

    execution_body = {
        "event": {
            "workflow_step": {"workflow_step_execute_id": workflow_step_execute_id}
        }
    }
    prev_msg_blocks = body["message"]["blocks"]
    # Keep just the first info block, then swap out rest with updated block.
    updated_blocks = prev_msg_blocks[:1]

    if "stop" in action_id:
        fail = Fail(client=client, body=execution_body)
        # TODO: add more context: by who? why? what workflow was this?
        errmsg = f"Workflow stopped manually by {action_user_name}:{action_user_id}."
        fail(error={"message": errmsg})
        replacement_text = f"🛑 <@{action_user_id}> halted {workflow_name}."
    else:
        # yay the Workflow continues!
        complete = Complete(client=client, body=execution_body)
        outputs = {"user_id": action_user_id, "user": action_user_id}
        complete(outputs=outputs)
        replacement_text = f"👉 <@{action_user_id}> continued {workflow_name}."

    updated_blocks.append(
        {
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": replacement_text,
                }
            ],
        }
    )
    respond(replace_original=True, text=replacement_text, blocks=updated_blocks)


@slack_app.action(re.compile("(debug-continue|debug-stop)"))
def debug_button_clicked(
    ack: Ack,
    body: dict,
    logger: logging.Logger,
    client: slack_sdk.WebClient,
    respond: Respond,
):
    global DEBUG_STEP_DATA_CACHE
    logger.debug("Continuing from debug button clicked...")
    logger.debug(f"ACTION_BODY: {body}")
    ack()

    actions_payload = body["actions"][0]
    action_id = actions_payload["action_id"]
    workflow_step_execute_id = actions_payload["value"]
    execution_body = {
        "event": {
            "workflow_step": {"workflow_step_execute_id": workflow_step_execute_id}
        }
    }
    fail = Fail(client=client, body=execution_body)

    if "stop" in action_id:
        errmsg = "Stopped manually for Debug step, not a failure in processing."
        with contextlib.suppress(slack_sdk.errors.SlackApiError):
            fail(error={"message": errmsg})
        replacement_text = f"🛑 Halted debug step for `{workflow_step_execute_id}`."
        respond(replace_original=True, text=replacement_text)
    else:
        cache_data = DEBUG_STEP_DATA_CACHE[workflow_step_execute_id]
        step = cache_data["step"]
        orig_execute_body = cache_data["body"]
        logger.debug(
            f"execution_id:{workflow_step_execute_id}|step:{step}|orig_body:{orig_execute_body}.===="
        )

        replacement_text = f"👉Debug step continued for `{workflow_step_execute_id}`.\n```{pprint.pformat(step, indent=2)}```"
        respond(replace_original=True, text=replacement_text)
        del DEBUG_STEP_DATA_CACHE[workflow_step_execute_id]

        complete = Complete(client=client, body=execution_body)

        step["already_sent_debug_message"] = True
        execute_utils(step, orig_execute_body, complete, fail, client, logger)
        logger.debug(f"DEBUG_STEPCACHE: {DEBUG_STEP_DATA_CACHE}")


@slack_app.action("scheduled_message_delete_clicked")
def delete_scheduled_message(
    ack: Ack, body: dict, logger: logging.Logger, client: slack_sdk.WebClient
):
    ack()
    payload = body["actions"][0]
    channel_id, scheduled_message_id = payload["value"].split("-")
    logger.info(f"SCHEDULED_MESSAGE_CLICKED - {channel_id}:{scheduled_message_id}")
    # rate-limiting: tier 3, 50+ per minute per workspace - should be fine.
    resp = client.chat_deleteScheduledMessage(
        channel=channel_id, scheduled_message_id=scheduled_message_id
    )

    if resp["ok"]:
        sm_modal = build_scheduled_message_modal(client)
        resp = client.views_update(
            view_id=body["view"]["id"], hash=body["view"]["hash"], view=sm_modal
        )
        logger.info(resp)


@slack_app.action("action_manual_complete")
def manual_complete_button_clicked(
    ack: Ack, body: dict, logger: logging.Logger, client: slack_sdk.WebClient
):
    ack()
    mc_modal = build_manual_complete_modal(client)
    client.views_open(trigger_id=body["trigger_id"], view=mc_modal)


@slack_app.action("action_manage_scheduled_messages")
def manage_scheduled_messages(
    ack: Ack, body: dict, logger: logging.Logger, client: slack_sdk.WebClient
):
    ack()
    sm_modal = build_scheduled_message_modal(client)
    client.views_open(trigger_id=body["trigger_id"], view=sm_modal)


@slack_app.action("action_export")
def export_button_clicked(
    ack: Ack,
    body: dict,
    logger: logging.Logger,
    client: slack_sdk.WebClient,
    context: BoltContext,
):
    ack()
    exported_json = json.dumps(utils.db_export(), indent=2)
    export_modal = {
        "type": "modal",
        "title": {"type": "plain_text", "text": "Webhook Config Export", "emoji": True},
        "close": {"type": "plain_text", "text": "Close", "emoji": True},
        "blocks": [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Exported Config:* \n```{exported_json}```",
                },
            }
        ],
    }
    client.views_open(trigger_id=body["trigger_id"], view=export_modal)


@slack_app.action("action_import")
def import_button_clicked(
    ack: Ack, body, logger: logging.Logger, client: slack_sdk.WebClient
):
    ack()
    blocks = [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": 'Import a JSON config of event type mapped to lists of webhooks.\n*Example:*\n```{"app_mention": [{"name": "Helpful Description","webhook_url": "https://webhook.site/4bf6c228"}]}```\n\nUpdates existing keys, but doesn\'t remove any.',
            },
        },
        {
            "type": "input",
            "block_id": "json_config_input",
            "element": {
                "type": "plain_text_input",
                "multiline": True,
                "action_id": "json_config_value",
            },
            "label": {"type": "plain_text", "text": "JSON Config", "emoji": True},
        },
    ]
    import_modal = {
        "type": "modal",
        "callback_id": "import_submission",
        "title": {"type": "plain_text", "text": "Import Event Mappings"},
        "submit": {"type": "plain_text", "text": "Import"},
        "blocks": blocks,
    }
    client.views_open(trigger_id=body["trigger_id"], view=import_modal)


@slack_app.view("manual_complete_submission")
def manual_complete_view_submission(
    ack: Ack, body, client: slack_sdk.WebClient, view: View, logger: logging.Logger
):
    values = view["state"]["values"]
    user_id = body["user"]["id"]
    ack()

    execution_id = values["execution_id_input"]["execution_id_value"]["value"]
    fail_checkbox_is_selected = (
        len(values["block_checkboxes"]["action_checkboxes"]["selected_options"]) > 0
    )
    error_message = values["error_message_input"]["error_message_value"]["value"] or ""

    msg = ""
    try:
        resp = utils.finish_an_execution(
            client,
            execution_id,
            failed=fail_checkbox_is_selected,
            err_msg=error_message,
        )
        msg = f"Successfully finished step with `{'Fail' if fail_checkbox_is_selected else 'Complete'}`."
    except Exception as e:
        logger.exception(e)
        # Handle error
        msg = f"There was an error trying to finish your Workflow Step:\n```{e}```"

    try:
        client.chat_postMessage(channel=user_id, text=msg)
    except e:
        logger.exception(f"Failed to send confirmation message {e}")


@slack_app.view("import_submission")
def import_config_view_submission(
    ack: Ack,
    body,
    client: slack_sdk.WebClient,
    view: View,
    logger: logging.Logger,
    context: BoltContext,
):
    values = view["state"]["values"]
    user_id = body["user"]["id"]
    json_config_str = values["json_config_input"]["json_config_value"]["value"]
    errors = {}
    try:
        data = json.loads(json_config_str)
        ack()
    except json.JSONDecodeError as e:
        errors["json_config_input"] = f"Invalid JSON. Error: {str(e)}"
        ack(response_action="errors", errors=errors)
        return

    msg = ""
    try:
        # Save to DB
        num_keys_updated = utils.db_import(data)
        msg = f"Imported {num_keys_updated} event_type keys into Workflow Buddy."
    except Exception as e:
        logger.exception(e)
        msg = "There was an error with your submission"

    try:
        client.chat_postMessage(channel=user_id, text=msg)
    except e:
        logger.exception(f"Failed to post a message {e}")

    utils.update_app_home(client, user_id)


@slack_app.action("event_delete_clicked")
def delete_event_mapping(
    ack: Ack,
    body: dict,
    logger: logging.Logger,
    client: slack_sdk.WebClient,
    context: BoltContext,
):
    ack()
    user_id = body["user"]["id"]
    payload = body["actions"][0]
    event_type = payload["value"]
    logger.info(f"EVENT_DELETE_CLICKED - {event_type}")
    utils.db_remove_event(event_type)
    utils.update_app_home(client, user_id)


@slack_app.action("action_add_webhook")
def add_button_clicked(
    ack: Ack, body: dict, client: slack_sdk.WebClient, context: BoltContext
):
    ack()
    add_webhook_modal = utils.build_add_webhook_modal()
    client.views_open(trigger_id=body["trigger_id"], view=add_webhook_modal)


@slack_app.view("webhook_form_submission")
def handle_config_webhook_submission(
    ack: Ack,
    body: dict,
    client: slack_sdk.WebClient,
    view: View,
    logger: logging.Logger,
):
    values = view["state"]["values"]
    user_id = body["user"]["id"]
    event_type = values["event_type_input"]["event_type_value"]["value"]
    name = values["desc_input"]["desc_value"]["value"]
    webhook_url = values["webhook_url_input"]["webhook_url_value"]["value"]
    filter_reaction = values["filter_reaction_input"]["filter_reaction_value"]["value"]
    # Validate the inputs
    logger.info(f"submission: {event_type}|{name}|{webhook_url}|{filter_reaction}")
    errors = {}
    if (event_type is not None and webhook_url is not None) and not utils.is_valid_url(
        webhook_url
    ):
        block_id = "webhook_url_input"
        errors[block_id] = f"Must be a valid URL with `http(s)://.`"
    if len(errors) > 0:
        ack(response_action="errors", errors=errors)
        return
    ack()

    msg = ""
    try:
        utils.db_add_webhook_to_event(
            event_type, name, webhook_url, user_id, filter_reaction=filter_reaction
        )
        msg = f"Your addition of {event_type}:{webhook_url} was successful."
    except Exception as e:
        logger.exception(e)
        msg = f"There was an error attempting to add {event_type}:{webhook_url}."
    try:
        client.chat_postMessage(channel=user_id, text=msg)
    except e:
        logger.exception(f"Failed to post a message {e}")

    utils.update_app_home(client, user_id)


@slack_app.event(c.EVENT_APP_MENTION)
def event_app_mention(logger: logging.Logger, event: dict, body: dict):
    utils.generic_event_proxy(logger, event, body)


@slack_app.event(c.EVENT_CHANNEL_ARCHIVE)
def event_channel_archive(logger: logging.Logger, event: dict, body: dict):
    utils.generic_event_proxy(logger, event, body)


@slack_app.event(c.EVENT_CHANNEL_CREATED)
def event_channel_created(logger: logging.Logger, event: dict, body: dict):
    utils.generic_event_proxy(logger, event, body)


@slack_app.event(c.EVENT_CHANNEL_DELETED)
def event_channel_deleted(logger: logging.Logger, event: dict, body: dict):
    utils.generic_event_proxy(logger, event, body)


@slack_app.event(c.EVENT_CHANNEL_UNARCHIVE)
def event_channel_unarchive(logger: logging.Logger, event: dict, body: dict):
    utils.generic_event_proxy(logger, event, body)


@slack_app.event(c.EVENT_REACTION_ADDED)
def event_reaction_added(logger: logging.Logger, event: dict, body: dict):
    utils.generic_event_proxy(logger, event, body)


@slack_app.event(c.EVENT_WORKFLOW_PUBLISHED)
def handle_workflow_published_events(body: dict, logger: logging.Logger):
    logger.debug(body)


@slack_app.event(c.EVENT_WORKFLOW_STEP_DELETED)
def handle_workflow_step_deleted_events(body: dict, logger: logging.Logger):
    logger.debug(body)


@slack_app.event(c.EVENT_APP_HOME_OPENED)
def update_app_home(
    event: dict,
    logger: logging.Logger,
    client: slack_sdk.WebClient,
    context: BoltContext,
):
    team_id = context.team_id
    app_home_view = utils.build_app_home_view()
    client.views_publish(user_id=event["user"], view=app_home_view)


def edit_utils(
    ack: Ack,
    step: dict,
    configure: Configure,
    client: slack_sdk.WebClient,
    logger: logging.Logger,
    context: BoltContext,
):
    # TODO: if I want to update modal, need to listen for the action/event separately
    ack()
    existing_inputs = copy.deepcopy(
        step["inputs"]
    )  # avoid potential issue when we delete from input dict

    blocks = copy.deepcopy(c.UTILS_STEP_MODAL_COMMON_BLOCKS)
    DEFAULT_ACTION = "webhook"
    chosen_action = (
        existing_inputs.get("selected_utility", {}).get("value") or DEFAULT_ACTION
    )
    chosen_config_item = c.UTILS_CONFIG[chosen_action]
    debug_mode_enabled = utils.sbool(
        existing_inputs.get("debug_mode_enabled", {}).get("value")
    )

    if debug_mode_enabled:
        copy_of_debug_blocks = copy.deepcopy(c.DEBUG_MODE_BLOCKS)
        blocks.extend(copy_of_debug_blocks)

    blocks.append(
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"{chosen_config_item.get('description')}",
            },
        }
    )
    blocks.extend(
        utils.dynamic_modal_top_blocks(chosen_action, user_token=context.user_token)
    )
    # have to make sure we aren't accidentally editing config blocks in memory
    blocks.extend(copy.deepcopy(chosen_config_item["modal_input_blocks"]))
    utils.update_blocks_with_previous_input_based_on_config(
        blocks, chosen_action, existing_inputs, chosen_config_item
    )
    configure(blocks=blocks)


# TODO: this seems like it would be a good thing to just have natively in Bolt.
# Lots of people want to update their Step view.
@slack_app.action(re.compile("(utilities_action_select_value|debug_mode)"))
def utils_update_step_modal(
    ack: Ack,
    body: dict,
    logger: logging.Logger,
    client: slack_sdk.WebClient,
    context: BoltContext,
):
    ack()
    logger.info(f"ACTION_CHANGE: {body}")

    # TODO: can get selectd action from the body
    curr_modal_state_values = body["view"]["state"]["values"]
    print("STATE", curr_modal_state_values)
    selected_buddy_action = curr_modal_state_values["general_options_action_select"][
        "utilities_action_select_value"
    ]["selected_option"]["value"]
    debug_mode_enabled = (
        len(
            curr_modal_state_values["general_options_action_select"]["debug_mode"][
                "selected_options"
            ]
        )
        > 0
    )

    updated_blocks = copy.deepcopy(c.UTILS_STEP_MODAL_COMMON_BLOCKS)
    if debug_mode_enabled:
        copy_of_debug_blocks = copy.deepcopy(c.DEBUG_MODE_BLOCKS)
        updated_blocks.extend(copy_of_debug_blocks)

    # action = body["actions"][0]
    # selected_action = action["selected_option"]["value"]
    updated_blocks.append(
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"{c.UTILS_CONFIG[selected_buddy_action].get('description')}",
            },
        }
    )

    updated_blocks.extend(
        utils.dynamic_modal_top_blocks(
            selected_buddy_action, user_token=context.user_token
        )
    )
    updated_blocks.extend(c.UTILS_CONFIG[selected_buddy_action]["modal_input_blocks"])
    updated_view = {
        "type": "workflow_step",
        "callback_id": c.WORKFLOW_STEP_UTILS_CALLBACK_ID,
        "blocks": updated_blocks,
    }
    resp = client.views_update(
        view_id=body["view"]["id"], hash=body["view"]["hash"], view=updated_view
    )
    logger.info(resp)


def save_utils(
    ack: Ack,
    view: View,
    update: Update,
    logger: logging.Logger,
    client: slack_sdk.WebClient,
):
    logger.debug("view", view)
    curr_modal_state_values = view["state"]["values"]
    action_select_block_id = "general_options_action_select"
    selected_option_object = curr_modal_state_values[action_select_block_id][
        "utilities_action_select_value"
    ]
    selected_utility_callback_id = selected_option_object["selected_option"]["value"]
    curr_action_config = c.UTILS_CONFIG[selected_utility_callback_id]

    debug_mode_enabled = (
        len(
            curr_modal_state_values["general_options_action_select"]["debug_mode"][
                "selected_options"
            ]
        )
        > 0
    )
    debug_block_id = "debug_conversation_id_input"
    debug_action_id = "debug_conversation_id_value"
    try:
        debug_conversation_id = curr_modal_state_values[debug_block_id][
            debug_action_id
        ]["selected_conversation"]
    except KeyError:
        # TODO: this works, but better UX would be to somehow track the previous option and bring it back
        debug_conversation_id = ""

    errors = {}
    if curr_action_config.get("needs_user_token"):
        # warning is shown to user on load; this prevents them from saving a bad config
        try:
            user_token = os.environ["SLACK_USER_TOKEN"]
            client = slack_sdk.WebClient(token=user_token)
            kwargs = {"query": "a", "count": 1}
            resp = client.search_messages(**kwargs)
        except KeyError:
            errors[
                "search_query_input"
            ] = f"Need a valid SLACK_USER_TOKEN secret for {c.UTILS_ACTION_LABELS[selected_utility_callback_id]}."
        except slack_sdk.errors.SlackApiError as e:
            logger.error(e.response)
            errmsg = f"Slack Error: Need a valid user token. {e.response['error']}"
            errors[action_select_block_id] = errmsg

    inputs = {
        "selected_utility": {"value": selected_utility_callback_id},
        "debug_mode_enabled": {"value": utils.bool_to_str(debug_mode_enabled)},
        "debug_conversation_id": {"value": debug_conversation_id},
    }
    inputs, input_errors = utils.parse_values_from_input_config(
        client, curr_modal_state_values, inputs, curr_action_config
    )
    errors.update(input_errors)

    if errors:
        ack(response_action="errors", errors=errors)
    else:
        ack()
        if curr_action_config.get("has_dynamic_outputs"):
            outputs = utils.dynamic_outputs(selected_utility_callback_id, inputs)
        else:
            outputs = curr_action_config["outputs"]
        kwargs = {"inputs": inputs, "outputs": outputs}
        if curr_action_config.get("step_image_url"):
            kwargs["step_image_url"] = curr_action_config["step_image_url"]
        if curr_action_config.get("step_name"):
            # No size limit, it just pushes it off the screen. Newline supported as well.
            debug_label = f"(DEBUG) " if debug_mode_enabled else ""
            kwargs["step_name"] = f"{debug_label}{curr_action_config['step_name']}"
        update(**kwargs)


def execute_utils(
    step: dict,
    body: dict,
    complete: Complete,
    fail: Fail,
    client: slack_sdk.WebClient,
    context: BoltContext,
    logger: logging.Logger,
):
    global DEBUG_STEP_DATA_CACHE

    try:
        should_send_complete_signal = True
        inputs = step["inputs"]
        event = body["event"]
        already_sent_debug_message = step.get("already_sent_debug_message", False)
        chosen_action = inputs["selected_utility"]["value"]
        # TODO: instead of this, leave the input - but add something to step so we can check if this is new run
        debug_mode = utils.get_input_val(inputs, "debug_mode_enabled", False)
        debug_conversation_id = utils.get_input_val(
            inputs, "debug_conversation_id", None
        )

        if debug_mode and debug_conversation_id and not already_sent_debug_message:
            try:
                execution_id = step["workflow_step_execute_id"]
                fallback_text = f"Debug (Inputs): {c.UTILS_ACTION_LABELS[chosen_action]}.\n```{pprint.pformat(step, indent=2)}```"
                blocks = [
                    {
                        "type": "section",
                        "text": {"type": "mrkdwn", "text": fallback_text},
                    },
                    {
                        "type": "actions",
                        "elements": [
                            {
                                "type": "button",
                                "text": {
                                    "type": "plain_text",
                                    "text": "Continue",
                                    "emoji": True,
                                },
                                "value": f"{execution_id}",
                                "style": "primary",
                                "action_id": "debug-continue",
                            },
                            {
                                "type": "button",
                                "text": {
                                    "type": "plain_text",
                                    "text": "Stop",
                                    "emoji": True,
                                },
                                "value": f"{execution_id}",
                                "action_id": "debug-stop",
                                "style": "danger",
                            },
                        ],
                    },
                    {"type": "divider"},
                    {
                        "type": "context",
                        "elements": [
                            {"type": "mrkdwn", "text": f"execution_id: {execution_id}."}
                        ],
                    },
                ]
                resp = client.chat_postMessage(
                    channel=debug_conversation_id, text=fallback_text, blocks=blocks
                )
                logger.info(resp)
                DEBUG_STEP_DATA_CACHE[execution_id] = {"step": step, "body": body}
                logger.debug(f"DEBUG_STEPCACHE: {DEBUG_STEP_DATA_CACHE}")
                return
            except slack_sdk.errors.SlackApiError as e:
                logger.error(
                    f"Debug Error: unable to send message with context. Continuing, so as to not block execution. {e.response['error']}."
                )

        outputs = {}

        logging.info(f"Chosen action: {chosen_action}")
        if chosen_action == "webhook":
            outputs = buddy.run_webhook(step)
        elif chosen_action == "random_int":
            outputs = buddy.run_random_int(step)
        elif chosen_action == "random_uuid":
            outputs = buddy.run_random_uuid(step)
        elif chosen_action == "random_member_picker":
            outputs = buddy.run_random_member_picker(step, client, logger)
        elif chosen_action == "set_channel_topic":
            outputs = buddy.run_set_channel_topic(step, client, logger)
        elif chosen_action == "manual_complete":
            should_send_complete_signal = False
            buddy.run_manual_complete(step, body, event, client, logger)
        elif chosen_action == "wait_for_webhook":
            should_send_complete_signal = False
            buddy.run_wait_for_webhook(step, event)
        elif chosen_action == "json_extractor":
            outputs = buddy.run_json_extractor(step)
        elif chosen_action == "get_email_from_slack_user":
            outputs = buddy.run_get_email_from_slack_user(step, client, logger)
        elif chosen_action == "add_reaction":
            outputs = buddy.run_add_reaction(step, client, logger)
        elif chosen_action == "find_message":
            outputs = buddy.run_find_message(step, logger, context)
        elif chosen_action == "wait_state":
            outputs = buddy.run_wait_state(step)
        elif chosen_action == "conversations_create":
            outputs = buddy.run_conversations_create(inputs, client)
        elif chosen_action == "find_user_by_email":
            outputs = buddy.run_find_user_by_email(inputs, client)
        elif chosen_action == "schedule_message":
            outputs = buddy.run_schedule_message(inputs, client)
        else:
            fail(error={"message": f"Unknown action chosen - {chosen_action}"})
    except buddy.errors.WorkflowStepFailError as e:
        fail(error={"message": e.errmsg})
    except Exception as e:
        # catch everything, otherwise our failures lead to orphaned 'In progress'
        logger.exception(e)
        exc_message = f"|## Want help? Check the community discussion (https://github.com/happybara-io/WorkflowBuddy/discussions), or reach out to support@happybara.io ##| Your error info --> Server error: {type(e).__name__}|{e}|{''.join(tb.format_exception(None, e, e.__traceback__))}"
        fail(error={"message": exc_message})

    if debug_mode and debug_conversation_id:
        # finish debug mode by sending `outputs` to the same location
        try:
            execution_id = step["workflow_step_execute_id"]
            fallback_text = f"Debug (Outputs): {c.UTILS_ACTION_LABELS[chosen_action]}.\n```{pprint.pformat(outputs, indent=2)}```"
            blocks = [
                {"type": "section", "text": {"type": "mrkdwn", "text": fallback_text}},
                {"type": "divider"},
                {
                    "type": "context",
                    "elements": [
                        {"type": "mrkdwn", "text": f"execution_id: {execution_id}."}
                    ],
                },
            ]
            resp = client.chat_postMessage(
                channel=debug_conversation_id, text=fallback_text, blocks=blocks
            )
        except slack_sdk.errors.SlackApiError as e:
            logger.error(
                f"Debug Error: unable to send message with context. Continuing, so as to not block execution. {e.response['error']}."
            )

    if should_send_complete_signal:
        complete(outputs=outputs)


def edit_webhook(ack: Ack, step: dict, configure: Configure):
    ack()
    existing_inputs = copy.deepcopy(step["inputs"])
    blocks = copy.deepcopy(c.WEBHOOK_STEP_MODAL_COMMON_BLOCKS)
    chosen_config_item = c.UTILS_CONFIG["webhook"]
    blocks.append(
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"{chosen_config_item.get('description')}",
            },
        }
    )
    # have to make sure we aren't accidentally editing config blocks in memory
    blocks.extend(copy.deepcopy(chosen_config_item["modal_input_blocks"]))
    utils.update_blocks_with_previous_input_based_on_config(
        blocks, "webhook", existing_inputs, chosen_config_item
    )
    configure(blocks=blocks)


def save_webhook(
    ack: Ack,
    view: View,
    update: Update,
    logger: logging.Logger,
    client: slack_sdk.WebClient,
):
    values = view["state"]["values"]
    selected_utility_callback_id = "webhook"
    curr_action_config = c.UTILS_CONFIG[selected_utility_callback_id]

    inputs = {}
    inputs, errors = utils.parse_values_from_input_config(
        client, values, inputs, curr_action_config
    )
    if errors:
        ack(response_action="errors", errors=errors)
    else:
        ack()
        logger.debug(f"INPUTS: {inputs}")
        outputs = curr_action_config["outputs"]

        kwargs = {"inputs": inputs, "outputs": outputs}
        if curr_action_config.get("step_image_url"):
            kwargs["step_image_url"] = curr_action_config["step_image_url"]
        if curr_action_config.get("step_name"):
            # No size limit, it just pushes it off the screen. Newline supported as well.
            kwargs["step_name"] = curr_action_config["step_name"]
        update(**kwargs)


def execute_webhook(
    step: dict,
    complete: Complete,
    fail: Fail,
    logger: logging.Logger,
):
    # TODO: add debug mode here as well
    try:
        outputs = buddy.run_webhook(step)
        complete(outputs=outputs)
    except Exception as e:
        # catch everything, otherwise our failures lead to orphaned 'In progress'
        logger.exception(e)
        exc_message = f"Server error: {type(e).__name__}|{e}|{''.join(tb.format_exception(None, e, e.__traceback__))}"
        fail(error={"message": exc_message})


###########################
# Instantiate all Steps visible to users
############################
utils_ws = WorkflowStep(
    callback_id=c.WORKFLOW_STEP_UTILS_CALLBACK_ID,
    edit=edit_utils,
    save=save_utils,
    execute=execute_utils,
)
slack_app.step(utils_ws)

webhook_ws = WorkflowStep(
    callback_id=c.WORKFLOW_STEP_WEBHOOK_CALLBACK_ID,
    edit=edit_webhook,
    save=save_webhook,
    execute=execute_webhook,
)
slack_app.step(webhook_ws)

###########################
# Flask app stuff
############################
flask_app = Flask(__name__)
handler = SlackRequestHandler(slack_app)


@flask_app.route("/", methods=["GET"])
def home():
    return """
<h2>Simple Homepage</h2>
<hr />
<br />
<h4>Endpoints</h4>
<ul>
    <li>Health: /health</li>
    <li>Events: /slack/events</li>
    <li>Interactivity: /slack/events</li>
    <li>Webhooks: /webhook</li>
    <li>Finish Execution: /workflow/finish-execution</li>
</ul>
"""


@flask_app.route("/health", methods=["GET"])
def health():
    return jsonify({"ok": True}), 201


@flask_app.route("/slack/events", methods=["POST"])
def slack_events():
    return handler.handle(request)


@flask_app.route("/slack/install", methods=["GET"])
def install():
    return handler.handle(request)


@flask_app.route("/slack/oauth_redirect", methods=["GET"])
def oauth_redirect():
    return handler.handle(request)


@flask_app.route("/webhook", methods=["POST"])
def inbound_webhook():
    d = request.data
    logging.info(f"#### RECEIVED ###: {d}")
    return jsonify({"ok": True}), 201


@flask_app.route("/workflow/finish-execution", methods=["POST"])
def finish_step_execution():
    json_body = request.json
    status_code, resp_body = utils.finish_step_execution_from_webhook(json_body)
    return jsonify(resp_body), status_code
