import logging
from datetime import datetime as dt
from unittest import mock

import pytest
import slack_sdk
from slack_sdk.errors import SlackApiError

import buddy.constants as bc
import buddy.step_actions as sut
from buddy.errors import WorkflowStepFailError

dummy_logger = logging.getLogger(name="testing")


class MockContext:
    team_id = "T11111"
    enterprise_id = None


def make_dummy_slack_api_error():
    return SlackApiError("message", {"error": "response err msg"})


def create_step_with_inputs_from_dict(kv_pairs: dict):
    step = {"inputs": {}}
    for k, v in kv_pairs.items():
        step["inputs"].update({k: {"value": v}})
    return step


def test_run_random_int():
    lower = 0
    upper = 100
    test_step = create_step_with_inputs_from_dict(
        {"lower_bound": str(lower), "upper_bound": str(upper)}
    )
    out = sut.run_random_int(test_step)
    random_int_text = out["random_int_text"]
    assert type(random_int_text) is str
    assert int(random_int_text) >= lower and int(random_int_text) <= upper


def test_run_find_user_by_email_slack_error():
    inputs = {"user_email": {"value": "a@b.com"}}
    mock_client = mock.MagicMock(name="slack_client")
    mock_client.users_lookupByEmail.side_effect = make_dummy_slack_api_error()
    with pytest.raises(WorkflowStepFailError):
        sut.run_find_user_by_email(inputs, mock_client)


def test_run_wait_state_user_requested_too_long_wait():
    int_beyond_max = bc.WAIT_STATE_MAX_SECONDS + 100
    test_step = {"inputs": {"seconds": {"value": str(int_beyond_max)}}}
    with pytest.raises(WorkflowStepFailError):
        out = sut.run_wait_state(test_step)


def test_run_add_reaction_already_added():
    test_step = create_step_with_inputs_from_dict(
        {
            "permalink": "https://workspace.slack.com/archives/CP3S47DAB/p1669229063902429",
            "reaction": ":boom:",
        }
    )
    mock_client = mock.MagicMock(name="slack_client")
    mock_client.reactions_add.side_effect = SlackApiError(
        "err msg", {"error": "already_reacted"}
    )
    out = sut.run_add_reaction(test_step, mock_client, dummy_logger)
    assert out == {}
    slack_args, slack_kwargs = mock_client.reactions_add.call_args_list[0]
    # check it's valid timestamp
    calling_datetime = dt.fromtimestamp(float(slack_kwargs["timestamp"]))
    assert (
        calling_datetime.year > 2020
    ), "Timestamp parsing must be messed up, year is too far in the past"
    assert (
        calling_datetime.year < 2030
    ), "Timestamp parsing must be messed up, year is too far in the future"


def test_run_add_reaction_invalid_permalink():
    test_step = create_step_with_inputs_from_dict(
        {"permalink": "https://some-other-url.com/whodidit"}
    )
    mock_client = mock.MagicMock(name="slack_client")
    with pytest.raises(WorkflowStepFailError):
        out = sut.run_add_reaction(test_step, mock_client, dummy_logger)


@mock.patch("buddy.step_actions.utils.send_webhook")
def test_run_webhook_happy_path(mock_send_webhook):
    # mock_utils = mock.MagicMock(name="MockBuddyUtils")
    mock_resp = mock.MagicMock(name="MockWebhookResp")
    mock_resp.status_code = 204
    mock_resp.text = "response text."
    mock_send_webhook.return_value = mock_resp
    step = {
        "inputs": {
            "webhook_url": {"value": "https://fake-webhook.com"},
            "http_method": {"value": "POST"},
        }
    }

    outputs = sut.run_webhook(step)
    assert outputs["webhook_status_code"] == str(mock_resp.status_code)


@mock.patch("buddy.step_actions.utils.send_webhook")
def test_run_webhook_continues_workflow_if_no_flag(mock_send_webhook):
    # mock_utils = mock.MagicMock(name="MockBuddyUtils")
    mock_resp = mock.MagicMock(name="MockWebhookResp")
    mock_resp.status_code = 500
    mock_resp.text = "Failure response text."
    mock_send_webhook.return_value = mock_resp
    step = {
        "inputs": {
            "webhook_url": {"value": "https://fake-webhook.com"},
            "http_method": {"value": "POST"},
        }
    }

    outputs = sut.run_webhook(step)
    assert outputs["webhook_status_code"] == str(mock_resp.status_code)


