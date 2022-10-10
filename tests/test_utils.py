import utils as sut
import logging
import json
import unittest.mock as mock
import pytest
import tests.tc as test_const

test_logger = logging.getLogger("TestLogger")


class FakeResponse:
    def __init__(self, status_code, body) -> None:
        self.status_code = status_code
        self.body = body


SLACK_WORKFLOW_BUILDER_WEBHOOK_VARIABLES_MAX = 20


def assert_dict_is_flat_and_all_keys_are_strings(d: dict):
    # Got error when I sent an integer instead of string to Slack for a variable
    # {"error":"invalid_webhook_format","ok":false,"response_metadata":{"messages":["[ERROR] invalid required field: 'channel_created'"]}}
    for k, v in d.items():
        assert (
            type(v) == str
        ), f"key:`{k}` was wrong type: {type(v)} vs str."  # implicitly, not dict


###############################################
# Tests
###############################################


def test_is_valid_slack_channel_name_too_long():
    name = "a" * 81
    is_valid = sut.is_valid_slack_channel_name(name)
    assert not is_valid


def test_is_valid_slack_channel_name_has_spaces_and_caps():
    name = "CAP_nocap woh"
    is_valid = sut.is_valid_slack_channel_name(name)
    assert not is_valid


def test_is_valid_slack_channel_name_happy_path():
    # Channel names may only contain lowercase letters, numbers, hyphens, underscores and be max 80 chars.
    name = "acceptable-channel-name_1"
    is_valid = sut.is_valid_slack_channel_name(name)
    assert not is_valid


def test_is_valid_url_happy_path_http():
    url = "http://abcdefg.com/you/arent-here/"
    is_valid = sut.is_valid_url(url)
    assert is_valid


def test_is_valid_url_happy_path_https():
    url = "https://abcdefg.com/you/ssl/"
    is_valid = sut.is_valid_url(url)
    assert is_valid


def test_is_valid_url_garbage():
    url = "silly other input text"
    is_valid = sut.is_valid_url(url)
    assert not is_valid


def test_load_json_body_from_input_with_nested_json():
    # testing scenario of JSON string output from previous step,
    # wanting to use it inside the JSON body of another webhook.
    input_str = """
{
"user": "Kevin Quinn",
"found": "TKM6AU1FG",
"webhook_status": "200",
"webhook_resp": ""{  \\"statusCode\\" : 200}""
}
"""
    body = sut.load_json_body_from_input_str(input_str)
    assert type(body) is dict


@pytest.mark.parametrize("name, event", list(test_const.SLACK_DEMO_EVENTS.items()))
def test_flatten_payload(name, event):
    new_payload = sut.flatten_payload_for_slack_workflow_builder(event)
    num_keys = len(new_payload.keys())
    assert num_keys <= SLACK_WORKFLOW_BUILDER_WEBHOOK_VARIABLES_MAX
    assert num_keys > 2
    assert_dict_is_flat_and_all_keys_are_strings(new_payload)


@pytest.mark.parametrize("name, event", list(test_const.SLACK_DEMO_EVENTS.items()))
@mock.patch("utils.send_webhook")
def test_generic_event_proxy(patched_send, name, event):
    # TODO: Gotta mock out DB for each run to actually test something useful, otherwise it's unkown what you're hitting
    patched_send.return_value = FakeResponse(201, {"body": True})
    sut.generic_event_proxy(test_logger, event, {})
