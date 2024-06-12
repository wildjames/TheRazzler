import json
import os
from contextlib import contextmanager
from logging import getLogger
from typing import IO, Generator, Optional

from .phonebook import PhoneBook

logger = getLogger(__name__)

DATA_DIR = os.environ.get("DATA_DIR", "data")

# Check that the DATA_DIR exists. If it doesn't, create it
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

# Check that the DATA_DIR is a directory
if not os.path.isdir(DATA_DIR):
    raise NotADirectoryError(f"{DATA_DIR} is not a directory")


def load_file(fname: str, mode="r") -> Optional[str]:
    """Load a file from disk. If the file does not exist, returns None."""
    # Don't allow loading files for writing
    if "w" in mode or "a" in mode:
        raise ValueError(
            "Cannot load a file for writing. Use `load_file_lock` instead."
        )

    fname = os.path.join(DATA_DIR, fname)
    logger.debug(f"Loading file from {fname}")
    if os.path.isfile(fname):
        with open(fname, mode) as f:
            return f.read()

    if not os.path.isdir(fname):
        return None

    raise FileNotFoundError(f"File {fname} not found.")


def save_file(fname: str, data: str):
    """Save a file to disk."""
    fname = os.path.join(DATA_DIR, fname)
    logger.debug(f"Saving data to {fname}: {data}")

    if not os.path.exists(os.path.dirname(fname)):
        os.makedirs(os.path.dirname(fname))

    with open(fname, "w") as f:
        f.write(data)


@contextmanager
def file_lock(fname, mode="r+") -> Generator[IO, None, None]:
    """Get a lock for a file.

    Note that this has no queueing mechanism, so if two processes try to
    acquire a lock at the same time (for example, if they are both waiting for
    the same process to release the lock), they may encounter a race condition.

    In other words, this ONLY reliably prevents two processes from writing to
    the same file at the same time. It does not prevent three.

    # TODO: Address the race condition. Some external packages exist,
    # maybe use that. https://pypi.org/project/portalocker/
    """
    lockfile = os.path.join(DATA_DIR, f"{fname}.lock")
    fname = os.path.join(DATA_DIR, fname)

    if os.path.exists(lockfile):
        logger.debug(f"Waiting for lock on {fname} to be released...")
        while os.path.exists(lockfile):
            pass
    logger.debug(f"Lock on {fname} acquired.")

    # Check that the directory we're using exists
    if not os.path.exists(os.path.dirname(fname)):
        os.makedirs(os.path.dirname(fname))

    # If the file doesn't exist yet, create it
    if not os.path.exists(fname):
        open(fname, "w").close()

    with open(lockfile, "w") as f:
        f.write("locked")
        with open(fname, mode) as f:
            yield f

    os.remove(lockfile)
    logger.debug(f"Lock on {fname} released.")


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
