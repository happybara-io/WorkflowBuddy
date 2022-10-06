import os
import random
import re
import logging
import requests
import shelve
import json
import copy
import constants as c
from urllib import parse, response
import slack_sdk
import slack_sdk.errors
from datetime import datetime, timedelta
from pathlib import Path

logging.basicConfig(level=logging.DEBUG)

# !! THIS ONLY WORKS IF YOU HAVE A SINGLE PROCESS
IN_MEMORY_WRITE_THROUGH_CACHE = {}
PERSISTED_JSON_FILE = "workflow-buddy-db.json"
Path(PERSISTED_JSON_FILE).touch()
# on startup, load current contents into cache
with open(PERSISTED_JSON_FILE, "r") as jf:
    try:

        IN_MEMORY_WRITE_THROUGH_CACHE = json.load(jf)
        logging.info("Cache loaded from file")
    except json.decoder.JSONDecodeError as e:
        logging.warning("Unable to load from file, starting empty cache.")
        IN_MEMORY_WRITE_THROUGH_CACHE = {}
logging.info(f"Starting DB: {IN_MEMORY_WRITE_THROUGH_CACHE}")


###################
# Utils
###################
def get_block_kit_builder_link(type="home", view=None, blocks=[]) -> str:
    block_kit_base_url = "https://app.slack.com/block-kit-builder/"
    payload = view
    if view is None:
        payload = {"type": type, "blocks": blocks}
    json_str = json.dumps(payload)
    return parse.quote(f"{block_kit_base_url}#{json_str}", safe="/:?=&#")


# TODO: accept any of the keyword args that are allowed?
def generic_event_proxy(logger: logging.Logger, event: dict, body: dict) -> None:
    event_type = event.get("type")
    logger.info(f"||{event_type}|BODY:{body}")
    try:
        workflow_webhooks_to_request = db_get_event_config(event_type)
        db_remove_unhandled_event(event_type)
    except KeyError:
        db_set_unhandled_event(event_type)
        return

    for webhook_config in workflow_webhooks_to_request:
        should_filter_reason = should_filter_event(webhook_config, event)
        if should_filter_reason:
            logger.info(f"Filtering event. Reason:{should_filter_reason} event:{event}")
            continue

        if webhook_config.get("raw_event"):
            json_body = event
        else:
            json_body = flatten_payload_for_slack_workflow_builder(event)
        resp = send_webhook(webhook_config["webhook_url"], json_body)
        if resp.status_code >= 300:
            logger.error(f"{resp.status_code}:{resp.text}|config:{webhook_config}")
    logger.info("Finished sending all webhooks for event")


def send_webhook(url, body: dict) -> requests.Response:
    logging.debug(f"body to send:{body}")
    resp = requests.post(url, json=body)
    logging.info(f"{resp.status_code}: {resp.text}")
    return resp


def db_get_unhandled_events() -> dict:
    try:
        return IN_MEMORY_WRITE_THROUGH_CACHE["unhandled_events"]
    except KeyError:
        return []


def db_remove_unhandled_event(event_type) -> None:
    try:
        IN_MEMORY_WRITE_THROUGH_CACHE["unhandled_events"].remove(event_type)
        logging.info(f"Remove unhandled event: {event_type}")
        sync_cache_to_disk()
    except ValueError:
        pass


def db_set_unhandled_event(event_type) -> None:
    logging.info(f"Adding unhandled event: {event_type}")
    try:
        IN_MEMORY_WRITE_THROUGH_CACHE["unhandled_events"].append(event_type)
    except KeyError:
        IN_MEMORY_WRITE_THROUGH_CACHE["unhandled_events"] = [event_type]
    sync_cache_to_disk()


def db_get_event_config(event_type) -> dict:
    return IN_MEMORY_WRITE_THROUGH_CACHE[event_type]


def sync_cache_to_disk() -> None:
    logging.debug(f"Syncing cache to disk - {IN_MEMORY_WRITE_THROUGH_CACHE}")
    json_str = json.dumps(IN_MEMORY_WRITE_THROUGH_CACHE, indent=2)
    with open(PERSISTED_JSON_FILE, "w") as jf:
        jf.write(json_str)


def db_add_webhook_to_event(
    event_type, name, webhook_url, adding_user_id, filter_reaction=None
) -> None:
    new_webhook = {"name": name, "webhook_url": webhook_url, "added_by": adding_user_id}
    if filter_reaction:
        new_webhook["filter_reaction"] = filter_reaction
    try:
        IN_MEMORY_WRITE_THROUGH_CACHE[event_type].append(new_webhook)
    except KeyError:
        IN_MEMORY_WRITE_THROUGH_CACHE[event_type] = [new_webhook]
    sync_cache_to_disk()


