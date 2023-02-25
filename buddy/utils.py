import contextlib
import copy
import http
import json
import logging
import os
import random
import re
import shelve
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
from urllib import parse, response
import buddy.db as db
import time

import requests
from requests.exceptions import Timeout, ConnectionError
import slack_sdk
import slack_sdk.errors

import buddy.constants as c

logging.basicConfig(level=logging.DEBUG)


###################
# Utils
###################
def get_input_val(inputs: dict, key: str, default_val: Any) -> Any:
    return inputs.get(key, {"value": default_val})["value"]


def get_block_kit_builder_link(type="home", view=None, blocks=[]) -> str:
    block_kit_base_url = "https://app.slack.com/block-kit-builder/"
    payload = view
    if view is None:
        payload = {"type": type, "blocks": blocks}
    json_str = json.dumps(payload)
    return parse.quote(f"{block_kit_base_url}#{json_str}", safe="/:?=&#")


# TODO: accept any of the keyword args that are allowed?
def generic_event_proxy(
    logger: logging.Logger,
    event: dict,
    body: dict,
    team_id: Union[str, None],
    enterprise_id: Union[str, None],
) -> None:
    event_type = event.get("type")
    logger.info(f"||{event_type}|BODY:{body}")

    # TODO: this has gotta be plural
    event_configs = db.get_event_configs(
        event_type, team_id, enterprise_id=enterprise_id
    )
    if not event_configs:
        db.set_unhandled_event(event_type, team_id, enterprise_id=enterprise_id)
    else:
        db.remove_unhandled_event(event_type, team_id, enterprise_id=enterprise_id)

    # TODO: run through each event
    for ec in event_configs:
        should_filter_reason = should_filter_event(ec, event)
        if should_filter_reason:
            logger.info(f"Filtering event. Reason:{should_filter_reason} event:{event}")
            continue

        if ec.use_raw_event:
            json_body = event
        else:
            json_body = flatten_payload_for_slack_workflow_builder(event)
        resp = send_webhook(ec.webhook_url, json_body)
        if resp.status_code >= 300:
            logger.error(f"{resp.status_code}:{resp.text}|config:{ec}")
    logger.info("Finished sending all webhooks for event")


def send_webhook(
    url: str, body: dict, method="POST", params=None, headers=None
) -> requests.Response:
    if headers is None:
        headers = {"Content-Type": "application/json"}
    logging.debug(f"Method:{method}. body to send:{body}")

    for i in range(c.HTTP_REQUEST_RETRIES + 1):
        try:
            resp = requests.request(
                method=method, url=url, json=body, params=params, headers=headers
            )
            logging.info(f"{resp.status_code}: {resp.text}")
            if resp.status_code < 300:
                return resp
        except (ConnectionError, Timeout) as e:
            # try again, unless it's already the last try
            final_index = c.HTTP_REQUEST_RETRIES
            if i == final_index:
                raise e
        # Don't hold up server long, but give a tiny break for whatever we're calling
        time.sleep(0.2)


def update_app_home(
    client, user_id, team_id: str, enterprise_id: Optional[str] = None, view=None
) -> None:
    app_home_view = view
    if not view:
        app_home_view = build_app_home_view(team_id, enterprise_id=enterprise_id)
    client.views_publish(user_id=user_id, view=app_home_view)


