import os
import logging
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from app.config.config import config
from app.database.db_manager import db_manager

logger = logging.getLogger(__name__)

class FolderMonitorHandler(FileSystemEventHandler):
    """Event handler that registers file changes inside the monitored folder."""
    
    def on_created(self, event):
        if event.is_directory:
            return
        logger.info(f"File created: {event.src_path}")
        db_manager.log_file_event("CREATE", event.src_path)

    def on_modified(self, event):
        if event.is_directory:
            return
        logger.info(f"File modified: {event.src_path}")
        db_manager.log_file_event("MODIFY", event.src_path)

    def on_deleted(self, event):
        if event.is_directory:
            return
        logger.info(f"File deleted: {event.src_path}")
        db_manager.log_file_event("DELETE", event.src_path)


class FolderMonitorService:
    """Service wrapper for starting and stopping the Watchdog folder monitor."""
    
    def __init__(self):
        self.watch_path = config.SEND_FILES_PATH
        self.observer = None

    def start(self):
        """Start monitoring the directory in a background thread."""
        # Ensure the watch directory exists
        os.makedirs(self.watch_path, exist_ok=True)
        
        event_handler = FolderMonitorHandler()
        self.observer = Observer()
        self.observer.schedule(event_handler, path=self.watch_path, recursive=True)
        self.observer.start()
        logger.info(f"Folder monitor started on: {self.watch_path}")

    def stop(self):
        """Stop the background monitor thread."""
        if self.observer:
            self.observer.stop()
            self.observer.join()
            logger.info("Folder monitor stopped.")

# Singleton service instance
folder_monitor = FolderMonitorService()
