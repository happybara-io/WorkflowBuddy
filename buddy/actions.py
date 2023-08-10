import contextlib
import logging
import re
import copy
import pprint

import slack_sdk
from slack_bolt import App, Ack, BoltContext, Respond
from slack_bolt.workflows.step import Complete, Configure, Fail, Update, WorkflowStep

import buddy.constants as c
import buddy.utils as utils
import buddy.db as db
import buddy.step_actions as step_actions
from buddy.workflow_steps import execute_utils

mlogger = logging.getLogger(__name__)


def register(slack_app: App):
    slack_app.action("scheduled_message_delete_clicked")(
        listener_delete_scheduled_message
    )
    slack_app.action("action_manage_scheduled_messages")(
        listener_manage_scheduled_messages
    )
    slack_app.action("action_manual_complete")(listener_manual_complete_button_clicked)
    slack_app.action(re.compile("(manual_complete-continue|manual_complete-stop)"))(
        listener_manual_complete_continue_or_stop
    )
    slack_app.action("event_delete_clicked")(listener_delete_event_mapping)
    slack_app.action("action_update_fail_notify_channels")(
        dispatch_action_update_fail_notify_channels
    )
    slack_app.action("action_add_webhook")(listener_add_button_clicked)
    slack_app.action(re.compile("(utilities_action_select_value|debug_mode)"))(
        listener_utils_update_step_modal
    )
    slack_app.action(re.compile("(debug-continue|debug-stop)"))(
        listener_debug_button_clicked
    )


######################
# Listeners Funcs
######################


def listener_delete_scheduled_message(
    ack: Ack, body: dict, logger: logging.Logger, client: slack_sdk.WebClient
):
    ack()
    payload = body["actions"][0]
    channel_id, scheduled_message_id = payload["value"].split("-")
    logger.info(f"SCHEDULED_MESSAGE_CLICKED - {channel_id}:{scheduled_message_id}")
    # rate-limiting: tier 3, 50+ per minute per workspace - should be fine.
    # resp = client.chat_deleteScheduledMessage(
    #     channel=channel_id, scheduled_message_id=scheduled_message_id
    # )
    resp = {"ok": False}

    # TODO: temp
    if resp["ok"]:
        sm_modal = build_scheduled_message_modal(client)
    else:
        sm_modal = build_scheduled_message_modal(
            client, delete_failed_id=scheduled_message_id
        )

    resp = client.views_update(
        view_id=body["view"]["id"], hash=body["view"]["hash"], view=sm_modal
    )
    logger.debug(resp)


def listener_manage_scheduled_messages(
    ack: Ack, body: dict, logger: logging.Logger, client: slack_sdk.WebClient
):
    ack()
    sm_modal = build_scheduled_message_modal(client)
    client.views_open(trigger_id=body["trigger_id"], view=sm_modal)


def listener_manual_complete_button_clicked(
    ack: Ack, body: dict, logger: logging.Logger, client: slack_sdk.WebClient
):
    ack()
    mc_modal = build_manual_complete_modal(client)
    client.views_open(trigger_id=body["trigger_id"], view=mc_modal)


def listener_manual_complete_continue_or_stop(
    ack: Ack,
    body: dict,
    logger: logging.Logger,
    client: slack_sdk.WebClient,
    respond: Respond,
    context: BoltContext,
):
    ack()
    replacement_text, updated_blocks = step_actions.manual_complete_continue_or_stop(
        body, logger, client, context
    )
    respond(replace_original=True, text=replacement_text, blocks=updated_blocks)


def listener_delete_event_mapping(
    ack: Ack,
    body: dict,
    logger: logging.Logger,
    client: slack_sdk.WebClient,
    context: BoltContext,
):
    ack()
    user_id = body["user"]["id"]
    payload = body["actions"][0]
    value = payload["value"]
    _, ec_id = value.split("EventConfig-")
    logger.info(f"EVENT_DELETE_CLICKED - {value}")
    db.remove_event_configs(ids=[ec_id])
    utils.update_app_home(
        client, user_id, context.team_id, enterprise_id=context.enterprise_id
    )


