import logging
import buddy.middleware as sut

logger = logging.getLogger(__name__)


class MockContext:
    team_id = "T11111"
    user_id = "U2222"
    enterprise_id = None


def fake_next():
    pass


def test_log_request_event():
    context = MockContext()
    # https://api.slack.com/events/app_home_opened
    body = {
        "type": "app_home_opened",
        "user": "U123ABC456",
        "channel": "D123ABC456",
        "event_ts": "1515449522000016",
        "tab": "home",
        "view": {
            "id": "V123ABC456",
            "team_id": "T123ABC456",
            "type": "home",
            "blocks": [],
            "private_metadata": "",
            "callback_id": "",
            "hash": "1231232323.12321312",
            "clear_on_close": False,
            "notify_on_close": False,
            "root_view_id": "V123ABC456",
            "app_id": "A123ABC456",
            "external_id": "",
            "app_installed_team_id": "T123ABC456",
            "bot_id": "B123ABC456",
        },
    }
    sut.log_request(logger, body, context, fake_next)
