import logging
import os
import copy

import slack_sdk
from slack_bolt import App, BoltContext, Ack
from slack_sdk.models.views import View
from slack_bolt.workflows.step import Complete, Configure, Fail, Update, WorkflowStep

import buddy.constants as c
import buddy.step_actions as step_actions
import buddy.utils as utils
import buddy.db as db

ENV = os.environ.get(c.ENV_ENV, "DEV")


def register(slack_app: App):
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


##########################
# Workflow Step (Utils)
##########################


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
    blocks = step_actions.edit_utils(step, context.user_token)
    configure(blocks=blocks)


def save_utils(
    ack: Ack,
    view: View,
    update: Update,
    logger: logging.Logger,
    client: slack_sdk.WebClient,
    context: BoltContext,
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
            client = slack_sdk.WebClient(token=context.user_token)
            kwargs = {"query": "a", "count": 1}
            resp = client.search_messages(**kwargs)
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
            label = ("(DEBUG) " if debug_mode_enabled else "") + (
                "(Dev) " if ENV.lower() != "prod" else ""
            )
            kwargs["step_name"] = f"{label}{curr_action_config['step_name']}"
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
                logger.debug(resp)
                db.save_debug_data_to_cache(execution_id, step, body)
                return
            except slack_sdk.errors.SlackApiError as e:
                logger.error(
                    f"Debug Error: unable to send message with context. Continuing, so as to not block execution. {e.response['error']}."
                )

        outputs = {}

        logger.info(f"Chosen action: {chosen_action}")
        # TODO: gotta add some actual team info to it
        db.save_execute_usage(chosen_action, context.team_id, step)
        if chosen_action == "webhook":
            outputs = step_actions.run_webhook(step)
        elif chosen_action == "random_int":
            outputs = step_actions.run_random_int(step)
        elif chosen_action == "random_uuid":
            outputs = step_actions.run_random_uuid(step)
        elif chosen_action == "random_member_picker":
            outputs = step_actions.run_random_member_picker(step, client, logger)
        elif chosen_action == "set_channel_topic":
            outputs = step_actions.run_set_channel_topic(step, client, logger)
        elif chosen_action == "manual_complete":
            should_send_complete_signal = False
            step_actions.run_manual_complete(step, body, event, client, logger)
        elif chosen_action == "wait_for_webhook":
            should_send_complete_signal = False
            step_actions.run_wait_for_webhook(step, event)
        elif chosen_action == "json_extractor":
            outputs = step_actions.run_json_extractor(step)
        elif chosen_action == "get_email_from_slack_user":
            outputs = step_actions.run_get_email_from_slack_user(step, client, logger)
        elif chosen_action == "add_reaction":
            outputs = step_actions.run_add_reaction(step, client, logger)
        elif chosen_action == "find_message":
            outputs = step_actions.run_find_message(step, logger, context)
        elif chosen_action == "wait_state":
            outputs = step_actions.run_wait_state(step)
        elif chosen_action == "conversations_create":
            outputs = step_actions.run_conversations_create(inputs, client)
        elif chosen_action == "find_user_by_email":
            outputs = step_actions.run_find_user_by_email(inputs, client)
        elif chosen_action == "schedule_message":
            outputs = step_actions.run_schedule_message(inputs, client)
        else:
            fail(error={"message": f"Unknown action chosen - {chosen_action}"})
    except step_actions.errors.WorkflowStepFailError as e:
        fail(error={"message": e.errmsg})
        should_send_complete_signal = False
        utils.send_step_failure_notifications(
            client,
            chosen_action,
            step,
            context.team_id,
            enterprise_id=context.enterprise_id,
        )
    except Exception as e:
        # catch everything, otherwise our failures lead to orphaned 'In progress'
        logger.exception(e)
        exc_message = f"|## Want help? Check the community discussion (https://github.com/happybara-io/WorkflowBuddy/discussions), or reach out to support@happybara.io ##| Your error info --> Server error: {type(e).__name__}|{e}|{''.join(tb.format_exception(None, e, e.__traceback__))}"
        fail(error={"message": exc_message})
        should_send_complete_signal = False
        utils.send_step_failure_notifications(
            client,
            chosen_action,
            step,
            context.team_id,
            enterprise_id=context.enterprise_id,
            short_err_msg=f"Server error: {type(e).__name__}|{e}|",
        )

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


##########################
# Workflow Step (Webhook)
##########################


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
    context: BoltContext,
):
    # TODO: add debug mode here as well
    try:
        db.save_execute_usage("webhook", context.team_id, step)
        outputs = step_actions.run_webhook(step)
        complete(outputs=outputs)
    except Exception as e:
        # catch everything, otherwise our failures lead to orphaned 'In progress'
        logger.exception(e)
        exc_message = f"Server error: {type(e).__name__}|{e}|{''.join(tb.format_exception(None, e, e.__traceback__))}"
        fail(error={"message": exc_message})
