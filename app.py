import logging
import random
import uuid
import os
import constants as c
import utils

logging.basicConfig(level=logging.DEBUG)

from slack_bolt import App
from slack_bolt.workflows.step import WorkflowStep
from slack_bolt.adapter.flask import SlackRequestHandler

from flask import Flask, request

app = App()


###########################
# Slack app stuff
############################
@app.middleware  # or app.use(log_request)
def log_request(logger, body, next):
    logger.debug(body)
    return next()


# TODO: accept any of the keyword args that are allowed?
def generic_event_proxy(logger, event, body):
    event_type = event.get("type")
    logger.info(f"||{event_type}|BODY:{body}")
    # workflows_to_webhook = c.EVENT_WORKFLOW_MAP[event_type]

    TEMP_CONFIG_MAP = {
        "app_mention": [{"webhook_url": os.getenv("EVENT_APP_MENTION_WEBHOOK_URL")}]
    }
    try:
        workflows_to_webhook = TEMP_CONFIG_MAP[event_type]
    except KeyError:
        raise
        # TODO: handle errors gracefully

    for workflow in workflows_to_webhook:
        json_body = event
        resp = utils.send_webhook(workflow["webhook_url"], json_body)
        if resp.status_code >= 300:
            logger.error(f"{resp.status_code}:{resp.text}|{workflow}")
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
                        }
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
    # EXAMPLE
    # 'state': {
    #     'values': {
    #         'utilities_action_select': {
    #             'utilities_action_select_value': {
    #                 'type': 'static_select',
    #                 'selected_option': {
    #                     'text': {
    #                         'type': 'plain_text',
    #                         'text': 'Send a Webhook',
    #                         'emoji': True
    #                     },
    #                         'value': 'webhook'
    #                     }
    #             }
    #         },
    #         'webhook_url_input': {
    #             'webhook_url_value': {
    #                 'type': 'plain_text_input',
    #                 'value': 'https://webhook.site/ece98740-9f9c-404a-9780-f55692bce841'}
    #         }
    #     }
    # },

    ack()

    inputs = {
        "selected_utility": {"value": selected_utility_callback_id},
    }
    for input_config in curr_action_config["inputs"].values():
        block_id = input_config["block_id"]
        action_id = input_config["action_id"]
        input_config["name"] = {"value": values[block_id][action_id]["value"]}

    print(f"INPUTS: {inputs}")
    outputs = curr_action_config["outputs"]
    update(inputs=inputs, outputs=outputs)


def run_webhook(step, complete, fail):
    # TODO: input validation & error handling
    inputs = step["inputs"]

    # TODO: hardcoded reach into
    url = inputs["webhook_url"]["value"]
    print("sending to url:", url)
    json_body = {"abc": "123"}
    resp = utils.send_webhook(url, json_body)

    outputs = {"webhook_status_code": str(resp.status_code)}
    complete(outputs=outputs)


def run_random_int(step, complete, fail):
    # TODO: input validation & error handling
    inputs = step["inputs"]
    lower_bound = inputs["lower_bound"]["value"]
    upper_bound = inputs["upper_bound"]["value"]

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
        # TODO: draft
        run_random_int(step, complete, fail)
    elif chosen_action == "random_uuid":
        # TODO: draft
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
                        }
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
        },
        {
            "type": "input",
            "block_id": "user_email_input",
            "element": {"type": "plain_text_input", "action_id": "user_email_value"},
            "label": {"type": "plain_text", "text": "User Email", "emoji": True},
        },
    ]
    configure(blocks=blocks)


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
    print("CURR_ACTION_CONFIG", selected_utility_callback_id, curr_action_config)
    for input_config in curr_action_config["inputs"].values():
        block_id = input_config["block_id"]
        action_id = input_config["action_id"]
        inputs[input_config["name"]] = {"value": values[block_id][action_id]["value"]}

    print(f"INPUTS: {inputs}")
    outputs = curr_action_config["outputs"]
    update(inputs=inputs, outputs=outputs)


def execute_slack_utils(step, complete, fail, client):
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
            fail(error={"message": f"Slack err: {resp.get('error')}"})
    elif chosen_action == "find_user_by_email":
        user_email = inputs["user_email"]["value"]
        resp = client.users_lookupByEmail(email=user_email)
        if resp["ok"]:
            outputs = {"user_id": resp["user"]["id"]}
            complete(outputs=outputs)
        else:
            fail(error={"message": f"Slack err: {resp.get('error')}"})
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


@flask_app.route("/slack/events", methods=["POST"])
def slack_events():
    return handler.handle(request)


@flask_app.route("/webhook", methods=["POST"])
def inbound_webhook():
    print("#### RECEIVED ###", request.json)
