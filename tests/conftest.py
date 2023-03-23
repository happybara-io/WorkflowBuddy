import os

# Set up fake environment variables before any real imports start
os.environ["SLACK_CLIENT_ID"] = "fake-client-id"

import pytest
import sqlalchemy
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session
from sqlalchemy import select

import buddy.db as db

print("### Setting up Conftest...")

IN_MEMORY_SQLITE_CONN_STR = "sqlite:///:memory:"
LOCAL_SQLITE_FILE = "test_output/test-buddy-db.db"
LOCAL_SQLITE_CONN_STR = f"sqlite:///{LOCAL_SQLITE_FILE}"

# Moved to conftest because it's used in db & utils
# https://stackoverflow.com/questions/22627659/run-code-before-and-after-each-test-in-py-test
@pytest.fixture(autouse=True, scope="function")
def get_db_objects():
    """Fixture to execute asserts before and after a test is run"""
    # Setup: fill with any logic you want
    engine: Engine = sqlalchemy.create_engine(LOCAL_SQLITE_CONN_STR)
    # db_sut = sut.DB(engine=engine)
    db.DB_ENGINE = engine
    db.drop_tables(engine)
    db.create_tables(engine)

    print("set up DB engine!")
    with Session(db.DB_ENGINE) as session:
        # db.DB_SESSION = session
        yield (engine, None)  # this is where the testing happens

    # Teardown : fill with any logic you want
    # print("Teardown after all tests!")
    # sut.drop_tables(engine)
    # engine.dispose()


# doesn't work because we need them at import time
# @pytest.fixture(scope='module', autouse=True)
# def test_env_vars(monkeypatch):
#     print("!!!!! SETTING ENV VARS ")
#     os.environ["ENV"] = "TEST"
#     monkeypatch.setenv("ENV", "TEST")
#     monkeypatch.setenv("WB_DATA_DIR", "./workflow-buddy-test/db/")
