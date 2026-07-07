"""
Continuous-RAG File Watcher
Monitors the documents/ folder for file changes using watchdog.
Automatically triggers incremental indexing when files are added, modified, or deleted.
"""
import os
import time
import threading
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from app.config import DOCUMENTS_DIR, logger
from app.ingestion import process_documents


class DocumentEventHandler(FileSystemEventHandler):
    """
    Handles filesystem events in the documents/ folder.
    Debounces rapid changes to avoid multiple re-indexes for batch uploads.
    """

    def __init__(self, debounce_seconds: float = 3.0):
        super().__init__()
        self._debounce_seconds = debounce_seconds
        self._timer = None
        self._lock = threading.Lock()
        self._pending_events = []

    def _schedule_sync(self, event_description: str):
        """Schedule a sync after debounce period. Resets timer on each new event."""
        with self._lock:
            self._pending_events.append(event_description)

            # Cancel existing timer
            if self._timer is not None:
                self._timer.cancel()

            # Schedule new timer
            self._timer = threading.Timer(self._debounce_seconds, self._run_sync)
            self._timer.start()

    def _run_sync(self):
        """Execute the sync after debounce period."""
        with self._lock:
            events = self._pending_events.copy()
            self._pending_events.clear()
            self._timer = None

        logger.info("=" * 50)
        logger.info("FILE WATCHER: Auto-sync triggered")
        for event in events:
            logger.info("  Event: %s", event)
        logger.info("=" * 50)

        try:
            result = process_documents()
            logger.info("Auto-sync complete: %s", result.get("status", "unknown"))
        except Exception as e:
            logger.error("Auto-sync failed: %s", e)

    def on_created(self, event):
        if not event.is_directory and event.src_path.endswith('.pdf'):
            filename = os.path.basename(event.src_path)
            logger.info("📄 New file detected: %s", filename)
            self._schedule_sync(f"CREATED: {filename}")

    def on_modified(self, event):
        if not event.is_directory and event.src_path.endswith('.pdf'):
            filename = os.path.basename(event.src_path)
            logger.info("📝 File modified: %s", filename)
            self._schedule_sync(f"MODIFIED: {filename}")

    def on_deleted(self, event):
        if not event.is_directory and event.src_path.endswith('.pdf'):
            filename = os.path.basename(event.src_path)
            logger.info("🗑️ File deleted: %s", filename)
            self._schedule_sync(f"DELETED: {filename}")


# Global observer instance
_observer = None


def start_watcher():
    """Start the file watcher in a background thread."""
    global _observer

    os.makedirs(DOCUMENTS_DIR, exist_ok=True)

    if _observer is not None and _observer.is_alive():
        logger.info("File watcher already running.")
        return

    event_handler = DocumentEventHandler(debounce_seconds=3.0)
    _observer = Observer()
    _observer.schedule(event_handler, DOCUMENTS_DIR, recursive=False)
    _observer.daemon = True  # Dies when main process exits
    _observer.start()

    logger.info("👁️ File watcher started — monitoring: %s", DOCUMENTS_DIR)


def stop_watcher():
    """Stop the file watcher."""
    global _observer

    if _observer is not None and _observer.is_alive():
        _observer.stop()
        _observer.join(timeout=5)
        logger.info("File watcher stopped.")
        _observer = None


def is_watching() -> bool:
    """Check if the file watcher is currently running."""
    return _observer is not None and _observer.is_alive()
