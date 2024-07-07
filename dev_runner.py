import time
import subprocess
import os
import sys
from typing import List, Optional
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from logging import getLogger, basicConfig, INFO, CRITICAL
import fnmatch

logger = getLogger(__name__)
basicConfig(level=INFO)


class ChangeHandler(FileSystemEventHandler):
    """Handles the file change events by restarting the application."""

    def __init__(
        self,
        command: List[str],
        ignores: Optional[List[str]] = None,
        exceptions: Optional[List[str]] = None,
    ):
        self.command = command
        self.env = os.environ.copy()
        self.process = subprocess.Popen(self.command, env=self.env)
        self.ignores = ignores or []
        self.exceptions = exceptions or []

        logger.info(f"Starting the managed process with command: {self.command}")
        logger.info(f"Ignoring directories: {self.ignores}")
        logger.info(f"Exceptions: {self.exceptions}")
        logger.info(f"Process ID: {self.process.pid}")

    def on_any_event(self, event):
        if event.is_directory:
            return

        if event.event_type not in ["modified", "created", "moved"]:
            return

        # Check if the event path matches with any of the ignores patterns
        for ignore_dir in self.ignores:
            if fnmatch.fnmatch(event.src_path, ignore_dir):
                for exception in self.exceptions:
                    if fnmatch.fnmatch(event.src_path, exception):
                        logger.info(
                            f"Event: {event.event_type} on {event.src_path} -"
                            " Ignore pattern matched, but reloading anyway"
                            " due to exception"
                        )
                        break
                else:
                    return

        logger.critical(f"Event: {event.event_type} on {event.src_path}")
        self.restart_process()

    def restart_process(self):
        """Restart the managed process."""
        if self.process:
            logger.critical("Restarting the managed process...")
            self.process.kill()
            self.process.wait()
        self.process = subprocess.Popen(self.command)
        logger.info(f"Restarted the process with command: {self.command}")
        logger.info(f"New Process ID: {self.process.pid}")


def start_monitoring(
    path,
    command: List[str],
    ignores: Optional[List[str]] = None,
    exceptions: Optional[List[str]] = None,
):
    event_handler = ChangeHandler(command, ignores, exceptions)
    observer = Observer()
    observer.schedule(event_handler, path, recursive=True)
    observer.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()


if __name__ == "__main__":
    # Set the path to the project directory
    path = sys.argv[1] if len(sys.argv) > 1 else "."

    ignores = [
        "venv/*",
        ".git*",
        "*__pycache__*",
        "data/*",
        "*.log",
        "*.pid",
        "dev_runner.py",
        ".devcontainer/*",
    ]
    ignores = [os.path.join(path, dir) for dir in ignores]

    exceptions = ["*/config.yaml"]

    command = ["python", "main.py"]
    start_monitoring(path, command, ignores=ignores, exceptions=exceptions)
