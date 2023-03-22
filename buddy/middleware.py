import logging
from slack_bolt import BoltContext
from typing import Callable, Union

##############
# Listener Middleware - https://slack.dev/bolt-python/concepts#listener-middleware
# Global Middleware - https://slack.dev/bolt-python/concepts#global-middleware
##############


def log_request(
    logger: logging.Logger, body: dict, context: BoltContext, next: Callable
):
    logger.debug(f"BODY: {body}")
    t = body.get("type")
    user_id = context.user_id  # body.get("user_id") or body.get("user", {}).get("id")
    team_id = context.team_id  # body.get("team_id") or body.get("team", {}).get("id")
    team: Union[dict, str, None] = body.get("team")
    # this seems to usually be empty, unfortunately
    team_name = team
    if type(team) == dict:
        team_name = team.get("domain")

    if t == "event_callback":
        t += f'-{body.get("event", {}).get("type")}'
    elif t == "block_actions":
        s = ""
        actions = body.get("actions", [{}])
        if len(actions) > 0:
            s = actions[0].get("action_id")
        t += f"-{s}"

    logger.info(f"type:{t} team_id:{team_id} team:{team_name} user_id:{user_id}")
    return next()
