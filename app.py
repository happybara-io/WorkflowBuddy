import logging
import random
from urllib import response
import uuid
import os
import constants as c
import utils
import json
import copy

logging.basicConfig(level=logging.DEBUG)

from slack_bolt import App, Ack
from slack_bolt.workflows.step import WorkflowStep
from slack_bolt.adapter.flask import SlackRequestHandler
import slack_sdk
from slack_sdk.models.views import View

from flask import Flask, request, jsonify

app = App()

###########################
# Slack app stuff
############################
@app.middleware  # or app.use(log_request)
def log_request(logger: logging.Logger, body, next):
    logger.debug(body)
    return next()


def build_scheduled_message_modal(client: slack_sdk.WebClient):
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
        {
			"type": "context",
			"elements": [
				{
					"type": "mrkdwn",
					"text": "_Backticks ` have been replaced with ' only for display._"
				}
			]
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
            # backticks were screwing up mine, escaping doesn't seem to work tho
            safe_text = text.replace('`', "'")
            blocks.append(
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*To:* <#{sm['channel_id']}> *At:* `{sm['post_at']}` *Text:*\n`{safe_text[:100]}{'...' if len(safe_text) > 100 else ''}`",
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


@app.action("scheduled_message_delete_clicked")
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
        # update modal
        sm_modal = build_scheduled_message_modal(client)
        resp = client.views_update(
            view_id=body["view"]["id"], hash=body["view"]["hash"], view=sm_modal
        )
        logger.info(resp)


@app.action("action_manage_scheduled_messages")
def manage_scheduled_messages(
    ack: Ack, body, logger: logging.Logger, client: slack_sdk.WebClient
):
    ack()
    sm_modal = build_scheduled_message_modal(client)
    client.views_open(trigger_id=body["trigger_id"], view=sm_modal)


@app.action("action_export")
def export_button_clicked(
    ack: Ack, body, logger: logging.Logger, client: slack_sdk.WebClient
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


@app.action("action_import")
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


@app.view("import_submission")
def import_config_submission(
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
        # Handle error
        msg = "There was an error with your submission"

    # Message the user
    try:
        client.chat_postMessage(channel=user_id, text=msg)
    except e:
        logger.exception(f"Failed to post a message {e}")

    utils.update_app_home(client, user_id)


@app.action("event_delete_clicked")
def delete_event_mapping(
    ack: Ack, body, logger: logging.Logger, client: slack_sdk.WebClient
):
    ack()
    user_id = body["user"]["id"]
    payload = body["actions"][0]
    event_type = payload["value"]
    logger.info(f"EVENT_DELETE_CLICKED - {event_type}")
    utils.db_remove_event(event_type)
    utils.update_app_home(client, user_id)


@app.action("action_add_webhook")
def add_button_clicked(ack: Ack, body, client: slack_sdk.WebClient):
    ack()

    add_webhook_form_blocks = [
        {
            "type": "input",
            "block_id": "event_type_input",
            "element": {"type": "plain_text_input", "action_id": "event_type_value"},
            "label": {"type": "plain_text", "text": "Event Type", "emoji": True},
        },
        {
            "type": "input",
            "block_id": "name_input",
            "element": {"type": "plain_text_input", "action_id": "name_value"},
            "label": {"type": "plain_text", "text": "Name", "emoji": True},
        },
        {
            "type": "input",
            "block_id": "webhook_url_input",
            "element": {"type": "plain_text_input", "action_id": "webhook_url_value"},
            "label": {"type": "plain_text", "text": "Webhook URL", "emoji": True},
        },
    ]

    add_webhook_modal = {
        "type": "modal",
        "callback_id": "webhook_form_submission",
        "title": {"type": "plain_text", "text": "Add Webhook"},
        "submit": {"type": "plain_text", "text": "Add"},
        "blocks": add_webhook_form_blocks,
    }
    client.views_open(trigger_id=body["trigger_id"], view=add_webhook_modal)


@app.view("webhook_form_submission")
def handle_webhook_submission(
    ack: Ack, body, client: slack_sdk.WebClient, view: View, logger: logging.Logger
):
    values = view["state"]["values"]
    user_id = body["user"]["id"]
    event_type = values["event_type_input"]["event_type_value"]["value"]
    name = values["name_input"]["name_value"]["value"]
    webhook_url = values["webhook_url_input"]["webhook_url_value"]["value"]
    # Validate the inputs
    logger.info(f"submission: {event_type}|{name}|{webhook_url}")
    errors = {}
    if (event_type is not None and webhook_url is not None) and webhook_url[
        :8
    ] != "https://":
        block_id = "webhook_url_input"
        errors[block_id] = "Must be a valid URL with `https://`"
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
def generic_event_proxy(logger: logging.Logger, event, body):
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


@app.event(c.EVENT_APP_MENTION)
def event_app_mention(logger: logging.Logger, event, body):
    generic_event_proxy(logger, event, body)


@app.event(c.EVENT_CHANNEL_CREATED)
def event_channel_created(logger: logging.Logger, event, body):
    generic_event_proxy(logger, event, body)


@app.event(c.EVENT_WORKFLOW_PUBLISHED)
def handle_workflow_published_events(body, logger: logging.Logger):
    logger.info(body)


@app.event(c.EVENT_APP_HOME_OPENED)
def update_app_home(event, logger: logging.Logger, client: slack_sdk.WebClient):
    app_home_view = utils.build_app_home_view()
    client.views_publish(user_id=event["user"], view=app_home_view)


@app.event("message")
def handle_message():
    pass


def edit(ack: Ack, step: WorkflowStep, configure):
    ack()

    blocks = [
        {
            "type": "input",
            "block_id": "task_name_input",
            "element": {
                "type": "plain_text_input",
                "action_id": "name",
                "placeholder": {"type": "plain_text", "text": "Add a task name"},
            },
            "label": {"type": "plain_text", "text": "Task name"},
        },
        {
            "type": "input",
            "block_id": "task_description_input",
            "element": {
                "type": "plain_text_input",
                "action_id": "description",
                "placeholder": {"type": "plain_text", "text": "Add a task description"},
            },
            "label": {"type": "plain_text", "text": "Task description"},
        },
    ]
    configure(blocks=blocks)


def save(ack: Ack, view, update):
    ack()

    values = view["state"]["values"]
    task_name = values["task_name_input"]["name"]
    task_description = values["task_description_input"]["description"]

    inputs = {
        "task_name": {"value": task_name["value"]},
        "task_description": {"value": task_description["value"]},
    }
    outputs = [
        {
            "type": "text",
            "name": "task_name",
            "label": "Task name",
        },
        {
            "type": "text",
            "name": "task_description",
            "label": "Task description",
        },
    ]
    update(inputs=inputs, outputs=outputs)


def execute(step: WorkflowStep, complete, fail):
    inputs = step["inputs"]
    # if everything was successful
    # outputs = {
    #     "task_name": inputs["task_name"]["value"],
    #     "task_description": inputs["task_description"]["value"],
    # }
    # complete(outputs=outputs)

    # if something went wrong
    error = {"message": "Just testing step failure!"}
    fail(error=error)


# Create a new WorkflowStep instance
ws = WorkflowStep(
    callback_id="demo",
    edit=edit,
    save=save,
    execute=execute,
)
# Pass Step to set up listeners
app.step(ws)

###########################
# Utilities (non-Slack helper tools)
############################
def edit_utils(ack: Ack, step: WorkflowStep, configure):
    # TODO: if I want to update modal, need to listen for the action/event separately
    ack()
    blocks = copy.deepcopy(c.UTILS_STEP_MODAL_COMMON_BLOCKS)
    DEFAULT_ACTION = "webhook"
    blocks.append(
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"{c.UTILS_CONFIG[DEFAULT_ACTION].get('description')}",
            },
        }
    )
    blocks.extend(c.UTILS_CONFIG[DEFAULT_ACTION]["modal_input_blocks"])
    configure(blocks=blocks)


# TODO: this seems like it would be a good thing to just have natively in Bolt.
# Lots of people want to update their Step view.
@app.action("utilities_action_select_value")
def utils_update_step_modal(
    ack: Ack, body, logger: logging.Logger, client: slack_sdk.WebClient
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


def save_utils(ack: Ack, view, update, logger: logging.Logger):
    logger.debug("view", view)
    values = view["state"]["values"]
    # include this in every event as context
    selected_option_object = values["utilities_action_select"][
        "utilities_action_select_value"
    ]
    selected_utility_callback_id = selected_option_object["selected_option"]["value"]
    curr_action_config = c.UTILS_CONFIG[selected_utility_callback_id]
    ack()

    inputs = {
        "selected_utility": {"value": selected_utility_callback_id},
    }
    for name, input_config in curr_action_config["inputs"].items():
        block_id = input_config["block_id"]
        action_id = input_config["action_id"]
        inputs[name] = {"value": values[block_id][action_id]["value"]}

    logger.debug(f"INPUTS: {inputs}")
    outputs = curr_action_config["outputs"]
    update(inputs=inputs, outputs=outputs)


def run_webhook(step: WorkflowStep, complete, fail):
    # TODO: input validation & error handling
    inputs = step["inputs"]
    url = inputs["webhook_url"]["value"]
    logging.info(f"sending to url:{url}")
    json_body = {"abc": "123"}
    resp = utils.send_webhook(url, json_body)

    outputs = {"webhook_status_code": str(resp.status_code)}
    complete(outputs=outputs)


def run_random_int(step: WorkflowStep, complete, fail):
    # TODO: input validation & error handling
    inputs = step["inputs"]
    lower_bound = int(inputs["lower_bound"]["value"])
    upper_bound = int(inputs["upper_bound"]["value"])

    rand_value = random.randint(lower_bound, upper_bound)
    outputs = {"random_int_text": str(rand_value)}
    complete(outputs=outputs)


def run_random_uuid(step: WorkflowStep, complete, fail):
    # TODO: input validation & error handling
    outputs = {"random_uuid": str(uuid.uuid4())}
    complete(outputs=outputs)


def execute_utils(step: WorkflowStep, complete, fail):
    chosen_action = step["inputs"]["selected_utility"]["value"]
    logging.info(f"Chosen action: {chosen_action}")
    if chosen_action == "webhook":
        run_webhook(step, complete, fail)
    elif chosen_action == "random_int":
        run_random_int(step, complete, fail)
    elif chosen_action == "random_uuid":
        run_random_uuid(step, complete, fail)
    else:
        fail()


utils_ws = WorkflowStep(
    callback_id=c.WORKFLOW_STEP_UTILS_CALLBACK_ID,
    edit=edit_utils,
    save=save_utils,
    execute=execute_utils,
)
app.step(utils_ws)

###########################
# Slack Utilities (give Workflow Builder access to more Slack APIs)
############################
def edit_slack_utils(ack: Ack, step: WorkflowStep, configure):
    ack()
    blocks = copy.deepcopy(c.SLACK_STEP_MODAL_COMMON_BLOCKS)
    DEFAULT_ACTION = "find_user_by_email"
    blocks.append(
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"{c.SLACK_UTILS_CONFIG[DEFAULT_ACTION].get('description')}",
            },
        }
    )
    blocks.extend(c.SLACK_UTILS_CONFIG[DEFAULT_ACTION]["modal_input_blocks"])
    configure(blocks=blocks)


# TODO: this seems like it would be a good thing to just have natively in Bolt.
# Lots of people want to update their Step view.
@app.action("slack_utilities_action_select_value")
def slack_utils_update_step_modal(
    ack: Ack, body, logger: logging.Logger, client: slack_sdk.WebClient
):
    ack()
    logger.info(f"SLACK_ACTION_CHANGE: {body}")
    selected_action = body["actions"][0]["selected_option"]["value"]
    updated_blocks = copy.deepcopy(c.SLACK_STEP_MODAL_COMMON_BLOCKS)
    updated_blocks.append(
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"{c.SLACK_UTILS_CONFIG[selected_action].get('description')}",
            },
        }
    )
    updated_blocks.extend(c.SLACK_UTILS_CONFIG[selected_action]["modal_input_blocks"])
    updated_view = {
        "type": "workflow_step",
        "callback_id": c.WORKFLOW_STEP_SLACK_UTILS_CALLBACK_ID,
        "blocks": updated_blocks,
    }
    resp = client.views_update(
        view_id=body["view"]["id"], hash=body["view"]["hash"], view=updated_view
    )
    logger.info(resp)


