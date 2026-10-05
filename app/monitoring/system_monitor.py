import socket
import shutil
import os
from app.config.config import config

def check_internet_connectivity(timeout: float = 2.0) -> bool:
    """
    Verify network connectivity.
    First attempts to connect to discord.com on port 443.
    Falls back to contacting 8.8.8.8 on port 53 (DNS) if that fails.
    
    Args:
        timeout: Socket timeout in seconds.
        
    Returns:
        bool: True if connection is successful, False otherwise.
    """
    # 1. Primary: Try to reach Discord API endpoint
    try:
        socket.setdefaulttimeout(timeout)
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect(("discord.com", 443))
        return True
    except Exception:
        pass
        
    # 2. Fallback: Try Google DNS directly
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect(("8.8.8.8", 53))
        return True
    except Exception:
        return False

def get_storage_info() -> dict:
    """
    Fetch disk partition metrics where SEND_FILES is stored,
    and tally the total file count and size inside the folder.
    
    Returns:
        dict: A dictionary containing partition usage (total, used, free in GB)
              and folder metrics (file count, folder size in MB).
    """
    folder_path = config.SEND_FILES_PATH
    
    # Ensure folder exists
    os.makedirs(folder_path, exist_ok=True)
    
    # Disk partition metrics
    total, used, free = shutil.disk_usage(folder_path)
    
    # File counts and sizes inside the target folder
    file_count = 0
    folder_size_bytes = 0
    for root, _, files in os.walk(folder_path):
        for f in files:
            fp = os.path.join(root, f)
            try:
                if os.path.exists(fp):
                    folder_size_bytes += os.path.getsize(fp)
                    file_count += 1
            except OSError:
                pass
                
    return {
        "disk_total_gb": round(total / (1024 ** 3), 2),
        "disk_used_gb": round(used / (1024 ** 3), 2),
        "disk_free_gb": round(free / (1024 ** 3), 2),
        "file_count": file_count,
        "folder_size_mb": round(folder_size_bytes / (1024 ** 2), 2)
    }

def get_files_count() -> int:
    """
    Quick count of files within SEND_FILES.
    
    Returns:
        int: Number of files.
    """
    folder_path = config.SEND_FILES_PATH
    if not os.path.exists(folder_path):
        return 0
    count = 0
    for root, _, files in os.walk(folder_path):
        count += len(files)
    return count
