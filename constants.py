GITHUB_REPO_URL = "https://github.com/happybara-io/WorkflowBuddy"

EVENT_APP_HOME_OPENED = "app_home_opened"
EVENT_APP_MENTION = "app_mention"
EVENT_CHANNEL_CREATED = "channel_created"
EVENT_WORKFLOW_PUBLISHED = "workflow_published"

APP_HOME_HEADER_BLOCKS = [
    {
        "type": "header",
        "text": {"type": "plain_text", "text": "Workflow Buddy", "emoji": True},
    },
    {"type": "divider"},
    {
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": f"Configure your Workflow Buddy bot here. _Need Help?_ :link: <{GITHUB_REPO_URL}|GitHub>",
        },
    },
    {
        "type": "actions",
        "elements": [
            {
                "type": "button",
                "style": "primary",
                "text": {"type": "plain_text", "text": "Add", "emoji": True},
                "value": "add_webhook",
                "action_id": "action_add_webhook",
            },
            {
                "type": "button",
                "style": "primary",
                "text": {"type": "plain_text", "text": "Import", "emoji": True},
                "value": "import",
                "action_id": "action_import",
            },
            {
                "type": "button",
                "text": {"type": "plain_text", "text": "Export", "emoji": True},
                "value": "export",
                "action_id": "action_export",
            },
        ],
    },
    {"type": "divider"},
]

APP_HOME_FOOTER_BLOCKS = [{
			"type": "section",
			"text": {
				"type": "mrkdwn",
				"text": "  "
			}
		},
		{
			"type": "section",
			"text": {
				"type": "plain_text",
				"text": "    "
			}
		},
		{
			"type": "section",
			"text": {
				"type": "plain_text",
				"text": "    "
			}
		},
		{
			"type": "section",
			"text": {
				"type": "plain_text",
				"text": "    "
			}
		},
		{
			"type": "divider"
		},
		{
			"type": "context",
			"elements": [
				{
					"type": "image",
					"image_url": "https://s3.happybara.io/happybara/main_logo.png",
					"alt_text": "happybara.io"
				},
				{
					"type": "mrkdwn",
					"text": "Proudly built by <https://happybara.io|Happybara>."
				}
			]
		}]

# TODO: incorporate the blocks here as well
UTILS_CONFIG = {
    "webhook": {
        "draft": False,
        "blocks": {"TODO": True},  # TODO
        "inputs": {
            "webhook_url": {
                "name": "webhook_url",
                "block_id": "webhook_url_input",
                "action_id": "webhook_url_value",
            }
        },
        "outputs": [
            {
                "type": "text",
                "name": "webhook_status_code",
                "label": "Webhook Status Code",
            }
        ],
    },
    "random_int": {
        "draft": False,
        "blocks": {},
        "inputs": {
            "lower_bound": {
                "name": "lower_bound",
                "block_id": "lower_bound_input",
                "action_id": "lower_bound_value",
            },
            "upper_bound": {
                "name": "upper_bound",
                "block_id": "upper_bound_input",
                "action_id": "upper_bound_value",
            },
        },
        "outputs": [
            {"name": "random_int_text", "label": "Random Int Text", "type": "text"}
        ],
    },
    "random_uuid": {
        "draft": False,
        "blocks": {},
        "inputs": {},
        "outputs": [{"name": "random_uuid", "label": "Random UUID", "type": "text"}],
    },
}


# TODO: handle optional API arguments
# TODO: make it easy to copy-paste blocks from block-kit builder
# and also easy to use the same block id/action id to access the submission
SLACK_UTILS_CONFIG = {
    "conversations_create": {
        "draft": False,
        "blocks": {},
        "inputs": {
            "channel_name": {
                "name": "channel_name",
                "block_id": "channel_name_input",
                "action_id": "channel_name_value",
                "notes": "Channel names may only contain lowercase letters, numbers, hyphens, underscores and be max 80 chars.",
            }
        },
        "outputs": [
            {"label": "Channel ID", "name": "channel_id", "type": "channel"},
            {"label": "Channel ID Text", "name": "channel_id_text", "type": "text"},
        ],
    },
    "find_user_by_email": {
        "draft": False,
        "blocks": {},
        "inputs": {
            "user_email": {
                "name": "user_email",
                "block_id": "user_email_input",
                "action_id": "user_email_value",
            }
        },
        "outputs": [
            {"label": "User ID", "name": "user_id", "type": "text"},
            {"label": "Team ID", "name": "team_id", "type": "text"},
            {"label": "User", "name": "user", "type": "user"},
            {"label": "Real Name", "name": "real_name", "type": "text"},
        ],
    },
    "set_channel_topic": {
        "draft": True,
        "blocks": {"TODO": True},  # TODO
        "inputs": {
            "conversation_id": {
                "name": "conversation_id",
                "block_id": "conversation_id",
                "action_id": "conversation_id_input",
            },
            "topic": {
                "name": "topic",
                "notes": "Does not support formatting or linkification",
            },
        },
        "outputs": [],
    },
}
