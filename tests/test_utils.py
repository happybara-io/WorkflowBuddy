import utils as sut
import json
import pytest


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
