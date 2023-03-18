import json
import logging
import os
import random
import copy
import string
import time
import uuid
from datetime import datetime, timedelta, timezone
import pprint

import slack_sdk
from slack_bolt import BoltContext, Ack
from jsonpath_ng import jsonpath
from jsonpath_ng.ext import parse

import buddy.constants as c
import buddy.utils as utils
import buddy.db as db
from buddy.errors import WorkflowStepFailError
from buddy.types import Outputs

from typing import List, Dict, Any, Union

logger = logging.getLogger("step_actions")

################################
# Step Actions funcs: take `inputs`, return Slack `outputs`
################################
# TODO: this has slowly become "move any Slack App function here so it's testable,
#  and only keep the initialization in app.py". That's fine, just confusing naming.


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
    try:
        resp = client.conversations_create(name=channel_name)
        return Outputs(
            {
                "channel_id": resp["channel"]["id"],
                "channel_id_text": resp["channel"]["id"],
            }
        )
    except slack_sdk.errors.SlackApiError as e:
        logger.error(e.response)
        errmsg = f"Slack Error: failed to create conversation. {e.response['error']}"
        raise WorkflowStepFailError(errmsg)


def run_find_user_by_email(inputs: dict, client: slack_sdk.WebClient) -> Outputs:
    user_email = inputs["user_email"]["value"]
    try:
        resp = client.users_lookupByEmail(email=user_email)
        return Outputs(
            {
                "user": resp["user"]["id"],
                "user_id": resp["user"]["id"],
                "team_id": resp["user"]["team_id"],
                "real_name": resp["user"]["real_name"],
            }
        )
    except slack_sdk.errors.SlackApiError as e:
        logger.error(e.response)
        errmsg = f"Slack Error: failed to get email. {e.response['error']}"
        raise WorkflowStepFailError(errmsg)


