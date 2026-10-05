import os
import sys
import logging
from logging.handlers import RotatingFileHandler
from app.config.config import config
from app.services.folder_monitor import folder_monitor
from app.bot.client import FileSenderBot

def setup_logging():
    """Configure system-wide logging with both stdout and rotating file outputs."""
    # Ensure logs folder exists
    config.LOGS_DIR.mkdir(parents=True, exist_ok=True)
    
    # Map configuration level
    log_level = getattr(logging, config.LOG_LEVEL, logging.INFO)
    
    # Root logger configuration
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    # Formatting
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Console output
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # File output (rotating: max 10MB per file, keeping up to 5 backups)
    file_handler = RotatingFileHandler(
        str(config.LOGS_DIR / "app.log"),
        maxBytes=10 * 1024 * 1024,
        backupCount=5
    )
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)

def main():
    setup_logging()
    logger = logging.getLogger("main")
    logger.info("Initializing Desktop File Sender service...")
    
    # Security checks on configuration
    if not config.DISCORD_BOT_TOKEN or config.DISCORD_BOT_TOKEN == "YOUR_DISCORD_BOT_TOKEN":
        logger.critical("DISCORD_BOT_TOKEN is not configured in the environment (.env). Shutdown.")
        sys.exit(1)
        
    if not config.AUTHORIZED_USERS:
        logger.warning(
            "AUTHORIZED_USERS is empty! Access will be denied to all incoming messages until configured."
        )
        
    # Ensure SEND_FILES directory is created
    try:
        os.makedirs(config.SEND_FILES_PATH, exist_ok=True)
        logger.info(f"Monitored folder: {config.SEND_FILES_PATH}")
    except Exception as e:
        logger.critical(f"Could not create SEND_FILES folder: {e}")
        sys.exit(1)
        
    # Start the folder monitoring background watchdog thread
    try:
        folder_monitor.start()
    except Exception as e:
        logger.critical(f"Failed to start folder monitoring watchdog: {e}")
        sys.exit(1)
        
    # Initialize and run the custom Discord Bot Client
    logger.info("System fully initialized. Starting Discord Bot Client...")
    
    try:
        bot = FileSenderBot()
        # log_handler=None prevents discord.py from resetting root logging configurations
        bot.run(config.DISCORD_BOT_TOKEN, log_handler=None)
    except Exception as e:
        logger.exception(f"Fatal crash during Bot run loop: {e}")
    finally:
        logger.info("Initiating shutdown. Stopping folder monitor...")
        try:
            folder_monitor.stop()
        except Exception as e:
            logger.error(f"Error during folder monitor shutdown: {e}")
        logger.info("Desktop File Sender service shutdown complete.")

if __name__ == "__main__":
    main()
