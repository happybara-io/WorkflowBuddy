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
    print(calling_datetime)
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
