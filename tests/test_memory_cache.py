import time
from services import memory_cache


def test_set_and_get():
    memory_cache.set("key", "value", ttl=60)
    assert memory_cache.get("key") == "value"


def test_get_missing_returns_none():
    assert memory_cache.get("missing") is None


def test_expired_entry_returns_none():
    memory_cache.set("key", "value", ttl=1)
    memory_cache._store["key"] = (time.monotonic() - 1, "value")
    assert memory_cache.get("key") is None


def test_delete_removes_key():
    memory_cache.set("key", "value", ttl=60)
    memory_cache.delete("key")
    assert memory_cache.get("key") is None


def test_delete_prefix():
    memory_cache.set("bookable_view:a", 1, ttl=60)
    memory_cache.set("bookable_view:b", 2, ttl=60)
    memory_cache.set("other", 3, ttl=60)
    memory_cache.delete_prefix("bookable_view:")
    assert memory_cache.get("bookable_view:a") is None
    assert memory_cache.get("bookable_view:b") is None
    assert memory_cache.get("other") == 3
