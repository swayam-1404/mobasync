import time
from collections import defaultdict
from app.config.config import config

class RateLimiter:
    """In-memory sliding window rate limiter to prevent spam/abuse."""
    
    def __init__(self, limit_per_minute: int):
        self.limit = limit_per_minute
        self.history: dict[int, list[float]] = defaultdict(list)

    def is_allowed(self, user_id: int) -> bool:
        """
        Check if the request from user_id is within the configured limits.
        
        Args:
            user_id: The Discord User ID.
            
        Returns:
            bool: True if allowed, False if rate-limited.
        """
        now = time.time()
        one_minute_ago = now - 60.0
        
        # Clean up timestamps older than 1 minute
        user_history = self.history[user_id]
        updated_history = [t for t in user_history if t > one_minute_ago]
        self.history[user_id] = updated_history
        
        # Check if the rate limit is exceeded
        if len(updated_history) >= self.limit:
            return False
            
        # Record the current action
        self.history[user_id].append(now)
        return True

# Initialize singletons for commands and transfers
command_limiter = RateLimiter(config.RATE_LIMIT_COMMANDS_PER_MIN)
transfer_limiter = RateLimiter(config.RATE_LIMIT_TRANSFERS_PER_MIN)
