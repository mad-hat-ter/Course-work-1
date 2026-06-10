import time
from typing import Any

_store: dict[str, tuple[float, Any]] = {}


def get(key: str) -> Any | None:
    item = _store.get(key)
    if item is None:
        return None
    expires_at, value = item
    if time.monotonic() > expires_at:
        _store.pop(key, key)
        return None
    return value


def set(key: str, value: Any, ttl: int) -> None:
    _store[key] = (time.monotonic() + ttl, value)


def delete(key: str) -> None:
    _store.pop(key, None)


def delete_prefix(prefix: str) -> None:
    for key in list(_store.keys()):
        if key.startswith(prefix):
            _store.pop(key, None)
