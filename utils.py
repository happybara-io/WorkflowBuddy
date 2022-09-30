import os
import re
import logging
import requests
import shelve
import json
import copy
import constants as c
from urllib import parse
import slack_sdk
import slack_sdk.errors
from datetime import datetime, timedelta

logging.basicConfig(level=logging.DEBUG)


def get_block_kit_builder_link(type="home", view=None, blocks=[]) -> str:
    block_kit_base_url = "https://app.slack.com/block-kit-builder/"
    payload = view
    if view is None:
        payload = {"type": type, "blocks": blocks}
    json_str = json.dumps(payload)
    return parse.quote(f"{block_kit_base_url}#{json_str}", safe="/:?=&#")


# !! THIS ONLY WORKS IF YOU HAVE A SINGLE PROCESS
IN_MEMORY_WRITE_THROUGH_CACHE = {}
PERSISTED_JSON_FILE = "workflow-buddy-db.json"
# on startup, load current contents into cache
with open(PERSISTED_JSON_FILE, "a+") as jf:
    try:
        IN_MEMORY_WRITE_THROUGH_CACHE = json.load(jf)
    except json.decoder.JSONDecodeError:
        IN_MEMORY_WRITE_THROUGH_CACHE = {}
logging.info(f"Starting DB: {IN_MEMORY_WRITE_THROUGH_CACHE}")

###################
# Utils
###################


def send_webhook(url, body: dict) -> requests.Response:
    resp = requests.post(url, json=body)
    logging.info(f"{resp.status_code}: {resp.text}")
    return resp


def db_get_event_config(event_type) -> dict:
    return IN_MEMORY_WRITE_THROUGH_CACHE[event_type]


def sync_cache_to_disk() -> None:
    logging.debug(f"Syncing cache to disk - {IN_MEMORY_WRITE_THROUGH_CACHE}")
    json_str = json.dumps(IN_MEMORY_WRITE_THROUGH_CACHE, indent=2)
    with open(PERSISTED_JSON_FILE, "w") as jf:
        jf.write(json_str)


def db_add_webhook_to_event(event_type, name, webhook_url) -> None:
    new_webhook = {"name": name, "webhook_url": webhook_url}
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
    if len(data.keys()) < 1:
        blocks.append(
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f":shrug: Nothing here yet! Try using the `Add` or `Import` options.",
                },
            }
        )
    for event_type, webhook_list in data.items():
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

    blocks.extend(c.APP_HOME_FOOTER_BLOCKS)
    return {"type": "home", "blocks": blocks}


# TODO: use this to make UX better for if users can select conversation that we might not be able to post to
def test_if_bot_able_to_post_to_conversation(
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
