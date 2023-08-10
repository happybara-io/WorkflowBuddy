import buddy.actions as sut
from unittest.mock import MagicMock


def test_register():
    mock_app = MagicMock(name="mock_slack_app")
    sut.register(mock_app)
    assert mock_app.action.call_count == 9, "Is there an unregistered action?"


def test_build_scheduled_message_modal():
    mock_client = MagicMock(name="mock_slack_client")
    mock_client.chat_scheduledMessages_list.return_value = {
        "ok": True,
        "scheduled_messages": [
            {
                "text": "a scheduled message",
                "post_at": "1234567890",
                "id": "Q1111111",
                "channel_id": "C1111111",
            }
        ],
    }

    modal = sut.build_scheduled_message_modal(mock_client)
    assert type(modal) is dict


def test_build_manual_complete_modal():
    mock_client = MagicMock(name="mock_slack_client")
    modal = sut.build_manual_complete_modal(mock_client)
    assert type(modal) is dict