def build_app_home_view(team_id: str, enterprise_id: Optional[str] = None) -> dict:
    # TODO: gotta pull existing events - this might be just as easy as team config
    team_config = db.get_team_config(team_id, enterprise_id=enterprise_id)
    event_configs: List[db.EventConfig] = team_config.event_configs
    unhandled_events = comma_str_to_list(team_config.unhandled_events or "")

    blocks = copy.deepcopy(c.APP_HOME_HEADER_BLOCKS)
    team_usages = db.get_team_action_usage(team_id)
    blocks.extend(
        [
            {
                "type": "header",
                "text": {"type": "plain_text", "text": f"Team Usage", "emoji": True},
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"Slack team id: `{team_id}`",
                },
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"```\n{team_usages}\n```",
                },
            },
        ]
    )

    blocks.extend(copy.deepcopy(c.APP_HOME_EVENT_TRIGGER_BLOCKS))
    if unhandled_events:
        blocks.extend(
            [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"⚠️ *events being received, but no URL destination to send to:* `{unhandled_events}` ⚠️",
                    },
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"   ",
                    },
                },
            ]
        )
    if not event_configs:
        blocks.append(
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "• :shrug: Nothing here yet! Try using the `Add` or `Import` options.",
                },
            }
        )

    for ec in event_configs:
        single_event_row: List[Dict[str, Any]] = [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f":black_small_square: `{ec.event_type}`",
                },
                "accessory": {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "Delete", "emoji": True},
                    "style": "danger",
                    "value": f"EventConfig-{ec.id}",
                    "action_id": "event_delete_clicked",
                },
            },
            {
                "type": "context",
                "elements": [
                    {
                        "type": "plain_text",
                        "text": f"--> url:`{ec.webhook_url}`,  creator:`{ec.creator}`, created:`{str(ec.created_at)}`, filter_react:`{ec.filter_react}`, use_raw_event:{ec.use_raw_event}, desc:`{ec.desc}`.",
                        "emoji": True,
                    }
                ],
            },
        ]
        blocks.extend(single_event_row)

    blocks.extend(c.APP_HOME_MIDDLE_BLOCKS)

    footer_blocks: List[Dict[str, Any]] = [
        {"type": "divider"},
        {
            "type": "context",
            "elements": [
                {
                    "type": "image",
                    "image_url": c.URLS["images"]["bara_main_logo"],
                    "alt_text": "happybara.io",
                },
                {
                    "type": "mrkdwn",
                    "text": "Proudly built by <https://happybara.io|Happybara>.",
                },
            ],
        },
    ]
    chosen_image_style = random.choice(["dark", "light", "oceanic"])
    footer_image_url = c.URLS["images"]["footer"][chosen_image_style]
    footer_blocks.insert(
        0, {"type": "image", "image_url": footer_image_url, "alt_text": "happybara.io"}
    )
    blocks.extend(footer_blocks)
    return {"type": "home", "blocks": blocks}


def test_if_bot_is_member(conversation_id: str, client: slack_sdk.WebClient) -> str:
    # now that we have chat:write.public, membership only matters for other types
    try:
        resp = client.conversations_info(
            channel=conversation_id,
        )
        logging.debug(resp)
        if resp["channel"]["is_member"]:
            return "is_member"
        elif resp["channel"]["is_channel"] and not resp["channel"]["is_private"]:
            return "not_member_but_public"
        else:
            return "not_in_convo"
    except slack_sdk.errors.SlackApiError as e:
        logging.error(e)
        if e.response["error"] == "channel_not_found":
            # happens for private channels that bot can't "see"
            return "not_in_convo"
        return "unable_to_test"


# TODO: use this to make UX better for if users can select conversation that we might not be able to post to
def test_if_bot_able_to_post_to_conversation_deprecated(
    conversation_id: str, client: slack_sdk.WebClient
) -> str:
    status = "unknown"
    now = datetime.now()
    three_months = timedelta(days=90)
    post_at = int((now + three_months).timestamp())
    text = "Testing channel membership. If you see this, please ignore."

    # Attempt to schedule a message - ask for forgiveness, not permission
    try:
        resp = client.chat_scheduleMessage(
            channel=conversation_id, text=text, post_at=post_at
        )
        print(resp)
        scheduled_id = resp["scheduled_message_id"]
        resp = client.chat_deleteScheduledMessage(
            channel=conversation_id, scheduled_message_id=scheduled_id
        )
        print(resp)
        status = "can_post"
    except slack_sdk.errors.SlackApiError as e:
        print("---------failure-----", e.response["error"], "-------")
        if e.response["error"] == "not_in_channel":
            status = "not_in_channel"
        print(type(e).__name__, e)

    return status


def is_valid_slack_channel_name(channel_name: str) -> bool:
    # Channel names may only contain lowercase letters, numbers, hyphens, underscores and be max 80 chars.
    return bool(
        (
            len(channel_name) <= 80
            and re.search(r"\d+", channel_name)
            and re.search(r"[a-z]+", channel_name)
            and re.search(r"[A-Z]+", channel_name)
            and re.search(r"\W+", channel_name)
            and not re.search(r"\s+", channel_name)
        )
    )


def is_valid_url(url: str) -> bool:
    return url.startswith("https://") or url.startswith("http://")


