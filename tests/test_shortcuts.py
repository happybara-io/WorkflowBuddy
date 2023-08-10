import buddy.shortcuts as sut
from unittest.mock import MagicMock


def test_register():
    mock_app = MagicMock(name="mock_slack_app")
    sut.register(mock_app)
    assert mock_app.shortcut.call_count == 1, "Is there an unregistered Shortcut?"
