GITHUB_REPO_URL = "https://github.com/happybara-io/WorkflowBuddy"

EVENT_APP_HOME_OPENED = "app_home_opened"
EVENT_APP_MENTION = "app_mention"
EVENT_CHANNEL_ARCHIVE = "channel_archive"
EVENT_CHANNEL_CREATED = "channel_created"
EVENT_CHANNEL_DELETED = "channel_deleted"
EVENT_CHANNEL_UNARCHIVE = "channel_unarchive"
EVENT_REACTION_ADDED = "reaction_added"
EVENT_WORKFLOW_PUBLISHED = "workflow_published"
EVENT_WORKFLOW_STEP_DELETED = "workflow_step_deleted"

WORKFLOW_STEP_UTILS_CALLBACK_ID = "utilities"
WORKFLOW_STEP_WEBHOOK_CALLBACK_ID = "outgoing_webhook"

TIME_5_MINS = 5 * 60
TIME_1_DAY = 24 * 3600

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
            "text": "Workflow Buddy lets you use any Slack Event as a trigger for Workflow Builder, as well as adding new Steps (e.g. `Send Outbound Webhook`).",
        },
    },
    {
        "type": "actions",
        "elements": [
            {
                "type": "button",
                "text": {"type": "plain_text", "text": "🔗GitHub Docs", "emoji": True},
                "value": GITHUB_REPO_URL,
                "url": GITHUB_REPO_URL,
                "action_id": "action_github_repo",
            },
        ],
    },
    {"type": "divider"},
    {
        "type": "header",
        "text": {"type": "plain_text", "text": "Event Triggers", "emoji": True},
    },
    {
        "type": "context",
        "elements": [
            {
                "type": "mrkdwn",
                "text": "How to add a new Event Trigger for Slack events. <https://github.com/happybara-io/WorkflowBuddy#-quickstarts|Quickstart Guide for reference>.",
            }
        ],
    },
    {
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": "_1. (In Workflow Builder) Create a Slack <https://slack.com/help/articles/360041352714-Create-more-advanced-workflows-using-webhooks|Webhook-triggered Workflow> - then save the URL nearby._",
        },
    },
    {
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": "*2. (Here) Set up the connection between `event` and the `webhook URL` from Step 1 by clicking `Add`.*",
        },
    },
    {
        "type": "context",
        "elements": [
            {
                "type": "mrkdwn",
                "text": "_Alternatively get a Webhook URL from <https://webhook.site|Webhook.site> if you are just testing events are working._",
            }
        ],
    },
    {
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": "_3. Send a test event to make sure workflow is triggered (e.g. for `app_mention`, go to a channel and `@WorkflowBuddy`)._",
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
    # {"type": "divider"},
]

URLS = {
    "images": {
        "bara_main_logo": "https://s3.happybara.io/happybara/main_logo.png",
        "slack_logo": "https://s3.happybara.io/common/slack-logo.png",
        "bara_slack_logo": "https://s3.happybara.io/happybara/main_logo_slack_badge.png",
        "bara_webhook_logo": "https://s3.happybara.io/happybara/main_logo_webhook_badge.png",
        "footer": {
            "dark": "https://s3.happybara.io/common/bara-footer-dark.jpg",
            "light": "https://s3.happybara.io/common/bara-footer-light.png",
            "oceanic": "https://s3.happybara.io/common/bara-footer-oceanic.jpg",
        },
    }
}

APP_HOME_MIDDLE_BLOCKS = [
    {"type": "section", "text": {"type": "mrkdwn", "text": "  "}},
    {"type": "section", "text": {"type": "plain_text", "text": "    "}},
    {"type": "section", "text": {"type": "plain_text", "text": "    "}},
    {"type": "section", "text": {"type": "plain_text", "text": "    "}},
    {"type": "divider"},
    {
        "type": "header",
        "text": {"type": "plain_text", "text": "Step Actions", "emoji": True},
    },
    {
        "type": "actions",
        "elements": [
            {
                "type": "button",
                "text": {
                    "type": "plain_text",
                    "text": "Manage Scheduled Messages",
                    "emoji": True,
                },
                "value": "manage_scheduled_messages",
                "action_id": "action_manage_scheduled_messages",
            },
            {
                "type": "button",
                "text": {
                    "type": "plain_text",
                    "text": "Complete Step Manually",
                    "emoji": True,
                },
                "value": "action_manual_complete",
                "action_id": "action_manual_complete",
            },
        ],
    },
    {
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": "The currently implemented Step actions. _<https://github.com/happybara-io/WorkflowBuddy#available-steps|Docs with more info>._",
        },
    },
    {
        "type": "section",
        "fields": [
            {"type": "plain_text", "text": "• Slack: Create a Channel", "emoji": True},
            {
                "type": "plain_text",
                "text": "• Slack: Find User by Email",
                "emoji": True,
            },
            {
                "type": "plain_text",
                "text": "• Slack: Schedule a Message",
                "emoji": True,
            },
            {
                "type": "plain_text",
                "text": "• Utils: Send Outbound Webhook",
                "emoji": True,
            },
            {
                "type": "plain_text",
                "text": "• Utils: Wait for Human",
                "emoji": True,
            },
            {
                "type": "plain_text",
                "text": "• Utils: Get Random Integer from Range",
                "emoji": True,
            },
            {"type": "plain_text", "text": "• Utils: Get Random UUID", "emoji": True},
        ],
    },
    {"type": "divider"},
]

