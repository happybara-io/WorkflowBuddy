# type: ignore
# interactions with our data store
import os
import logging
import json
from pathlib import Path

from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, text, Boolean
from sqlalchemy import event, create_engine, select, delete, func
from sqlalchemy.orm import declarative_base, relationship, Session, selectinload
from datetime import datetime
from sqlalchemy.engine import Engine
from typing import Dict, Any, Optional, Union, List, Generator
from contextlib import nullcontext

logger = logging.getLogger(__name__)
# TODO: feels like I shouldn't have to write all these CRUD ops by hand,
# I must be missing something with SQLAlchemy
logging.getLogger("sqlalchemy.engine.Engine").setLevel(logging.WARN)

ENV = os.environ.get("ENV", "DEV")
IS_SQLITE_DB = os.environ.get("DB_TYPE", "sqlite") == "sqlite"

WB_DATA_DIR = os.getenv("WB_DATA_DIR") or (
    "/usr/app/data/" if ENV == "PROD" else "./workflow-buddy-local/"
)
Path(WB_DATA_DIR).mkdir(parents=True, exist_ok=True)

DB_FILE_NAME = "workflow_buddy.db"
LOCAL_SQLITE_DB = f"{WB_DATA_DIR}{DB_FILE_NAME}"
LOCAL_SQLITE_CONN_STR = f"sqlite:///{LOCAL_SQLITE_DB}"
# TODO: if an alternative connection string is provided - postgres?
conn_str = os.environ.get("SQL_CONN_STR", LOCAL_SQLITE_CONN_STR)
logger.info(f"Starting SQLAlchemy connected to: {conn_str}")
DB_ENGINE: Engine = create_engine(conn_str, future=True)


# Using a global variable seems to roughly map to Flask-SQLAlchemy
# having a db = SQLAlchemy(), and then using db.session.* in requests.
# Appears it handles that behind the scenes.
# "the basic pattern is create a Session at the start of a web request, ...then close the session at the end of web request."
# DB_SESSION: Session = None
# SessionLocal: Generator = sessionmaker(autocommit=False, autoflush=False, bind=engine)
# TODO: it's bad practice to manage session from within these funcs - but also it's easy enough to reason
# through and the alternatives have been confusing. Explore updating if needed.


