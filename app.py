import logging
from multiprocessing.sharedctypes import Value
import random
from urllib import response
import uuid
import os
import constants as c
import utils
import json
import copy
from typing import Tuple
import re

logging.basicConfig(level=logging.DEBUG)

from slack_bolt import App, Ack
from slack_bolt.workflows.step import WorkflowStep, Configure, Complete, Fail, Update
from slack_bolt.adapter.flask import SlackRequestHandler
import slack_sdk
from slack_sdk.models.views import View

from flask import Flask, request, jsonify

slack_app = App()


@slack_app.middleware  # or app.use(log_request)
def log_request(logger: logging.Logger, body: dict, next):
    logger.debug(body)
    return next()


def update_blocks_with_previous_input_based_on_config(
    blocks: list, chosen_action, existing_inputs: dict, action_config_item: dict
) -> None:
    # kinda a crappy way to fill out existing inputs into initial values, but fast enough
    if existing_inputs:
        for input_name, value_obj in existing_inputs.items():
            prev_input_value = value_obj["value"]
            curr_input_config = action_config_item["inputs"].get(input_name)
            # loop through blocks to find it's home
            for block in blocks:
                if block.get("block_id") == "utilities_action_select":
                    block["elements"][0]["initial_option"] = {
                        "text": {
                            "type": "plain_text",
                            "text": c.UTILS_ACTION_LABELS[chosen_action],
                            "emoji": True,
                        },
                        "value": chosen_action,
                    }
                else:
                    if curr_input_config and (
                        block.get("block_id") == curr_input_config.get("block_id")
                    ):
                        # add initial placeholder info
                        if curr_input_config.get("type") == "conversations_select":
                            block["element"]["initial_conversation"] = prev_input_value
                        elif curr_input_config.get("type") == "channels_select":
                            block["element"]["initial_channel"] = prev_input_value
                        elif curr_input_config.get("type") == "users_select":
                            block["element"]["initial_user"] = prev_input_value
                        elif curr_input_config.get("type") == "checkboxes":
                            initial_options = json.loads(prev_input_value)
                            if len(initial_options) < 1:
                                try:
                                    del block["element"]["initial_options"]
                                except KeyError:
                                    pass
                            else:
                                block["element"]["initial_options"] = initial_options
                        else:
                            # assume plain_text_input cuz it's common
                            print('PROBLEM VALUE', prev_input_value)
                            block["element"]["initial_value"] = prev_input_value


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


def finish_an_execution(
    client: slack_sdk.WebClient, execution_id: str, failed=False, err_msg=""
) -> dict:
    if failed:
        resp = client.workflows_stepFailed(
            workflow_step_execute_id=execution_id, error={"message": err_msg}
        )
    else:
        # outputs = {}
        resp = client.workflows_stepCompleted(workflow_step_execute_id=execution_id)
    return resp


@slack_app.action("scheduled_message_delete_clicked")
def delete_scheduled_message(
    ack: Ack, body, logger: logging.Logger, client: slack_sdk.WebClient
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
        resp = finish_an_execution(
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
    except Exception:
        errors["json_config_input"] = "Invalid JSON."
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
    # Validate the inputs
    logger.info(f"submission: {event_type}|{name}|{webhook_url}")
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
        utils.db_add_webhook_to_event(event_type, name, webhook_url)
        msg = f"Your addition of {webhook_url} was successful."
    except Exception as e:
        logger.exception(e)
        msg = f"There was an error attempting to add {webhook_url}."
    try:
        client.chat_postMessage(channel=user_id, text=msg)
    except e:
        logger.exception(f"Failed to post a message {e}")

    utils.update_app_home(client, user_id)


# TODO: accept any of the keyword args that are allowed?
def generic_event_proxy(logger: logging.Logger, event: dict, body: dict) -> None:
    event_type = event.get("type")
    logger.info(f"||{event_type}|BODY:{body}")
    try:
        workflow_webhooks_to_request = utils.db_get_event_config(event_type)
    except KeyError:
        raise
        # TODO: handle errors gracefully

    for webhook in workflow_webhooks_to_request:
        json_body = event
        resp = utils.send_webhook(webhook["webhook_url"], json_body)
        if resp.status_code >= 300:
            logger.error(f"{resp.status_code}:{resp.text}|{webhook}")
    logger.info("Finished sending all webhooks for event")


@slack_app.event(c.EVENT_APP_MENTION)
def event_app_mention(logger: logging.Logger, event: dict, body: dict):
    generic_event_proxy(logger, event, body)


@slack_app.event(c.EVENT_CHANNEL_ARCHIVE)
def event_channel_archive(logger: logging.Logger, event: dict, body: dict):
    generic_event_proxy(logger, event, body)


@slack_app.event(c.EVENT_CHANNEL_CREATED)
def event_channel_created(logger: logging.Logger, event: dict, body: dict):
    generic_event_proxy(logger, event, body)


@slack_app.event(c.EVENT_CHANNEL_DELETED)
def event_channel_deleted(logger: logging.Logger, event: dict, body: dict):
    generic_event_proxy(logger, event, body)


@slack_app.event(c.EVENT_CHANNEL_UNARCHIVE)
def event_channel_unarchive(logger: logging.Logger, event: dict, body: dict):
    generic_event_proxy(logger, event, body)


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


def edit_utils(ack: Ack, step: dict, configure: Configure):
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
    blocks.append(
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"{chosen_config_item.get('description')}",
            },
        }
    )
    blocks.extend(chosen_config_item["modal_input_blocks"])
    update_blocks_with_previous_input_based_on_config(
        blocks, chosen_action, existing_inputs, chosen_config_item
    )
    configure(blocks=blocks)


