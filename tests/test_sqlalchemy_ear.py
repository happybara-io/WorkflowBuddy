# type: ignore
###########################
#
# Heavily influenced/copied from slack_sdk tests
# - Installation store https://github.com/slackapi/python-slack-sdk/blob/main/tests/slack_sdk/oauth/installation_store/test_sqlalchemy.py
###########################
import sqlalchemy
from sqlalchemy.engine import Engine
import pytest
import copy
import os

from typing import Tuple

import buddy.sqlalchemy_ear as sut
from slack_sdk.oauth.installation_store import Installation
from cryptography.fernet import Fernet

from tests.tools import oasd

IN_MEMORY_SQLITE_CONN_STR = "sqlite:///:memory:"
LOCAL_SQLITE_FILE = "test_output/test-sqlalchemy.db"
LOCAL_SQLITE_CONN_STR = f"sqlite:///{LOCAL_SQLITE_FILE}"
FAKE_CLIENT_ID = "111.222"
FAKE_BOT_TOKEN = "xoxb-111"
FAKE_ORG_BOT_TOKEN = "xoxb-O111"
FAKE_SECRET_KEY = Fernet.generate_key()
FAKE_TEAM_NAME = "My Private Slack Workspace"
FAKE_GENERIC_INSTALLATION_TEMPLATE = Installation(
    app_id="A111",
    enterprise_id="E111",
    team_id="T111",
    team_name=FAKE_TEAM_NAME,
    user_id="U111",
    bot_id="B111",
    bot_token=FAKE_BOT_TOKEN,
    bot_scopes=["chat:write"],
    bot_user_id="U222",
)
FAKE_GENERIC_ORG_INSTALLATION_TEMPLATE = Installation(
    app_id="AO111",
    enterprise_id="EO111",
    user_id="UO111",
    bot_id="BO111",
    bot_token=FAKE_ORG_BOT_TOKEN,
    bot_scopes=["chat:write"],
    bot_user_id="UO222",
    is_enterprise_install=True,
)

# https://stackoverflow.com/questions/22627659/run-code-before-and-after-each-test-in-py-test
@pytest.fixture(autouse=True, scope="module")
def get_db_objects():
    """Fixture to execute asserts before and after a test is run"""
    # Setup: fill with any logic you want
    engine: Engine = sqlalchemy.create_engine(LOCAL_SQLITE_CONN_STR)
    store = sut.SQLAlchemyInstallationStore(
        client_id="111.222", engine=engine, encryption_key=FAKE_SECRET_KEY
    )
    store.metadata.drop_all(engine)
    store.metadata.create_all(engine)

    print("set up DB engine!")
    yield (engine, store)  # this is where the testing happens

    # Teardown : fill with any logic you want
    # print("Teardown after all tests!")
    # store.metadata.drop_all(engine)
    # engine.dispose()


def test_save_and_find(get_db_objects):
    engine, store = get_db_objects
    # do stuff

    installation = copy.deepcopy(FAKE_GENERIC_INSTALLATION_TEMPLATE)
    store.encryption_key = None
    store.save(installation)

    # find bots
    bot = store.find_bot(enterprise_id="E111", team_id="T111")
    assert bot is not None
    bot = store.find_bot(enterprise_id="E111", team_id="T222")
    assert bot is None
    bot = store.find_bot(enterprise_id=None, team_id="T111")
    assert bot is None

    # delete bots
    store.delete_bot(enterprise_id="E111", team_id="T222")
    bot = store.find_bot(enterprise_id="E111", team_id="T222")
    assert bot is None

    # find installations
    i = store.find_installation(enterprise_id="E111", team_id="T111")
    assert i is not None
    i = store.find_installation(enterprise_id="E111", team_id="T222")
    assert i is None
    i = store.find_installation(enterprise_id=None, team_id="T111")
    assert i is None

    i = store.find_installation(enterprise_id="E111", team_id="T111", user_id="U111")
    assert i is not None
    i = store.find_installation(enterprise_id="E111", team_id="T111", user_id="U222")
    assert i is None
    i = store.find_installation(enterprise_id="E111", team_id="T222", user_id="U111")
    assert i is None

    # delete installations
    store.delete_installation(enterprise_id="E111", team_id="T111", user_id="U111")
    i = store.find_installation(enterprise_id="E111", team_id="T111", user_id="U111")
    assert i is None
    i = store.find_installation(enterprise_id="E111", team_id="T111")
    assert i is None

    # delete all
    installation = copy.deepcopy(FAKE_GENERIC_INSTALLATION_TEMPLATE)
    store.save(installation)
    store.delete_all(enterprise_id="E111", team_id="T111")

    i = store.find_installation(enterprise_id="E111", team_id="T111")
    assert i is None
    i = store.find_installation(enterprise_id="E111", team_id="T111", user_id="U111")
    assert i is None
    bot = store.find_bot(enterprise_id="E111", team_id="T222")
    assert bot is None