UTILS_ACTION_LABELS = {
    "webhook": "Send a Webhook",
    "random_int": "Random Integer",
    "random_uuid": "Random UUID",
    "manual_complete": "Wait for Manual Complete",
    "conversations_create": "Slack: Channels Create",
    "find_user_by_email": "Slack: Find User by Email",
    "schedule_message": "Slack: Schedule a Message",
}

WEBHOOK_STEP_MODAL_COMMON_BLOCKS = [
    {
        "type": "header",
        "text": {
            "type": "plain_text",
            "text": "Send an outgoing webhook",
            "emoji": True,
        },
    },
]


# Try to avoid needing variables in blocks, break it down if needed - want to be able to
# easily use this with Block Kit Builder
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
                        "text": UTILS_ACTION_LABELS["webhook"],
                        "emoji": True,
                    },
                    "value": "webhook",
                },
                "options": [
                    {
                        "text": {
                            "type": "plain_text",
                            "text": UTILS_ACTION_LABELS["webhook"],
                            "emoji": True,
                        },
                        "value": "webhook",
                    },
                    {
                        "text": {
                            "type": "plain_text",
                            "text": UTILS_ACTION_LABELS["random_int"],
                            "emoji": True,
                        },
                        "value": "random_int",
                    },
                    {
                        "text": {
                            "type": "plain_text",
                            "text": UTILS_ACTION_LABELS["random_uuid"],
                            "emoji": True,
                        },
                        "value": "random_uuid",
                    },
                    {
                        "text": {
                            "type": "plain_text",
                            "text": UTILS_ACTION_LABELS["manual_complete"],
                            "emoji": True,
                        },
                        "value": "manual_complete",
                    },
                    {
                        "text": {
                            "type": "plain_text",
                            "text": UTILS_ACTION_LABELS["conversations_create"],
                            "emoji": True,
                        },
                        "value": "conversations_create",
                    },
                    {
                        "text": {
                            "type": "plain_text",
                            "text": UTILS_ACTION_LABELS["find_user_by_email"],
                            "emoji": True,
                        },
                        "value": "find_user_by_email",
                    },
                    {
                        "text": {
                            "type": "plain_text",
                            "text": UTILS_ACTION_LABELS["schedule_message"],
                            "emoji": True,
                        },
                        "value": "schedule_message",
                    },
                ],
                "action_id": "utilities_action_select_value",
            }
        ],
    },
]