@mock.patch("buddy.step_actions.utils.send_webhook")
def test_run_webhook_stops_workflow_if_flagged(mock_send_webhook):
    # mock_utils = mock.MagicMock(name="MockBuddyUtils")
    mock_resp = mock.MagicMock(name="MockWebhookResp")
    mock_resp.status_code = 407
    mock_resp.text = "Failure response text."
    mock_send_webhook.return_value = mock_resp
    step = {
        "inputs": {
            "webhook_url": {"value": "https://fake-webhook.com"},
            "http_method": {"value": "POST"},
            "bool_flags": {"value": '[{"value": "fail_on_http_error"}]'},
        }
    }

    with pytest.raises(WorkflowStepFailError):
        _ = sut.run_webhook(step)


def test_edit_utils_debug_mode_adds_blocks():
    step = {
        "inputs": {
            "selected_utility": {"value": "random_int"},
            "debug_mode_enabled": {"value": "true"},
        }
    }
    user_token = None
    blocks = sut.edit_utils(step, user_token)
    assert blocks[2]["block_id"] == "debug_conversation_id_input"


def test_edit_utils_no_debug_mode_adds_no_blocks():
    step = {
        "inputs": {
            "selected_utility": {"value": "random_int"},
            "debug_mode_enabled": {"value": "false"},
        }
    }
    user_token = None
    blocks = sut.edit_utils(step, user_token)
    for b in blocks:
        assert b.get("block_id", "") != "debug_conversation_id_input"


@mock.patch("buddy.utils.test_if_bot_is_member")
def test_dispatch_action_update_fail_notify_channels(test_if_bot_is_member):
    # test if all are valid, but not channel member yet
    test_if_bot_is_member.side_effect = ["not_in_convo", "not_in_convo"]

    ack = mock.MagicMock(name="Ack")
    mock_client = mock.MagicMock(name="slack_client")
    context = MockContext()
    body = {
        "user": {
            "id": "U1111",
        },
        "actions": [{"value": "C1234,C123456", "block_id": "crazy_block_id"}],
        "trigger_id": "111122222233333",
        "view": {
            "state": {
                "values": {
                    "home_dispatch_notify_channels": {
                        "action_update_fail_notify_channels": {
                            "type": "plain_text_input",
                            "value": "C1234,C123456",
                        }
                    }
                }
            },
        },
    }
    resp = sut.dispatch_action_update_fail_notify_channels(
        ack, body, mock_client, MockContext
    )
    assert type(resp) is dict, "Must have failed when trying to set new channels in DB"
    assert "none" in resp["readyMsg"]
    assert "<#C1234>" in resp["errMsg"]
    assert "<#C123456>" in resp["errMsg"]