def test_org_installation(get_db_objects):
    engine, store = get_db_objects

    installation = copy.deepcopy(FAKE_GENERIC_ORG_INSTALLATION_TEMPLATE)
    store.encryption_key = None
    store.save(installation)

    # inspector = sqlalchemy.inspection.inspect(engine)

    # print(inspector.get_table_names())

    # find bots
    bot = store.find_bot(enterprise_id="EO111", team_id=None)
    assert bot is not None
    bot = store.find_bot(
        enterprise_id="EO111", team_id="TO222", is_enterprise_install=True
    )
    assert bot is not None
    bot = store.find_bot(enterprise_id="EO111", team_id="TO222")
    assert bot is None
    bot = store.find_bot(enterprise_id=None, team_id="TO111")
    assert bot is None

    # delete bots
    store.delete_bot(enterprise_id="EO111", team_id="TO222")
    bot = store.find_bot(enterprise_id="EO111", team_id=None)
    assert bot is not None

    store.delete_bot(enterprise_id="EO111", team_id=None)
    bot = store.find_bot(enterprise_id="EO111", team_id=None)
    assert bot is None

    # find installations
    i = store.find_installation(enterprise_id="EO111", team_id=None)
    assert i is not None
    i = store.find_installation(
        enterprise_id="EO111", team_id="T111", is_enterprise_install=True
    )
    assert i is not None
    i = store.find_installation(enterprise_id="EO111", team_id="T222")
    assert i is None
    i = store.find_installation(enterprise_id=None, team_id="T111")
    assert i is None

    i = store.find_installation(enterprise_id="EO111", team_id=None, user_id="UO111")
    assert i is not None
    i = store.find_installation(
        enterprise_id="E111",
        team_id="T111",
        is_enterprise_install=True,
        user_id="U222",
    )
    assert i is None
    i = store.find_installation(enterprise_id=None, team_id="T222", user_id="U111")
    assert i is None

    # delete installations
    store.delete_installation(enterprise_id="E111", team_id=None)
    i = store.find_installation(enterprise_id="E111", team_id=None)
    assert i is None

    # delete all
    installation = copy.deepcopy(FAKE_GENERIC_ORG_INSTALLATION_TEMPLATE)
    store.save(installation)
    store.delete_all(enterprise_id="E111", team_id=None)

    i = store.find_installation(enterprise_id="E111", team_id=None)
    assert i is None
    i = store.find_installation(enterprise_id="E111", team_id=None, user_id="U111")
    assert i is None
    bot = store.find_bot(enterprise_id=None, team_id="T222")
    assert bot is None


