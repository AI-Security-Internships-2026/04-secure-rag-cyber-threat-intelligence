import time

# Simple in-memory cache
# Stores query results with a timestamp
_cache = {}
CACHE_TTL = 300  # seconds — cached results expire after 5 minutes

def get_cached(query: str, privacy_method: str):
    """
    Returns cached result if it exists and hasn't expired.
    Returns None if not found or expired.
    """
    key = f"{query}::{privacy_method}"
    if key in _cache:
        result, timestamp = _cache[key]
        if time.time() - timestamp < CACHE_TTL:
            print(f"[CACHE HIT] {query[:50]}...")
            return result
        else:
            # Expired — remove it
            del _cache[key]
            print(f"[CACHE EXPIRED] {query[:50]}...")
    return None


def set_cache(query: str, privacy_method: str, result: dict):
    """
    Stores a result in cache with current timestamp.
    """
    key = f"{query}::{privacy_method}"
    _cache[key] = (result, time.time())
    print(f"[CACHE SET] {query[:50]}...")


def get_cache_stats() -> dict:
    """
    Returns current cache statistics.
    """
    now = time.time()
    active = sum(1 for _, (_, ts) in _cache.items() if now - ts < CACHE_TTL)
    return {
        "total_cached": len(_cache),
        "active_entries": active,
        "ttl_seconds": CACHE_TTL
    }


def clear_cache():
    """
    Clears all cached results.
    """
    _cache.clear()
    print("[CACHE CLEARED]")