import os
import pytest

print("Run conftest")

# doesn't work because we need them at import time
# @pytest.fixture(scope='module', autouse=True)
# def test_env_vars(monkeypatch):
#     print("!!!!! SETTING ENV VARS ")
#     os.environ["ENV"] = "TEST"
#     monkeypatch.setenv("ENV", "TEST")
#     monkeypatch.setenv("WB_DATA_DIR", "./workflow-buddy-test/db/")
