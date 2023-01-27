###########################
#
# Heavily influenced/copied from slack_sdk tests
# - InstallationStore https://github.com/slackapi/python-slack-sdk/blob/main/tests/slack_sdk/oauth/installation_store/test_sqlite3.py
# - StateStore https://github.com/slackapi/python-slack-sdk/blob/main/tests/slack_sdk/oauth/state_store/test_sqlite3.py
###########################

import buddy.sqlite_ear as sut

import tests.tools as tools
from slack_sdk.oauth.installation_store import Installation
from cryptography.fernet import Fernet

FAKE_CLIENT_ID = "111.222"
FAKE_BOT_TOKEN = "xoxb-111"
FAKE_SECRET_KEY = Fernet.generate_key()
FAKE_TEAM_NAME = "My Private Slack Workspace"


def test_instance():
    database = "test_output/test_instance.db"
    store = sut.SQLite3InstallationStore(database=database, client_id=FAKE_CLIENT_ID)
    assert store is not None
    conn = store.connect()
    assert conn is not None
    conn.close()


def test_init():
    database = "test_output/test_init.db"
    store = sut.SQLite3InstallationStore(database=database, client_id=FAKE_CLIENT_ID)
    store.init()


def test_save_and_find():
    database = "test_output/test_save_and_find.db"
    store = sut.SQLite3InstallationStore(database=database, client_id=FAKE_CLIENT_ID)
    installation = Installation(
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
    store.save(installation)
    store.delete_all(enterprise_id="E111", team_id="T111")

    i = store.find_installation(enterprise_id="E111", team_id="T111")
    assert i is None
    i = store.find_installation(enterprise_id="E111", team_id="T111", user_id="U111")
    assert i is None
    bot = store.find_bot(enterprise_id="E111", team_id="T222")
    assert bot is None


def test_save_and_find_encrypted():
    database = "test_output/test_save_and_find_encrypted.db"
    store = sut.SQLite3InstallationStore(
        database=database, client_id=FAKE_CLIENT_ID, encryption_key=FAKE_SECRET_KEY
    )
    installation = Installation(
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
    store.save(installation, encrypt=True)

    # find bots
    bot = store.find_bot(enterprise_id="E111", team_id="T111")
    assert bot.bot_token != FAKE_BOT_TOKEN, "Value wasn't stored encrypted."
    bot = store.find_bot(enterprise_id="E111", team_id="T111", decrypt=True)
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
    i = store.find_installation(enterprise_id="E111", team_id="T111")
    assert i is not None
    i = store.find_installation(enterprise_id="E111", team_id="T222")
    assert i is None
    i = store.find_installation(enterprise_id=None, team_id="T111")
    assert i is None

    i = store.find_installation(enterprise_id="E111", team_id="T111", user_id="U111")
    assert i.bot_token != FAKE_BOT_TOKEN, "Value wasn't stored encrypted."
    i = store.find_installation(
        enterprise_id="E111", team_id="T111", user_id="U111", decrypt=True
    )
    assert i.bot_token == FAKE_BOT_TOKEN, "Decryption didn't work."

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
    store.save(installation, encrypt=True)
    store.delete_all(enterprise_id="E111", team_id="T111")

    i = store.find_installation(enterprise_id="E111", team_id="T111")
    assert i is None
    i = store.find_installation(enterprise_id="E111", team_id="T111", user_id="U111")
    assert i is None
    bot = store.find_bot(enterprise_id="E111", team_id="T222")
    assert bot is None


#######################################
# State Store tests
#######################################
