import buddy.events as sut
from unittest.mock import MagicMock


def test_register():
    mock_app = MagicMock(name="mock_slack_app")
    sut.register(mock_app)
    assert mock_app.event.call_count == 7, "Is there an unregistered Event?"
