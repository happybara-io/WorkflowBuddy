import json

import logging
import slack_sdk
from slack_bolt import App, Ack

mlogger = logging.getLogger(__name__)


def register(slack_app: App):
    slack_app.shortcut("message_details")(listener_shortcut_message_details)


def listener_shortcut_message_details(
    ack: Ack, shortcut: dict, client: slack_sdk.WebClient
):
    ack()

    blocks = [
        {"type": "section", "text": {"type": "mrkdwn", "text": "Message details:"}},
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"```{json.dumps(shortcut, indent=2)}```",
            },
        },
    ]
    client.views_open(
        trigger_id=shortcut["trigger_id"],
        view={
            "type": "modal",
            "title": {"type": "plain_text", "text": "Inspect Message"},
            "close": {"type": "plain_text", "text": "Close"},
            "blocks": blocks,
        },
    )
