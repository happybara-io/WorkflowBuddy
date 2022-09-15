import logging
import random
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


@app.event(c.EVENT_APP_MENTION)
def event_test(event, body, say, logger):
    logger.info(f'BODY:{body}')

    # TODO: this can be a generic function, since i'm just passing the event payload through to Workflow Builder
    # Nothing specific to any event happening here

    # workflows_to_webhook = c.EVENT_WORKFLOW_MAP[c.EVENT_APP_MENTION]
    workflows_to_webhook = [
        {'webhook_url': os.getenv('EVENT_APP_MENTION_WEBHOOK_URL')}
    ]
    for workflow in workflows_to_webhook:
        json_body = event
        json_body['custom'] = 'true'
        resp = utils.send_webhook(workflow["webhook_url"], json_body)

    logger.info('Finished sending all webhooks for event')

    say("What's up? + " + str(resp.status_code))

# @app.event(c.EVENT_CHANNEL_CREATED)
# def event_channel_created(event):
#     pass

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
        "task_description": {"value": task_description["value"]}
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
        }
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
    print('utils: edit')
    ack()
    blocks = [
        {
			"type": "header",
			"text": {
				"type": "plain_text",
				"text": "Choose Your Action Utility",
				"emoji": True
			}
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
						"emoji": True
					},
					"initial_option": {
						"text": {
							"type": "plain_text",
							"text": "Send a Webhook",
							"emoji": True
						},
						"value": "webhook"
					},
					"options": [
						{
							"text": {
								"type": "plain_text",
								"text": "Send a Webhook",
								"emoji": True
							},
							"value": "webhook"
						}
					],
					"action_id": "utilities_action_select_value"
				}
			]
		},
		{
			"type": "input",
            "block_id": "webhook_url_input",
			"element": {
				"type": "plain_text_input",
				"action_id": "webhook_url_value"
			},
			"label": {
				"type": "plain_text",
				"text": "Webhook URL",
				"emoji": True
			}
		}
    ]
    configure(blocks=blocks)

# TODO: if I want to update modal, need to listen for the action/event separately

def save_utils(ack, view, update):
    print('utils: save')
    print('view', view)
    values = view["state"]["values"]
    # values['<block_id>']['<element action_id>']
    selected_option_object = values["utilities_action_select"]["utilities_action_select_value"]
    selected_utility_callback_id = selected_option_object["selected_option"]["value"]

    webhook_url = values["webhook_url_input"]["webhook_url_value"]["value"]
    
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
        "webhook_url": {"value": webhook_url},

    }
    # TODO: these outputs would need to be genericized
    outputs = [
        {
            "type": "text",
            "name": "webhook_status_code",
            "label": "Webhook Status Code"
        }
    ]
    update(inputs=inputs, outputs=outputs)


def execute_utils(step, complete, fail):
    print('utils: execute')
    inputs = step["inputs"]
    
    # url = "https://webhook.site/ece98740-9f9c-404a-9780-f55692bce841"
    url = inputs["webhook_url"]["value"]
    print('sending to url:', url)
    json_body = {"abc": "123"}
    resp = utils.send_webhook(url, json_body)
    
    outputs = {
        "webhook_status_code": str(resp.status_code)
    }
    complete(outputs=outputs)


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

# slack_utils_ws = WorkflowStep(
#     callback_id="slack_utilities",
#     edit=edit_slack_utils,
#     save=save_slack_utils,
#     execute=execute_slack_utils,
# )
# app.step(slack_utils_ws)

###########################
# Flask app stuff
############################
flask_app = Flask(__name__)
handler = SlackRequestHandler(app)

@flask_app.route('/', methods=["GET"])
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
    print('#### RECEIVED ###', request.json)