def build_add_webhook_modal():
    add_webhook_form_blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": "Adding new events as Workflow triggers",
                "emoji": True,
            },
        },
        {
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": "<https://github.com/happybara-io/WorkflowBuddy#-quickstarts|Quickstart Guide for reference>.",
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
                "text": "*2. ⭐(Here!) Set up the connection between `event` and `webhook URL`.*",
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
        {"type": "divider"},
        {
            "type": "input",
            "block_id": "event_type_input",
            "element": {
                "type": "plain_text_input",
                "action_id": "event_type_value",
                "placeholder": {"type": "plain_text", "text": "app_mention"},
            },
            "label": {"type": "plain_text", "text": "Event Type", "emoji": True},
        },
        {
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": "The Slack event type you want to connect to your workflow, e.g. `app_mention`. <https://api.slack.com/events|Full list>.",
                }
            ],
        },
        {
            "type": "input",
            "block_id": "desc_input",
            "element": {"type": "plain_text_input", "action_id": "desc_value"},
            "label": {"type": "plain_text", "text": "Description", "emoji": True},
        },
        {
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": "In 6 months you won't remember why you connected `app_mention` to `https://abc.webhook.com`. This field lets you save context for your team.",
                }
            ],
        },
        {
            "type": "input",
            "block_id": "webhook_url_input",
            "element": {
                "type": "plain_text_input",
                "action_id": "webhook_url_value",
                "placeholder": {
                    "type": "plain_text",
                    "text": "https://hooks.slack.com/workflows/...",
                },
            },
            "label": {"type": "plain_text", "text": "Webhook URL", "emoji": True},
        },
        {
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": "You should have gotten this Webhook URL from your Slack Workflow, unless you are following the <https://github.com/happybara-io/WorkflowBuddy/#proxy-slack-events-to-another-service|advanced usage>.",
                }
            ],
        },
        {
            "type": "input",
            "optional": True,
            "block_id": "filter_reaction_input",
            "element": {
                "type": "plain_text_input",
                "action_id": "filter_reaction_value",
                "placeholder": {
                    "type": "plain_text",
                    "text": "smiley",
                },
            },
            "label": {"type": "plain_text", "text": "Filter Reaction", "emoji": True},
        },
        {
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": "Optionally filter `reaction_added` events to a single reaction/emoji e.g. :smiley:.",
                }
            ],
        },
    ]

    add_webhook_modal = {
        "type": "modal",
        "callback_id": "webhook_form_submission",
        "title": {"type": "plain_text", "text": "Add Webhook"},
        "submit": {"type": "plain_text", "text": "Add"},
        "blocks": add_webhook_form_blocks,
    }
    return add_webhook_modal


def sanitize_webhook_response(resp_text: str) -> str:
    # need to make sure if we get JSON back, it's properly sanitized so it can be used downstream
    sanitized = resp_text.replace("\n", "")
    with contextlib.suppress(json.JSONDecodeError):
        # make resp text usable in future webhooks/json elements
        sanitized = json.dumps(sanitized)
        sanitized.replace('"', '\\"')
        logging.debug(f"Escaped resp is {sanitized}")
    return sanitized


def clean_json_quotes(s: str) -> str:
    # slack adding weird smart quotes on Mac, try to handle any smart quotes.
    # Need to use this utility likely wherever we allow JSON input from users.
    s = s.replace("“", '"')
    s = s.replace("”", '"')
    return s


def sanitize_unescaped_quotes_and_load_json_str(s: str, strict=False) -> dict:  # type: ignore
    # TODO: one thing this doesn't handle, is if the unescaped text includes valid JSON - then you're just out of luck
    js_str = s
    prev_pos = -1
    curr_pos = 0
    while curr_pos > prev_pos:
        # after while check, move marker before we overwrite it
        prev_pos = curr_pos
        try:
            return json.loads(js_str, strict=strict)
        except json.JSONDecodeError as err:
            curr_pos = err.pos
            if curr_pos <= prev_pos:
                # previous change didn't make progress, so error
                raise err

            # find the previous " before e.pos
            prev_quote_index = js_str.rfind('"', 0, curr_pos)
            # escape it to \"
            js_str = js_str[:prev_quote_index] + "\\" + js_str[prev_quote_index:]


