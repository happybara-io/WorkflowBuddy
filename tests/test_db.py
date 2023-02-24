import pytest
import sqlalchemy
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session
from sqlalchemy import select
import buddy.db as sut


IN_MEMORY_SQLITE_CONN_STR = "sqlite:///:memory:"
LOCAL_SQLITE_FILE = "test_output/test-buddy-db.db"
LOCAL_SQLITE_CONN_STR = f"sqlite:///{LOCAL_SQLITE_FILE}"

# https://stackoverflow.com/questions/22627659/run-code-before-and-after-each-test-in-py-test
@pytest.fixture(autouse=True, scope="function")
def get_db_objects():
    """Fixture to execute asserts before and after a test is run"""
    # Setup: fill with any logic you want
    engine: Engine = sqlalchemy.create_engine(LOCAL_SQLITE_CONN_STR)
    # db_sut = sut.DB(engine=engine)
    sut.DB_ENGINE = engine
    sut.drop_tables(engine)
    sut.create_tables(engine)

    print("set up DB engine!")
    with Session(sut.DB_ENGINE) as session:
        # sut.DB_SESSION = session
        yield (engine, None)  # this is where the testing happens

    # Teardown : fill with any logic you want
    # print("Teardown after all tests!")
    # sut.drop_tables(engine)
    # engine.dispose()


def test_hello_world(get_db_objects):
    engine, _ = get_db_objects

    with Session(engine) as session:
        session.add(sut.TeamConfig(client_id="abcdefg4", team_id="T0112334"))
        session.commit()

        # TODO: how to add event config tied to a team?
        stmt = select(sut.TeamConfig).where(sut.TeamConfig.client_id == "abcdefg4")

        first_row = session.scalars(stmt).one()
        session.add(
            sut.EventConfig(
                team_config_id=first_row.id,
                event_type="app_mention",
                desc="Proxying values on the way",
                webhook_url="https://webhook.url",
                creator="UMTUPT124",
            )
        )
        session.commit()

        stmt = select(sut.TeamConfig)

        # for tc in session.scalars(stmt):
        #     print("TC", tc.event_configs)


def test_save_and_fetch_debug_data_to_cache(get_db_objects):
    engine, _ = get_db_objects

    execution_id = "12323243243433afsdfdsfdfsdfd"
    mock_step = {"abc": 233}
    mock_body = {"body": True}
    sut.save_debug_data_to_cache(execution_id, mock_step, mock_body)
    data = sut.get_debug_data_from_cache(execution_id)
    assert data["workflow_step_execute_id"] == execution_id

    sut.delete_debug_data_from_cache(execution_id)
    data = sut.get_debug_data_from_cache(execution_id)
    assert data is None


def test_get_team_config_item_from_slack_ids(get_db_objects):
    engine, _ = get_db_objects
    # setup, fill the DB with data
    core_team_id = "T4444"
    core_enterprise_id = "E4444"
    with Session(engine) as session:
        session.add(
            sut.TeamConfig(client_id="abcdefg", team_id="T1111", enterprise_id=None)
        )
        session.add(
            sut.TeamConfig(client_id="abcdef", team_id="T2222", enterprise_id=None)
        )
        session.add(
            sut.TeamConfig(client_id="abcde", team_id="T3333", enterprise_id=None)
        )
        session.add(
            sut.TeamConfig(
                client_id="abcd", team_id=core_team_id, enterprise_id=core_enterprise_id
            )
        )
        session.add(
            sut.TeamConfig(client_id="abc", team_id="T5555", enterprise_id=None)
        )
        session.add(sut.TeamConfig(client_id="ab", team_id="T6666", enterprise_id=None))
        session.commit()

        out = sut.get_team_config(
            team_id=core_team_id, enterprise_id=core_enterprise_id, session=session
        )
        assert out.id == 4


