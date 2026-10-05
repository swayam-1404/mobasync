import os
from app.config.config import config

def validate_user(discord_id: int) -> bool:
    """
    Validate if a Discord user ID is pre-approved.
    
    Args:
        discord_id: The numeric ID of the Discord user.
        
    Returns:
        bool: True if authorized, False otherwise.
    """
    return discord_id in config.AUTHORIZED_USERS

def validate_path(target_path: str) -> bool:
    """
    Validate that target_path is strictly within the boundaries of SEND_FILES_PATH.
    Resolves symbolic links, prevents path traversal, and blocks null-byte injection.
    
    Args:
        target_path: The filename or path requested.
        
    Returns:
        bool: True if the path is valid and within the allowed directory, False otherwise.
    """
    if not target_path:
        return False
        
    # Reject null-byte injection
    if '\x00' in target_path:
        return False
        
    # Resolve the allowed root directory to its absolute canonical form
    base_canonical = os.path.realpath(config.SEND_FILES_PATH)
    
    # Resolve the requested target path.
    # If the user input is a relative path, join it with the base directory.
    if not os.path.isabs(target_path):
        if target_path.startswith('~'):
            target_abs = os.path.expanduser(target_path)
        else:
            target_abs = os.path.join(base_canonical, target_path)
    else:
        target_abs = target_path
        
    # Resolve the target path to its absolute canonical form (resolving symlinks)
    target_canonical = os.path.realpath(target_abs)
    
    try:
        # Determine the common path. If the target is inside the base,
        # the common path must be exactly the base path.
        common = os.path.commonpath([base_canonical, target_canonical])
        return common == base_canonical
    except ValueError:
        # Raised if paths are on different drives/mounts or are structurally incompatible
        return False
