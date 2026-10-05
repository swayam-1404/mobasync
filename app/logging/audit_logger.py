import sqlite3
import threading
from datetime import datetime
from app.config.config import config

class AuditLogger:
    """Manages SQLite database operations for auditing in a thread-safe manner."""
    
    def __init__(self):
        self.db_path = config.DB_PATH
        self.lock = threading.Lock()
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        """Create a new SQLite connection on demand."""
        # Ensure target directory exists
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        return sqlite3.connect(str(self.db_path))

    def _init_db(self):
        """Initialize the database schema if the tables do not exist."""
        with self.lock:
            conn = self._get_connection()
            try:
                cursor = conn.cursor()
                
                # Create audit_logs table with discord_id instead of telegram_id
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS audit_logs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp TEXT NOT NULL,
                        discord_id INTEGER,
                        username TEXT,
                        command TEXT NOT NULL,
                        file_name TEXT,
                        success INTEGER NOT NULL,
                        reason TEXT
                    )
                """)
                
                # Create file_events table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS file_events (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp TEXT NOT NULL,
                        event_type TEXT NOT NULL,
                        file_path TEXT NOT NULL
                    )
                """)
                
                conn.commit()
            finally:
                conn.close()

    def log_audit(self, discord_id: int, username: str | None, command: str, file_name: str | None, success: bool, reason: str | None = None):
        """Log a Discord interaction to the database."""
        with self.lock:
            conn = self._get_connection()
            try:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO audit_logs (timestamp, discord_id, username, command, file_name, success, reason)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    datetime.now().astimezone().isoformat(),
                    discord_id,
                    username,
                    command,
                    file_name,
                    1 if success else 0,
                    reason
                ))
                conn.commit()
            except Exception as e:
                import sys
                print(f"[DB ERROR] Failed to write to audit log: {e}", file=sys.stderr)
            finally:
                conn.close()

    def log_file_event(self, event_type: str, file_path: str):
        """Log a folder monitoring file change event to the database."""
        with self.lock:
            conn = self._get_connection()
            try:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO file_events (timestamp, event_type, file_path)
                    VALUES (?, ?, ?)
                """, (
                    datetime.now().astimezone().isoformat(),
                    event_type,
                    file_path
                ))
                conn.commit()
            except Exception as e:
                import sys
                print(f"[DB ERROR] Failed to write to file event log: {e}", file=sys.stderr)
            finally:
                conn.close()

# Singleton DB manager instance
audit_logger = AuditLogger()
