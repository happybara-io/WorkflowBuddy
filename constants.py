## Act as our datastore until it's worth adding - ope, jk webhooks should be confidential though 🤦

# TODO: these webhook URLs should only ever be committed if it's a private repo - even then questionable
# EVENT_WORKFLOW_MAP = {
#     'channel_joined': [],
#     'app_mention': [
#         {
#             'webhook_url': ''
#         }
#     ]
# }

EVENT_APP_MENTION = "app_mention"
EVENT_CHANNEL_CREATED = "channel_created"
EVENT_WORKFLOW_PUBLISHED = "workflow_published"

# TODO: incorporate the blocks here as well
UTILS_CONFIG = {
    "webhook": {
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
        "draft": True,
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
        "draft": True,
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
        "draft": True,
        "blocks": {},
        "inputs": {
            "user_email": {
                "name": "user_email",
                "block_id": "user_email_input",
                "action_id": "user_email_value",
            }
        },
        "outputs": [
            {"label": "User ID Text", "name": "user_id_text", "type": "text"},
            {"label": "User ID", "name": "user_id", "type": "user"},
            {"label": "Team ID", "name": "team_id", "type": "text"},
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

# Suggested Slack actions based on Zapier
# Add reminder
# Invite user to channel
# Send channel message (slack built-in)
# Send direct message (slack built-in)
# Create channel
# Set channel topic ! Cannot be done with a Bot token, only user token :(
# Update profile
# Set status
# Find message
# Find user by email
# find user by ID
# Find user by name
# Find user by username
