import logging
from slack_bolt import App

mlogger = logging.getLogger(__name__)


def register(slack_app: App):
    slack_app.message("help")(listener_help)


def listener_help(message, say):
    help_message = "Want help? Check the community discussion (https://github.com/happybara-io/WorkflowBuddy/discussions), or reach out to support@happybara.io."
    say(help_message)