def run_find_message(
    step: dict, logger: logging.Logger, context: BoltContext
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
        user_token = context.user_token
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


def run_wait_state(step: dict) -> Outputs:
    inputs = step["inputs"]
    lower_bound = 0
    upper_bound = c.WAIT_STATE_MAX_SECONDS
    try:
        wait_duration = int(inputs["seconds"]["value"])
        if wait_duration <= lower_bound or wait_duration > upper_bound:
            raise ValueError("Not in valid Workflow Buddy Wait Step range.")
    except ValueError:
        errmsg = f"err5467: seconds value is not in our valid range, given: {inputs['seconds']['value']} but must be in {lower_bound} - {upper_bound}."
        raise WorkflowStepFailError(errmsg)

    start_ts = int(datetime.now(timezone.utc).timestamp())
    time.sleep(wait_duration)
    end_ts = int(datetime.now(timezone.utc).timestamp())
    return Outputs(
        {
            "wait_start_ts": str(start_ts),
            "wait_end_ts": str(end_ts),
            "waited_for": str(wait_duration),
        }
    )


def run_json_extractor(step: dict) -> Outputs:
    inputs = step["inputs"]
    json_string = inputs["json_string"]["value"]
    jsonpath_expr_str = inputs["jsonpath_expr"]["value"]

    try:
        # TODO: do I need to do a safe load here for double quotes/etc? Hopefully it should be well-formed if it's coming here and not built by hand
        json_data = json.loads(json_string, strict=False)
    except json.JSONDecodeError as e:
        errmsg = utils.pretty_json_error_msg(
            "err2111: invalid JSON provided for JSONPATH parsing.", json_string, e
        )
        raise WorkflowStepFailError(errmsg)

    jsonpath_expr = parse(jsonpath_expr_str)
    results = jsonpath_expr.find(json_data)
    logger.debug(f"JSONPATH {jsonpath_expr_str}| RESULTS: {results}")
    matches = [match.value for match in results]
    if len(matches) == 1:
        matches = matches[0]
    return Outputs({"extracted_matches": str(matches)})


def run_random_member_picker(
    step: dict,
    client: slack_sdk.WebClient,
    logger: logging.Logger,
) -> Outputs:
    inputs = step["inputs"]
    conversation_id = inputs["conversation_id"]["value"]
    number_of_users = int(inputs["number_of_users"]["value"])
    num_per_request = 200

    try:
        resp = client.conversations_members(
            channel=conversation_id, limit=num_per_request
        )
    except slack_sdk.errors.SlackApiError as e:
        logger.error(e.response)
        errmsg = f"Slack Error: unable to get conversation members from Slack. {e.response['error']}"
        raise WorkflowStepFailError(errmsg)

    # When will Slack just natively filter from their side?
    # Save time by checking for bots after random selection, rather than cleaning whole list of people.
    members = resp["members"]

    try:
        sample_of_users = utils.sample_list_until_no_bots_are_found(
            client, members, number_of_users
        )
        outputs = Outputs({})
        for i, user_id in enumerate(sample_of_users):
            user_num = i + 1
            outputs.update(
                {
                    f"selected_user_{user_num}": user_id,
                    f"selected_user_id_{user_num}": user_id,
                }
            )
        return outputs
    except ValueError:
        errmsg = f"Error: requested number of users {number_of_users} larger than members size {len(members)}."
        raise WorkflowStepFailError(errmsg)


def run_schedule_message(inputs: dict, client: slack_sdk.WebClient) -> Outputs:
    channel = inputs["channel"]["value"]
    post_at = inputs["post_at"]["value"]  # unix epoch timestamp
    # TODO: needs to support the time format in Workflow Builder variables
    # -> Tuesday, September 27th 8:38:26 AM (at least in message display it's converted to user's TZ
    # will have to check how it's passed internally)
    text = inputs["msg_text"]["value"]
    try:
        resp = client.chat_scheduleMessage(channel=channel, post_at=post_at, text=text)
        return Outputs(
            {
                "scheduled_message_id": resp["scheduled_message_id"],
            }
        )
    except slack_sdk.errors.SlackApiError as e:
        logger.error(e.response)
        errmsg = f"Slack Error: unable to schedule message. {e.response['error']}"
        raise WorkflowStepFailError(errmsg)


def run_manual_complete(
    step: dict,
    body: dict,
    event: dict,
    client: slack_sdk.WebClient,
    logger: logging.Logger,
) -> None:
    # https://api.slack.com/methods/chat.postMessage
    # https://api.slack.com/events/workflow_step_execute
    inputs = step["inputs"]
    conversation_id = inputs["conversation_id"]["value"]
    workflow_context_msg = inputs["context_msg"]["value"]
    workflow_name = utils.iget(inputs, "workflow_name", "the Workflow")
    execution_id = event["workflow_step"]["workflow_step_execute_id"]
    workflow_id = event["workflow_step"]["workflow_id"]
    delimited_workflow_info = f"{execution_id}{c.BUDDY_VALUE_DELIMITER}{workflow_name}{c.BUDDY_VALUE_DELIMITER}{workflow_id}"
    team_id = body["team_id"]
    app_id = body["api_app_id"]
    app_home_deeplink = utils.slack_deeplink("app_home", team_id, app_id=app_id)
    fallback_text = f"👋 Workflow Buddy here! You've been asked to `Continue/Stop` a Workflow.\nUse these buttons once tasks have been completed to your satisfaction.\n*Name:* `{workflow_name}`\n*Context About the Workflow:*\n```{workflow_context_msg}```"
    blocks = [
        {"type": "section", "text": {"type": "mrkdwn", "text": fallback_text}},
        {
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "👉 Continue",
                        "emoji": True,
                    },
                    "value": delimited_workflow_info,
                    "style": "primary",
                    "action_id": "manual_complete-continue",
                },
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "🛑 Stop",
                        "emoji": True,
                    },
                    "value": delimited_workflow_info,
                    "action_id": "manual_complete-stop",
                    "style": "danger",
                },
            ],
        },
        {"type": "divider"},
        {
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": f"_execution_id: {execution_id}. This execution can be manually completed from the <{app_home_deeplink}|🏡App Home>, if needed._",
                }
            ],
        },
    ]
    try:
        resp = client.chat_postMessage(
            channel=conversation_id, text=fallback_text, blocks=blocks  # type: ignore
        )
        logger.debug(resp)
    except slack_sdk.errors.SlackApiError as e:
        logger.error(e.response)
        errmsg = f"Slack Error: unable to send message with execution_id to conversation. {e.response['error']}."
        raise WorkflowStepFailError(errmsg)
    # Don't even think about calling fail/complete!
    pass