# TODO: this is exactly the same as the other utils func with tiny change, why am i duplicating?
def save_slack_utils(ack: Ack, view, update, logger: logging.Logger):
    values = view["state"]["values"]
    # include this in every event as context
    selected_option_object = values["slack_utilities_action_select"][
        "slack_utilities_action_select_value"
    ]
    selected_utility_callback_id = selected_option_object["selected_option"]["value"]
    curr_action_config = c.SLACK_UTILS_CONFIG[selected_utility_callback_id]
    ack()
    inputs = {
        "selected_utility": {"value": selected_utility_callback_id},
    }

    for name, input_config in curr_action_config["inputs"].items():
        block_id = input_config["block_id"]
        action_id = input_config["action_id"]
        if input_config.get("type") == "channels_select":
            print("VALUES", values)
            value = values[block_id][action_id]["selected_channel"]
        else:
            value = values[block_id][action_id]["value"]
        inputs[name] = {"value": value}

    outputs = curr_action_config["outputs"]
    update(inputs=inputs, outputs=outputs)


def execute_slack_utils(
    step: WorkflowStep, complete, fail, client, logger: logging.Logger
):
    # TODO: make sure to log the execution event so it can be killed manually if needed
    inputs = step["inputs"]
    chosen_action = step["inputs"]["selected_utility"]["value"]
    logger.info(f"Chosen action: {chosen_action}")

    if chosen_action == "conversations_create":
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
        resp = client.chat_scheduleMessage(channel=channel, post_at=post_at, text=text)
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
        fail(error={"message": f"Unknown Slack action chosen - {chosen_action}"})


slack_utils_ws = WorkflowStep(
    callback_id=c.WORKFLOW_STEP_SLACK_UTILS_CALLBACK_ID,
    edit=edit_slack_utils,
    save=save_slack_utils,
    execute=execute_slack_utils,
)
app.step(slack_utils_ws)

###########################
# Flask app stuff
############################
flask_app = Flask(__name__)
handler = SlackRequestHandler(app)


@flask_app.route("/", methods=["GET"])
def home():
    return """
<h2>Simple App Home</h2>
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
    logging.info(f"#### RECEIVED ###: {request.json}")
