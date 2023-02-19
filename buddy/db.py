# type: ignore
# interactions with our data store
import os
import logging
import json

from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, text
from sqlalchemy import event, create_engine, select
from sqlalchemy.orm import declarative_base, relationship, Session
from datetime import datetime
from sqlalchemy.engine import Engine
from typing import Dict, Any

logging.getLogger("sqlalchemy.engine.Engine").setLevel(logging.WARN)

ENV = os.environ.get("ENV", "DEV")
IS_SQLITE_DB = os.environ.get("DB_TYPE", "sqlite") == "sqlite"

LOCAL_SQLITE_DB = "workflow_buddy.db"
if ENV == "PROD":
    LOCAL_SQLITE_DB = f"/usr/app/data/{LOCAL_SQLITE_DB}"
LOCAL_SQLITE_CONN_STR = f"sqlite:///{LOCAL_SQLITE_DB}"
# TODO: if an alternative connection string is provided - postgres?
conn_str = os.environ.get("SQL_CONN_STR", LOCAL_SQLITE_CONN_STR)
logging.info(f"Starting SQLAlchemy connected to: {conn_str}")
ENGINE: Engine = create_engine(conn_str, future=True)


@event.listens_for(ENGINE, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    if IS_SQLITE_DB:
        # disable pysqlite's emitting of the BEGIN statement entirely.
        # also stops it from emitting COMMIT before any DDL.
        dbapi_connection.isolation_level = None
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=normal")
        cursor.close()


@event.listens_for(ENGINE, "begin")
def do_begin(conn):
    if IS_SQLITE_DB:
        # emit our own BEGIN
        conn.execute(text("BEGIN IMMEDIATE"))


Base = declarative_base()


def create_tables(engine: Engine) -> None:
    Base.metadata.create_all(engine)


def drop_tables(engine: Engine) -> None:
    Base.metadata.drop_all(engine)


TEAM_CONFIG_TABLE_NAME = "team_config"
EVENT_CONFIG_TABLE_NAME = "event_config"
USAGE_TABLE_NAME = "usage"
DEBUG_DATA_CACHE_TABLE_NAME = "debug_data_cache"


class TeamConfig(Base):
    """
    Team class which should encompass both single workspace entities
    as well as Enterprise Grid deployments - unless that causes issues.
    This table should be easy to find from Installation information.
    """

    __tablename__ = TEAM_CONFIG_TABLE_NAME
    id = Column(Integer, primary_key=True)
    client_id = Column(String(32), nullable=False)
    team_id = Column(String(32))
    enterprise_id = Column(String(32))
    unhandled_events = Column(String)  # comma separated list; easiest to do
    event_configs = relationship("EventConfig")
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(
        DateTime, default=datetime.now, onupdate=datetime.now
    )  # name/desc

    def __repr__(self):
        return f"Team({str(self.__dict__)})"


class EventConfig(Base):
    """
    Event configs should contain the metadata needed so when a new event is received,
    Buddy knows what actions to take on it: proxy it to a webhook, drop it, etc.
    """

    __tablename__ = EVENT_CONFIG_TABLE_NAME
    id = Column(Integer, primary_key=True)
    team_config_id = Column(Integer, ForeignKey(f"{TEAM_CONFIG_TABLE_NAME}.id"))
    event_type = Column(String)  # (app_mention, etc)
    desc = Column(String)
    webhook_url = Column(String)
    creator = Column(String)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(
        DateTime, default=datetime.now, onupdate=datetime.now
    )  # name/desc

    def __repr__(self):
        return f"EventConfig({str(self.__dict__)})"


# TODO: track num and type of the step actions being used
# TODO: what else? don't want it to be too granular and
# get overwhelmed in data that doesn't matter.
class Usage(Base):
    """
    Usages to help understand how we are using the sytem, what features are most
    valuable, etc.
    """

    __tablename__ = USAGE_TABLE_NAME
    id = Column(Integer, primary_key=True)
    created_at = Column(DateTime, default=datetime.now)
    team_config_id = Column(Integer, ForeignKey(f"{TEAM_CONFIG_TABLE_NAME}.id"))
    usage_type = Column(String)

    def __repr__(self):
        return f"Usage({str(self.__dict__)})"


class DebugDataCache(Base):
    """
    Enables the Debug Mode in Workflow Buddy. Short-term caching of the original Workflow event so
    user can delay indefinitely "in the middle" and still run the same event since
    we saved it in this cache.
    """

    __tablename__ = DEBUG_DATA_CACHE_TABLE_NAME
    id = Column(Integer, primary_key=True)
    # Doesn't require being tied to a team
    # team_config_id = Column(Integer, ForeignKey(f"{TEAM_CONFIG_TABLE_NAME}.id"))
    created_at = Column(DateTime, default=datetime.now)
    execution_id = Column(String)
    json_str_data = Column(String)

    def __repr__(self):
        return f"DebugDataCache({str(self.__dict__)})"


# TODO: data to track
# unhandled events (by team)
# event configs (by team)
# import/export (meh utility now)
# Debug step data cache - cache in a sqlite table rather than in memory

# class DB():
#     """
#     Generic class for data store interactions
#     """
#     def __init__(self, engine: Engine=None) -> None:
#         self.engine = engine

# def remove_event(self, event_type: str) -> None:
#     pass


# def get_event_config(self, event_type: str) -> Dict[Any, Any]:
#     pass


# def set_unhandled_event(self, event_type: str) -> None:
#     pass


# def remove_unhandled_event_type(self, event_type) -> bool:
#     pass


def save_usage(usage_type: str) -> None:
    # TODO: find team in this func from values?
    team_config_id = "5"
    with Session(ENGINE) as s:
        s.add(Usage(team_config_id=team_config_id, usage_type=usage_type))
        s.commit()


def save_debug_data_to_cache(
    workflow_step_execute_id: str, step: dict, body: dict
) -> None:
    cache_data = {"step": step, "body": body}
    json_str = json.dumps(cache_data)
    with Session(ENGINE) as s:
        s.add(
            DebugDataCache(
                execution_id=workflow_step_execute_id, json_str_data=json_str
            )
        )
        s.commit()


def fetch_debug_data_from_cache(workflow_step_execute_id: str) -> DebugDataCache:
    with Session(ENGINE) as s:
        return (
            s.query(DebugDataCache)
            .filter(DebugDataCache.execution_id == workflow_step_execute_id)
            .first()
        )


def delete_debug_data_from_cache(workflow_step_execute_id: str) -> None:
    with Session(ENGINE) as s:
        target = (
            s.query(DebugDataCache)
            .filter(DebugDataCache.execution_id == workflow_step_execute_id)
            .first()
        )
        if target:
            s.delete(target)
            s.commit()