def run_wait_for_webhook(step: dict, event: dict) -> None:
    inputs = step["inputs"]
    external_service_url = inputs["destination_url"]["value"]
    execution_id = event["workflow_step"]["workflow_step_execute_id"]

    simple_secret_key = "".join(
        random.choice(string.ascii_letters) for _ in range(c.WEBHOOK_SK_LENGTH)
    )
    body = {"execution_id": execution_id, "sk": simple_secret_key}
    # TODO: any errors here will get handled in our global catch; but can we handle better here?
    utils.send_webhook(external_service_url, body)


def run_set_channel_topic(
    step: dict,
    client: slack_sdk.WebClient,
    logger: logging.Logger,
) -> Outputs:
    inputs = step["inputs"]
    conversation_id = inputs["conversation_id"]["value"]
    topic_string = inputs["topic_string"]["value"]

    try:
        resp = client.conversations_setTopic(
            channel=conversation_id, topic=topic_string
        )
        return Outputs({})
    except slack_sdk.errors.SlackApiError as e:
        logger.error(e.response)
        errmsg = f"Slack Error: unable to set channel topic. {e.response['error']}"
        raise WorkflowStepFailError(errmsg)


def run_get_email_from_slack_user(
    step: dict,
    client: slack_sdk.WebClient,
    logger: logging.Logger,
) -> Outputs:
    inputs = step["inputs"]
    # TODO: gotta be able to get this from text variable passed to me, or from Slack "user" type variable
    user_id = inputs["user_id"]["value"]
    # just in case they pass in user mention anyway
    user_id = user_id.replace("<@", "").replace(">", "")

    try:
        resp = client.users_info(user=user_id)
        email = resp["user"]["profile"]["email"]
        return Outputs({"email": email})
    except slack_sdk.errors.SlackApiError as e:
        logger.error(e.response)
        errmsg = f"Slack Error: unable to get email from user. {e.response['error']}"
        raise WorkflowStepFailError(errmsg)


def run_add_reaction(
    step: dict,
    client: slack_sdk.WebClient,
    logger: logging.Logger,
) -> Outputs:
    # From Slack's emoji reaction trigger we get a link to message which has channel id & ts
    # if they get TS from somewhere else - then what?
    inputs = step["inputs"]
    # TODO: permalink is useful for Slack triggered reaction events, but what about broader use cases?
    # channel_id = inputs["conversation_id"]["value"]
    # ts = inputs["message_ts"]["value"]
    permalink = inputs["permalink"][
        "value"
    ]  # like this -> https://workspace.slack.com/archives/CP3S47DAB/p1669229063902429
    try:
        _, _, _, _, channel_id, p_ts = permalink.split("/")
    except ValueError:
        errmsg = f"Unable to parse permalink formatting. Permalink provided was: '{permalink}', but expected format is `https://workspace.slack.com/archives/CP3S47DAB/p1669229063902429`."
        raise WorkflowStepFailError(errmsg)

    ts = f"{p_ts.replace('p', '')[:10]}.{p_ts[11:]}"
    reaction = inputs["reaction"]["value"].replace(":", "")  # :boom:
    try:
        resp = client.reactions_add(channel=channel_id, timestamp=ts, name=reaction)
        return Outputs({})
    except slack_sdk.errors.SlackApiError as e:
        if e.response["error"] == "already_reacted":
            return Outputs({})
        logger.error(e.response)
        errmsg = f"Slack Error: unable to add reaction. {e.response['error']}"
        raise WorkflowStepFailError(errmsg)