def dispatch_action_update_fail_notify_channels(
    ack: Ack, body: dict, client: slack_sdk.WebClient, context: BoltContext
):
    step_actions.dispatch_action_update_fail_notify_channels(ack, body, client, context)


def listener_add_button_clicked(
    ack: Ack, body: dict, client: slack_sdk.WebClient, context: BoltContext
):
    ack()
    add_webhook_modal = utils.build_add_webhook_modal()
    client.views_open(trigger_id=body["trigger_id"], view=add_webhook_modal)


# TODO: this seems like it would be a good thing to just have natively in Bolt.
# Lots of people want to update their Step view.
def listener_utils_update_step_modal(
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
    logger.debug(resp)


def listener_debug_button_clicked(
    ack: Ack,
    body: dict,
    logger: logging.Logger,
    client: slack_sdk.WebClient,
    respond: Respond,
    context: BoltContext,
):
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
        # TODO: could consider notifying of "failure" here like in other workflow execution spots, but that just
        # seems annoying.
    else:
        cache_data = db.get_debug_data_from_cache(workflow_step_execute_id)
        step = cache_data["step"]
        orig_execute_body = cache_data["body"]
        logger.debug(
            f"execution_id:{workflow_step_execute_id}|step:{step}|orig_body:{orig_execute_body}.===="
        )

        replacement_text = f"👉Debug step continued for `{workflow_step_execute_id}`.\n```{pprint.pformat(step, indent=2)}```"
        respond(replace_original=True, text=replacement_text)
        db.delete_debug_data_from_cache(workflow_step_execute_id)

        complete = Complete(client=client, body=execution_body)

        step["already_sent_debug_message"] = True
        execute_utils(step, orig_execute_body, complete, fail, client, context, logger)


######################
# Non-Listeners
######################


def build_scheduled_message_modal(
    client: slack_sdk.WebClient, delete_failed_id: str = None
) -> dict:
    """
    param delete_failed_id: since Slack doesn't provide an Ack errors mechanism like for view submissions,
        I'm making my own.
    """
    # https://api.slack.com/methods/chat.scheduledMessages.list
    # TODO: error handling
    resp = client.chat_scheduledMessages_list()
    blocks = []
    if resp["ok"]:
        # TODO: add stuff for pagination? etc? Average user will have <10 I'd bet,
        # so fine to leave off for now.
        messages_list = resp["scheduled_messages"]
        num_messages = len(messages_list)
        blocks = [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"{num_messages} messages scheduled to be sent from this bot.",
                },
            },
            {"type": "divider"},
        ]
        if num_messages < 1:
            blocks.append(
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"🤷 Nothing scheduled currently.",
                    },
                }
            )
        for i, sm in enumerate(messages_list):
            text = sm["text"]
            visual_id = i + 1
            failed = delete_failed_id == sm["id"]
            ts = sm["post_at"]
            formatted_date = utils.slack_format_date(ts)
            blocks.append(
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*{'❌' if failed else ''}{visual_id}.* *To:* <#{sm['channel_id']}> *At:* `{formatted_date}`\n*Text:*\n```{text[:100]}{'...' if len(text) > 100 else ''}```\n_id:{sm['id']}_",
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
            if failed:
                blocks.append(
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"*☹️ Deleting message {visual_id} failed - try again in a couple minutes.*\n\n",
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

    blocks.extend(
        [
            {"type": "divider"},
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": "Not seeing all X-hundred of your scheduled messages? Reach out the the dev team of Workflow Buddy with your use case if you need to see more.",
                    }
                ],
            },
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


# test build_scheduled_message_modal function
def test_build_scheduled_message_modal():
    sm_modal = build_scheduled_message_modal()
    assert sm_modal


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
