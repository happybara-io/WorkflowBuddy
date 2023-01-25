###########################
#
# Heavily influenced by slack_sdk tests
# https://github.com/slackapi/python-slack-sdk/blob/main/tests/slack_sdk/oauth/installation_store/test_sqlite3.py
#
###########################

import buddy.sqlite_ear as sut

from slack_sdk.oauth.installation_store import Installation

FAKE_CLIENT_ID = "111.222"


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
        user_id="U111",
        bot_id="B111",
        bot_token="xoxb-111",
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