def load_json_body_from_untrusted_input_str(input_str: str) -> dict:
    # TODO: probably need a better handle on this, or make it very obvious to users that we will do it
    input_str = input_str.replace('""{', '"{').replace(
        '}""', '}"'
    )  # ran into JSON parsing issues when JSON string inside body string and Slack
    deny_control_characters = False
    data = sanitize_unescaped_quotes_and_load_json_str(
        input_str, strict=deny_control_characters
    )

    for k, v in data.items():
        convert_newline_to_list = k.startswith("__")
        if convert_newline_to_list:
            print("CONVERTING", k, "|", v, "|")
            # do our best to handle any odd data without causing errors
            data[k] = v.split("\n") if type(v) == str else v
    return data


def should_filter_event(event_config: db.EventConfig, event: dict) -> Optional[str]:
    # from past experience, make sure to explicitly log if you drop in case logic is messed up
    event_type = event.get("type")
    should_filter_reason = None

    if event_type == c.EVENT_REACTION_ADDED:
        # https://api.slack.com/events/reaction_added
        filter_react = event_config.filter_react or ""
        filter_channel = event_config.filter_channel or ""
        # allow messy config
        filter_react = filter_react.replace(":", "")
        reaction = event.get("reaction")
        channel_id = event.get("item", {}).get("channel")
        if filter_react and filter_react != reaction:
            should_filter_reason = f"No emoji match: {filter_react} but got {reaction}."
        elif filter_channel and filter_channel != channel_id:
            should_filter_reason = (
                f"No channel match: {filter_channel} but got {channel_id}."
            )
    elif event_type == c.EVENT_APP_MENTION:
        filter_channel = event_config.filter_channel or ""
        channel_id = event.get("channel")
        if filter_channel and filter_channel != channel_id:
            should_filter_reason = (
                f"No channel match: {filter_channel} but got {channel_id}."
            )

    return should_filter_reason


def flatten_payload_for_slack_workflow_builder(event):
    # sourcery skip: lift-return-into-if, switch
    # TODO: seems like a good place to consistently add common data like team_id, etc.
    flat_payload = {}
    # see slack limitations - 20 variables max, no nested https://slack.com/help/articles/360041352714-Create-more-advanced-workflows-using-webhooks
    # this has to match templates
    et = event["type"]
    if et == "reaction_added":
        flat_payload = {
            "type": et,
            "user": event["user"],
            "reaction": event["reaction"],
            "item_user": event["item_user"],
            "item_type": event["item"]["type"],
            "item_channel": event["item"]["channel"],
            "item_ts": event["item"]["ts"],
            "event_ts": event["event_ts"],
        }
    elif et == "channel_created":
        flat_payload = {
            "type": et,
            "channel_id": event["channel"]["id"],
            "channel_name": event["channel"]["name"],
            "channel_created": str(event["channel"]["created"]),
            "channel_creator": event["channel"]["creator"],
        }
    else:
        # TODO: gotta do this for other events, otherwise key info will be missed in nested objects
        flat_payload = event
    return flat_payload


def includes_slack_workflow_variable(value: Union[str, None]) -> bool:
    # Slack includes them like I am a value with {{65591853-edfe-4721-856d-ecd157766461==user.name}} in it
    if value is None:
        return False

    pattern = "^.*{{.*==.*}}.*$"
    return re.search(pattern, value) is not None


def pretty_json_error_msg(prefix: str, orig_input: str, e: json.JSONDecodeError) -> str:
    start_index = e.pos - 3
    end_index = e.pos + 4  # 1 extra cuz range is non-inclusive
    problem_area = f"{e.doc[start_index:end_index]}"
    return f"{prefix} Error: {str(e)}.\n|Problem Area(chars{start_index}-{end_index}):-->{problem_area}<--|\nInput was: {repr(orig_input)}."


