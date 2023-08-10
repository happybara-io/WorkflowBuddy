import logging
import os
import random

import buddy.constants as c

from flask import Flask, jsonify, request, render_template
from slack_bolt import App
from slack_bolt.adapter.flask import SlackRequestHandler


import buddy
import buddy.errors
import buddy.utils as utils
import buddy.db as db
import buddy.middleware as middleware
from sqlalchemy import text
from slack_bolt import App
from slack_bolt.oauth.oauth_settings import OAuthSettings

# attempting and failing to silence DEBUG loggers
level = (
    logging.DEBUG
    if os.environ.get(c.ENV_LOG_LEVEL, "INFO") == "DEBUG"
    else logging.INFO
)
logging.basicConfig(level=level)
logger = logging.getLogger(__name__)

logging.info("Starting app...")
logger.info("Starting app...")
ENV = os.environ.get(c.ENV_ENV, "DEV")
slack_client_id = os.environ[c.ENV_SLACK_CLIENT_ID]
encryption_key = os.environ.get(c.ENV_SECRET_ENCRYPTION_KEY)
ignore_encryption_warning = os.environ.get(c.ENV_IGNORE_ENCRYPTION, False)
if not encryption_key and not ignore_encryption_warning:
    logger.warning(
        "[!] Starting server without an encryption key...data will not be encrypted at rest by this application."
    )

db_engine = db.DB_ENGINE

with db_engine.connect() as conn:
    try:
        conn.execute(text("select count(*) from team_config"))
    except Exception as e:
        logger.exception(e)
        logger.info("Creating all tables...")
        db.create_tables(db_engine)


# Seeing this odd error popping up, hoping it was a mistake during development:
# "Although the app should be installed into this workspace,.."
# Their comment for how it happens  -->
# > This situation can arise if:
# >   * A developer installed the app from the "Install to Workspace" button in Slack app config page
#  >   * The InstallationStore failed to save or deleted the installation for this workspace
# src: https://github.com/slackapi/bolt-python/blob/12aae7ff9ecf49c2f1d11a8dc81088e84f26960e/slack_bolt/middleware/authorization/multi_teams_authorization.py#L90

slack_app = App(
    signing_secret=os.environ[c.ENV_SLACK_SIGNING_SECRET],
    oauth_settings=OAuthSettings(
        client_id=slack_client_id,
        client_secret=os.environ[c.ENV_SLACK_CLIENT_SECRET],
        scopes=c.SCOPES,
        user_scopes=c.USER_SCOPES,
        installation_store=db.INSTALLATIION_STORE,
        state_store=db.OAUTH_STATE_STORE,
    ),
)


# TODO: this is confusing to users (found during my QA testing) when it happens from something in the background
# @slack_app.error
# def custom_error_handler(
#     error: Union[BoltError, SlackApiError],
#     body: dict,
#     client: slack_sdk.WebClient,
#     context: BoltContext,
#     logger: logging.Logger,
# ):
#     # kwargs available https://slack.dev/bolt-python/api-docs/slack_bolt/kwargs_injection/args.html
#     logger.exception(f"Error: {error}")
#     logger.info(f"Request body: {body}")

#     fail_text = (
#         f"Dang, sorry that last action didn't run correctly. Error:\n```\n{error}\n```"
#     )
#     try:
#         if context.user_id:
#             resp = client.chat_postMessage(channel=context.user_id, text=fail_text)
#     except Exception as e:
#         logger.error(
#             f"Failed trying to send error handler message to {context.user_id}"
#         )


###########################
# Slack App listeners &
# Instantiate all Steps visible to users
############################
buddy.register_listeners(slack_app)

###########################
# Slack App Middleware
############################
slack_app.use(middleware.log_request)

###########################
# Flask app stuff
############################
flask_app = Flask(__name__)
handler = SlackRequestHandler(slack_app)


@flask_app.route("/", methods=["GET"])
def home():
    return render_template("index.html", dev=ENV)


@flask_app.route("/health", methods=["GET"])
def health():
    return jsonify({"ok": True}), 201


@flask_app.route("/reflect", methods=["POST"])
def reflect_body():
    """
    Reflects the request body to ease integration testing of workflows
    """
    request_body = request.get_json()
    return request_body, 200


@flask_app.route("/random-fail", methods=["GET"])
def random_fail():
    # doesn't need to be all of them, just a random assortment of 4xx + 5xx
    random_http_fail_errors = [400, 407, 410, 500, 503, 520, 577]
    fail_code = random.choice(random_http_fail_errors)
    return jsonify({"ok": False}), fail_code


@flask_app.route("/slack/events", methods=["POST"])
def slack_events():
    return handler.handle(request)


@flask_app.route("/slack/install", methods=["GET"])
def install():
    return handler.handle(request)


@flask_app.route("/slack/oauth_redirect", methods=["GET"])
def oauth_redirect():
    return handler.handle(request)


@flask_app.route("/webhook", methods=["POST"])
def inbound_webhook():
    d = request.data
    logger.info(f"#### RECEIVED ###: {d}")
    return jsonify({"ok": True}), 201


@flask_app.route("/workflow/finish-execution", methods=["POST"])
def finish_step_execution():
    json_body = request.json
    status_code, resp_body = utils.finish_step_execution_from_webhook(json_body)
    return jsonify(resp_body), status_code
