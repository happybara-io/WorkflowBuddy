GITHUB_REPO_URL = "https://github.com/happybara-io/WorkflowBuddy"

EVENT_APP_HOME_OPENED = "app_home_opened"
EVENT_APP_MENTION = "app_mention"
EVENT_CHANNEL_CREATED = "channel_created"
EVENT_WORKFLOW_PUBLISHED = "workflow_published"

WORKFLOW_STEP_UTILS_CALLBACK_ID = "utilities"
WORKFLOW_STEP_SLACK_UTILS_CALLBACK_ID = "slack_utils"

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

APP_HOME_FOOTER_BLOCKS = [
    {"type": "section", "text": {"type": "mrkdwn", "text": "  "}},
    {"type": "section", "text": {"type": "plain_text", "text": "    "}},
    {"type": "section", "text": {"type": "plain_text", "text": "    "}},
    {"type": "section", "text": {"type": "plain_text", "text": "    "}},
    {"type": "divider"},
    {
        "type": "context",
        "elements": [
            {
                "type": "image",
                "image_url": "https://s3.happybara.io/happybara/main_logo.png",
                "alt_text": "happybara.io",
            },
            {
                "type": "mrkdwn",
                "text": "Proudly built by <https://happybara.io|Happybara>.",
            },
        ],
    },
]

UTILS_STEP_MODAL_COMMON_BLOCKS = [
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
]

UTILS_CONFIG = {
    "webhook": {
        "draft": False,
        "description": "Send a webhook to the defined URL.",
        "modal_input_blocks": [
            {
                "type": "input",
                "block_id": "webhook_url_input",
                "element": {
                    "type": "plain_text_input",
                    "action_id": "webhook_url_value",
                    "placeholder": {
                        "type": "plain_text",
                        "text": "https://webhook.site/abcdefghijk",
                    },
                },
                "label": {"type": "plain_text", "text": "Webhook URL", "emoji": True},
                # "optional": True,
            },
        ],
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
        "description": "Get a random integer from the range [lower bound - upper bound] (inclusive).",
        "modal_input_blocks": [
            {
                "type": "input",
                "block_id": "lower_bound_input",
                "element": {
                    "type": "plain_text_input",
                    "action_id": "lower_bound_value",
                    "placeholder": {"type": "plain_text", "text": "5"},
                },
                "label": {"type": "plain_text", "text": "Lower Bound", "emoji": True},
                "optional": True,
            },
            {
                "type": "input",
                "block_id": "upper_bound_input",
                "element": {
                    "type": "plain_text_input",
                    "action_id": "upper_bound_value",
                    "placeholder": {"type": "plain_text", "text": "100"},
                },
                "label": {"type": "plain_text", "text": "Upper Bound", "emoji": True},
                "optional": True,
            },
        ],
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
        "description": "Generated a UUID, e.g. `'9ba98b34-7e54-4b78-8833-ca29380aae08`.",
        "modal_input_blocks": [],
        "inputs": {},
        "outputs": [{"name": "random_uuid", "label": "Random UUID", "type": "text"}],
    },
}

SLACK_STEP_MODAL_COMMON_BLOCKS = [
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
                            "text": "Find user by email",
                            "emoji": True,
                        },
                        "value": "find_user_by_email",
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
]

# TODO: handle optional API arguments
# TODO: make it easy to copy-paste blocks from block-kit builder
# and also easy to use the same block id/action id to access the submission
SLACK_UTILS_CONFIG = {
    "conversations_create": {
        "draft": False,
        "description": "Create a new channel with your specified channel name.\n⚠️_Channel names may only contain lowercase letters, numbers, hyphens, underscores and be max 80 chars._",
        "modal_input_blocks": [
            {
                "type": "input",
                "block_id": "channel_name_input",
                "element": {
                    "type": "plain_text_input",
                    "action_id": "channel_name_value",
                    "placeholder": {
                        "type": "plain_text",
                        "text": "my-super-awesome-new-channel",
                    },
                },
                "label": {"type": "plain_text", "text": "Channel Name", "emoji": True},
                # "optional": True,
            }
        ],
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
        "description": "Find a Slack user based on their account email.",
        "modal_input_blocks": [
            {
                "type": "input",
                "block_id": "user_email_input",
                "element": {
                    "type": "plain_text_input",
                    "action_id": "user_email_value",
                    "placeholder": {"type": "plain_text", "text": "user@example.com"},
                },
                "label": {"type": "plain_text", "text": "User Email", "emoji": True},
                # "optional": True,
            }
        ],
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
