import logging
from datetime import datetime as dt
from unittest import mock
import json

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
    mock_resp.text = '{"ok":true}'
    mock_send_webhook.return_value = mock_resp
    step = {
        "inputs": {
            "webhook_url": {"value": "https://fake-webhook.com"},
            "http_method": {"value": "POST"},
        }
    }

    outputs = sut.run_webhook(step)
    assert outputs["webhook_status_code"] == str(mock_resp.status_code)
    json_dict = json.loads(outputs["webhook_response_text_unsanitized"])
    assert json_dict["ok"] == True
    s = json.loads(outputs["webhook_response_text"])
    assert type(s) == str


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
        ack, body, mock_client, context
    )
    assert type(resp) is dict, "Must have failed when trying to set new channels in DB"
    assert "none" in resp["readyMsg"]
    assert "<#C1234>" in resp["errMsg"]
    assert "<#C123456>" in resp["errMsg"]


@pytest.mark.parametrize(
    "action, mock_body",
    [
        (
            "continue",
            {
                "message": {"blocks": [{"type": "mrkdwn"}]},
                "user": {"id": "U1111"},
                "actions": [
                    {
                        "action_id": "manual_complete-continue",
                        "value": "fake-workflow-execute-id|+|fake-workflow-name|+|fake-workflow-id",
                    }
                ],
            },
        ),
        (
            "stop",
            {
                "message": {"blocks": [{"type": "mrkdwn"}]},
                "user": {"id": "U1111"},
                "actions": [
                    {
                        "action_id": "manual_complete-stop",
                        "value": "fake-workflow-execute-id|+|fake-workflow-name|+|fake-workflow-id",
                    }
                ],
            },
        ),
    ],
)
def test_manual_complete_continue_or_stop(action, mock_body):
    mock_client = mock.MagicMock(name="slack_client")
    context = MockContext()
    text, blocks = sut.manual_complete_continue_or_stop(
        mock_body, dummy_logger, mock_client, context
    )
    if action == "stop":
        assert "🛑" in text
        assert "👉" not in text
    elif action == "continue":
        assert "👉" in text
        assert "🛑" not in text


def test_run_json_extractor_broken_input():
    # This test was written based on a variable of the 'Response Text',
    # coming from our Webhook step - I guess the JSON string comes with extra
    # quotes? Is that from me?
    step = {
        "inputs": {
            "json_string": {"value": '"{\\"ok\\":true}"'},
            "jsonpath_expr": {"value": "$.ok"},
        }
    }
    outputs = sut.run_json_extractor(step)
    assert list(outputs.values()) == ["[]"]


def test_run_json_extractor_expected_function():
    step = {
        "inputs": {
            "json_string": {"value": '{"ok":true}'},
            "jsonpath_expr": {"value": "$.ok"},
        }
    }
    outputs = sut.run_json_extractor(step)
    assert list(outputs.values()) == ["True"]


def test_schedule_messages_still_handles_deprecated_post_at_key():
    mock_client = mock.MagicMock(name="slack_client")
    mock_client.chat_scheduleMessage.return_value = {
        "ok": True,
        "scheduled_message_id": "Q1111111",
    }
    inputs = {
        "channel": {"value": "C111111"},
        "post_at": {"value": "1669557726"},
        "msg_text": {"value": "I'm a silly message to send"},
    }
    out = sut.run_schedule_message(inputs, mock_client)
    slack_client_kwargs = mock_client.chat_scheduleMessage.call_args[1]
    assert type(slack_client_kwargs["post_at"]) is str


def test_schedule_messages_with_relative_times():
    mock_client = mock.MagicMock(name="slack_client")
    mock_client.chat_scheduleMessage.return_value = {
        "ok": True,
        "scheduled_message_id": "Q1111111",
    }
    inputs = {
        "channel": {"value": "C111111"},
        "relative_days": {"value": "115"},
        "relative_hours": {"value": "8"},
        "relative_minutes": {"value": "17"},
        "msg_text": {"value": "I'm a silly message to send"},
    }
    out = sut.run_schedule_message(inputs, mock_client)
    slack_client_kwargs = mock_client.chat_scheduleMessage.call_args[1]
    assert type(slack_client_kwargs["post_at"]) is str