def db_remove_event(event_type) -> None:
    try:
        del IN_MEMORY_WRITE_THROUGH_CACHE[event_type]
        sync_cache_to_disk()
    except KeyError:
        logging.info("Key doesnt exist to delete")
        pass


def db_import(new_data) -> None:
    count = len(new_data.keys())
    for k, v in new_data.items():
        IN_MEMORY_WRITE_THROUGH_CACHE[k] = v
    sync_cache_to_disk()
    return count


def db_export() -> dict:
    return IN_MEMORY_WRITE_THROUGH_CACHE


def update_app_home(client, user_id, view=None) -> None:
    app_home_view = view
    if not view:
        app_home_view = build_app_home_view()
    client.views_publish(user_id=user_id, view=app_home_view)


def build_app_home_view() -> dict:
    data = db_export()

    blocks = copy.deepcopy(c.APP_HOME_HEADER_BLOCKS)
    unhandled_events = db_get_unhandled_events()
    if len(unhandled_events) > 0:
        blocks.extend(
            [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"⚠️ *event types without a destination configured:* `{unhandled_events}` ⚠️",
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
    if len(data.keys()) < 1:
        blocks.append(
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"• :shrug: Nothing here yet! Try using the `Add` or `Import` options.",
                },
            }
        )
    for event_type, webhook_list in data.items():
        if event_type == "unhandled_events":
            continue
        single_event_row = [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f":black_small_square: `{event_type}`",
                },
                "accessory": {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "Delete", "emoji": True},
                    "style": "danger",
                    "value": f"{event_type}",
                    "action_id": "event_delete_clicked",
                },
            },
            {
                "type": "context",
                "elements": [
                    {
                        "type": "plain_text",
                        "text": f"--> {str(webhook_list)}",
                        "emoji": True,
                    }
                ],
            },
        ]
        blocks.extend(single_event_row)

    blocks.extend(c.APP_HOME_MIDDLE_BLOCKS)

    footer_blocks = [
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
    try:
        resp = client.conversations_info(
            channel=conversation_id,
        )
        print(resp)
        if resp["channel"]["is_member"]:
            return "is_member"
        else:
            return "not_in_channel"
    except slack_sdk.errors.SlackApiError as e:
        print(type(e).__name__, e)
        return "unable_to_test"


# TODO: use this to make UX better for if users can select conversation that we might not be able to post to
def test_if_bot_able_to_post_to_conversation_deprecated(
    conversation_id: str, client: slack_sdk.WebClient
) -> str:
    status = "unknown"
    now = datetime.now()
    three_months = timedelta(days=90)
    post_at = int((now + three_months).timestamp())
    print("Time to post at", post_at)
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
        print("---------failure-----", e.get("error"), "-------")
        if e.get("error") == "not_in_channel":
            status = "not_in_channel"
        print(type(e).__name__, e)

    return status


def is_valid_slack_channel_name(channel_name: str) -> bool:
    # Channel names may only contain lowercase letters, numbers, hyphens, underscores and be max 80 chars.
    if (
        len(channel_name) <= 80
        and re.search(r"\d+", channel_name)
        and re.search(r"[a-z]+", channel_name)
        and re.search(r"[A-Z]+", channel_name)
        and re.search(r"\W+", channel_name)
        and not re.search(r"\s+", channel_name)
    ):
        return True
    else:
        return False
    # return len(channel_name) <= 80 and re.match("^[a-z0-9_-]*$", channel_name)


def is_valid_url(url: str) -> bool:
    return (url[:8] == "https://") or (url[:7] == "http://")


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
    try:
        # make resp text usable in future webhooks/json elements
        sanitized = json.dumps(sanitized)
        sanitized.replace('"', '\\"')
        logging.debug(f"Escaped resp is {sanitized}")
    except json.JSONDecodeError:
        pass
    return sanitized


def load_json_body_from_input_str(input_str: str) -> dict:
    # TODO: probably need a better handle on this, or make it very obvious to users that we will do it
    input_str = input_str.replace(
        '""', '"'
    )  # ran into JSON parsing issues when JSON string inside body string and Slack
    return json.loads(input_str)


def should_filter_event(webhook_config: dict, event: dict) -> bool:
    # from past experience, make sure to explicitly log if you drop in case logic is messed up
    event_type = event.get("type")
    should_filter_reason = None

    if event_type == c.EVENT_REACTION_ADDED:
        # https://api.slack.com/events/reaction_added
        filter_react = webhook_config.get("filter_react", "")
        filter_channel = webhook_config.get("filter_channel", "")
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
        filter_channel = webhook_config.get("filter_channel", "")
        channel_id = event.get("channel")
        if filter_channel and filter_channel != channel_id:
            should_filter_reason = (
                f"No channel match: {filter_channel} but got {channel_id}."
            )

    return should_filter_reason


def flatten_payload_for_slack_workflow_builder(event):
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