l = {
    "type": "block_actions",
    "user": {
        "id": "UMTUPT124",
        "username": "kevin",
        "name": "kevin",
        "team_id": "TKM6AU1FG",
    },
    "api_app_id": "A040W1RHGBX",
    "token": "yDbUfM6PzCoqJgW5t56KTrGe",
    "container": {"type": "view", "view_id": "V043VV9PEN8"},
    "trigger_id": "4974447958289.667214953526.ecb9fb6cc3fea9f8fa87715a04ba4f66",
    "team": {"id": "TKM6AU1FG", "domain": "happybara"},
    "enterprise": None,
    "is_enterprise_install": False,
    "view": {
        "id": "V043VV9PEN8",
        "team_id": "TKM6AU1FG",
        "type": "home",
        "blocks": [
            {
                "type": "header",
                "block_id": "jG/sU",
                "text": {"type": "plain_text", "text": "Workflow Buddy", "emoji": True},
            },
            {"type": "divider", "block_id": "MQeu"},
            {
                "type": "section",
                "block_id": "PH=Gj",
                "text": {
                    "type": "mrkdwn",
                    "text": "Workflow Buddy lets you use any Slack Event as a trigger for Workflow Builder, as well as adding new Steps (e.g. `Send Outbound Webhook`).",
                    "verbatim": False,
                },
            },
            {
                "type": "actions",
                "block_id": "Aruo",
                "elements": [
                    {
                        "type": "button",
                        "action_id": "action_github_repo",
                        "text": {
                            "type": "plain_text",
                            "text": ":link:GitHub Docs",
                            "emoji": True,
                        },
                        "value": "https://github.com/happybara-io/WorkflowBuddy",
                        "url": "https://github.com/happybara-io/WorkflowBuddy",
                    }
                ],
            },
            {"type": "divider", "block_id": "=he"},
            {
                "type": "header",
                "block_id": "g5K",
                "text": {"type": "plain_text", "text": "Team", "emoji": True},
            },
            {
                "type": "section",
                "block_id": "Njq",
                "text": {
                    "type": "mrkdwn",
                    "text": "Slack team id: `TKM6AU1FG`",
                    "verbatim": False,
                },
            },
            {
                "type": "input",
                "block_id": "+W+Rm",
                "label": {
                    "type": "plain_text",
                    "text": "🔔 Notify Channels on Step Failure",
                    "emoji": True,
                },
                "optional": False,
                "dispatch_action": True,
                "element": {
                    "type": "plain_text_input",
                    "action_id": "action_update_fail_notify_channels",
                    "placeholder": {
                        "type": "plain_text",
                        "text": "C1111,C2222",
                        "emoji": True,
                    },
                    "initial_value": "",
                    "dispatch_action_config": {
                        "trigger_actions_on": ["on_enter_pressed"]
                    },
                },
            },
            {
                "type": "context",
                "block_id": "5Ml",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": "These are the channels where you would like a notification sent if a Buddy Step in a Workflow fails :x:.\nThis is a stopgap since Slack's Workflows fail silently as far as we can tell.\n\n:warning:Limitations: This can only notify if Buddy steps fail, NOT any other type of Step, unfortunately.",
                        "verbatim": False,
                    }
                ],
            },
            {
                "type": "section",
                "block_id": "ShN",
                "text": {
                    "type": "mrkdwn",
                    "text": "Team's usage by event name:\n```\n{}\n```",
                    "verbatim": False,
                },
            },
            {
                "type": "header",
                "block_id": "ShLTq",
                "text": {"type": "plain_text", "text": "Event Triggers", "emoji": True},
            },
            {
                "type": "context",
                "block_id": "9oF7",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": "How to add a new Event Trigger for Slack events. <https://github.com/happybara-io/WorkflowBuddy#-quickstarts|Quickstart Guide for reference>.",
                        "verbatim": False,
                    }
                ],
            },
            {
                "type": "section",
                "block_id": "7xOV",
                "text": {
                    "type": "mrkdwn",
                    "text": "_1. (In Workflow Builder) Create a Slack <https://slack.com/help/articles/360041352714-Create-more-advanced-workflows-using-webhooks|Webhook-triggered Workflow> - then save the URL nearby._",
                    "verbatim": False,
                },
            },
            {
                "type": "section",
                "block_id": "WPB1",
                "text": {
                    "type": "mrkdwn",
                    "text": "*2. (Here) Set up the connection between `event` and the `webhook URL` from Step 1 by clicking `Add`.*",
                    "verbatim": False,
                },
            },
            {
                "type": "context",
                "block_id": "5rD",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": "_Alternatively get a Webhook URL from <https://webhook.site|Webhook.site> if you are just testing events are working._",
                        "verbatim": False,
                    }
                ],
            },
            {
                "type": "section",
                "block_id": "a/4d",
                "text": {
                    "type": "mrkdwn",
                    "text": "_3. Send a test event to make sure workflow is triggered (e.g. for `app_mention`, go to a channel and `@WorkflowBuddy`)._",
                    "verbatim": False,
                },
            },
            {
                "type": "actions",
                "block_id": "mzf",
                "elements": [
                    {
                        "type": "button",
                        "action_id": "action_add_webhook",
                        "text": {"type": "plain_text", "text": "Add", "emoji": True},
                        "style": "primary",
                        "value": "add_webhook",
                    }
                ],
            },
            {
                "type": "section",
                "block_id": "=pW",
                "text": {
                    "type": "mrkdwn",
                    "text": "• :shrug: Nothing here yet! Try using the `Add` or `Import` options.",
                    "verbatim": False,
                },
            },
            {
                "type": "section",
                "block_id": "lRJ",
                "text": {"type": "mrkdwn", "text": "  ", "verbatim": False},
            },
            {
                "type": "section",
                "block_id": "210",
                "text": {"type": "plain_text", "text": "    ", "emoji": True},
            },
            {
                "type": "section",
                "block_id": "OX/49",
                "text": {"type": "plain_text", "text": "    ", "emoji": True},
            },
            {
                "type": "section",
                "block_id": "nQ8d",
                "text": {"type": "plain_text", "text": "    ", "emoji": True},
            },
            {"type": "divider", "block_id": "6=JU"},
            {
                "type": "header",
                "block_id": "L1+M/",
                "text": {"type": "plain_text", "text": "Step Actions", "emoji": True},
            },
            {
                "type": "actions",
                "block_id": "GkaB",
                "elements": [
                    {
                        "type": "button",
                        "action_id": "action_manage_scheduled_messages",
                        "text": {
                            "type": "plain_text",
                            "text": "Manage Scheduled Messages",
                            "emoji": True,
                        },
                        "value": "manage_scheduled_messages",
                    },
                    {
                        "type": "button",
                        "action_id": "action_manual_complete",
                        "text": {
                            "type": "plain_text",
                            "text": "Complete Step Manually",
                            "emoji": True,
                        },
                        "value": "action_manual_complete",
                    },
                ],
            },
            {
                "type": "section",
                "block_id": "uUAb",
                "text": {
                    "type": "mrkdwn",
                    "text": "The currently implemented Step actions. _<https://github.com/happybara-io/WorkflowBuddy#available-steps|Docs with more info>._",
                    "verbatim": False,
                },
            },
            {
                "type": "section",
                "block_id": "T67CM",
                "fields": [
                    {
                        "type": "plain_text",
                        "text": "• Slack: Create a Channel",
                        "emoji": True,
                    },
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
                    {
                        "type": "plain_text",
                        "text": "• Utils: Get Random UUID",
                        "emoji": True,
                    },
                ],
            },
            {"type": "divider", "block_id": "P5IhY"},
            {
                "type": "image",
                "block_id": "jOE=2",
                "image_url": "https://s3.happybara.io/common/bara-footer-dark.jpg",
                "alt_text": "happybara.io",
                "image_width": 2400,
                "image_height": 640,
                "image_bytes": 250880,
                "is_animated": True,
                "fallback": "2400x640px image",
            },
            {"type": "divider", "block_id": "6KS"},
            {
                "type": "context",
                "block_id": "BYcLn",
                "elements": [
                    {
                        "type": "image",
                        "image_url": "https://s3.happybara.io/happybara/main_logo.png",
                        "alt_text": "happybara.io",
                    },
                    {
                        "type": "mrkdwn",
                        "text": "Proudly built by <https://happybara.io|Happybara>.",
                        "verbatim": False,
                    },
                ],
            },
        ],
        "private_metadata": "",
        "callback_id": "",
        "state": {
            "values": {
                "+W+Rm": {
                    "action_update_fail_notify_channels": {
                        "type": "plain_text_input",
                        "value": "C045UDN9H6D",
                    }
                }
            }
        },
        "hash": "1678974682.bugIg1OL",
        "title": {"type": "plain_text", "text": "View Title", "emoji": True},
        "clear_on_close": False,
        "notify_on_close": False,
        "close": None,
        "submit": None,
        "previous_view_id": None,
        "root_view_id": "V043VV9PEN8",
        "app_id": "A040W1RHGBX",
        "external_id": "",
        "app_installed_team_id": "TKM6AU1FG",
        "bot_id": "B040SD6RZK8",
    },
    "actions": [
        {
            "type": "plain_text_input",
            "block_id": "+W+Rm",
            "action_id": "action_update_fail_notify_channels",
            "value": "C045UDN9H6D",
            "action_ts": "1678974686.747841",
        }
    ],
}


# C045UDN9H6D
