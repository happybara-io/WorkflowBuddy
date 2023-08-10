from buddy.step_actions import *
from buddy.actions import register as register_actions
from buddy.views import register as register_views
from buddy.shortcuts import register as register_shortcuts
from buddy.events import register as register_events
from buddy.messages import register as register_messages
from buddy.workflow_steps import register as register_workflow_steps

from slack_bolt import App


def register_listeners(slack_app: App):
    register_actions(slack_app)
    register_views(slack_app)
    register_shortcuts(slack_app)
    register_events(slack_app)
    register_messages(slack_app)
    register_workflow_steps(slack_app)
