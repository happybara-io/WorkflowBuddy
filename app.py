import logging
import random
from urllib import response
import uuid
import os
import constants as c
import utils
import json

logging.basicConfig(level=logging.DEBUG)

from slack_bolt import App
from slack_bolt.workflows.step import WorkflowStep
from slack_bolt.adapter.flask import SlackRequestHandler

from flask import Flask, request, jsonify

try:
    # test shelf on load, ran into file permission errors in Docker container
    print('TEST_SHELVE', utils.db_get_event_config('test_key'))
except KeyError:
    pass

app = App()

###########################
# Slack app stuff
############################
@app.middleware  # or app.use(log_request)
def log_request(logger, body, next):
    logger.debug(body)
    return next()


@app.action("action_export")
def export_button_clicked(ack, body, logger, client):
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
def import_button_clicked(ack, body, logger, client):
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
def import_config_submission(ack, body, client, view, logger):
    values = view["state"]["values"]
    user = body["user"]["id"]
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
        client.chat_postMessage(channel=user, text=msg)
    except e:
        logger.exception(f"Failed to post a message {e}")


@app.action("event_delete_clicked")
def delete_event_mapping(ack, body, logger, client):
    ack()
    user_id = body["user"]["id"]
    payload = body["actions"][0]
    event_type = payload["value"]
    logger.info(f"EVENT_DELETE_CLICKED - {event_type}")
    utils.db_remove_event(event_type)

    app_home_view = utils.build_app_home_view()
    client.views_publish(user_id=user_id, view=app_home_view)


@app.action("action_add_webhook")
def add_button_clicked(ack, body, client):
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
def handle_webhook_submission(ack, body, client, view, logger):
    values = view["state"]["values"]
    user = body["user"]["id"]
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
        client.chat_postMessage(channel=user, text=msg)
    except e:
        logger.exception(f"Failed to post a message {e}")


# TODO: accept any of the keyword args that are allowed?
def generic_event_proxy(logger, event, body):
    event_type = event.get("type")
    logger.info(f"||{event_type}|BODY:{body}")
    # TEMP_CONFIG_MAP = {
    #     "app_mention": [{"webhook_url": os.getenv("EVENT_APP_MENTION_WEBHOOK_URL")}]
    # }
    try:
        workflow_webhooks_to_request = utils.db_get_event_config(event_type)
    except KeyError:
        raise
        # TODO: handle errors gracefully

    for webhook in workflow_webhooks_to_request:
        json_body = event
        resp = utils.send_webhook(webhook['webhook_url'], json_body)
        if resp.status_code >= 300:
            logger.error(f"{resp.status_code}:{resp.text}|{webhook}")
    logger.info("Finished sending all webhooks for event")


@app.event(c.EVENT_APP_MENTION)
def event_app_mention(logger, event, body):
    generic_event_proxy(logger, event, body)


@app.event(c.EVENT_CHANNEL_CREATED)
def event_channel_created(logger, event, body):
    generic_event_proxy(logger, event, body)


@app.event(c.EVENT_WORKFLOW_PUBLISHED)
def handle_workflow_published_events(body, logger):
    logger.info(body)


@app.event(c.EVENT_APP_HOME_OPENED)
def update_app_home(event, logger, client):
    app_home_view = utils.build_app_home_view()
    client.views_publish(user_id=event["user"], view=app_home_view)


@app.event("message")
def handle_message():
    pass


def edit(ack, step, configure):
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


def save(ack, view, update):
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


def execute(step, complete, fail):
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
def edit_utils(ack, step, configure):
    # TODO: if I want to update modal, need to listen for the action/event separately
    print("utils: edit")
    ack()
    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": "Choose Your Action Utility",
                "emoji": True,
            },
        },
        {
            "type": "actions",
            "block_id": "utilities_action_select",
            "elements": [
                {
                    "type": "static_select",
                    "placeholder": {
                        "type": "plain_text",
                        "text": "Select an item",
                        "emoji": True,
                    },
                    "initial_option": {
                        "text": {
                            "type": "plain_text",
                            "text": "Send a Webhook",
                            "emoji": True,
                        },
                        "value": "webhook",
                    },
                    "options": [
                        {
                            "text": {
                                "type": "plain_text",
                                "text": "Send a Webhook",
                                "emoji": True,
                            },
                            "value": "webhook",
                        },
                        {
                            "text": {
                                "type": "plain_text",
                                "text": "Random Integer",
                                "emoji": True,
                            },
                            "value": "random_int",
                        },
                        {
                            "text": {
                                "type": "plain_text",
                                "text": "Random UUID",
                                "emoji": True,
                            },
                            "value": "random_uuid",
                        },
                    ],
                    "action_id": "utilities_action_select_value",
                }
            ],
        },
        {
            "type": "input",
            "block_id": "webhook_url_input",
            "element": {"type": "plain_text_input", "action_id": "webhook_url_value"},
            "label": {"type": "plain_text", "text": "Webhook URL", "emoji": True},
            "optional": True,
        },
        {
            "type": "input",
            "block_id": "lower_bound_input",
            "element": {"type": "plain_text_input", "action_id": "lower_bound_value"},
            "label": {"type": "plain_text", "text": "Lower Bound", "emoji": True},
            "optional": True,
        },
        {
            "type": "input",
            "block_id": "upper_bound_input",
            "element": {"type": "plain_text_input", "action_id": "upper_bound_value"},
            "label": {"type": "plain_text", "text": "Upper Bound", "emoji": True},
            "optional": True,
        },
    ]
    configure(blocks=blocks)


