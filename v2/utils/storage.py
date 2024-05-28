import json
import os
from logging import getLogger
from typing import Optional

from pydantic import BaseModel

from .phonebook import PhoneBook

logger = getLogger(__name__)

DATA_DIR = os.environ.get("DATA_DIR", "data")

# Check that the DATA_DIR exists. If it doesn't, create it
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

# Check that the DATA_DIR is a directory
if not os.path.isdir(DATA_DIR):
    raise NotADirectoryError(f"{DATA_DIR} is not a directory")


def save_phonebook(phonebook: PhoneBook):
    """Dump the phonebook to a file."""
    logger.debug("Saving phonebook to disk...")
    fname = os.path.join(DATA_DIR, "phonebook.json")
    with open(fname, "w") as f:
        f.write(phonebook.model_dump_json(indent=4))


def load_phonebook() -> PhoneBook:
    """Load the phonebook from a file."""
    fname = os.path.join(DATA_DIR, "phonebook.json")
    logger.debug(f"Loading phonebook from {fname}")

    try:
        with open(fname, "r") as f:
            return PhoneBook(**json.load(f))
    except FileNotFoundError:
        return PhoneBook()
    except json.JSONDecodeError:
        return PhoneBook()


class RedisCredentials(BaseModel):
    host: str = "localhost"
    port: int = 6379
    db: int = 0
    password: Optional[str] = None
