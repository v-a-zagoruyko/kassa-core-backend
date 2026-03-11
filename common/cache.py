"""
Cache utility helpers.

Wraps Django's cache framework with graceful degradation:
if Redis is unavailable, operations fail silently and log a warning.
"""

import logging

from django.core.cache import cache

logger = logging.getLogger(__name__)


def cache_get(key: str):
    """Get value from cache. Returns None on failure."""
    try:
        return cache.get(key)
    except Exception as exc:
        logger.warning("Cache get failed for key %s: %s", key, exc)
        return None


def cache_set(key: str, value, timeout: int = 300) -> bool:
    """Set value in cache. Returns True on success, False on failure."""
    try:
        cache.set(key, value, timeout)
        return True
    except Exception as exc:
        logger.warning("Cache set failed for key %s: %s", key, exc)
        return False


def cache_delete(key: str) -> bool:
    """Delete key from cache. Returns True on success, False on failure."""
    try:
        cache.delete(key)
        return True
    except Exception as exc:
        logger.warning("Cache delete failed for key %s: %s", key, exc)
        return False


def cache_delete_many(keys: list) -> bool:
    """Delete multiple keys from cache."""
    try:
        cache.delete_many(keys)
        return True
    except Exception as exc:
        logger.warning("Cache delete_many failed for keys %s: %s", keys, exc)
        return False


def make_cache_key(*parts) -> str:
    """Build a namespaced cache key from parts."""
    return ":".join(str(p) for p in parts)
