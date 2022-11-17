import logging
import time
import random
import uuid
import os
import constants as c
import utils
import string
import pprint
import json
import copy
from typing import Tuple
import re
from datetime import datetime, timedelta, timezone
import traceback as tb
from jsonpath_ng import jsonpath
from jsonpath_ng.ext import parse

logging.basicConfig(level=logging.DEBUG)

from slack_bolt import App, Ack, Respond
from slack_bolt.workflows.step import WorkflowStep, Configure, Complete, Fail, Update
from slack_bolt.adapter.flask import SlackRequestHandler
import slack_sdk
from slack_sdk.models.views import View


from flask import Flask, request, jsonify

slack_app = App()


# TODO: this only works if we have a single process, not good! Tech debt!
DEBUG_STEP_DATA_CACHE = {}


@slack_app.middleware  # or app.use(log_request)
def log_request(logger: logging.Logger, body: dict, next):
    logger.debug(body)
    return next()


def update_blocks_with_previous_input_based_on_config(
    blocks: list, chosen_action, existing_inputs: dict, action_config_item: dict
) -> None:
    # TODO: workflow builder keeps pulling old input on the step even when you are creating it totally new 🤔
    # kinda a crappy way to fill out existing inputs into initial values, but fast enough
    if existing_inputs:
        for input_name, value_obj in existing_inputs.items():
            prev_input_value = value_obj["value"]
            curr_input_config = action_config_item["inputs"].get(input_name)
            # loop through blocks to find it's home
            for block in blocks:
                block_id = block.get("block_id")
                if block_id == "general_options_action_select":
                    block["elements"][0]["initial_option"] = {
                        "text": {
                            "type": "plain_text",
                            "text": c.UTILS_ACTION_LABELS[chosen_action],
                            "emoji": True,
                        },
                        "value": chosen_action,
                    }

                    # checkboxes, just debug on it's own for now
                    if not utils.sbool(
                        existing_inputs.get("debug_mode_enabled", {}).get("value")
                    ):
                        print("BYE BYE")
                        try:
                            del block["elements"][1]["initial_options"]
                        except KeyError:
                            pass
                    else:
                        print("SETTING IT")
                        # TODO: this breaks as soon as we change anything in the constants for it
                        block["elements"][1]["initial_options"] = [
                            {
                                "text": {
                                    "type": "mrkdwn",
                                    "text": "🐛 *Debug Mode*",
                                    "verbatim": False,
                                },
                                "value": "debug_mode",
                                "description": {
                                    "type": "mrkdwn",
                                    "text": "_When enabled, Buddy will pause before each step starts, send a message, and wait for you to click `Continue`._",
                                    "verbatim": False,
                                },
                            }
                        ]
                elif block_id == "debug_conversation_id_input":
                    debug_conversation_id = existing_inputs.get(
                        "debug_conversation_id", {}
                    ).get("value")
                    block["element"]["initial_conversation"] = debug_conversation_id
                else:
                    element_key = "element"
                    if curr_input_config and (
                        block_id == curr_input_config.get("block_id")
                    ):
                        # add initial placeholder info
                        if curr_input_config.get("type") == "conversations_select":
                            block[element_key][
                                "initial_conversation"
                            ] = prev_input_value
                        elif curr_input_config.get("type") == "channels_select":
                            block[element_key]["initial_channel"] = prev_input_value
                        elif curr_input_config.get("type") == "static_select":
                            block[element_key]["initial_option"] = {
                                "text": {
                                    "type": "plain_text",
                                    "text": curr_input_config.get("label", {}).get(
                                        prev_input_value
                                    )
                                    or prev_input_value.upper(),
                                    "emoji": True,
                                },
                                "value": prev_input_value,
                            }
                        elif curr_input_config.get("type") == "users_select":
                            block[element_key]["initial_user"] = prev_input_value
                        elif curr_input_config.get("type") == "checkboxes":
                            initial_options = json.loads(prev_input_value)
                            if len(initial_options) < 1:
                                try:
                                    del block[element_key]["initial_options"]
                                except KeyError:
                                    pass
                            else:
                                block["element"]["initial_options"] = initial_options
                        else:
                            # assume plain_text_input cuz it's common
                            block["element"]["initial_value"] = prev_input_value or ""
    else:
        logging.debug(
            "No previous inputs to reload, anything you see is happening because of bad coding."
        )


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
        try:
            fail(error={"message": errmsg})
        except slack_sdk.errors.SlackApiError:
            pass
        replacement_text = f"🛑 Halted debug step for `{workflow_step_execute_id}`."
        respond(replace_original=True, text=replacement_text)
    else:
        cache_data = DEBUG_STEP_DATA_CACHE[workflow_step_execute_id]
        step = cache_data["step"]
        event = cache_data["event"]
        logger.debug(
            f"execution_id:{workflow_step_execute_id}|step:{step}|event:{event}.===="
        )

        replacement_text = f"👉Debug step continued for `{workflow_step_execute_id}`.\n```{pprint.pformat(step, indent=2)}```"
        respond(replace_original=True, text=replacement_text)
        del DEBUG_STEP_DATA_CACHE[workflow_step_execute_id]

        complete = Complete(client=client, body=execution_body)

        step["already_sent_debug_message"] = True
        execute_utils(step, event, complete, fail, client, logger)
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
    ack: Ack, body: dict, logger: logging.Logger, client: slack_sdk.WebClient
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
    ack: Ack, body, client: slack_sdk.WebClient, view: View, logger: logging.Logger
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
    ack: Ack, body: dict, logger: logging.Logger, client: slack_sdk.WebClient
):
    ack()
    user_id = body["user"]["id"]
    payload = body["actions"][0]
    event_type = payload["value"]
    logger.info(f"EVENT_DELETE_CLICKED - {event_type}")
    utils.db_remove_event(event_type)
    utils.update_app_home(client, user_id)