# # TODO: handle optional API arguments
UTILS_CONFIG = {
    "webhook": {
        "step_name": "Send a webhook",
        "step_image_url": URLS["images"]["bara_webhook_logo"],
        "draft": False,
        "isSlack": False,
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
            },
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": "_Open <https://webhook.site|Webhook.site> to get a URL for debugging._",
                    }
                ],
            },
            {
                "type": "input",
                "optional": True,
                "block_id": "block_checkboxes",
                "element": {
                    "type": "checkboxes",
                    "options": [
                        {
                            "text": {"type": "mrkdwn", "text": " "},
                            "description": {
                                "type": "mrkdwn",
                                "text": "_Check this if you want Workflow to halt on server errors, otherwise it can continue._",
                            },
                            "value": "fail_on_http_error",
                        }
                    ],
                    "action_id": "action_checkboxes",
                },
                "label": {
                    "type": "plain_text",
                    "text": "❌ Fail for HTTP error codes (4xx, 5xx)",
                    "emoji": True,
                },
            },
            {
                "type": "input",
                "block_id": "request_json_str_input",
                "optional": True,
                "element": {
                    "type": "plain_text_input",
                    "multiline": True,
                    "action_id": "request_json_str_value",
                    "placeholder": {
                        "type": "plain_text",
                        "text": '{\n    "key": "value"\n}',
                    },
                },
                "label": {
                    "type": "plain_text",
                    "text": "Request JSON Body",
                    "emoji": True,
                },
            },
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": "_Format your JSON using your text editor or a site like <https://www.jsonformatter.io/|JSON Formatter>._",
                    }
                ],
            },
        ],
        "inputs": {
            "webhook_url": {
                "name": "webhook_url",
                "validation_type": "url",
                "block_id": "webhook_url_input",
                "action_id": "webhook_url_value",
            },
            "bool_flags": {
                "name": "bool_flags",
                "type": "checkboxes",
                "block_id": "block_checkboxes",
                "action_id": "action_checkboxes",
            },
            "request_json_str": {
                "name": "request_json_str",
                "validation_type": "json",
                "block_id": "request_json_str_input",
                "action_id": "request_json_str_value",
            },
        },
        "outputs": [
            {
                "type": "text",
                "name": "webhook_status_code",
                "label": "Webhook Status Code",
            },
            {
                "type": "text",
                "name": "webhook_response_text",
                "label": "Webhook Response Text",
            },
        ],
    },
    "random_int": {
        "step_name": "Random Integer",
        "step_image_url": URLS["images"]["bara_main_logo"],
        "draft": False,
        "isSlack": False,
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
                "validation_type": "integer",
                "block_id": "lower_bound_input",
                "action_id": "lower_bound_value",
            },
            "upper_bound": {
                "name": "upper_bound",
                "validation_type": "integer",
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
        "step_name": "Random UUID",
        "step_image_url": URLS["images"]["bara_main_logo"],
        "description": "Generated a UUID, e.g. `'9ba98b34-7e54-4b78-8833-ca29380aae08`.",
        "modal_input_blocks": [],
        "inputs": {},
        "outputs": [{"name": "random_uuid", "label": "Random UUID", "type": "text"}],
    },
    "manual_complete": {
        "draft": False,
        "step_name": "Wait for Human",
        "step_image_url": URLS["images"]["bara_main_logo"],
        "isSlack": False,
        "description": "Hold in progress until an execution ID is submitted to complete/fail the execution.",
        "modal_input_blocks": [
            {
                "type": "input",
                "block_id": "conversation_id_input",
                "element": {
                    "type": "conversations_select",
                    "placeholder": {
                        "type": "plain_text",
                        "text": "Select conversation",
                        "emoji": True,
                    },
                    "action_id": "conversation_id_value",
                },
                "label": {"type": "plain_text", "text": "Conversation", "emoji": True},
            }
        ],
        "inputs": {
            "conversation_id": {
                "name": "conversation_id",
                "validation_type": "able_to_post",
                "type": "conversations_select",
                "block_id": "conversation_id_input",
                "action_id": "conversation_id_value",
            }
        },
        "outputs": [],
    },
    "conversations_create": {
        "draft": False,
        "isSlack": True,
        "step_name": "Create a channel",
        "step_image_url": URLS["images"]["bara_slack_logo"],
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
                "validation_type": "slack_channel_name",
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
        "isSlack": True,
        "step_name": "Find user by email",
        "step_image_url": URLS["images"]["bara_slack_logo"],
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
                "validation_type": "email",
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
    "schedule_message": {
        "draft": False,
        "isSlack": True,
        "step_name": "Schedule a message",
        "step_image_url": URLS["images"]["bara_slack_logo"],
        "description": "Schedule a message up to 120 days in the future.",
        "modal_input_blocks": [
            {
                "type": "input",
                "block_id": "channel_input",
                "element": {
                    "type": "channels_select",
                    "placeholder": {
                        "type": "plain_text",
                        "text": "#taco-tuesday",
                        "emoji": True,
                    },
                    "action_id": "channel_value",
                },
                "label": {"type": "plain_text", "text": "Channel", "emoji": True},
            },
            {
                "type": "input",
                "block_id": "post_at_input",
                "element": {
                    "type": "plain_text_input",
                    "action_id": "post_at_value",
                    "placeholder": {"type": "plain_text", "text": "1669557726"},
                },
                "label": {
                    "type": "plain_text",
                    "text": "Post At Unix Timestamp",
                    "emoji": True,
                },
                "hint": {
                    "type": "plain_text",
                    "text": "Use https://www.unixtimestamp.com/ to convert easily.",
                    "emoji": True,
                }
                # "optional": True,
            },
            {
                "type": "input",
                "block_id": "msg_text_input",
                "element": {
                    "type": "plain_text_input",
                    "action_id": "msg_text_value",
                    "multiline": True,
                    "placeholder": {"type": "plain_text", "text": "A great message!"},
                },
                "label": {"type": "plain_text", "text": "Message", "emoji": True},
                # "optional": True,
            },
        ],
        "inputs": {
            "channel": {
                "type": "channels_select",
                "validation_type": "able_to_post",
                "block_id": "channel_input",
                "action_id": "channel_value",
            },
            "post_at": {
                "block_id": "post_at_input",
                "validation_type": "future_timestamp",
                "action_id": "post_at_value",
            },
            "msg_text": {"block_id": "msg_text_input", "action_id": "msg_text_value"},
        },
        "outputs": [
            {
                "label": "Scheduled Message ID",
                "name": "scheduled_message_id",
                "type": "text",
            }
        ],
    },
    "set_channel_topic": {
        "draft": True,
        "isSlack": True,
        "step_name": "Create a channel",
        "step_image_url": URLS["images"]["bara_slack_logo"],
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
