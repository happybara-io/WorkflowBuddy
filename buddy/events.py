import json

import logging
from slack_bolt import App, BoltContext
import slack_sdk

import buddy.utils as utils
import buddy.constants as c

mlogger = logging.getLogger(__name__)


def register(slack_app: App):
    slack_app.event(c.EVENT_APP_MENTION)(listener_generic_event_handler)
    slack_app.event(c.EVENT_CHANNEL_ARCHIVE)(listener_generic_event_handler)
    slack_app.event(c.EVENT_CHANNEL_CREATED)(listener_generic_event_handler)
    slack_app.event(c.EVENT_CHANNEL_DELETED)(listener_generic_event_handler)
    slack_app.event(c.EVENT_CHANNEL_UNARCHIVE)(listener_generic_event_handler)
    slack_app.event(c.EVENT_REACTION_ADDED)(listener_generic_event_handler)
    slack_app.event(c.EVENT_APP_HOME_OPENED)(listener_update_app_home)
    # Mediocre ability to track how many workflows currently are using App Steps
    # https://api.slack.com/workflows/steps#tracking
    # slack_app.event(c.EVENT_WORKFLOW_PUBLISHED)
    # slack_app.event(c.EVENT_WORKFLOW_UNPUBLISHED)
    # slack_app.event(c.EVENT_WORKFLOW_DELETED)
    # slack_app.event(c.EVENT_WORKFLOW_STEP_DELETED)


def listener_generic_event_handler(
    logger: logging.Logger, event: dict, body: dict, context: BoltContext
):
    utils.generic_event_proxy(logger, event, context.team_id, context.enterprise_id)


def listener_update_app_home(
    event: dict,
    logger: logging.Logger,
    client: slack_sdk.WebClient,
    context: BoltContext,
):
    team_id = context.team_id
    app_home_view = utils.build_app_home_view(
        context.team_id, enterprise_id=context.enterprise_id
    )
    client.views_publish(user_id=event["user"], view=app_home_view)