def test_save_and_find_encrypted(get_db_objects):
    engine, store = get_db_objects

    installation = copy.deepcopy(FAKE_GENERIC_INSTALLATION_TEMPLATE)
    store.encryption_key = FAKE_SECRET_KEY
    store.save(installation)

    # find bots
    bot = store.find_bot(enterprise_id="E111", team_id="T111", decrypt=False)
    assert (
        bot.bot_token != FAKE_BOT_TOKEN
    ), "Value wasn't stored encrypted to begin with."
    bot = store.find_bot(enterprise_id="E111", team_id="T111")
    assert bot.bot_token == FAKE_BOT_TOKEN, "Decryption failed."

    bot = store.find_bot(enterprise_id="E111", team_id="T222")
    assert bot is None
    bot = store.find_bot(enterprise_id=None, team_id="T111")
    assert bot is None

    # delete bots
    store.delete_bot(enterprise_id="E111", team_id="T222")
    bot = store.find_bot(enterprise_id="E111", team_id="T222")
    assert bot is None

    # find installations
    i = store.find_installation(enterprise_id="E111", team_id="T111", decrypt=False)
    assert i.bot_token != FAKE_BOT_TOKEN, "Value wasn't stored encrypted."
    i = store.find_installation(enterprise_id="E111", team_id="T111", decrypt=True)
    assert i.bot_token == FAKE_BOT_TOKEN, "Decryption didn't work."

    i = store.find_installation(enterprise_id="E111", team_id="T222")
    assert i is None
    i = store.find_installation(enterprise_id=None, team_id="T111")
    assert i is None

    i = store.find_installation(enterprise_id="E111", team_id="T111", user_id="U111")
    assert i is not None
    i = store.find_installation(enterprise_id="E111", team_id="T111", user_id="U222")
    assert i is None
    i = store.find_installation(enterprise_id="E111", team_id="T222", user_id="U111")
    assert i is None

    # delete installations
    store.delete_installation(enterprise_id="E111", team_id="T111", user_id="U111")
    i = store.find_installation(enterprise_id="E111", team_id="T111", user_id="U111")
    assert i is None
    i = store.find_installation(enterprise_id="E111", team_id="T111")
    assert i is None

    # delete all
    installation = copy.deepcopy(FAKE_GENERIC_INSTALLATION_TEMPLATE)
    store.save(installation)
    store.delete_all(enterprise_id="E111", team_id="T111")

    i = store.find_installation(enterprise_id="E111", team_id="T111")
    assert i is None
    i = store.find_installation(enterprise_id="E111", team_id="T111", user_id="U111")
    assert i is None
    bot = store.find_bot(enterprise_id="E111", team_id="T222")
    assert bot is None


def test_org_installation_encrypted(get_db_objects):
    engine, store = get_db_objects

    installation = copy.deepcopy(FAKE_GENERIC_ORG_INSTALLATION_TEMPLATE)
    store.encryption_key = FAKE_SECRET_KEY
    store.save(installation)

    # find bots
    bot = store.find_bot(enterprise_id="EO111", team_id=None, decrypt=False)
    assert bot.bot_token != FAKE_ORG_BOT_TOKEN, "Value wasn't stored encrypted."
    bot = store.find_bot(enterprise_id="EO111", team_id=None, decrypt=True)
    assert bot.bot_token == FAKE_ORG_BOT_TOKEN, "Decryption failed."

    bot = store.find_bot(
        enterprise_id="EO111", team_id="TO222", is_enterprise_install=True
    )
    assert bot is not None
    bot = store.find_bot(enterprise_id="EO111", team_id="TO222")
    assert bot is None
    bot = store.find_bot(enterprise_id=None, team_id="TO111")
    assert bot is None

    # delete bots
    store.delete_bot(enterprise_id="EO111", team_id="TO222")
    bot = store.find_bot(enterprise_id="EO111", team_id=None)
    assert bot is not None

    store.delete_bot(enterprise_id="EO111", team_id=None)
    bot = store.find_bot(enterprise_id="EO111", team_id=None)
    assert bot is None

    # find installations
    i = store.find_installation(enterprise_id="EO111", team_id=None)
    assert i is not None
    i = store.find_installation(
        enterprise_id="EO111", team_id="T111", is_enterprise_install=True
    )
    assert i is not None
    i = store.find_installation(enterprise_id="EO111", team_id="T222")
    assert i is None
    i = store.find_installation(enterprise_id=None, team_id="T111")
    assert i is None

    i = store.find_installation(enterprise_id="EO111", team_id=None, user_id="UO111")
    assert i is not None
    i = store.find_installation(
        enterprise_id="E111",
        team_id="T111",
        is_enterprise_install=True,
        user_id="U222",
    )
    assert i is None
    i = store.find_installation(enterprise_id=None, team_id="T222", user_id="U111")
    assert i is None

    # delete installations
    store.delete_installation(enterprise_id="E111", team_id=None)
    i = store.find_installation(enterprise_id="E111", team_id=None)
    assert i is None

    # delete all
    installation = copy.deepcopy(FAKE_GENERIC_ORG_INSTALLATION_TEMPLATE)
    store.save(installation, encrypt=True)
    store.delete_all(enterprise_id="E111", team_id=None)

    i = store.find_installation(enterprise_id="E111", team_id=None)
    assert i is None
    i = store.find_installation(enterprise_id="E111", team_id=None, user_id="U111")
    assert i is None
    bot = store.find_bot(enterprise_id=None, team_id="T222")
    assert bot is None
