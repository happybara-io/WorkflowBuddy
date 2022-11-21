import utils as sut
import logging
import json
import unittest.mock as mock
import pytest
import tests.tc as test_const
import slack_sdk.errors
from typing import List

test_logger = logging.getLogger("TestLogger")

# Start from a fresh DB unless we explicitly do something different
sut.sync_cache_to_disk(override_data={})


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
    body = sut.load_json_body_from_untrusted_input_str(input_str)
    assert type(body) is dict


def test_load_json_body_with_control_characters():
    input_str = """
{
    "key": "value
new_lined_value"
}
"""
    body = sut.load_json_body_from_untrusted_input_str(input_str)
    assert type(body) is dict


def test_load_json_body_with_valid_double_quotes():
    input_str = """
{
    "key": "I am a text value that includes a "quoted" piece of text"
}
"""
    body = sut.load_json_body_from_untrusted_input_str(input_str)
    assert type(body) is dict


def test_load_json_body_newlines_converted_to_list():
    converting_key = "__key"
    nonconvert_key = "nonconvert_key"
    input_str = """
{
"__key": "value_1
value_2
value_3",
"nonconvert_key": "value_1
value_2
value_3",
"__convert_to_single_list": "abc",
"regular_data": 5,
"__regular_data": 5,
"__empty_input": "",
"__item_should_not_be_absorbed_by_previous": "abcd"
}
"""
    body = sut.load_json_body_from_untrusted_input_str(input_str)
    print(body)
    assert type(body) is dict
    new_list = body[converting_key]
    assert type(new_list) is list
    assert len(new_list) == 3
    assert type(body[nonconvert_key]) is str
    test_if_no_characters_is_still_string = body["__convert_to_single_list"]
    assert (
        type(test_if_no_characters_is_still_string) is list
        and len(test_if_no_characters_is_still_string) == 1
    )
    assert type(body["__regular_data"]) is int
    assert type(body["__empty_input"]) is list
    assert type(body["__item_should_not_be_absorbed_by_previous"]) is list


@pytest.mark.parametrize("name, event", list(test_const.SLACK_DEMO_EVENTS.items()))
def test_flatten_payload(name, event):
    new_payload = sut.flatten_payload_for_slack_workflow_builder(event)
    num_keys = len(new_payload.keys())
    assert num_keys <= SLACK_WORKFLOW_BUILDER_WEBHOOK_VARIABLES_MAX
    assert num_keys > 2
    assert_dict_is_flat_and_all_keys_are_strings(new_payload)


@pytest.mark.parametrize(
    "value, expected_result",
    [
        (
            "I am a value with {{65591853-edfe-4721-856d-ecd157766461==user.name}} in it",
            True,
        ),
        ("abc@example.com", False),
        ("5", False),
        (None, False),
    ],
)
def test_includes_slack_workflow_variable(value, expected_result):
    result = sut.includes_slack_workflow_variable(value)
    assert (
        result == expected_result
    ), "Unexpected outcome when testing for Workflow variables."


@pytest.mark.parametrize("name, event", list(test_const.SLACK_DEMO_EVENTS.items()))
@mock.patch("utils.send_webhook")
def test_generic_event_proxy(patched_send, name, event):
    # TODO: Gotta mock out DB for each run to actually test something useful, otherwise it's unkown what you're hitting
    patched_send.return_value = FakeResponse(201, {"body": True})
    fake_team_id = "T014334"
    sut.generic_event_proxy(test_logger, event, {}, fake_team_id)


@pytest.mark.parametrize(
    "input_json_str, expected_result",
    [
        (
            "{“dq”:“Double quote”}",
            '{"dq":"Double quote"}',
        ),
    ],
)
def test_weird_quotes_cleaned_up_for_json(input_json_str, expected_result):
    output = sut.clean_json_quotes(input_json_str)
    assert output == expected_result
    json.loads(output)


def test_pretty_json_error_msg():
    prefix = "err1111: prefix message"
    orig_input = '{"key": "value}'
    try:
        json.loads(orig_input)
        pytest.fail(msg="JSON input didn't cause an error as expected.")
    except json.JSONDecodeError as e:
        msg = sut.pretty_json_error_msg(prefix, orig_input, e)
        assert type(msg) is str


@pytest.mark.parametrize(
    "notes, test_str, expected_error, expected_keys",
    [
        ("invalid json", "abcdefeggdg", True, None),
        ("empty", "{}", False, []),
        ("single extra quote", '{"key": "value with "quote inside"}', False, ["key"]),
        (
            "even number of quotes",
            '{"key": "value with "two quotes" inside"}',
            False,
            ["key"],
        ),
        (
            "Many quotes",
            '{"key": "naughty value in "quotes" yes it is; but "why"? would I "do" that?"}',
            False,
            ["key"],
        ),
        (
            "Many quotes",
            '{"key": "naughty value in "quotes"""""" yes it is; but "why"? would I "do" ""\n"\n that?"}',
            False,
            ["key"],
        ),
        (
            "actual broken json missing a quote",
            '{"key": "different json error that quote wont fix;}',
            True,
            None,
        ),
        (
            "valid unescaped JSON nested inside string - won't error, but won't come out as expected either.",
            '{"key": "trying to add special chars if they wrote example json like {"a": "b","c": "d"} "}',
            False,
            ["key", "c"],
        ),
        (
            "testing if empty is absorbing next item",
            '{"__empty_input": "","__item_should_not_be_absorbed_by_previous": "abcd"}',
            False,
            ["__empty_input", "__item_should_not_be_absorbed_by_previous"],
        ),
    ],
)
def test_sanitizing_unescaped_quotes(
    notes: str, test_str: str, expected_error: bool, expected_keys: List[str]
):
    try:
        out = sut.sanitize_unescaped_quotes_and_load_json_str(test_str)
        if expected_error:
            raise ValueError("Shouldn't have passed successfully with that input!")
        assert set(expected_keys) == set(out.keys())
        print("OUT", out)
    except json.JSONDecodeError as err:
        if not expected_error:
            raise err