# TODO: this seems like it would be a good thing to just have natively in Bolt.
# Lots of people want to update their Step view.
@slack_app.action("utilities_action_select_value")
def utils_update_step_modal(
    ack: Ack, body: dict, logger: logging.Logger, client: slack_sdk.WebClient
):
    ack()
    logger.info(f"ACTION_CHANGE: {body}")
    selected_action = body["actions"][0]["selected_option"]["value"]
    updated_blocks = copy.deepcopy(c.UTILS_STEP_MODAL_COMMON_BLOCKS)
    updated_blocks.append(
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"{c.UTILS_CONFIG[selected_action].get('description')}",
            },
        }
    )
    updated_blocks.extend(c.UTILS_CONFIG[selected_action]["modal_input_blocks"])
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
    values = view["state"]["values"]
    selected_option_object = values["utilities_action_select"][
        "utilities_action_select_value"
    ]
    selected_utility_callback_id = selected_option_object["selected_option"]["value"]
    curr_action_config = c.UTILS_CONFIG[selected_utility_callback_id]

    inputs = {
        "selected_utility": {"value": selected_utility_callback_id},
    }
    inputs, errors = parse_values_from_input_config(
        client, values, inputs, curr_action_config
    )
    if errors:
        ack(response_action="errors", errors=errors)
    else:
        ack()
        outputs = curr_action_config["outputs"]
        kwargs = {"inputs": inputs, "outputs": outputs}
        if curr_action_config.get("step_image_url"):
            kwargs["step_image_url"] = curr_action_config["step_image_url"]
        if curr_action_config.get("step_name"):
            # No size limit, it just pushes it off the screen. Newline supported as well.
            kwargs["step_name"] = curr_action_config["step_name"]
        update(**kwargs)


def run_webhook(step: dict, complete: Complete, fail: Fail) -> None:
    # TODO: input validation & error handling
    inputs = step["inputs"]
    url = inputs["webhook_url"]["value"]
    bool_flags = {"fail_on_http_error": False}
    request_json_str = inputs.get("request_json_str", {}).get("value", {}) or "{}"
    logging.info(f"sending to url:{url}")
    body = {}
    try:
        selected_checkboxes = json.loads(inputs.get("bool_flags", {}).get("value", []))
        for box_item in selected_checkboxes:
            flag_name = box_item["value"]
            bool_flags[flag_name] = True

        body = json.loads(request_json_str)
    except json.JSONDecodeError:
        fail(
            error={
                "message": f"Unable to parse JSON when attempting to send webhook to {url}."
            }
        )
        return

    resp = utils.send_webhook(url, body)

    if bool_flags["fail_on_http_error"] and resp.status_code > 300:
        # TODO: is there a limit to error message string size?
        fail(
            error={
                "message": f"fail_on_http_error:true|code:{resp.status_code}|{resp.text[:100]}"
            }
        )
    else:
        # TODO: is there a limit to output variable string size?
        outputs = {
            "webhook_status_code": str(resp.status_code),
            "webhook_response_text": f"{resp.text}",
        }
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


