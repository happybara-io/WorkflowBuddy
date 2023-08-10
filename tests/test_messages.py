import buddy.messages as sut
from unittest.mock import MagicMock


def test_register():
    mock_app = MagicMock(name="mock_slack_app")
    sut.register(mock_app)
    assert mock_app.message.call_count == 1, "Is there an unregistered Message handler?"
