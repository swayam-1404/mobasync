import os
from pathlib import Path
from dotenv import load_dotenv

# Load environmental variables from .env in the project directory
# Since main.py runs from the project root, this will find the root .env
load_dotenv(override=True)

class Config:
    """Config manager that parses environment variables with default values."""
    
    def __init__(self):
        self.DISCORD_BOT_TOKEN: str = os.getenv("DISCORD_BOT_TOKEN", "").strip()
        
        # Parse authorized users to a set of integers (64-bit Discord IDs)
        raw_users = os.getenv("AUTHORIZED_USERS", "")
        self.AUTHORIZED_USERS: set[int] = set()
        if raw_users:
            for uid in raw_users.split(","):
                uid = uid.strip()
                if uid.isdigit():
                    self.AUTHORIZED_USERS.add(int(uid))
                    
        # Parse and expand path for file sharing
        raw_path = os.getenv("SEND_FILES_PATH", "~/SEND_FILES").strip()
        self.SEND_FILES_PATH: str = os.path.abspath(os.path.expanduser(raw_path))
        
        # Log level mapping
        self.LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO").upper()
        if self.LOG_LEVEL not in ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"):
            self.LOG_LEVEL = "INFO"
            
        # Large file handling strategy
        self.LARGE_FILE_STRATEGY: str = os.getenv("LARGE_FILE_STRATEGY", "split").strip().lower()
        if self.LARGE_FILE_STRATEGY not in ("compress", "split", "link", "notify"):
            self.LARGE_FILE_STRATEGY = "split"
            
        # Optional Guild ID for rapid slash commands registration in dev/testing
        raw_guild_id = os.getenv("DISCORD_GUILD_ID", "").strip()
        self.DISCORD_GUILD_ID: int | None = int(raw_guild_id) if raw_guild_id.isdigit() else None
        
        # Rate limit thresholds
        try:
            self.RATE_LIMIT_COMMANDS_PER_MIN: int = int(os.getenv("RATE_LIMIT_COMMANDS_PER_MIN", "20"))
        except ValueError:
            self.RATE_LIMIT_COMMANDS_PER_MIN = 20
            
        try:
            self.RATE_LIMIT_TRANSFERS_PER_MIN: int = int(os.getenv("RATE_LIMIT_TRANSFERS_PER_MIN", "10"))
        except ValueError:
            self.RATE_LIMIT_TRANSFERS_PER_MIN = 10
            
        # Standard directories derived from the project structure
        self.BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent
        self.LOGS_DIR: Path = self.BASE_DIR / "logs"
        self.DB_PATH: Path = self.LOGS_DIR / "audit.db"

# Create a globally importable singleton instance
config = Config()