def run_manual_complete(
    step: dict, event: dict, client: slack_sdk.WebClient, logger: logging.Logger
) -> None:
    # https://api.slack.com/methods/chat.postMessage
    # https://api.slack.com/events/workflow_step_execute
    inputs = step["inputs"]
    # TODO: by providing a conversation ID, rather than restricting to something else, it brings up possibility Bot isn't in the channel.
    # Need to rectify during configuration step for good UX.
    conversation_id = inputs["conversation_id"]["value"]
    execution_id = event["workflow_step"]["workflow_step_execute_id"]

    # TODO: this message needs to provide context on the workflow it's connected to, otherwise it's just a random ID
    # TODO: this could be nice as 2 buttons rather than an ID, one for Complete/one for Fail, pops a modal and asks for failure reason then kills it.
    fallback_text = f"WorkflowBuddy dropping off your execution ID:\n`{execution_id}`.\nUse this to manually complete the workflow once tasks have been completed to your satisfaction."
    blocks = [{"type": "section", "text": {"type": "mrkdwn", "text": fallback_text}}]
    resp = client.chat_postMessage(
        channel=conversation_id, text=fallback_text, blocks=blocks
    )
    logger.info(resp)
    # Don't even think about calling fail/complete!
    pass


def execute_utils(
    step: dict,
    event: dict,
    complete: Complete,
    fail: Fail,
    client: slack_sdk.WebClient,
    logger: logging.Logger,
):
    try:
        inputs = step["inputs"]
        chosen_action = inputs["selected_utility"]["value"]
        logging.info(f"Chosen action: {chosen_action}")
        if chosen_action == "webhook":
            run_webhook(step, complete, fail)
        elif chosen_action == "random_int":
            run_random_int(step, complete, fail)
        elif chosen_action == "random_uuid":
            run_random_uuid(step, complete, fail)
        elif chosen_action == "manual_complete":
            run_manual_complete(step, event, client, logger)
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
        exc_message = f"Server error: {type(e).__name__}|{e}"
        fail(error={"message": exc_message})


def edit_webhook(ack: Ack, step: dict, configure: Configure):
    ack()
    existing_inputs = step["inputs"]
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
    blocks.extend(chosen_config_item["modal_input_blocks"])
    update_blocks_with_previous_input_based_on_config(
        blocks, "webhook", existing_inputs, chosen_config_item
    )
    configure(blocks=blocks)


def parse_values_from_input_config(
    client, values: dict, inputs: dict, curr_action_config: dict
) -> Tuple[dict, dict]:
    inputs = inputs
    errors = {}

    for name, input_config in curr_action_config["inputs"].items():
        block_id = input_config["block_id"]
        action_id = input_config["action_id"]
        if input_config.get("type") == "channels_select":
            value = values[block_id][action_id]["selected_channel"]
        elif input_config.get("type") == "conversations_select":
            value = values[block_id][action_id]["selected_conversation"]
        elif input_config.get("type") == "checkboxes":
            value = json.dumps(values[block_id][action_id]["selected_options"])
        else:
            # plain-text input by default
            value = values[block_id][action_id]["value"]

        validation_type = input_config.get("validation_type")
        if validation_type == "json" and value:
            try:
                json.loads(value)
            except Exception:
                errors[block_id] = "Invalid JSON."
        elif validation_type == "integer":
            try:
                int(value)
            except ValueError:
                errors[block_id] = f"Must be a valid integer."
        elif validation_type == "url":
            if not utils.is_valid_url(value):
                errors[block_id] = f"Must be a valid URL with `http(s)://.`"
        elif validation_type == "slack_channel_name":
            if not utils.is_valid_slack_channel_name(value):
                errors[
                    block_id
                ] = "Channel names may only contain lowercase letters, numbers, hyphens, underscores and be max 80 chars."
        elif validation_type == "able_to_post":
            status = utils.test_if_bot_able_to_post_to_conversation(value, client)
            if status == "not_in_channel":
                errors[
                    block_id
                ] = f"Bot needs to be invited to conversation before it can post."
        inputs[name] = {"value": value}

    return inputs, errors


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
    inputs, errors = parse_values_from_input_config(
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
    event: dict,
    complete: Complete,
    fail: Fail,
    client: slack_sdk.WebClient,
    logger: logging.Logger,
):
    try:
        run_webhook(step, complete, fail)
    except Exception as e:
        # catch everything, otherwise our failures lead to orphaned 'In progress'
        logger.exception(e)
        exc_message = f"Server error: {type(e).__name__}|{e}"
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


@flask_app.route("/slack/events", methods=["POST"])
def slack_events():
    return handler.handle(request)


@flask_app.route("/webhook", methods=["POST"])
def inbound_webhook():
    d = request.data
    logging.info(f"#### RECEIVED ###: {d}")
    return jsonify({"ok": True}), 201
