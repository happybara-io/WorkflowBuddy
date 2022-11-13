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
    },
    "github-repo": {
        "home": "https://github.com/happybara-io/WorkflowBuddy",
        "new-issue": "https://github.com/happybara-io/WorkflowBuddy/issues/new/choose",
    },
}

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

DB_UNHANDLED_EVENTS_KEY = "unhandled_events"

TIME_5_MINS = 5 * 60
TIME_1_DAY = 24 * 3600

WEBHOOK_SK_LENGTH = 20

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
                "value": URLS["github-repo"]["home"],
                "url": URLS["github-repo"]["home"],
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
                "text": "• Slack: Set Channel Topic",
                "emoji": True,
            },
            {
                "type": "plain_text",
                "text": "• Slack: Random Members Picker",
                "emoji": True,
            },
            {
                "type": "plain_text",
                "text": "• Slack: Get Email From User",
                "emoji": True,
            },
            {
                "type": "plain_text",
                "text": "• Utils: Send Outbound Webhook",
                "emoji": True,
            },
            {
                "type": "plain_text",
                "text": "• Utils: Extract Values from JSON",
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
    "random_member_picker": "Random Member Picker",
    "manual_complete": "Wait for Manual Complete",
    "wait_for_webhook": "Wait for Webhook",
    "json_extractor": "Extract Values from JSON",
    "conversations_create": "Slack: Channels Create",
    "find_user_by_email": "Slack: Find User by Email",
    "get_email_from_slack_user": "Slack: Get Email From User",
    "schedule_message": "Slack: Schedule a Message",
    "set_channel_topic": "Slack: Set Conversation Topic",
    "add_reaction": "Slack: Add Reaction",
    "find_message": "Slack: Find Message",
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
                            "text": UTILS_ACTION_LABELS["random_member_picker"],
                            "emoji": True,
                        },
                        "value": "random_member_picker",
                    },
                    {
                        "text": {
                            "type": "plain_text",
                            "text": UTILS_ACTION_LABELS["json_extractor"],
                            "emoji": True,
                        },
                        "value": "json_extractor",
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
                            "text": UTILS_ACTION_LABELS["wait_for_webhook"],
                            "emoji": True,
                        },
                        "value": "wait_for_webhook",
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
                            "text": UTILS_ACTION_LABELS["get_email_from_slack_user"],
                            "emoji": True,
                        },
                        "value": "get_email_from_slack_user",
                    },
                    {
                        "text": {
                            "type": "plain_text",
                            "text": UTILS_ACTION_LABELS["schedule_message"],
                            "emoji": True,
                        },
                        "value": "schedule_message",
                    },
                    {
                        "text": {
                            "type": "plain_text",
                            "text": UTILS_ACTION_LABELS["set_channel_topic"],
                            "emoji": True,
                        },
                        "value": "set_channel_topic",
                    },
                    {
                        "text": {
                            "type": "plain_text",
                            "text": UTILS_ACTION_LABELS["add_reaction"],
                            "emoji": True,
                        },
                        "value": "add_reaction",
                    },
                    {
                        "text": {
                            "type": "plain_text",
                            "text": UTILS_ACTION_LABELS["find_message"],
                            "emoji": True,
                        },
                        "value": "find_message",
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
        "is_slack": False,
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
                "block_id": "http_method_action_select",
                "label": {"type": "plain_text", "text": "HTTP Method", "emoji": True},
                "element": {
                    "type": "static_select",
                    "placeholder": {
                        "type": "plain_text",
                        "text": "HTTP Method",
                        "emoji": True,
                    },
                    "initial_option": {
                        "text": {
                            "type": "plain_text",
                            "text": "POST",
                            "emoji": True,
                        },
                        "value": "POST",
                    },
                    "options": [
                        {
                            "text": {
                                "type": "plain_text",
                                "text": "POST",
                                "emoji": True,
                            },
                            "value": "POST",
                        },
                        {
                            "text": {
                                "type": "plain_text",
                                "text": "GET",
                                "emoji": True,
                            },
                            "value": "GET",
                        },
                        {
                            "text": {
                                "type": "plain_text",
                                "text": "PUT",
                                "emoji": True,
                            },
                            "value": "PUT",
                        },
                        {
                            "text": {
                                "type": "plain_text",
                                "text": "PATCH",
                                "emoji": True,
                            },
                            "value": "PATCH",
                        },
                        {
                            "text": {
                                "type": "plain_text",
                                "text": "DELETE",
                                "emoji": True,
                            },
                            "value": "DELETE",
                        },
                    ],
                    "action_id": "http_method_action_select_value",
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
                        "text": '_Format your JSON using your text editor or a site like <https://www.jsonformatter.io/|JSON Formatter>._\n_ℹIf you prefix a key with `__`; e.g. `__key`, Buddy will convert it to a JSON list based on newlines. If no newlines (`\\n`) are found, it will be a list of 1 item (e.g. `["abc"]`)._',
                    }
                ],
            },
            {
                "type": "input",
                "block_id": "headers_json_str_input",
                "optional": True,
                "element": {
                    "type": "plain_text_input",
                    "multiline": True,
                    "action_id": "headers_json_str_value",
                    "placeholder": {
                        "type": "plain_text",
                        "text": '{\n    "Authorization": "Bearer ..."\n}',
                    },
                },
                "label": {
                    "type": "plain_text",
                    "text": "Headers JSON",
                    "emoji": True,
                },
            },
            {
                "type": "input",
                "block_id": "query_params_json_str_input",
                "optional": True,
                "element": {
                    "type": "plain_text_input",
                    "multiline": True,
                    "action_id": "query_params_json_str_value",
                    "placeholder": {
                        "type": "plain_text",
                        "text": '{\n    "q": "abc"\n}',
                    },
                },
                "label": {
                    "type": "plain_text",
                    "text": "Query Params JSON",
                    "emoji": True,
                },
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
            "http_method": {
                "name": "http_method",
                "type": "static_select",
                "block_id": "http_method_action_select",
                "action_id": "http_method_action_select_value",
            },
            "request_json_str": {
                "name": "request_json_str",
                "validation_type": "json",
                "block_id": "request_json_str_input",
                "action_id": "request_json_str_value",
            },
            "headers_json_str": {
                "name": "headers_json_str",
                "validation_type": "json",
                "block_id": "headers_json_str_input",
                "action_id": "headers_json_str_value",
            },
            "query_params_json_str": {
                "name": "query_params_json_str",
                "validation_type": "json",
                "block_id": "query_params_json_str_input",
                "action_id": "query_params_json_str_value",
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
        "is_slack": False,
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
    "random_member_picker": {
        "draft": False,
        "step_name": "Random Member Picker",
        "step_image_url": URLS["images"]["bara_slack_logo"],
        "description": f"Choose random members from a channel/conversation. Picks from the first 200 names it finds.\n_⚠ Slack makes it hard to filter bots & workflows from members, so please <{URLS['github-repo']['home']}|open an issue on the repo>_",
        "modal_input_blocks": [
            {
                "type": "input",
                "block_id": "number_of_users_input",
                "element": {
                    "type": "plain_text_input",
                    "action_id": "number_of_users_value",
                    "initial_value": "1",
                    "placeholder": {"type": "plain_text", "text": "1"},
                },
                "label": {
                    "type": "plain_text",
                    "text": "Number of Users to Select",
                    "emoji": True,
                },
            },
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
                    "filter": {
                        "include": ["public", "private", "mpim"],
                        "exclude_bot_users": True,
                    },
                    "action_id": "conversation_id_value",
                },
                "label": {"type": "plain_text", "text": "Conversation", "emoji": True},
            },
        ],
        "inputs": {
            "conversation_id": {
                "name": "conversation_id",
                "validation_type": "membership_check",
                "type": "conversations_select",
                "block_id": "conversation_id_input",
                "action_id": "conversation_id_value",
            },
            "number_of_users": {
                "name": "number_of_users",
                "validation_type": "integer",
                "block_id": "number_of_users_input",
                "action_id": "number_of_users_value",
            },
        },
        "has_dynamic_outputs": True,
    },
    "manual_complete": {
        "draft": False,
        "step_name": "Wait for Human",
        "step_image_url": URLS["images"]["bara_main_logo"],
        "is_slack": False,
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
                    "filter": {
                        "include": ["public", "private", "mpim" "im"],
                        "exclude_bot_users": True,
                    },
                    "action_id": "conversation_id_value",
                },
                "label": {"type": "plain_text", "text": "Conversation", "emoji": True},
            }
        ],
        "inputs": {
            "conversation_id": {
                "name": "conversation_id",
                "validation_type": "membership_check",
                "type": "conversations_select",
                "block_id": "conversation_id_input",
                "action_id": "conversation_id_value",
            }
        },
        "outputs": [],
    },
    "conversations_create": {
        "draft": False,
        "is_slack": True,
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
        "is_slack": True,
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
        "is_slack": True,
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
                "validation_type": "membership_check",
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
        "draft": False,
        "step_name": "Set Channel Topic",
        "step_image_url": URLS["images"]["bara_slack_logo"],
        "description": f"<https://api.slack.com/methods/conversations.setTopic|Slack API docs> - does not support formatting or linkification.",
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
                    "filter": {
                        "include": ["public", "private", "mpim"],
                        "exclude_bot_users": True,
                    },
                    "action_id": "conversation_id_value",
                },
                "label": {"type": "plain_text", "text": "Conversation", "emoji": True},
            },
            {
                "type": "input",
                "block_id": "topic_string_input",
                "element": {
                    "type": "plain_text_input",
                    "action_id": "topic_string_value",
                    "placeholder": {"type": "plain_text", "text": "A fantastic topic!"},
                },
                "label": {
                    "type": "plain_text",
                    "text": "Topic String",
                    "emoji": True,
                },
                "hint": {
                    "type": "plain_text",
                    "text": "⚠ Text must be <250 characters, and does not support formatting or linkification.",
                    "emoji": True,
                },
            },
        ],
        "inputs": {
            "conversation_id": {
                "name": "conversation_id",
                "validation_type": "membership_check",
                "type": "conversations_select",
                "block_id": "conversation_id_input",
                "action_id": "conversation_id_value",
            },
            "topic_string": {
                "name": "topic_string",
                "block_id": "topic_string_input",
                "validation_type": "str_length-250",
                "action_id": "topic_string_value",
            },
        },
        "outputs": [],
    },
    "json_extractor": {
        "draft": False,
        "step_name": "Extract Value from JSON",
        "step_image_url": URLS["images"]["bara_main_logo"],
        "description": "Use JSONPATH to extract specific data from JSON (such as an HTTP response body) _(<https://github.com/h2non/jsonpath-ng|Parsing docs>)_.",
        "modal_input_blocks": [
            {
                "type": "input",
                "block_id": "json_string_input",
                "element": {
                    "type": "plain_text_input",
                    "action_id": "json_string_value",
                    "placeholder": {
                        "type": "plain_text",
                        "text": '{"key": "valid json"}',
                    },
                },
                "label": {
                    "type": "plain_text",
                    "text": "JSON String",
                    "emoji": True,
                },
            },
            {
                "type": "input",
                "block_id": "jsonpath_expr_input",
                "element": {
                    "type": "plain_text_input",
                    "action_id": "jsonpath_expr_value",
                    "placeholder": {"type": "plain_text", "text": "$"},
                },
                "label": {
                    "type": "plain_text",
                    "text": "JSONPATH Expression",
                    "emoji": True,
                },
            },
        ],
        "inputs": {
            "json_string": {
                "name": "json_string",
                "block_id": "json_string_input",
                "action_id": "json_string_value",
            },
            "jsonpath_expr": {
                "name": "jsonpath_expr",
                "block_id": "jsonpath_expr_input",
                "action_id": "jsonpath_expr_value",
            },
        },
        "outputs": [
            {
                "label": "Extracted Data Matches",
                "name": "extracted_matches",
                "type": "text",
            }
        ],
    },
    "get_email_from_slack_user": {
        "draft": False,
        "is_slack": True,
        "step_name": "Get Email from User",
        "step_image_url": URLS["images"]["bara_slack_logo"],
        "description": "Get a Slack user's email as a variable from a text user id.\n> _⚠ If your variable is a 'user' type, you already have access to the email and don't need to use this utility! To access, insert the variable into your input, then click on it - from there you can choose from mention `<@U1234>`, name `First Last`, or email `you@example.com`._",
        "modal_input_blocks": [
            {
                "type": "input",
                "block_id": "user_id_input",
                "element": {
                    "type": "plain_text_input",
                    "action_id": "user_id_value",
                    "placeholder": {"type": "plain_text", "text": "U123456"},
                },
                "label": {
                    "type": "plain_text",
                    "text": "User/User ID",
                    "emoji": True,
                },
            }
        ],
        "inputs": {
            "user_id": {"block_id": "user_id_input", "action_id": "user_id_value"},
        },
        "outputs": [
            {
                "label": "User Email",
                "name": "user_email",
                "type": "text",
            }
        ],
    },
    "add_reaction": {
        "draft": True,
        "is_slack": True,
        "step_name": "Add Reaction",
        "step_image_url": URLS["images"]["bara_slack_logo"],
        "description": "Add a reaction to a message.",
        "modal_input_blocks": [
            # {
            #     "type": "input",
            #     "block_id": "conversation_id_input",
            #     "element": {
            #         "type": "conversations_select",
            #         "placeholder": {
            #             "type": "plain_text",
            #             "text": "Select conversation",
            #             "emoji": True,
            #         },
            #         "filter": {
            #             "include": [
            #             "public",
            #             "private",
            #             "mpim"
            #             ],
            #             "exclude_bot_users" : True
            #         },
            #         "action_id": "conversation_id_value",
            #     },
            #     "label": {"type": "plain_text", "text": "Conversation", "emoji": True},
            # },
            # {
            #     "type": "input",
            #     "block_id": "message_ts_input",
            #     "element": {
            #         "type": "plain_text_input",
            #         "action_id": "message_ts_value",
            #         "placeholder": {"type": "plain_text", "text": "1111111111.2222"},
            #     },
            #     "label": {
            #         "type": "plain_text",
            #         "text": "Message TS",
            #         "emoji": True,
            #     },
            # },
            {
                "type": "input",
                "block_id": "permalink_input",
                "element": {
                    "type": "plain_text_input",
                    "action_id": "permalink_value",
                    "placeholder": {
                        "type": "plain_text",
                        "text": "https://workspace.slack.com/archives/CP3S47DAB/p1669229063902429",
                    },
                },
                "label": {
                    "type": "plain_text",
                    "text": "Permalink to Message",
                    "emoji": True,
                },
            },
            {
                "type": "input",
                "block_id": "reaction_input",
                "element": {
                    "type": "plain_text_input",
                    "action_id": "reaction_value",
                    "placeholder": {"type": "plain_text", "text": ":boom:"},
                },
                "label": {
                    "type": "plain_text",
                    "text": "Reaction",
                    "emoji": True,
                },
                "hint": {
                    "type": "plain_text",
                    "text": "Can provide either the name: `boom` or the reaction 💥 in the text box.",
                    "emoji": True,
                },
            },
        ],
        "inputs": {
            # "conversation_id": {
            #     "name": "conversation_id",
            #     "validation_type": "membership_check",
            #     "type": "conversations_select",
            #     "block_id": "conversation_id_input",
            #     "action_id": "conversation_id_value",
            # },
            # "message_ts": {
            #     "name": "message_ts",
            #     "block_id": "message_ts_input",
            #     "action_id": "message_ts_value",
            # },
            "permalink": {
                "name": "permalink",
                "block_id": "permalink_input",
                "action_id": "permalink_value",
            },
            "reaction": {
                "name": "reaction",
                "block_id": "reaction_input",
                "action_id": "reaction_value",
            },
        },
        "outputs": [],
    },
    "wait_for_webhook": {
        "draft": False,
        "step_name": "Wait for Webhook",
        "step_image_url": URLS["images"]["bara_main_logo"],
        "description": "Waits to receive a webhook from an external service before continuing.",
        "modal_input_blocks": [
            {
                "type": "input",
                "block_id": "destination_url_input",
                "element": {
                    "type": "plain_text_input",
                    "action_id": "destination_url_value",
                    "placeholder": {
                        "type": "plain_text",
                        "text": "https://webhook.site/abcdefghijk",
                    },
                },
                "label": {
                    "type": "plain_text",
                    "text": "Destination URL",
                    "emoji": True,
                },
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
        ],
        "inputs": {
            "destination_url": {
                "name": "destination_url",
                "validation_type": "url",
                "block_id": "destination_url_input",
                "action_id": "destination_url_value",
            },
        },
        "outputs": [],
    },
    "find_message": {
        "draft": False,
        "needs_user_token": True,
        "step_name": "Find a Message",
        "step_image_url": URLS["images"]["bara_main_logo"],
        "description": "Search in Slack for a message, return the top result.",
        "modal_input_blocks": [
            {
                "type": "input",
                "block_id": "search_query_input",
                "element": {
                    "type": "plain_text_input",
                    "action_id": "search_query_value",
                    "placeholder": {
                        "type": "plain_text",
                        "text": 'in:#general "thanks for all the fish"',
                    },
                },
                "label": {
                    "type": "plain_text",
                    "text": "Slack Search Query",
                    "emoji": True,
                },
            },
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": "_This query uses the same formatting and options as the search bar in the Slack app._",
                    }
                ],
            },
            {
                "type": "input",
                "block_id": "sort_select",
                "label": {"type": "plain_text", "text": "Results Sort", "emoji": True},
                "element": {
                    "type": "static_select",
                    "initial_option": {
                            "text": {
                                "type": "plain_text",
                                "text": "Timestamp",
                                "emoji": True,
                            },
                            "value": "timestamp",
                        },
                    "options": [
                        {
                            "text": {
                                "type": "plain_text",
                                "text": "Timestamp",
                                "emoji": True,
                            },
                            "value": "timestamp",
                        },
                        {
                            "text": {
                                "type": "plain_text",
                                "text": "Match Score",
                                "emoji": True,
                            },
                            "value": "score",
                        },
                    ],
                    "action_id": "sort_select_value",
                },
            },
            {
                "type": "input",
                "block_id": "sort_dir_select",
                "label": {
                    "type": "plain_text",
                    "text": "Results Sort Direction",
                    "emoji": True,
                },
                "element": {
                    "type": "static_select",
                    "initial_option": {
                            "text": {
                                "type": "plain_text",
                                "text": "Descending (newest or best first)",
                                "emoji": True,
                            },
                            "value": "desc",
                        },
                    "options": [
                        {
                            "text": {
                                "type": "plain_text",
                                "text": "Ascending (oldest or worst first)",
                                "emoji": True,
                            },
                            "value": "asc",
                        },
                        {
                            "text": {
                                "type": "plain_text",
                                "text": "Descending (newest or best first)",
                                "emoji": True,
                            },
                            "value": "desc",
                        },
                    ],
                    "action_id": "sort_dir_select_value",
                },
            },
        ],
        "inputs": {
            "search_query": {
                "name": "search_query",
                "block_id": "search_query_input",
                "action_id": "search_query_value",
            },
            "sort": {
                "name": "sort",
                "type": "static_select",
                "label": {
                    "timestamp": "Timestamp",
                    "score": "Match Score"
                },
                "block_id": "sort_select",
                "action_id": "sort_select_value",
            },
            "sort_dir": {
                "name": "sort_dir",
                "type": "static_select",
                "label": {
                    "desc": "Descending (newest or best first)",
                    "asc": "Ascending (oldest or worst first)"
                },
                "block_id": "sort_dir_select",
                "action_id": "sort_dir_select_value",
            },
        },
        "outputs": [
            {
                "label": "Channel",
                "name": "channel",
                "type": "channel",
            },
            {
                "label": "Channel ID",
                "name": "channel_id",
                "type": "text",
            },
            {
                "label": "Message TS",
                "name": "message_ts",
                "type": "text",
            },
            {
                "label": "Permalink",
                "name": "permalink",
                "type": "text",
            },
            {
                "label": "Message Text",
                "name": "message_text",
                "type": "text",
            },
            {
                "label": "User",
                "name": "user",
                "type": "user",
            },
            {
                "label": "User ID",
                "name": "user_id",
                "type": "text",
            },
        ],
    },
}