@event.listens_for(DB_ENGINE, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    if IS_SQLITE_DB:
        # disable pysqlite's emitting of the BEGIN statement entirely.
        # also stops it from emitting COMMIT before any DDL.
        dbapi_connection.isolation_level = None
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=normal")
        cursor.close()


@event.listens_for(DB_ENGINE, "begin")
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
    unhandled_events = Column(String, default="")  # comma separated list; easiest to do
    event_configs = relationship(
        "EventConfig", back_populates="team_config", cascade="all, delete-orphan"
    )
    usages = relationship(
        "Usage", back_populates="team_config", cascade="all, delete-orphan"
    )
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    subscription = Column(String, default="self_hosted")
    fail_notify_channels = Column(
        String, default=""
    )  # comma separated list; easiest to do

    def __repr__(self):
        return f"Team({str(self.__dict__)})"


class EventConfig(Base):
    """
    Event configs should contain the metadata needed so when a new event is received,
    Buddy knows what actions to take on it: proxy it to a webhook, drop it, etc.

    Multiple EventConfig's are allowed per event_type
    """

    __tablename__ = EVENT_CONFIG_TABLE_NAME
    id = Column(Integer, primary_key=True)
    team_config_id = Column(
        Integer, ForeignKey(f"{TEAM_CONFIG_TABLE_NAME}.id"), nullable=False
    )
    team_config = relationship("TeamConfig", back_populates="event_configs")
    event_type = Column(String)  # (app_mention, etc)
    desc = Column(String)
    webhook_url = Column(String)
    creator = Column(String)
    use_raw_event = Column(Boolean, default=False)
    filter_react = Column(String)
    filter_channel = Column(String)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(
        DateTime, default=datetime.now, onupdate=datetime.now
    )  # name/desc

    def __repr__(self):
        return f"EventConfig({str(self.__dict__)})"


class Usage(Base):
    """
    Usages to help understand how we are using the sytem, what features are most
    valuable, etc.

    For now, usage_type should just be the different step actions - signifying they were ran by that team.
    """

    __tablename__ = USAGE_TABLE_NAME
    id = Column(Integer, primary_key=True)
    created_at = Column(DateTime, default=datetime.now)
    team_config_id = Column(Integer, ForeignKey(f"{TEAM_CONFIG_TABLE_NAME}.id"))
    team_config = relationship("TeamConfig", back_populates="usages")
    usage_type = Column(String(100))  # usually slack event type->workflow_step_execute
    action = Column(String(100))  # usually callback_id->webhook
    workflow_id = Column(String(50))
    workflow_instance_id = Column(String(50))
    step_id = Column(String(50))

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


def set_unhandled_event(
    event_type: str, team_id: str, enterprise_id: Optional[str] = None
) -> None:
    with Session(DB_ENGINE) as s:
        team_config: TeamConfig = get_team_config(
            team_id, enterprise_id=enterprise_id, session=s
        )
        curr_str = team_config.unhandled_events or ""
        if event_type not in curr_str:
            new_str = f"{curr_str}{event_type},"
            team_config.unhandled_events = new_str
            s.commit()


def remove_unhandled_event(
    event_type: str, team_id: str, enterprise_id: Optional[str] = None
) -> None:
    with Session(DB_ENGINE) as s:
        team_config: TeamConfig = get_team_config(
            team_id, enterprise_id=enterprise_id, session=s
        )
        events_str = team_config.unhandled_events or ""
        new_str = events_str.replace(f"{event_type},", "")
        team_config.unhandled_events = new_str
        s.commit()


# TODO: when do I ever need this, but not the rest of team config?
def get_unhandled_events(
    team_id: str, enterprise_id: Optional[str] = None
) -> List[str]:
    with Session(DB_ENGINE) as s:
        team_config: TeamConfig = get_team_config(
            team_id, enterprise_id=enterprise_id, session=s
        )
        events_str = team_config.unhandled_events or ""
        return [x for x in events_str.split(",") if x]


def set_failure_notification_channels(
    channel_ids: str, team_id: str, enterprise_id: Optional[str] = None
) -> None:
    with Session(DB_ENGINE) as s:
        team_config: TeamConfig = get_team_config(
            team_id, enterprise_id=enterprise_id, session=s
        )
        team_config.fail_notify_channels = channel_ids
        s.commit()


def add_failure_notification_channel(
    channel_id: str, team_id: str, enterprise_id: Optional[str] = None
) -> None:
    with Session(DB_ENGINE) as s:
        team_config: TeamConfig = get_team_config(
            team_id, enterprise_id=enterprise_id, session=s
        )
        curr_str = team_config.fail_notify_channels or ""
        if channel_id not in curr_str:
            new_str = f"{curr_str}{channel_id},"
            team_config.fail_notify_channels = new_str
            s.commit()


def remove_failure_notification_channel(
    channel_id: str, team_id: str, enterprise_id: Optional[str] = None
) -> None:
    with Session(DB_ENGINE) as s:
        team_config: TeamConfig = get_team_config(
            team_id, enterprise_id=enterprise_id, session=s
        )
        fail_notify_channels_str = team_config.fail_notify_channels or ""
        new_str = fail_notify_channels_str.replace(f"{channel_id},", "")
        team_config.fail_notify_channels = new_str
        s.commit()


def get_team_config(
    team_id: Optional[str],
    enterprise_id: Optional[str],
    is_enterprise_install: Optional[bool] = False,
    fail_if_none=False,
    session: Optional[Session] = None,
) -> Union[TeamConfig, None]:
    # TODO: do i want this to be more flexible to use enterprise id OR client_id OR team_id and be successful?
    # copied logic from Slack's own installation lookup
    with Session(DB_ENGINE, expire_on_commit=False) if not session else nullcontext(
        session
    ) as s:
        if is_enterprise_install or team_id is None:
            team_id = None
        stmt = (
            select(TeamConfig)
            .options(selectinload(TeamConfig.event_configs))
            .filter(
                TeamConfig.enterprise_id == enterprise_id, TeamConfig.team_id == team_id
            )
        )
        team_config = s.execute(stmt).scalar_one_or_none()
        if not team_config:
            if fail_if_none:
                raise ValueError(f"No team config found for that team id({team_id})!")
            # create it if it doesn't exist
            team_config = create_team_config("", team_id, enterprise_id, session=s)

    return team_config


def create_team_config(
    client_id: str, team_id: str, enterprise_id: str, session: Optional[Session] = None
) -> TeamConfig:
    with Session(DB_ENGINE) if not session else nullcontext(session) as s:
        tc = TeamConfig(
            client_id=client_id, team_id=team_id, enterprise_id=enterprise_id
        )
        s.add(tc)
        s.commit()
        return tc


def create_event_config(
    team_id: str,
    event_type: str,
    desc: str,
    webhook_url: str,
    creator: str,
    enterprise_id: Optional[str] = None,
    filter_react: Optional[str] = None,
    filter_channel: Optional[str] = None,
    use_raw_event: Optional[bool] = False,
) -> int:
    # Multiple EventConfig's are allowed of the same event_type, so no need to worry about duplicates
    with Session(DB_ENGINE) as s:
        team_config: TeamConfig = get_team_config(
            team_id, enterprise_id=enterprise_id, session=s
        )
        ec_vals = {
            "event_type": event_type,
            "desc": desc,
            "webhook_url": webhook_url,
            "creator": creator,
            "filter_react": filter_react,
            "filter_channel": filter_channel,
            "use_raw_event": use_raw_event,
        }
        new_event_config = EventConfig(**ec_vals)
        team_config.event_configs.append(new_event_config)
        s.commit()
        return new_event_config.id


def get_event_configs(
    event_type: str,
    team_id: str,
    enterprise_id: Optional[str] = None,
    session: Optional[Session] = None,
) -> List[EventConfig]:
    with Session(DB_ENGINE, expire_on_commit=False) if not session else nullcontext(
        session
    ) as s:
        team_config: TeamConfig = get_team_config(
            team_id, enterprise_id=enterprise_id, session=s
        )
        stmt = select(EventConfig).filter(
            EventConfig.team_config_id == team_config.id,
            EventConfig.event_type == event_type,
        )
        return s.execute(stmt).scalars().all()


def remove_event_configs(ids: List[int] = None, ecs: List[EventConfig] = None) -> None:
    if ids is None:
        ids = []
    if ecs is None:
        ecs = []
    if not ids and not ecs:
        raise ValueError(
            "Need at least one valid way to identify EventConfigs to remove..."
        )

    with Session(DB_ENGINE) as s:
        for id in ids:
            event_config = s.get(EventConfig, id)
            s.delete(event_config)

        for ec in ecs:
            s.delete(ec)
        s.commit()


# TODO: how do I want to handle it, since there can be multiple event configs of the same event type?
def find_and_remove_event_config(
    event_type: str, team_id: str, enterprise_id: Optional[str] = None
) -> None:
    with Session(DB_ENGINE) as s:
        # TODO: seems like this could be done in one query rather than two....
        team_config: TeamConfig = get_team_config(
            team_id, enterprise_id=enterprise_id, session=s
        )
        stmt = delete(EventConfig).where(
            EventConfig.team_config_id == team_config.id,
            EventConfig.event_type == event_type,
        )
        s.execute(stmt)
        s.commit()


def save_execute_usage(
    action: str, team_id: str, step: dict, enterprise_id: Optional[str] = None
) -> None:
    with Session(DB_ENGINE) as s:
        team_config: TeamConfig = get_team_config(
            team_id, enterprise_id=enterprise_id, session=s
        )
        # TODO: premature optimization labeling them all as workflow_step_execute,
        # but space isn't a concern for now.
        usage_vals = {
            "usage_type": "workflow_step_execute",
            "action": action,
            "workflow_id": step.get("workflow_id"),
            "workflow_instance_id": step.get("workflow_instance_id"),
            "step_id": step.get("step_id"),
        }
        new_usage = Usage(**usage_vals)
        team_config.usages.append(new_usage)
        s.commit()


def get_team_action_usage(
    team_id: str, enterprise_id: Optional[str] = None
) -> Dict[str, int]:
    with Session(DB_ENGINE, expire_on_commit=False) as s:
        # TODO: seems like it could be written as one query with join, but idk
        # team_config: TeamConfig = get_team_config(team_id, session=s)
        # team_config.usages
        stmt = (
            select(Usage.action, func.count())
            .join(TeamConfig)
            .where(
                TeamConfig.team_id == team_id,
                Usage.usage_type == "workflow_step_execute",
            )
            .group_by(Usage.action)
        )
        rows = s.execute(stmt).all()
        return {row[0]: row[1] for row in rows}


def save_debug_data_to_cache(
    workflow_step_execute_id: str, step: dict, body: dict
) -> None:
    cache_data = {
        "workflow_step_execute_id": workflow_step_execute_id,
        "step": step,
        "body": body,
    }
    json_str = json.dumps(cache_data)
    with Session(DB_ENGINE) as s:
        s.add(
            DebugDataCache(
                execution_id=workflow_step_execute_id, json_str_data=json_str
            )
        )
        s.commit()


def get_debug_data_from_cache(
    workflow_step_execute_id: str,
) -> Union[Dict[str, Union[str, Dict[str, Any]]], None]:
    with Session(DB_ENGINE, expire_on_commit=False) as s:
        cache_data: DebugDataCache = (
            s.query(DebugDataCache)
            .filter(DebugDataCache.execution_id == workflow_step_execute_id)
            .first()
        )
        if cache_data:
            json_str = cache_data.json_str_data
            if json_str:
                return json.loads(cache_data.json_str_data)
        return None


def delete_debug_data_from_cache(workflow_step_execute_id: str) -> None:
    with Session(DB_ENGINE) as s:
        target = (
            s.query(DebugDataCache)
            .filter(DebugDataCache.execution_id == workflow_step_execute_id)
            .first()
        )
        if target:
            s.delete(target)
            s.commit()