def save_utils(ack, view, update):
    print("utils: save")
    print("view", view)
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
    for input_config in curr_action_config["inputs"].values():
        block_id = input_config["block_id"]
        action_id = input_config["action_id"]
        inputs[input_config["name"]] = {"value": values[block_id][action_id]["value"]}

    print(f"INPUTS: {inputs}")
    outputs = curr_action_config["outputs"]
    update(inputs=inputs, outputs=outputs)


def run_webhook(step, complete, fail):
    # TODO: input validation & error handling
    inputs = step["inputs"]
    url = inputs["webhook_url"]["value"]
    print("sending to url:", url)
    json_body = {"abc": "123"}
    resp = utils.send_webhook(url, json_body)

    outputs = {"webhook_status_code": str(resp.status_code)}
    complete(outputs=outputs)


def run_random_int(step, complete, fail):
    # TODO: input validation & error handling
    inputs = step["inputs"]
    lower_bound = int(inputs["lower_bound"]["value"])
    upper_bound = int(inputs["upper_bound"]["value"])

    rand_value = random.randint(lower_bound, upper_bound)
    outputs = {"random_int_text": str(rand_value)}
    complete(outputs=outputs)


def run_random_uuid(step, complete, fail):
    # TODO: input validation & error handling
    outputs = {"random_uuid": str(uuid.uuid4())}
    complete(outputs=outputs)


def execute_utils(step, complete, fail):
    print("utils: execute")
    chosen_action = step["inputs"]["selected_utility"]["value"]
    if chosen_action == "webhook":
        run_webhook(step, complete, fail)
    elif chosen_action == "random_int":
        run_random_int(step, complete, fail)
    elif chosen_action == "random_uuid":
        run_random_uuid(step, complete, fail)
    else:
        fail()


utils_ws = WorkflowStep(
    callback_id="utilities",
    edit=edit_utils,
    save=save_utils,
    execute=execute_utils,
)
app.step(utils_ws)

###########################
# Slack Utilities (give Workflow Builder access to more Slack APIs)
############################
def edit_slack_utils(ack, step, configure):
    print("slack_utils: edit")
    ack()
    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": "Choose Your Slack Action",
                "emoji": True,
            },
        },
        {
            "type": "actions",
            "block_id": "slack_utilities_action_select",
            "elements": [
                {
                    "type": "static_select",
                    "placeholder": {
                        "type": "plain_text",
                        "text": "Select an item",
                        "emoji": True,
                    },
                    "initial_option": {
                        "text": {
                            "type": "plain_text",
                            "text": "Channels Create",
                            "emoji": True,
                        },
                        "value": "conversations_create",
                    },
                    "options": [
                        {
                            "text": {
                                "type": "plain_text",
                                "text": "Channels Create",
                                "emoji": True,
                            },
                            "value": "conversations_create",
                        },
                        {
                            "text": {
                                "type": "plain_text",
                                "text": "Find user by email",
                                "emoji": True,
                            },
                            "value": "find_user_by_email",
                        },
                    ],
                    "action_id": "slack_utilities_action_select_value",
                }
            ],
        },
        {
            "type": "input",
            "block_id": "channel_name_input",
            "element": {"type": "plain_text_input", "action_id": "channel_name_value"},
            "label": {"type": "plain_text", "text": "Channel Name", "emoji": True},
            "optional": True,
        },
        {
            "type": "input",
            "block_id": "user_email_input",
            "element": {"type": "plain_text_input", "action_id": "user_email_value"},
            "label": {"type": "plain_text", "text": "User Email", "emoji": True},
            "optional": True,
        },
    ]
    configure(blocks=blocks)


@app.action("slack_utilities_action_select_value")
def handle_some_action(ack, body, logger, client):
    ack()
    logger.info(f"SLACK_ACTION_CHANGE: {body}")

    updated_view = {
        "type": "modal",
        "callback_id": "view_1",
        "title": {"type": "plain_text", "text": "Updated modal"},
        "blocks": [
            {
                "type": "section",
                "text": {"type": "plain_text", "text": "You updated the modal!"},
            },
            {
                "type": "image",
                "image_url": "https://media.giphy.com/media/SVZGEcYt7brkFUyU90/giphy.gif",
                "alt_text": "Yay! The modal was updated",
            },
        ],
    }
    resp = client.views_update(
        view_id=body["view"]["id"], hash=body["view"]["hash"], view=updated_view
    )


# TODO: this is exactly the same as the other utils func with tiny change, why am i duplicating?
def save_slack_utils(ack, view, update):
    print("slack utils: save")
    print("view", view)
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

    for input_config in curr_action_config["inputs"].values():
        block_id = input_config["block_id"]
        action_id = input_config["action_id"]
        inputs[input_config["name"]] = {"value": values[block_id][action_id]["value"]}

    outputs = curr_action_config["outputs"]
    update(inputs=inputs, outputs=outputs)


def execute_slack_utils(step, complete, fail, client, logger):
    # TODO: make sure to log the execution event so it can be killed manually if needed
    print("slack utils: execute")
    inputs = step["inputs"]
    chosen_action = step["inputs"]["selected_utility"]["value"]
    if chosen_action == "conversations_create":
        channel_name = inputs["channel_name"]["value"]
        resp = client.conversations_create(name=channel_name)
        print(f"RESP|{resp}")
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
    else:
        fail(error={"message": f"Unknown Slack action chosen - {chosen_action}"})

    outputs = {}
    complete(outputs=outputs)


slack_utils_ws = WorkflowStep(
    callback_id="slack_utils",
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
    return jsonify({
        "ok": True
    }), 201


@flask_app.route("/slack/events", methods=["POST"])
def slack_events():
    return handler.handle(request)


@flask_app.route("/webhook", methods=["POST"])
def inbound_webhook():
    print("#### RECEIVED ###", request.json)
