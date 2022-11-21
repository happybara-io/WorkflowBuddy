from buddy.errors import WorkflowStepFailError
from buddy.types import Outputs
import buddy.utils as utils
import buddy.constants as c
import os
import random
import slack_sdk
import logging
import time
import uuid

logging.basicConfig(level=logging.DEBUG)

################################
# Step Actions funcs: take `inputs`, return Slack `outputs`
################################


def run_random_int(step: dict) -> Outputs:
    # TODO: input validation & error handling
    inputs = step["inputs"]
    lower_bound = int(inputs["lower_bound"]["value"])
    upper_bound = int(inputs["upper_bound"]["value"])
    rand_value = random.randint(lower_bound, upper_bound)
    return Outputs({"random_int_text": str(rand_value)})


def run_random_uuid(step: dict) -> Outputs:
    return Outputs({"random_uuid": str(uuid.uuid4())})


def run_conversations_create(inputs: dict, client: slack_sdk.WebClient) -> Outputs:
    channel_name = inputs["channel_name"]["value"]
    resp = client.conversations_create(name=channel_name)
    logging.debug(f"RESP|{resp}")
    if resp["ok"]:
        return Outputs(
            {
                "channel_id": resp["channel"]["id"],
                "channel_id_text": resp["channel"]["id"],
            }
        )

    errmsg = f"Slack err: {resp.get('error')}"
    logging.error(errmsg)
    raise WorkflowStepFailError(errmsg)


def run_find_user_by_email(inputs: dict, client: slack_sdk.WebClient) -> Outputs:
    user_email = inputs["user_email"]["value"]
    resp = client.users_lookupByEmail(email=user_email)
    if resp["ok"]:
        return Outputs(
            {
                "user": resp["user"]["id"],
                "user_id": resp["user"]["id"],
                "team_id": resp["user"]["team_id"],
                "real_name": resp["user"]["real_name"],
            }
        )

    errmsg = f"Slack err: {resp.get('error')}"
    logging.error(errmsg)
    raise WorkflowStepFailError(errmsg)


def run_find_message(
    step: dict,
    logger: logging.Logger,
) -> Outputs:
    # https://api.slack.com/methods/search.messages
    inputs = step["inputs"]
    search_query = inputs["search_query"]["value"]
    sort = inputs["sort"]["value"]
    sort_dir = inputs["sort_dir"]["value"]
    delay_seconds = inputs["delay_seconds"]["value"]
    fail_if_empty_results = utils.sbool(inputs["fail_if_empty_results"]["value"])

    try:
        delay_seconds = int(inputs["delay_seconds"]["value"])
        lower_bound = 0
        upper_bound = c.WAIT_STATE_MAX_SECONDS
        if delay_seconds <= lower_bound or delay_seconds > upper_bound:
            raise ValueError("Not in valid Workflow Buddy Wait Step range.")
    except ValueError:
        errmsg = f"err5466: seconds value is not in our valid range, given: {inputs['delay_seconds']['value']} but must be in {lower_bound} - {upper_bound}."
        raise WorkflowStepFailError(errmsg)

    # TODO: team_id is required attribute if using an org-token
    try:
        user_token = os.environ["SLACK_USER_TOKEN"]
        client = slack_sdk.WebClient(token=user_token)
    except KeyError:
        errmsg = "No SLACK_USER_TOKEN provided to Workflow Buddy - required for searching Slack messages."
        raise WorkflowStepFailError(errmsg)

    if delay_seconds > 0:
        seconds_needed_before_new_message_shows_in_search = delay_seconds
        time.sleep(seconds_needed_before_new_message_shows_in_search)

    kwargs = {"query": search_query, "count": 1, "sort": sort, "sort_dir": sort_dir}
    try:
        resp = client.search_messages(**kwargs)
        message = resp["messages"]["matches"][0]
        channel_id = message["channel"]["id"]
        return Outputs(
            {
                "channel": channel_id,
                "channel_id": channel_id,
                "message_ts": message["ts"],
                "permalink": message["permalink"],
                "message_text": message["text"],
                "user": message["user"],
                "user_id": message["user"],
            }
        )
    except IndexError:
        if not fail_if_empty_results:
            return Outputs({})
        errmsg = f"Search results came back empty for query: {search_query}."
        raise WorkflowStepFailError(errmsg)
    except slack_sdk.errors.SlackApiError as e:
        logger.error(e.response)
        errmsg = f"Slack Error: failed to search messages. {e.response['error']}"
        raise WorkflowStepFailError(errmsg)
