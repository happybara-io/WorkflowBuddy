import json

import logging
import slack_sdk
from slack_bolt import App, Ack, BoltContext
from slack_sdk.models.views import View

import buddy.utils as utils
import buddy.db as db

mlogger = logging.getLogger(__name__)


def register(slack_app: App):
    slack_app.view("manual_complete_submission")(
        listener_manual_complete_view_submission
    )
    slack_app.view("webhook_form_submission")(handle_event_config_submission)


def listener_manual_complete_view_submission(
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
    except Exception as e:
        logger.exception(f"Failed to send confirmation message {e}")


def handle_event_config_submission(
    ack: Ack,
    body: dict,
    client: slack_sdk.WebClient,
    view: View,
    logger: logging.Logger,
    context: BoltContext,
):
    # TODO: add more robust error handling
    # TODO: add support for 'raw_event' and 'filter_channel'
    errors = {}
    try:
        values = view["state"]["values"]
        user_id = body["user"]["id"]
        event_type = values["event_type_input"]["event_type_value"]["value"]
        desc = values["desc_input"]["desc_value"]["value"]
        webhook_url = values["webhook_url_input"]["webhook_url_value"]["value"]
        filter_react = values["filter_reaction_input"]["filter_reaction_value"]["value"]
        # Validate the inputs
        logger.info(f"submission: {event_type}|{desc}|{webhook_url}|{filter_react}")
        if (
            event_type is not None and webhook_url is not None
        ) and not utils.is_valid_url(webhook_url):
            block_id = "webhook_url_input"
            errors[block_id] = "Must be a valid URL with `http(s)://.`"
    except Exception as e:
        errors[
            "filter_reaction_input"
        ] = f"💥 Sorry, but Buddy hit a server error. If you don't recognize the following failure, it's on us: {type(e).__name__}|{e}."
    if errors:
        ack(response_action="errors", errors=errors)
        return
    ack()

    msg = ""
    try:
        db.create_event_config(
            context.team_id,
            event_type,
            desc,
            webhook_url,
            user_id,
            filter_react=filter_react,
            enterprise_id=context.enterprise_id,
        )
        # msg = f"Your addition of {event_type}:{webhook_url} was successful."
    except Exception as e:
        logger.exception(e)
        msg = f"There was an error attempting to add {event_type}:{webhook_url}."
        try:
            client.chat_postMessage(channel=user_id, text=msg)
        except e:
            logger.exception(f"Failed to post a message {e}")

    utils.update_app_home(
        client, user_id, context.team_id, enterprise_id=context.enterprise_id
    )