def dynamic_modal_top_blocks(action_name: str, **kwargs):
    if action_name == "find_message":
        context_text = ""
        try:
            user_token = kwargs["user_token"]
            if not user_token:
                logging.error("User token is empty! What gives!")
            client = slack_sdk.WebClient(token=user_token)
            resp = client.auth_test(token=user_token)
            context_text = f"> Current authed user for search is: <@{resp.get('user_id')}>. Results will match what is visible to them. Questions? Check the <{c.URLS['github-repo']['home']}|repo for info.>"
        except KeyError:
            context_text = f"> ❌💥 *Need a valid SLACK_USER_TOKEN secret for {c.UTILS_ACTION_LABELS[action_name]}.* ❌"
        except slack_sdk.errors.SlackApiError as e:
            logging.error(e.response)
            context_text = (
                f"> ❌💥 *Slack Error: Need a valid user token. {e.response['error']}.* ❌"
            )
        return [
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": context_text,
                    }
                ],
            },
            {"type": "divider"},
        ]
    return []


def dynamic_outputs(action_name: str, inputs: dict) -> List:
    outputs: List[Dict[str, str]] = []
    if action_name == "random_member_picker":
        number_of_users = int(inputs["number_of_users"]["value"])
        outputs = []
        for i in range(1, number_of_users + 1):
            outputs.extend(
                [
                    {
                        "name": f"selected_user_{i}",
                        "label": f"Selected User {i}",
                        "type": "user",
                    },
                    {
                        "name": f"selected_user_id_{i}",
                        "label": f"Selected User ID {i}",
                        "type": "text",
                    },
                ]
            )
    elif action_name == "future":
        outputs = []
    else:
        raise ValueError(f"No dynamic outputs specified for {action_name}")
    return outputs


def filter_bots(client: slack_sdk.WebClient, user_list: List) -> List:
    # SLACKBOT might show up as a problem in the future;
    # not sure if it can be a channel member - depends on API you're working with
    filtered = []
    for user_id in user_list:
        resp = client.users_info(user=user_id)
        if not resp["ok"]:
            logging.error(resp)
            # TODO: handle common errors better
            continue

        user: Dict[str, Any] = resp.get("user", {})
        if user.get("is_bot") or user.get("is_workflow_bot"):
            continue

        filtered.append(user_id)

    return filtered


def sample_list_until_no_bots_are_found(
    client: slack_sdk.WebClient, members: List, number_of_users: int
) -> List:
    # TODO: if bots were prefiltered, could just use sample() and avoid this whole mess.
    # TODO: surface to users the fact that we are limiting iterations
    # if we give back less people than they expected - use case: a channel that has more bots than people
    max_num_allowed_iterations = 15
    no_bot_users_sample: List[str] = []
    runs = 0
    while (
        len(no_bot_users_sample) < number_of_users and runs < max_num_allowed_iterations
    ):
        rand_user = random.choice(members)
        if rand_user in no_bot_users_sample:
            continue
        filtered = filter_bots(client, [rand_user])
        no_bot_users_sample.extend(filtered)
    return no_bot_users_sample


def finish_an_execution(
    client: slack_sdk.WebClient, execution_id: str, failed=False, err_msg=""
) -> slack_sdk.web.SlackResponse:
    return (
        client.workflows_stepFailed(
            workflow_step_execute_id=execution_id, error={"message": err_msg}
        )
        if failed
        else client.workflows_stepCompleted(workflow_step_execute_id=execution_id)
    )


def finish_step_execution_from_webhook(body: dict) -> Tuple[int, dict]:
    status_code = 201
    resp_body = {"ok": True}
    err_msg = ""

    # TODO: this WILL NOT WORK for multi-tenant app until we figure out mapping from request info to team bot tokens
    bot_token = os.getenv("SLACK_BOT_TOKEN")
    client = slack_sdk.WebClient(token=bot_token)
    execution_id = body.get("execution_id")
    if not execution_id:
        return http.HTTPStatus.BAD_REQUEST, {
            "ok": False,
            "error": "Need a valid execution ID.",
        }
    mark_as_failed = body.get("mark_as_failed", False)
    if mark_as_failed:
        err_msg = body.get("err_msg", "Marked as failed from webhook completion event.")

    sk = body.get("sk")
    if not sk or len(sk) != c.WEBHOOK_SK_LENGTH:
        # TODO: put actual validation here in the future
        return http.HTTPStatus.FORBIDDEN, {
            "ok": False,
            "error": "Need a valid sk pair for the execution ID.",
        }

    try:
        finish_an_execution(
            client, execution_id, failed=mark_as_failed, err_msg=err_msg
        )
    except slack_sdk.errors.SlackApiError as e:
        status_code = 518
        resp_body = {"ok": False, "error": e.response["error"]}

    return status_code, resp_body