def test_dynamic_outputs_random_member():
    action_name = "random_member_picker"
    inputs = {"number_of_users": {"value": "3"}}
    outputs = sut.dynamic_outputs(action_name, inputs)
    assert len(outputs) == 6


@pytest.mark.parametrize(
    "member_list, num_users, error_expected, side_effects",
    [
        ([], 1, True, []),
        (
            ["bot_user1", "user2", "user3", "user4"],
            2,
            False,
            [
                {"ok": True, "user": {"is_bot": True}},
                {"ok": True, "user": {"is_bot": False}},
                {"ok": True, "user": {"is_bot": False}},
                {"ok": True, "user": {"is_bot": False}},
            ],
        ),
    ],
)
def test_sample_list_until_no_bots_are_found(
    member_list, num_users, error_expected, side_effects
):
    mock_client = mock.MagicMock()
    mock_client.users_info.side_effect = side_effects

    try:
        users = sut.sample_list_until_no_bots_are_found(
            mock_client, member_list, num_users
        )
        if error_expected:
            pytest.fail("Yikes! expected an error to occur but none did.")
        assert len(set(users)) == num_users
    except IndexError as e:
        if not error_expected:
            raise e


def test_finish_step_execution_from_webhook():
    json_body = {
        "execution_id": "1132323232322",
        "sk": "1" * 20,
        "mark_as_failed": True,
    }
    with mock.patch("utils.slack_sdk.WebClient") as mock_class:
        # https://stackoverflow.com/questions/17731477/python-mock-class-instance-variable#17731909
        # instance = mock_class.return_value
        # instance.workflows_stepCompleted.return_value =
        code, body = sut.finish_step_execution_from_webhook(json_body)
    assert code == 201
    assert body["ok"]


def test_finish_step_execution_from_webhook_api_error():
    json_body = {
        "execution_id": "1132323232322",
        "sk": "1" * 20,
        "mark_as_failed": True,
        "err_msg": "Something blew up in external service.",
    }
    with mock.patch("utils.slack_sdk.WebClient") as mock_class:
        # https://stackoverflow.com/questions/17731477/python-mock-class-instance-variable#17731909
        instance = mock_class.return_value
        slack_error = slack_sdk.errors.SlackApiError("slack boom", {"error": "errmsg"})
        instance.workflows_stepCompleted.side_effect = slack_error
        instance.workflows_stepFailed.side_effect = slack_error
        code, body = sut.finish_step_execution_from_webhook(json_body)
        assert code == 518


@pytest.mark.parametrize(
    "bool_str, expected", [("true", True), ("false", False), ("random", False)]
)
def test_sbool(bool_str, expected):
    out = sut.sbool(bool_str)
    assert out == expected


@pytest.mark.skip()
def test_parse_values_from_input_config():
    # TODO: can create more confidence in this now that it's moved here for unit tests than in app
    pass


def test_slack_deeplink():
    team_id = "T0123456"
    app_id = "A123445"
    app_home_deeplink = sut.slack_deeplink("app_home", team_id, app_id=app_id)
    assert team_id in app_home_deeplink and app_id in app_home_deeplink
def test_db_integration_unhandled_event():
    sut.sync_cache_to_disk(override_data={})

    team_id = "T12345"
    new_event = "event_thing"

    unhandled = sut.db_get_unhandled_events(team_id)
    assert len(unhandled) == 0

    sut.db_remove_unhandled_event(team_id, new_event)

    sut.db_set_unhandled_event(team_id, new_event)

    unhandled = sut.db_get_unhandled_events(team_id)
    assert len(unhandled) == 1

    sut.db_remove_unhandled_event(team_id, new_event)

    unhandled = sut.db_get_unhandled_events(team_id)
    assert len(unhandled) == 0


def test_db_integration_event_config():
    sut.sync_cache_to_disk(override_data={})

    team_id = "T12345"
    test_event_type = "test_event"

    try:
        config = sut.db_get_event_config(team_id, test_event_type)
        assert False
    except KeyError:
        logging.debug("successfully failed.")

    import_data = {}
    import_data[test_event_type] = {"abc": "123"}
    sut.db_import(team_id, import_data)

    config = sut.db_get_event_config(team_id, test_event_type)
    assert type(config) is dict

    sut.db_remove_event(team_id, test_event_type)

    try:
        config = sut.db_get_event_config(team_id, test_event_type)
        assert False
    except KeyError:
        logging.debug("successfully failed.")
    sut.db_add_webhook_to_event(
        team_id, test_event_type, "namestr", "https://url", "U12234"
    )
    config = sut.db_get_event_config(team_id, test_event_type)
    assert type(config) is list
