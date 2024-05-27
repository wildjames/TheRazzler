import json
import os
from typing import Optional

from pydantic import BaseModel

from .phonebook import PhoneBook

DATA_DIR = os.environ.get("DATA_DIR", "data")

# Check that the DATA_DIR exists. If it doesn't, create it
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

# Check that the DATA_DIR is a directory
if not os.path.isdir(DATA_DIR):
    raise NotADirectoryError(f"{DATA_DIR} is not a directory")


def save_phonebook(phonebook: PhoneBook):
    """Dump the phonebook to a file."""
    fname = os.path.join(DATA_DIR, "phonebook.json")
    with open(fname, "w") as f:
        f.write(phonebook.model_dump_json())


def load_phonebook() -> PhoneBook:
    """Load the phonebook from a file."""
    fname = os.path.join(DATA_DIR, "phonebook.json")
    if not os.path.exists(fname):
        return PhoneBook()

    with open(fname, "r") as f:
        return PhoneBook(**json.load(f))


class RedisCredentials(BaseModel):
    host: str = "localhost"
    port: int = 6379
    db: int = 0
    password: Optional[str] = None
