# interactions with our data store
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
from sqlalchemy.engine import Engine
from typing import Dict, Any

Base = declarative_base()

def create_tables(engine: Engine) -> None:
    Base.metadata.create_all(engine)

def drop_tables(engine: Engine) -> None:
    Base.metadata.drop_all(engine)

# TODO: data to track
# unhandled events (by team)
# event configs (by team)
# import/export (meh utility now)

def remove_event(event_type: str) -> None:
    pass

def get_event_config(event_type: str) -> Dict[Any, Any]:
    pass

def set_unhandled_event(event_type: str) -> None:
    pass

def remove_unhandled_event_type(event_type) -> bool:
    pass

def insert_usage(usage_type) -> None:
    pass

TEAM_CONFIG_TABLE_NAME = "team_config"
EVENT_CONFIG_TABLE_NAME = "event_config"
USAGE_TABLE_NAME = "usage"

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
    unhandled_events = Column(String) # comma separated list; easiest to do
    event_configs = relationship("EventConfig")
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)     # name/desc

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
    event_type = Column(String) # (app_mention, etc)
    desc = Column(String)
    webhook_url = Column(String)
    creator = Column(String)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)     # name/desc

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
    team_config_id = Column(Integer, ForeignKey(f"{TEAM_CONFIG_TABLE_NAME}.id"))
    usage_type = Column(String) 
    created_at = Column(DateTime, default=datetime.now)

    def __repr__(self):
        return f"Usage({str(self.__dict__)})"
