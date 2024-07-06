import time
import subprocess
import os
import sys
from typing import List, Optional
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from logging import getLogger, basicConfig, INFO

logger = getLogger(__name__)
basicConfig(level=INFO)

class ChangeHandler(FileSystemEventHandler):
    """Handles the file change events by restarting the application."""

    def __init__(self, command: List[str], ignore_dirs: Optional[List[str]] = None):
        self.command = command
        self.env = os.environ.copy()
        self.process = subprocess.Popen(self.command, env=self.env)
        self.ignore_dirs = ignore_dirs or []

        logger.info(f"Starting the managed process with command: {self.command}")
        logger.info(f"Ignoring directories: {self.ignore_dirs}")
        logger.info(f"Process ID: {self.process.pid}")

    def on_any_event(self, event):
        if event.is_directory:
            return

        # Check if the event path is in any of the ignored directories
        for ignore_dir in self.ignore_dirs:
            if event.src_path.startswith(ignore_dir):
                return  # Ignore this event

        if event.event_type in ['modified', 'created', 'moved']:
            logger.critical(f"Event: {event.event_type} on {event.src_path}")
            self.restart_process()

    def restart_process(self):
        """Restart the managed process."""
        if self.process:
            logger.critical("Restarting the managed process...")
            self.process.kill()
            self.process.wait()
        self.process = subprocess.Popen(self.command)

def start_monitoring(path, command: List[str], ignore_dirs: Optional[List[str]] = None):
    event_handler = ChangeHandler(command, ignore_dirs)
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
    path = sys.argv[1] if len(sys.argv) > 1 else '.'

    ignore_dirs = ['venv', '.git', '__pycache__', "data"]
    ignore_dirs = [os.path.join(path, dir) for dir in ignore_dirs]

    command = ['python', 'main.py']
    start_monitoring(path, command, ignore_dirs=ignore_dirs)