def run_webhook(step: dict) -> Outputs:
    # TODO: input validation & error handling
    inputs = step["inputs"]
    url = inputs["webhook_url"]["value"]
    bool_flags = {"fail_on_http_error": False}
    http_method = inputs["http_method"]["value"]
    request_json_str = inputs.get("request_json_str", {}).get("value", {}) or "{}"
    headers_json_str = inputs.get("headers_json_str", {}).get("value", {}) or "{}"
    query_params_json_str = (
        inputs.get("query_params_json_str", {}).get("value", {}) or "{}"
    )
    logger.info(f"sending to url:{url}")
    body = {}
    bool_flags_input = inputs.get("bool_flags", {})
    try:
        selected_checkboxes = json.loads(bool_flags_input.get("value", "[]"))
        for box_item in selected_checkboxes:
            flag_name = box_item["value"]
            bool_flags[flag_name] = True
    except json.JSONDecodeError as e:
        full_err_msg = utils.pretty_json_error_msg(
            f"err111: Unable to parse JSON Flags when preparing to send webhook to {url}.",
            bool_flags_input,
            e,
        )
        logger.error(full_err_msg)
        raise WorkflowStepFailError(full_err_msg)

    try:
        body = utils.load_json_body_from_untrusted_input_str(request_json_str)
    except json.JSONDecodeError as e:
        # e.g. Expecting ':' delimiter: line 1 column 22 (char 21)
        full_err_msg = utils.pretty_json_error_msg(
            f"err112: Unable to parse JSON when preparing to send webhook to {url}.",
            request_json_str,
            e,
        )
        logger.error(full_err_msg)
        raise WorkflowStepFailError(full_err_msg)

    try:
        new_headers = utils.load_json_body_from_untrusted_input_str(headers_json_str)
    except json.JSONDecodeError as e:
        full_err_msg = utils.pretty_json_error_msg(
            f"err113: Unable to parse JSON Headers when preparing to send webhook to {url}.",
            headers_json_str,
            e,
        )
        logger.error(full_err_msg)
        raise WorkflowStepFailError(full_err_msg)

    try:
        query_params = utils.load_json_body_from_untrusted_input_str(
            query_params_json_str
        )
    except json.JSONDecodeError as e:
        full_err_msg = utils.pretty_json_error_msg(
            f"err114: Unable to parse JSON Query Params when preparing to send webhook to {url}.",
            query_params_json_str,
            e,
        )
        logger.error(full_err_msg)
        raise WorkflowStepFailError(full_err_msg)

    logger.info(f"Method:{http_method}|Headers:{new_headers}|QP:{query_params}")
    resp = utils.send_webhook(
        url, body, method=http_method, params=query_params, headers=new_headers
    )

    if bool_flags["fail_on_http_error"] and resp.status_code > 300:
        errmsg = f"fail_on_http_error:true|code:{resp.status_code}|{resp.text[:500]}"
        raise WorkflowStepFailError(errmsg)

    # TODO: is there a limit to output variable string size?
    sanitized_resp = utils.sanitize_webhook_response(resp.text)
    return Outputs(
        {
            "webhook_status_code": str(resp.status_code),
            "webhook_response_text": f"{sanitized_resp}",
        }
    )


def edit_utils(step: Dict[str, Any], user_token: str) -> List[Dict[Any, Any]]:
    existing_inputs = copy.deepcopy(
        step["inputs"]
    )  # avoid potential issue when we delete from input dict

    blocks = copy.deepcopy(c.UTILS_STEP_MODAL_COMMON_BLOCKS)
    DEFAULT_ACTION = "webhook"
    chosen_action = (
        existing_inputs.get("selected_utility", {}).get("value") or DEFAULT_ACTION
    )
    chosen_config_item = c.UTILS_CONFIG[chosen_action]
    debug_mode_enabled = utils.sbool(
        existing_inputs.get("debug_mode_enabled", {}).get("value")
    )

    if debug_mode_enabled:
        copy_of_debug_blocks = copy.deepcopy(c.DEBUG_MODE_BLOCKS)
        blocks.extend(copy_of_debug_blocks)

    blocks.append(
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"{chosen_config_item.get('description')}",
            },
        }
    )
    blocks.extend(utils.dynamic_modal_top_blocks(chosen_action, user_token=user_token))
    # have to make sure we aren't accidentally editing config blocks in memory
    blocks.extend(copy.deepcopy(chosen_config_item["modal_input_blocks"]))
    utils.update_blocks_with_previous_input_based_on_config(
        blocks, chosen_action, existing_inputs, chosen_config_item
    )
    return blocks


