import logging
import requests
import shelve
import json
import copy
import constants as c

logging.basicConfig(level=logging.DEBUG)

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


def send_webhook(url, json_body):
    resp = requests.post(url, json=json_body)
    logging.info(f"{resp.status_code}: {resp.text}")
    return resp


def db_get_event_config(event_type):
    return IN_MEMORY_WRITE_THROUGH_CACHE[event_type]


def sync_cache_to_disk():
    logging.debug(f"Syncing cache to disk - {IN_MEMORY_WRITE_THROUGH_CACHE}")
    json_str = json.dumps(IN_MEMORY_WRITE_THROUGH_CACHE, indent=2)
    with open(PERSISTED_JSON_FILE, "w") as jf:
        jf.write(json_str)


def db_add_webhook_to_event(event_type, name, webhook_url):
    new_webhook = {"name": name, "webhook_url": webhook_url}
    try:
        IN_MEMORY_WRITE_THROUGH_CACHE[event_type].append(new_webhook)
    except KeyError:
        IN_MEMORY_WRITE_THROUGH_CACHE[event_type] = [new_webhook]
    sync_cache_to_disk()


def db_remove_event(event_type):
    try:
        del IN_MEMORY_WRITE_THROUGH_CACHE[event_type]
        sync_cache_to_disk()
    except KeyError:
        logging.info("Key doesnt exist to delete")
        pass


def db_import(new_data):
    count = len(new_data.keys())
    for k, v in new_data.items():
        IN_MEMORY_WRITE_THROUGH_CACHE[k] = v
    sync_cache_to_disk()
    return count


def db_export():
    return IN_MEMORY_WRITE_THROUGH_CACHE


def build_app_home_view():
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