def parse_values_from_input_config(
    client, values: dict, inputs: dict, curr_action_config: dict
) -> Tuple[dict, dict]:
    inputs = inputs
    errors = {}

    for name, input_config in curr_action_config["inputs"].items():
        block_id = input_config["block_id"]
        action_id = input_config["action_id"]
        if input_config.get("type") == "channels_select":
            value = values[block_id][action_id]["selected_channel"]
        elif input_config.get("type") == "conversations_select":
            value = values[block_id][action_id]["selected_conversation"]
        elif input_config.get("type") == "checkboxes":
            value = json.dumps(values[block_id][action_id]["selected_options"])
        elif input_config.get("type") == "static_select":
            value = values[block_id][action_id]["selected_option"]["value"]
        else:
            # plain-text input by default
            value = values[block_id][action_id]["value"]

        validation_type = input_config.get("validation_type")
        # have to consider that people can pass variables, which would mess with some of validation
        value_has_workflow_variable = includes_slack_workflow_variable(value)
        if validation_type == "json" and value:
            value = clean_json_quotes(value)
            try:
                json.loads(value)
            except json.JSONDecodeError as e:
                errors[block_id] = f"Invalid JSON. Error: {str(e)}"
        elif (
            validation_type is not None
            and validation_type.startswith("integer")
            and not value_has_workflow_variable
        ):
            try:
                validation_type, upper_bound = validation_type.split("-")
            except ValueError:
                upper_bound = 100000000
            try:
                v = int(value)
                if v > int(upper_bound):
                    raise ValueError("Input is above our upper bound.")
            except ValueError:
                errors[block_id] = f"Must be a valid integer and <= {upper_bound}."
        elif validation_type == "email" and not value_has_workflow_variable:
            if "@" not in value:
                errors[block_id] = "Must be a valid email."
        elif validation_type == "url" and not value_has_workflow_variable:
            if not is_valid_url(value):
                errors[block_id] = "Must be a valid URL with `http(s)://.`"
        elif (
            validation_type == "slack_channel_name" and not value_has_workflow_variable
        ):
            if not is_valid_slack_channel_name(value):
                errors[
                    block_id
                ] = "Channel names may only contain lowercase letters, numbers, hyphens, underscores and be max 80 chars."
        elif (
            validation_type in ["membership_check", "msg_check"]
            and not value_has_workflow_variable
        ):
            status = test_if_bot_is_member(value, client)
            if status == "not_in_convo" or (
                status == "not_member_but_public" and validation_type != "msg_check"
            ):
                errors[
                    block_id
                ] = "Bot needs to be invited to the conversation before it can interact or read information about it, except for public channels."
        elif validation_type == "future_timestamp" and not value_has_workflow_variable:
            try:
                timestamp_int = int(value)
                curr = datetime.now().timestamp()
                if (timestamp_int - curr) < c.TIME_5_MINS:
                    readable_bad_dt = str(datetime.fromtimestamp(timestamp_int))
                    errors[
                        block_id
                    ] = f"Need a timestamp from > 5 mins in future, but got {readable_bad_dt}."
            except ValueError:
                errors[block_id] = f"Must be valid timestamp integer."
        elif (
            validation_type is not None
            and validation_type.startswith("str_length")
            and not value_has_workflow_variable
        ):
            v_type, str_len = validation_type.split("-")
            allowed_len = int(str_len)
            user_input_len = len(value)
            if user_input_len > allowed_len:
                errors[
                    block_id
                ] = f"Input must be shorter than {allowed_len}, but was {user_input_len}."

        inputs[name] = {"value": value}

    return inputs, errors


def sbool(s: str) -> bool:
    return s == "true"


def bool_to_str(b: bool) -> str:
    return "true" if b else "false"


