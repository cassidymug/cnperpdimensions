from typing import Optional, Any
from functools import lru_cache
try:
    import redis
    RedisType = redis.Redis
except ImportError:
    redis = None
    RedisType = Any
from .config import settings

_redis_client: Optional[RedisType] = None

def get_redis() -> Optional[RedisType]:
    global _redis_client
    if redis is None:
        return None
    if _redis_client is not None:
        return _redis_client
    try:
        _redis_client = redis.from_url(settings.redis_url, decode_responses=False)  # binary safe
        # quick ping to validate
        _redis_client.ping()
        return _redis_client
    except Exception:
        _redis_client = None
        return None

def redis_available() -> bool:
    return get_redis() is not None
