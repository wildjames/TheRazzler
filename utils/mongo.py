from datetime import datetime
from logging import getLogger
from typing import Any, Dict, List, Optional

import pymongo
from pydantic import BaseModel, model_validator, Field
from pymongo.collection import Collection
from pymongo.database import Database

from .local_storage import load_file

logger = getLogger(__name__)


DEFAULTS = {
    "reply": "reply.txt",
    "reply_razzle_target": "reply_razzle_target.txt",
    "personality": "personality.txt",
    "insult": "insult.txt",
    "dream_prompt": "dream_prompt.txt",
    "describe_image": "describe_image.txt",
    "react_when_active_chat": "react_when_active_chat.txt",
}


def load_default_value(key: str) -> str:
    data = load_file(DEFAULTS[key])
    if not data:
        logger.error(f"Could not load default value for {key}")
        raise FileNotFoundError(f"Could not load default value for {key}")
    data = data.strip()
    return data


class UserPreferences(BaseModel):
    user_id: str
    reply: Optional[str] = None
    reply_razzle_target: Optional[str] = None
    personality: Optional[str] = None
    insult: Optional[str] = None
    dream_prompt: Optional[str] = None
    describe_image: Optional[str] = None
    react_when_active_chat: Optional[str] = None

    @model_validator(mode="after")
    @classmethod
    def set_default_values(cls, v: "UserPreferences") -> "UserPreferences":
        for key in DEFAULTS.keys():
            if not getattr(v, key):
                setattr(v, key, load_default_value(key))
        return v


class UserPreferencesUpdate(BaseModel):
    reply: Optional[str] = None
    reply_razzle_target: Optional[str] = None
    personality: Optional[str] = None
    insult: Optional[str] = None
    dream_prompt: Optional[str] = None
    describe_image: Optional[str] = None

    class Config:
        extra = "forbid"


class UserState(BaseModel):
    user_id: str
    recent_usage: List[datetime] = Field(default_factory=list)
    cost: float = 0.0
    rate_limit_window: int = 60
    rate_limit_count: int = 10

    class Config:
        extra = "forbid"


class UserStateUpdate(BaseModel):
    recent_usage: Optional[list] = []
    cost: Optional[float] = None

    class Config:
        extra = "forbid"

    @model_validator(mode="after")
    @classmethod
    def limit_recent_usage_length(cls, v: "UserStateUpdate") -> "UserStateUpdate":
        v.recent_usage = v.recent_usage[-100:]
        return v


class MongoConfig(BaseModel):
    host: str
    port: int
    db: str
    user: Optional[str] = None
    password: Optional[str] = None


def get_mongo_db(config: MongoConfig) -> Database:

    host = (
        f"mongodb://{config.user}:{config.password}@{config.host}"
        if config.user
        else f"mongodb://{config.host}"
    )

    client = pymongo.MongoClient(host, port=config.port, connect=True)

    db = client[config.db]

    return db


def initialize_preferences_collection(
    db: Database,
) -> Collection:
    collection = db["user_preferences"]
    # Ensure index on user_id for faster query performance
    logger.info("Creating index on user_id for user_preferences collection")
    collection.create_index("user_id", unique=True)
    logger.info("Index created")
    return collection


def get_user_preferences(collection: Collection, user_id: str) -> UserPreferences:
    preferences = collection.find_one({"user_id": user_id})
    if preferences:
        return UserPreferences(**preferences)
    return UserPreferences(user_id=user_id)


def update_user_preferences(
    collection: Collection, user_id: str, update_data: UserPreferencesUpdate
):
    update_data = update_data.model_dump(exclude_none=True)
    collection.update_one({"user_id": user_id}, {"$set": update_data}, upsert=True)


def clear_user_preferences(collection: Collection, user_id: str):
    collection.delete_one({"user_id": user_id})


# User state collection


def initialize_user_state_collection(
    db: Database,
) -> Collection:
    """The user state stores persistent data about the user. e.g. recent usage,
    cost of the user, etc."""
    collection = db["user_state"]
    # Ensure index on user_id for faster query performance
    logger.info("Creating index on user_id for user_state collection")
    collection.create_index("user_id", unique=True)
    logger.info("Index created")
    return collection


def get_user_state(collection: Collection, user_id: str) -> Dict[str, Any]:
    state = collection.find_one({"user_id": user_id})
    if state:
        return UserState(**state)

    # If no state is found, return a new state object
    return UserState(user_id=user_id)


def update_user_state(
    collection: Collection, user_id: str, update_data: UserStateUpdate
):
    update_data = update_data.model_dump(exclude_none=True)
    collection.update_one({"user_id": user_id}, {"$set": update_data}, upsert=True)


def clear_user_state(collection: Collection, user_id: str):
    collection.delete_one({"user_id": user_id})


# Example usage
if __name__ == "__main__":
    from logging import INFO, basicConfig
    from pprint import pprint

    basicConfig(level=INFO)

    logger.info("Connecting to MongoDB...")
    config = MongoConfig(
        host="192.168.0.111",
        port=27017,
        db="razzler",
        # user="razzler",
        # password="razzlerpassword",
    )
    db = get_mongo_db(config)
    logger.info("Connected! Initializing user preferences collection...")
    preferences_collection = initialize_preferences_collection(db)
    logger.info("OK")

    logger.info("Clearing preferences for user 123...")
    clear_user_preferences(preferences_collection, "123")

    logger.info("Getting preferences for an unrecognized user...")
    user_prefs = get_user_preferences(preferences_collection, "123")
    pprint(user_prefs.model_dump())

    # Update a user's preference
    logger.info("Updating preferences for user 123...")
    updated_prefs = UserPreferencesUpdate(personality="FRIENDLY")
    update_user_preferences(preferences_collection, "123", updated_prefs)

    # Fetch a user's preferences
    user_prefs = get_user_preferences(preferences_collection, "123")
    pprint(user_prefs.model_dump())

    # Clear a user's preferences
    logger.info("Clearing preferences for user 123...")
    clear_user_preferences(preferences_collection, "123")