def slack_deeplink(link_type: str, team_id: str, **kwargs) -> str:
    # https://api.slack.com/reference/deep-linking
    if link_type == "app_home":
        app_id = kwargs["app_id"]
        return f"slack://app?team={team_id}&id={app_id}&tab=home"
    elif link_type == "app_home_messages":
        app_id = kwargs["app_id"]
        return f"slack://app?team={team_id}&id={app_id}&tab=messages"
    elif link_type == "workspace":
        return f"slack://open?team={team_id}"
    elif link_type == "channel":
        channel_id = kwargs["channel_id"]
        return f"slack://channel?team={team_id}&id={channel_id}"
    elif link_type == "dm":
        user_id = kwargs["user_id"]
        return f"slack://user?team={team_id}&id={user_id}"
    elif link_type == "file":
        file_id = kwargs["file_id"]
        return f"slack://file?team={team_id}&id={file_id}"
    elif link_type == "share-file":
        file_id = kwargs["file_id"]
        return f"slack://share-file?team={team_id}&id={file_id}"
    else:
        raise ValueError("Unknown Deeplink type!")


def iget(inputs: dict, key: str, default: str) -> str:
    return inputs.get(key, {"value": default})["value"]


def update_blocks_with_previous_input_based_on_config(
    blocks: list, chosen_action: str, existing_inputs: dict, action_config_item: dict
) -> bool:
    did_edit = False
    # TODO: workflow builder keeps pulling old input on the step even when you are creating it totally new 🤔
    # kinda a crappy way to fill out existing inputs into initial values, but fast enough
    if existing_inputs:
        for input_name, value_obj in existing_inputs.items():
            prev_input_value = value_obj["value"]
            curr_input_config = action_config_item["inputs"].get(input_name)
            # loop through blocks to find it's home
            for block in blocks:
                block_id = block.get("block_id")
                if block_id == "general_options_action_select":
                    block["elements"][0]["initial_option"] = {
                        "text": {
                            "type": "plain_text",
                            "text": c.UTILS_ACTION_LABELS[chosen_action],
                            "emoji": True,
                        },
                        "value": chosen_action,
                    }

                    # checkboxes, just debug on it's own for now
                    if not sbool(
                        existing_inputs.get("debug_mode_enabled", {}).get("value")
                    ):
                        print("BYE BYE")
                        try:
                            del block["elements"][1]["initial_options"]
                        except KeyError:
                            pass
                    else:
                        print("SETTING IT")
                        # TODO: this breaks as soon as we change anything in the constants for it
                        block["elements"][1]["initial_options"] = [
                            {
                                "text": {
                                    "type": "mrkdwn",
                                    "text": "🐛 *Debug Mode*",
                                    "verbatim": False,
                                },
                                "value": "debug_mode",
                                "description": {
                                    "type": "mrkdwn",
                                    "text": "_When enabled, Buddy will pause before each step starts, send a message, and wait for you to click `Continue`._",
                                    "verbatim": False,
                                },
                            }
                        ]
                elif block_id == "debug_conversation_id_input":
                    debug_conversation_id = existing_inputs.get(
                        "debug_conversation_id", {}
                    ).get("value")
                    block["element"]["initial_conversation"] = debug_conversation_id
                else:
                    element_key = "element"
                    if curr_input_config and (
                        block_id == curr_input_config.get("block_id")
                    ):
                        # add initial placeholder info
                        if curr_input_config.get("type") == "conversations_select":
                            block[element_key][
                                "initial_conversation"
                            ] = prev_input_value
                        elif curr_input_config.get("type") == "channels_select":
                            block[element_key]["initial_channel"] = prev_input_value
                        elif curr_input_config.get("type") == "static_select":
                            block[element_key]["initial_option"] = {
                                "text": {
                                    "type": "plain_text",
                                    "text": curr_input_config.get("label", {}).get(
                                        prev_input_value
                                    )
                                    or prev_input_value.upper(),
                                    "emoji": True,
                                },
                                "value": prev_input_value,
                            }
                        elif curr_input_config.get("type") == "users_select":
                            block[element_key]["initial_user"] = prev_input_value
                        elif curr_input_config.get("type") == "checkboxes":
                            initial_options = json.loads(prev_input_value)
                            if len(initial_options) < 1:
                                try:
                                    del block[element_key]["initial_options"]
                                except KeyError:
                                    pass
                            else:
                                block["element"]["initial_options"] = initial_options
                        else:
                            # assume plain_text_input cuz it's common
                            block["element"]["initial_value"] = prev_input_value or ""
        did_edit = True
    else:
        logging.debug(
            "No previous inputs to reload, anything you see is happening because of bad coding."
        )

    return did_edit


def comma_str_to_list(s: str) -> List[str]:
    return [x for x in s.split(",") if x]