def test_unhandled_event(get_db_objects):
    engine, _ = get_db_objects
    assert sut.DB_ENGINE == engine
    test_team_id = "T0112334"
    with Session(engine) as session:
        session.add(sut.TeamConfig(client_id="abcdefg4", team_id=test_team_id))
        session.commit()

    event_type = "test_event"
    event_type_2 = "test_event_2"
    sut.remove_unhandled_event(event_type, test_team_id)

    sut.set_unhandled_event(event_type, test_team_id)
    sut.set_unhandled_event(event_type_2, test_team_id)
    sut.set_unhandled_event(event_type, test_team_id)

    with Session(engine) as session:
        # TODO: how to add event config tied to a team?
        stmt = select(sut.TeamConfig).where(sut.TeamConfig.team_id == test_team_id)
        first_item: sut.TeamConfig = session.scalars(stmt).one()

    assert (
        first_item.unhandled_events == f"{event_type},{event_type_2},"
    ), "Must only store one of an event type, and concatenate unique types into comma list."

    unhandled = sut.get_unhandled_events(test_team_id)
    assert len(unhandled) == 2, "Must only store one of an event type."

    sut.remove_unhandled_event(event_type, test_team_id)
    sut.remove_unhandled_event(event_type_2, test_team_id)

    with Session(engine) as session:
        # TODO: how to add event config tied to a team?
        stmt = select(sut.TeamConfig).where(sut.TeamConfig.team_id == test_team_id)
        first_item: sut.TeamConfig = session.scalars(stmt).one()

    assert first_item.unhandled_events == "", "Didn't remove unhandled events properly"


def test_event_config(get_db_objects):
    engine, _ = get_db_objects
    assert sut.DB_ENGINE == engine
    test_team_id = "T0112334"
    with Session(engine) as session:
        session.add(sut.TeamConfig(client_id="abcdefg4", team_id=test_team_id))
        session.commit()

    event_type = "test_event"
    event_type_2 = "test_event_2"

    desc = "description"
    webhook_url = "https://webhook.test.url"
    creator = "U0000"
    first_id = sut.create_event_config(
        test_team_id, event_type, desc, webhook_url, creator
    )
    second_id = sut.create_event_config(
        test_team_id,
        event_type,
        "alternate description",
        "https://diff-webhook_url",
        creator,
    )
    sut.create_event_config(test_team_id, event_type_2, desc, webhook_url, creator)

    with Session(engine) as session:
        # TODO: how to add event config tied to a team?
        # stmt = select(sut.TeamConfig).where(sut.TeamConfig.team_id == test_team_id)
        # team_config: sut.TeamConfig = session.scalars(stmt).one()
        team_config: sut.TeamConfig = sut.get_team_config(
            test_team_id, None, fail_if_none=True, session=session
        )
        assert len(team_config.event_configs) == 3

    sut.remove_event_configs(ids=[first_id, second_id])

    with Session(engine) as session:
        # TODO: how to add event config tied to a team?
        stmt = select(sut.TeamConfig).where(sut.TeamConfig.team_id == test_team_id)
        team_config: sut.TeamConfig = session.scalars(stmt).one()
        assert len(team_config.event_configs) == 1

    # get the remaining event config, and check it
    event_configs = sut.get_event_configs(event_type_2, test_team_id)
    assert event_configs[0].event_type == event_type_2


def test_usages(get_db_objects):
    engine, _ = get_db_objects
    assert sut.DB_ENGINE == engine
    test_team_id = "T0112334"
    with Session(engine) as session:
        session.add(sut.TeamConfig(client_id="abcdefg4", team_id=test_team_id))
        session.commit()

    event_type = "webhook"
    event_type_2 = "test_event_2"

    num_unique_events = 2
    num_events_per_usage = 3
    for _ in range(num_events_per_usage):
        sut.save_usage(event_type, test_team_id)
        sut.save_usage(event_type_2, test_team_id)

    usage_map = sut.get_team_usage(test_team_id)
    assert len(usage_map.keys()) == num_unique_events
    for v in usage_map.values():
        assert v == num_events_per_usage