@slack_app.action("action_add_webhook")
def add_button_clicked(ack: Ack, body: dict, client: slack_sdk.WebClient):
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
def update_app_home(event: dict, logger: logging.Logger, client: slack_sdk.WebClient):
    app_home_view = utils.build_app_home_view()
    client.views_publish(user_id=event["user"], view=app_home_view)


def edit_utils(
    ack: Ack,
    step: dict,
    configure: Configure,
    client: slack_sdk.WebClient,
    logger: logging.Logger,
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
    blocks.extend(utils.dynamic_modal_top_blocks(chosen_action))
    # have to make sure we aren't accidentally editing config blocks in memory
    blocks.extend(copy.deepcopy(chosen_config_item["modal_input_blocks"]))
    update_blocks_with_previous_input_based_on_config(
        blocks, chosen_action, existing_inputs, chosen_config_item
    )
    configure(blocks=blocks)


# TODO: this seems like it would be a good thing to just have natively in Bolt.
# Lots of people want to update their Step view.
@slack_app.action(re.compile("(utilities_action_select_value|debug_mode)"))
def utils_update_step_modal(
    ack: Ack, body: dict, logger: logging.Logger, client: slack_sdk.WebClient
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

    updated_blocks.extend(utils.dynamic_modal_top_blocks(selected_buddy_action))
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
        except slack_sdk.errors.SlackAPIError as e:
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


def run_webhook(step: dict, complete: Complete, fail: Fail) -> None:
    # TODO: input validation & error handling
    inputs = step["inputs"]
    url = inputs["webhook_url"]["value"]
    bool_flags = {"fail_on_http_error": False}
    http_method = inputs["http_method"]["value"]
    request_json_str = inputs.get("request_json_str", {}).get("value", {}) or "{}"
    headers_json_str = inputs.get("headers_json_str", {}).get("value", {}) or "{}"
    query_params_json_str = (
        inputs.get("query_params_json_str", {}).get("value", {}) or "{}"
    )
    logging.info(f"sending to url:{url}")
    body = {}
    bool_flags_input = inputs.get("bool_flags", {})
    try:
        selected_checkboxes = json.loads(bool_flags_input.get("value", []))
        for box_item in selected_checkboxes:
            flag_name = box_item["value"]
            bool_flags[flag_name] = True
    except json.JSONDecodeError as e:
        full_err_msg = utils.pretty_json_error_msg(
            f"err111: Unable to parse JSON Flags when preparing to send webhook to {url}.",
            bool_flags_input,
            e,
        )
        logging.error(full_err_msg)
        fail(error={"message": full_err_msg})
        return

    try:
        body = utils.load_json_body_from_untrusted_input_str(request_json_str)
    except json.JSONDecodeError as e:
        # e.g. Expecting ':' delimiter: line 1 column 22 (char 21)
        full_err_msg = utils.pretty_json_error_msg(
            f"err112: Unable to parse JSON when preparing to send webhook to {url}.",
            request_json_str,
            e,
        )
        logging.error(full_err_msg)
        fail(error={"message": full_err_msg})
        return

    try:
        new_headers = utils.load_json_body_from_untrusted_input_str(headers_json_str)
    except json.JSONDecodeError as e:
        full_err_msg = utils.pretty_json_error_msg(
            f"err113: Unable to parse JSON Headers when preparing to send webhook to {url}.",
            headers_json_str,
            e,
        )
        logging.error(full_err_msg)
        fail(error={"message": full_err_msg})
        return

    try:
        query_params = utils.load_json_body_from_untrusted_input_str(
            query_params_json_str
        )
    except json.JSONDecodeError as e:
        full_err_msg = utils.pretty_json_error_msg(
            f"err114: Unable to parse JSON Query Params when preparing to send webhook to {url}.",
            query_params_json_str,
            e,
        )
        logging.error(full_err_msg)
        fail(error={"message": full_err_msg})
        return

    logging.debug(f"Method:{http_method}|Headers:{new_headers}|QP:{query_params}")
    resp = utils.send_webhook(
        url, body, method=http_method, params=query_params, headers=new_headers
    )

    if bool_flags["fail_on_http_error"] and resp.status_code > 300:
        fail(
            error={
                "message": f"fail_on_http_error:true|code:{resp.status_code}|{resp.text[:500]}"
            }
        )
    else:
        # TODO: is there a limit to output variable string size?
        sanitized_resp = utils.sanitize_webhook_response(resp.text)
        outputs = {
            "webhook_status_code": str(resp.status_code),
            "webhook_response_text": f"{sanitized_resp}",
        }
        logging.info(f"OUTPUTS: {outputs}")
        complete(outputs=outputs)


def run_random_int(step: dict, complete: Complete, fail: Fail) -> None:
    # TODO: input validation & error handling
    inputs = step["inputs"]
    lower_bound = int(inputs["lower_bound"]["value"])
    upper_bound = int(inputs["upper_bound"]["value"])

    rand_value = random.randint(lower_bound, upper_bound)
    outputs = {"random_int_text": str(rand_value)}
    complete(outputs=outputs)


def run_random_uuid(step: dict, complete: Complete, fail: Fail) -> None:
    outputs = {"random_uuid": str(uuid.uuid4())}
    complete(outputs=outputs)


def run_wait_state(step: dict, complete: Complete, fail: Fail) -> None:
    inputs = step["inputs"]
    lower_bound = 0
    upper_bound = c.WAIT_STATE_MAX_SECONDS
    try:
        wait_duration = int(inputs["seconds"]["value"])
        if wait_duration <= lower_bound or wait_duration > upper_bound:
            raise ValueError("Not in valid Workflow Buddy Wait Step range.")
    except ValueError:
        errmsg = f"err5467: seconds value is not in our valid range, given: {inputs['seconds']['value']} but must be in {lower_bound} - {upper_bound}."
        fail(error={"message": errmsg})

    start_ts = int(datetime.now(timezone.utc).timestamp())
    time.sleep(wait_duration)
    end_ts = int(datetime.now(timezone.utc).timestamp())
    outputs = {
        "wait_start_ts": start_ts,
        "wait_end_ts": end_ts,
        "waited_for": wait_duration,
    }
    complete(outputs=outputs)


def run_json_extractor(step: dict, complete: Complete, fail: Fail) -> None:
    inputs = step["inputs"]
    json_string = inputs["json_string"]["value"]
    jsonpath_expr_str = inputs["jsonpath_expr"]["value"]

    try:
        # TODO: do I need to do a safe load here for double quotes/etc? Hopefully it should be well-formed if it's coming here and not built by hand
        json_data = json.loads(json_string, strict=False)
    except json.JSONDecodeError as e:
        errmsg = utils.pretty_json_error_msg(
            "err2111: invalid JSON provided for JSONPATH parsing.", json_string, e
        )
        fail(error={"message": errmsg})
        return

    jsonpath_expr = parse(jsonpath_expr_str)
    results = jsonpath_expr.find(json_data)
    logging.debug(f"JSONPATH {jsonpath_expr_str}| RESULTS: {results}")
    matches = [match.value for match in results]
    if len(matches) == 1:
        matches = matches[0]
    outputs = {"extracted_matches": str(matches)}
    complete(outputs=outputs)


def run_random_member_picker(
    step: dict,
    complete: Complete,
    fail: Fail,
    client: slack_sdk.WebClient,
    logger: logging.Logger,
):
    inputs = step["inputs"]
    conversation_id = inputs["conversation_id"]["value"]
    number_of_users = int(inputs["number_of_users"]["value"])
    num_per_request = 200
    resp = client.conversations_members(channel=conversation_id, limit=num_per_request)

    if not resp["ok"]:
        logger.error(resp)
        errmsg = f"Slack Error: unable to get conversation members from Slack. {resp['error']}"
        fail(error={"message": errmsg})
    else:
        # When will Slack just natively filter from their side?
        # Save time by checking for bots after random selection, rather than cleaning whole list of people.
        members = resp["members"]

        try:
            sample_of_users = utils.sample_list_until_no_bots_are_found(
                client, members, number_of_users
            )
            outputs = {}
            for i, user_id in enumerate(sample_of_users):
                user_num = i + 1
                outputs.update(
                    {
                        f"selected_user_{user_num}": user_id,
                        f"selected_user_id_{user_num}": user_id,
                    }
                )
            complete(outputs=outputs)
        except ValueError:
            errmsg = f"Error: requested number of users {number_of_users} larger than members size {len(members)}."
            fail(error={"message": errmsg})


def run_manual_complete(
    step: dict,
    event: dict,
    fail: Fail,
    client: slack_sdk.WebClient,
    logger: logging.Logger,
) -> None:
    # https://api.slack.com/methods/chat.postMessage
    # https://api.slack.com/events/workflow_step_execute
    inputs = step["inputs"]
    conversation_id = inputs["conversation_id"]["value"]
    execution_id = event["workflow_step"]["workflow_step_execute_id"]

    # TODO: this message needs to provide context on the workflow it's connected to, otherwise it's just a random ID
    # TODO: this could be nice as 2 buttons rather than an ID, one for Complete/one for Fail, pops a modal and asks for failure reason then kills it.
    fallback_text = f"WorkflowBuddy dropping off your execution ID:\n`{execution_id}`.\nUse this to manually complete the workflow once tasks have been completed to your satisfaction."
    blocks = [{"type": "section", "text": {"type": "mrkdwn", "text": fallback_text}}]
    try:
        resp = client.chat_postMessage(
            channel=conversation_id, text=fallback_text, blocks=blocks
        )
        logger.info(resp)
    except slack_sdk.errors.SlackApiError as e:
        logger.error(e.response)
        errmsg = f"Slack Error: unable to send message with execution_id to conversation. {e.response['error']}."
        fail(error={"message": errmsg})
    # Don't even think about calling fail/complete!
    pass


def run_wait_for_webhook(
    step: dict, event: dict, fail: Fail, logger: logging.Logger
) -> None:
    inputs = step["inputs"]
    external_service_url = inputs["destination_url"]["value"]
    execution_id = event["workflow_step"]["workflow_step_execute_id"]

    simple_secret_key = "".join(
        random.choice(string.ascii_letters) for _ in range(c.WEBHOOK_SK_LENGTH)
    )
    body = {"execution_id": execution_id, "sk": simple_secret_key}
    utils.send_webhook(external_service_url, body)


def run_set_channel_topic(
    step: dict,
    complete: Complete,
    fail: Fail,
    client: slack_sdk.WebClient,
    logger: logging.Logger,
):
    inputs = step["inputs"]
    conversation_id = inputs["conversation_id"]["value"]
    topic_string = inputs["topic_string"]["value"]

    try:
        resp = client.conversations_setTopic(
            channel=conversation_id, topic=topic_string
        )
        complete(outputs={})
    except slack_sdk.errors.SlackApiError as e:
        logger.error(e.response)
        errmsg = f"Slack Error: unable to get conversation members from Slack. {e.response['error']}"
        fail(error={"message": errmsg})


def run_get_email_from_slack_user(
    step: dict,
    complete: Complete,
    fail: Fail,
    client: slack_sdk.WebClient,
    logger: logging.Logger,
):
    inputs = step["inputs"]
    # TODO: gotta be able to get this from text variable passed to me, or from Slack "user" type variable
    user_id = inputs["user_id"]["value"]
    # just in case they pass in user mention anyway
    user_id = user_id.replace("<@", "").replace(">", "")

    try:
        resp = client.users_info(user=user_id)
        email = resp["user"]["profile"]["email"]
        outputs = {"email": email}
        complete(outputs=outputs)
    except slack_sdk.errors.SlackApiError as e:
        logger.error(e.response)
        errmsg = f"Slack Error: unable to get email from user. {e.response['error']}"
        fail(error={"message": errmsg})


def run_add_reaction(
    step: dict,
    complete: Complete,
    fail: Fail,
    client: slack_sdk.WebClient,
    logger: logging.Logger,
):
    # From Slack's emoji reaction trigger we get a link to message which has channel id & ts
    # if they get TS from somewhere else - then what?
    inputs = step["inputs"]
    # TODO: permalink is useful for Slack triggered reaction events, but what about broader use cases?
    # channel_id = inputs["conversation_id"]["value"]
    # ts = inputs["message_ts"]["value"]
    permalink = inputs["permalink"][
        "value"
    ]  # "https://workspace.slack.com/archives/CP3S47DAB/p1669229063902429
    try:
        _, _, _, _, channel_id, p_ts = permalink.split("/")
    except ValueError:
        errmsg = f"Unable to parse permalink formatting. Permalink provided was: '{permalink}', but expected format is `https://workspace.slack.com/archives/CP3S47DAB/p1669229063902429`."
        fail(error={"message": errmsg})
        return

    ts = f"{p_ts.replace('p', '')[:10]}.{p_ts[11:]}"
    reaction = inputs["reaction"]["value"].replace(":", "")  # :boom:
    try:
        resp = client.reactions_add(channel=channel_id, timestamp=ts, name=reaction)
        complete(outputs={})
    except slack_sdk.errors.SlackApiError as e:
        if e.response["error"] == "already_reacted":
            complete(outputs={})
        else:
            logger.error(e.response)
            errmsg = f"Slack Error: unable to add reaction. {e.response['error']}"
            fail(error={"message": errmsg})


def run_find_message(
    step: dict,
    complete: Complete,
    fail: Fail,
    logger: logging.Logger,
):
    # https://api.slack.com/methods/search.messages
    inputs = step["inputs"]
    search_query = inputs["search_query"]["value"]
    sort = inputs["sort"]["value"]
    sort_dir = inputs["sort_dir"]["value"]
    delay_seconds = inputs["delay_seconds"]["value"]
    fail_if_empty_results = utils.sbool(inputs["fail_if_empty_results"]["value"])

    try:
        delay_seconds = int(inputs["delay_seconds"]["value"])
        lower_bound = 0
        upper_bound = c.WAIT_STATE_MAX_SECONDS
        if delay_seconds <= lower_bound or delay_seconds > upper_bound:
            raise ValueError("Not in valid Workflow Buddy Wait Step range.")
    except ValueError:
        errmsg = f"err5466: seconds value is not in our valid range, given: {inputs['delay_seconds']['value']} but must be in {lower_bound} - {upper_bound}."
        fail(error={"message": errmsg})

    # TODO: team_id is required attribute if using an org-token
    try:
        user_token = os.environ["SLACK_USER_TOKEN"]
        client = slack_sdk.WebClient(token=user_token)
    except KeyError:
        errmsg = "No SLACK_USER_TOKEN provided to Workflow Buddy - required for searching Slack messages."
        fail(error={"message": errmsg})
        return

    if delay_seconds > 0:
        seconds_needed_before_new_message_shows_in_search = delay_seconds
        time.sleep(seconds_needed_before_new_message_shows_in_search)

    kwargs = {"query": search_query, "count": 1, "sort": sort, "sort_dir": sort_dir}
    try:
        resp = client.search_messages(**kwargs)
        message = resp["messages"]["matches"][0]
        channel_id = message["channel"]["id"]
        outputs = {
            "channel": channel_id,
            "channel_id": channel_id,
            "message_ts": message["ts"],
            "permalink": message["permalink"],
            "message_text": message["text"],
            "user": message["user"],
            "user_id": message["user"],
        }
        complete(outputs=outputs)
    except IndexError:
        if fail_if_empty_results:
            errmsg = f"Search results came back empty for query: {search_query}."
            fail(error={"message": errmsg})
        else:
            complete(outputs={})
    except slack_sdk.errors.SlackApiError as e:
        logger.error(e.response)
        errmsg = f"Slack Error: failed to search messages. {e.response['error']}"
        fail(error={"message": errmsg})


def execute_utils(
    step: dict,
    event: dict,
    complete: Complete,
    fail: Fail,
    client: slack_sdk.WebClient,
    logger: logging.Logger,
):
    global DEBUG_STEP_DATA_CACHE

    inputs = step["inputs"]
    already_sent_debug_message = step.get("already_sent_debug_message", False)
    chosen_action = inputs["selected_utility"]["value"]
    # TODO: instead of this, leave the input - but add something to step so we can check if this is new run
    debug_mode = inputs.get("debug_mode_enabled", {"value": "false"})["value"] == "true"
    debug_conversation_id = inputs["debug_conversation_id"]["value"]

    if debug_mode and not already_sent_debug_message:
        try:
            execution_id = step["workflow_step_execute_id"]
            fallback_text = f"Debug Step: {c.UTILS_ACTION_LABELS[chosen_action]}.\n```{pprint.pformat(step, indent=2)}```"
            blocks = [
                {"type": "section", "text": {"type": "mrkdwn", "text": fallback_text}},
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
            DEBUG_STEP_DATA_CACHE[execution_id] = {"step": step, "event": event}
            logger.debug(f"DEBUG_STEPCACHE: {DEBUG_STEP_DATA_CACHE}")
            return
        except slack_sdk.errors.SlackApiError as e:
            logger.error(
                f"Debug Error: unable to send message with context. Continuing, so as to not block execution. {e.response['error']}."
            )

    # save as JSON in button metadata? then call this execute function with
    # some sort of marker so we know not to infinitely loop on debug
    try:
        logging.info(f"Chosen action: {chosen_action}")
        if chosen_action == "webhook":
            run_webhook(step, complete, fail)
        elif chosen_action == "random_int":
            run_random_int(step, complete, fail)
        elif chosen_action == "random_uuid":
            run_random_uuid(step, complete, fail)
        elif chosen_action == "random_member_picker":
            run_random_member_picker(step, complete, fail, client, logger)
        elif chosen_action == "set_channel_topic":
            run_set_channel_topic(step, complete, fail, client, logger)
        elif chosen_action == "manual_complete":
            run_manual_complete(step, event, fail, client, logger)
        elif chosen_action == "wait_for_webhook":
            run_wait_for_webhook(step, event, fail, logger)
        elif chosen_action == "json_extractor":
            run_json_extractor(step, complete, fail)
        elif chosen_action == "get_email_from_slack_user":
            run_get_email_from_slack_user(step, complete, fail, client, logger)
        elif chosen_action == "add_reaction":
            run_add_reaction(step, complete, fail, client, logger)
        elif chosen_action == "find_message":
            run_find_message(step, complete, fail, logger)
        elif chosen_action == "wait_state":
            run_wait_state(step, complete, fail)
        elif chosen_action == "conversations_create":
            channel_name = inputs["channel_name"]["value"]
            resp = client.conversations_create(name=channel_name)
            logger.debug(f"RESP|{resp}")
            if resp["ok"]:
                outputs = {
                    "channel_id": resp["channel"]["id"],
                    "channel_id_text": resp["channel"]["id"],
                }
                complete(outputs=outputs)
            else:
                errmsg = f"Slack err: {resp.get('error')}"
                logger.error(errmsg)
                fail(error={"message": errmsg})
        elif chosen_action == "find_user_by_email":
            user_email = inputs["user_email"]["value"]
            resp = client.users_lookupByEmail(email=user_email)
            if resp["ok"]:
                outputs = {
                    "user": resp["user"]["id"],
                    "user_id": resp["user"]["id"],
                    "team_id": resp["user"]["team_id"],
                    "real_name": resp["user"]["real_name"],
                }
                complete(outputs=outputs)
            else:
                errmsg = f"Slack err: {resp.get('error')}"
                logger.error(errmsg)
                fail(error={"message": errmsg})
        elif chosen_action == "schedule_message":
            channel = inputs["channel"]["value"]
            post_at = inputs["post_at"]["value"]  # unix epoch timestamp
            # TODO: needs to support the time format in Workflow Builder variables
            # -> Tuesday, September 27th 8:38:26 AM (at least in message display it's converted to user's TZ
            # will have to check how it's passed internally)
            text = inputs["msg_text"]["value"]
            resp = client.chat_scheduleMessage(
                channel=channel, post_at=post_at, text=text
            )
            if resp["ok"]:
                outputs = {
                    "scheduled_message_id": resp["scheduled_message_id"],
                }
                complete(outputs=outputs)
            else:
                errmsg = f"Slack err: {resp.get('error')}"
                logger.error(errmsg)
                fail(error={"message": errmsg})
        else:
            fail(error={"message": f"Unknown action chosen - {chosen_action}"})
    except Exception as e:
        # catch everything, otherwise our failures lead to orphaned 'In progress'
        logger.exception(e)
        exc_message = f"Server error: {type(e).__name__}|{e}|{''.join(tb.format_exception(None, e, e.__traceback__))}"
        fail(error={"message": exc_message})


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
    update_blocks_with_previous_input_based_on_config(
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

    # TODO: add debug mode here as well
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
    try:
        run_webhook(step, complete, fail)
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
    <li>Events: /slack/events</li>
    <li>Interactivity: /slack/events</li>
    <li>Webhooks: /webhook</li>
</ul>
"""


@flask_app.route("/health", methods=["GET"])
def health():
    return jsonify({"ok": True}), 201


# @flask_app.route("/sleep", methods=["POST"])
# def sleep():
#     duration = 60
#     for i in range(duration):
#         time.sleep(1)
#         print('sleep', i)
#     # time.sleep(duration)
#     return jsonify({"ok": True, "waited_seconds": duration}), 208


@flask_app.route("/slack/events", methods=["POST"])
def slack_events():
    return handler.handle(request)


@flask_app.route("/webhook", methods=["POST"])
def inbound_webhook():
    d = request.data
    logging.info(f"#### RECEIVED ###: {d}")
    return jsonify({"ok": True}), 201


@flask_app.route("/finish-execution", methods=["POST"])
def finish_step_execution():
    json_body = request.json
    status_code, resp_body = utils.finish_step_execution_from_webhook(json_body)
    return jsonify(resp_body), status_code
