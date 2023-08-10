import buddy.workflow_steps as sut
from unittest.mock import MagicMock


def test_register():
    mock_app = MagicMock(name="mock_slack_app")
    sut.register(mock_app)
    assert mock_app.step.call_count == 2, "Is there an unregistered Workflow Step?"
