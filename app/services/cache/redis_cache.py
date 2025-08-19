import redis
import json
import os
import hashlib
from typing import Optional, Any
import structlog
from functools import wraps

logger = structlog.get_logger()

class CacheService:
    def __init__(self):
        redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379')
        try:
            self.redis_client = redis.Redis.from_url(redis_url, decode_responses=True)
            # Test connection
            self.redis_client.ping()
            logger.info("Redis cache connected successfully")
        except Exception as e:
            logger.error("Redis connection failed, using no-cache mode", error=str(e))
            self.redis_client = None
    
    def get(self, key: str) -> Optional[Any]:
        """Get cached data"""
        if not self.redis_client:
            return None
        
        try:
            data = self.redis_client.get(key)
            return json.loads(data) if data else None
        except Exception as e:
            logger.error("Cache get failed", key=key, error=str(e))
            return None
    
    def set(self, key: str, value: Any, ttl: int = 3600):
        """Set cached data with TTL"""
        if not self.redis_client:
            return
        
        try:
            self.redis_client.setex(key, ttl, json.dumps(value, default=str))
            logger.debug("Cached data", key=key, ttl=ttl)
        except Exception as e:
            logger.error("Cache set failed", key=key, error=str(e))
    
    def delete(self, key: str):
        """Delete cached data"""
        if not self.redis_client:
            return
        
        try:
            self.redis_client.delete(key)
            logger.debug("Deleted cache", key=key)
        except Exception as e:
            logger.error("Cache delete failed", key=key, error=str(e))
    
    def delete_pattern(self, pattern: str):
        """Delete all keys matching pattern"""
        if not self.redis_client:
            return
        
        try:
            keys = self.redis_client.keys(pattern)
            if keys:
                self.redis_client.delete(*keys)
                logger.info("Deleted cache pattern", pattern=pattern, count=len(keys))
        except Exception as e:
            logger.error("Cache pattern delete failed", pattern=pattern, error=str(e))

# Global cache instance
cache_service = CacheService()

def cache_result(ttl: int = 1800, key_prefix: str = ""):
    """Decorator for caching function results"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Create cache key from function name and arguments
            func_name = func.__name__
            args_str = json.dumps({"args": args[1:], "kwargs": kwargs}, sort_keys=True, default=str)
            cache_key = f"{key_prefix}:{func_name}:{hashlib.md5(args_str.encode()).hexdigest()}"
            
            # Try cache first
            cached_result = cache_service.get(cache_key)
            if cached_result is not None:
                logger.info("Cache hit", function=func_name, key=cache_key)
                return cached_result
            
            # Call function and cache result
            result = await func(*args, **kwargs)
            cache_service.set(cache_key, result, ttl)
            logger.info("Cache miss - stored result", function=func_name, key=cache_key)
            
            return result
        return wrapper
    return decorator