def dispatch_action_update_fail_notify_channels(
    ack: Ack, body: dict, client: slack_sdk.WebClient, context: BoltContext
) -> Union[dict, None]:
    ack()
    block_id = "home_dispatch_notify_channels"
    action_id = "action_update_fail_notify_channels"
    trigger_id = body["trigger_id"]
    try:
        channel_ids_string = body["view"]["state"]["values"][block_id][action_id][
            "value"
        ]
        channel_ids_string = utils.remove_duplicates_from_comma_separated_string(
            channel_ids_string
        )
        db.set_failure_notification_channels(
            channel_ids_string, context.team_id, enterprise_id=context.enterprise_id
        )
    except Exception as e:
        # TODO: if anything blows up,
        # send a message so they know - maybe also a confirm in the channel itself?
        # why not a modal instead?
        # TODO: when considering sending a message in the channel itself - we don't want to hammer it.
        # Would need to check which ones are new, but that's slightly more effort rn so
        # gonna save that for the future.
        logger.exception(e)
        utils.slack_send_server_error_modal(client, trigger_id)
        return None

    # run a check against all the channels, make sure we have access to post to them
    # if not, send a message to this offending user that it's not all gucci
    all_input_channels = channel_ids_string.split(",")
    messageable_channels = []
    channels_needing_invite = []
    garbage_channels = []
    for channel_id in all_input_channels:
        logger.info(
            f"Checking {channel_id} for ability to post failure notifications..."
        )
        status = utils.test_if_bot_is_member(channel_id, client)
        if status == "not_in_convo":
            # this should cover private channels as well
            channels_needing_invite.append(channel_id)
        elif status == "unable_to_test":
            garbage_channels.append(channel_id)
        else:
            messageable_channels.append(channel_id)

    errMsg = ""
    messageable_channels = ",".join([f"<#{cid}>" for cid in messageable_channels])
    formatted_invite_channels = ",".join(
        [f"<#{cid}>" for cid in channels_needing_invite]
    )
    readyMsg = f"""
🫡 _Ready to send Step Failure notifications to these channels: {messageable_channels or "none"}._
"""
    blocks = [
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"{readyMsg}"},
        }
    ]

    if channels_needing_invite or garbage_channels:
        errMsg = f"""
⚠️ Workflow Buddy was configured to send Step Failure notifications to more channels, but it's not a member yet.

 - You need to invite `@WorkflowBuddy` if you want to use these channels: names: {formatted_invite_channels} | _ids: `{",".join(channels_needing_invite)}`_
"""
        if garbage_channels:
            errMsg += f"\n- These channels either had an error during testing, or don't exist: `{','.join(garbage_channels)}`"

        blocks.extend(
            [
                {"type": "divider"},
                {
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": f"{errMsg}"},
                },
            ]
        )

    try:
        channels_modal = {
            "type": "modal",
            "callback_id": "fail_notification_channels",
            "title": {
                "type": "plain_text",
                "text": "Fail Notifications",
                "emoji": True,
            },
            "close": {"type": "plain_text", "text": "Close", "emoji": True},
            "blocks": blocks,
        }
        client.views_open(trigger_id=trigger_id, view=channels_modal)
        # app_home_user_id = body["user"]["id"]
        # client.chat_postMessage(channel=app_home_user_id, text=errMsg)
    except Exception as e:
        logger.exception(f"Failed to send confirmation message {e}")

    return {
        "needs_invite": channels_needing_invite,
        "garbage_channels": garbage_channels,
        "readyMsg": readyMsg,
        "errMsg": errMsg,
    }
