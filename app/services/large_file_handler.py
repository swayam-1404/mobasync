import os
import zipfile
import shutil
import logging
import subprocess
from abc import ABC, abstractmethod
from pathlib import Path
from app.config.config import config

logger = logging.getLogger(__name__)
TEMP_DIR: Path = config.LOGS_DIR / "temp"
DISCORD_LIMIT_MB = 25  # Standard Discord free upload limit

def get_temp_dir() -> Path:
    """Ensure the temporary workspace directory exists and return its path."""
    TEMP_DIR.mkdir(parents=True, exist_ok=True)
    return TEMP_DIR

def zip_directory(source_path: str, output_name: str = "archive.zip") -> str:
    """
    Compresses a file or directory into a ZIP archive.
    Saves the archive in the workspace logs/temp/ directory.
    """
    temp_dir = get_temp_dir()
    zip_path = temp_dir / output_name
    
    src = Path(os.path.realpath(source_path))
    
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        if src.is_file():
            zipf.write(src, src.name)
        else:
            for root, _, files in os.walk(src):
                for file in files:
                    full_path = Path(root) / file
                    rel_path = full_path.relative_to(src)
                    zipf.write(full_path, rel_path)
                    
    logger.info(f"Successfully zipped {source_path} to {zip_path}")
    return str(zip_path)

def split_file(file_path: str, chunk_size_mb: int = 24) -> list[str]:
    """
    Splits a large file into multiple smaller chunks.
    Saves the chunks in the workspace logs/temp/ directory.
    """
    temp_dir = get_temp_dir()
    file_real_path = os.path.realpath(file_path)
    file_name = os.path.basename(file_real_path)
    
    chunk_bytes = chunk_size_mb * 1024 * 1024
    chunk_paths = []
    
    chunk_num = 1
    with open(file_real_path, 'rb') as f:
        while True:
            chunk_data = f.read(chunk_bytes)
            if not chunk_data:
                break
                
            chunk_name = f"{file_name}.part{chunk_num:03d}"
            chunk_file_path = temp_dir / chunk_name
            
            with open(chunk_file_path, 'wb') as chunk_f:
                chunk_f.write(chunk_data)
                
            chunk_paths.append(str(chunk_file_path))
            chunk_num += 1
            
    logger.info(f"Split {file_path} into {len(chunk_paths)} chunks")
    return chunk_paths

def cleanup_files(paths: list[str]):
    """Safely delete temporary files or directories."""
    for p in paths:
        try:
            if os.path.exists(p):
                if os.path.isdir(p):
                    shutil.rmtree(p)
                else:
                    os.remove(p)
                logger.debug(f"Cleaned up temporary path: {p}")
        except Exception as e:
            logger.warning(f"Could not clean up temporary file {p}: {e}")


class StrategyResult:
    """Encapsulates the action and data returned by a large file strategy."""
    def __init__(self, action: str, files: list[str] = None, message: str = None):
        self.action = action  # 'upload', 'message', 'error'
        self.files = files or []
        self.message = message or ""


class LargeFileStrategy(ABC):
    """Abstract base class for large file strategies."""
    @abstractmethod
    def handle_large_file(self, file_path: str) -> StrategyResult:
        pass


class ZipStrategy(LargeFileStrategy):
    """Strategy that compresses the requested directory or file."""
    def handle_large_file(self, file_path: str) -> StrategyResult:
        logger.info(f"Applying ZipStrategy to: {file_path}")
        try:
            zip_name = f"{os.path.basename(file_path)}.zip"
            zip_path = zip_directory(file_path, zip_name)
            
            # Check size of zipped file
            size_mb = os.path.getsize(zip_path) / (1024 * 1024)
            if size_mb > DISCORD_LIMIT_MB:
                logger.warning(f"Zipped file size ({size_mb:.1f}MB) still exceeds Discord limit. Splitting...")
                # Fallback: split the zip file
                chunks = split_file(zip_path, chunk_size_mb=DISCORD_LIMIT_MB - 1)
                # We need to clean up the zip file itself, but keep the chunks
                cleanup_files([zip_path])
                return StrategyResult(action="upload", files=chunks, message=f"Compressed & split into {len(chunks)} parts.")
                
            return StrategyResult(action="upload", files=[zip_path])
        except Exception as e:
            logger.error(f"ZipStrategy failed: {e}")
            return StrategyResult(action="error", message=f"Failed to compress file: {str(e)}")


class SplitStrategy(LargeFileStrategy):
    """Strategy that splits files exceeding the upload limit."""
    def handle_large_file(self, file_path: str) -> StrategyResult:
        logger.info(f"Applying SplitStrategy to: {file_path}")
        try:
            chunks = split_file(file_path, chunk_size_mb=DISCORD_LIMIT_MB - 1)
            return StrategyResult(action="upload", files=chunks, message=f"File split into {len(chunks)} parts.")
        except Exception as e:
            logger.error(f"SplitStrategy failed: {e}")
            return StrategyResult(action="error", message=f"Failed to split file: {str(e)}")


class LinkStrategy(LargeFileStrategy):
    """Strategy that generates a local network / Tailscale download link."""
    def handle_large_file(self, file_path: str) -> StrategyResult:
        logger.info(f"Applying LinkStrategy to: {file_path}")
        filename = os.path.basename(file_path)
        # Check for Tailscale IP or local IP if available, fallback to localhost
        ip = "127.0.0.1"
        try:
            # Attempt to get Tailscale IP or primary local IP
            res = subprocess.run(["tailscale", "ip", "-4"], stdout=subprocess.PIPE, text=True, timeout=1)
            if res.returncode == 0:
                ip = res.stdout.strip()
        except Exception:
            pass
            
        download_url = f"http://{ip}:8080/download/{filename}"
        message = (
            f"⚠️ **File too large to send** ({os.path.getsize(file_path) / (1024*1024):.1f} MB)\n"
            f"🔗 Download link: `{download_url}`\n"
            f"*Note: Ensure your Tailscale VPN or local network is connected.*"
        )
        return StrategyResult(action="message", message=message)


class NotifyStrategy(LargeFileStrategy):
    """Strategy that sends a desktop notification on the host computer."""
    def handle_large_file(self, file_path: str) -> StrategyResult:
        logger.info(f"Applying NotifyStrategy to: {file_path}")
        filename = os.path.basename(file_path)
        
        # Trigger standard host OS notification
        try:
            subprocess.run([
                "notify-send", 
                "📁 Desktop File Sender", 
                f"File request for '{filename}' is too large to send ({os.path.getsize(file_path)/(1024*1024):.1f}MB)."
            ], timeout=2)
        except Exception as e:
            logger.warning(f"Could not trigger desktop notification: {e}")
            
        message = (
            f"⚠️ **File too large to send** ({os.path.getsize(file_path)/(1024*1024):.1f} MB).\n"
            f"🖥️ A desktop notification has been triggered on the host PC.\n"
            f"Path on disk: `{file_path}`"
        )
        return StrategyResult(action="message", message=message)


def get_large_file_strategy(strategy_name: str = None) -> LargeFileStrategy:
    """Factory to get the configured strategy."""
    name = strategy_name or config.LARGE_FILE_STRATEGY
    if name == "compress":
        return ZipStrategy()
    elif name == "link":
        return LinkStrategy()
    elif name == "notify":
        return NotifyStrategy()
    else:
        return SplitStrategy()
