import logging
import requests
import shelve
import json
import copy

import constants as c

DEFAULT_SHELF_DB = "workflow_buddy_db"


def send_webhook(url, json_body):
    resp = requests.post(url, json=json_body)
    logging.info(f"{resp.status_code}: {resp.text}")
    return resp


def db_get_event_config(event_type):
    with shelve.open(DEFAULT_SHELF_DB, writeback=True) as db:
        return db[event_type]


def db_add_webhook_to_event(event_type, name, webhook_url):
    with shelve.open(DEFAULT_SHELF_DB, writeback=True) as db:
        new_webhook = {
                'name': name,
                'webhook_url': webhook_url
            }
        try:
            db[event_type].append(new_webhook)
        except KeyError:
            db[event_type] = [new_webhook]


def db_remove_event(event_type):
    with shelve.open(DEFAULT_SHELF_DB, writeback=True) as db:
        try:
            del db[event_type]
        except KeyError:
            print("Key doesnt exist to delete")
            pass


def db_import(new_data):
    count = len(new_data.keys())
    with shelve.open(DEFAULT_SHELF_DB, writeback=True) as db:
        for k, v in new_data.items():
            db[k] = v
    return count


def db_export():
    data = {}
    with shelve.open(DEFAULT_SHELF_DB, writeback=True) as db:
        for k, v in db.items():
            data[k] = v
    print("DUMP", data)
    return data


def build_app_home_view():

    data = db_export()

    blocks = copy.deepcopy(c.APP_HOME_HEADER_BLOCKS)
    if len(data.keys()) < 1:
        blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f":shrug: Nothing here yet! Try using the `Add` or `Import` options.",
                }
            })
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

    print('blocks', blocks)
    return {"type": "home", "blocks": blocks}
