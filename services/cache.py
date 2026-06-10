import json
import logging
from typing import Any, Awaitable, Callable
import redis.asyncio as redis
from config.settings import settings
from services import memory_cache, sheets_client
from services.bootstrap_cache import get_opening_time_local
from services.sheets_client import get_bookable_view
from services.timezone_utils import parse_opening_time

logger = logging.getLogger(__name__)

_pool: redis.Redis | None = None
_redis_available: bool | None = None


async def get_redis() -> redis.Redis | None:
    global _pool, _redis_available
    if _redis_available is False:
        return None
    if _pool is None:
        try:
            _pool = redis.from_url(settings.REDIS_URL, decode_responses=True)
            await _pool.ping()
            _redis_available = True
        except Exception as exc:
            logger.warning("Redis недоступен, работа без кэша: %s", exc)
            _redis_available = False
            _pool = None
            return None
    return _pool


async def get_cached(key: str, fetch_fn: Callable[[], Awaitable[Any]], ttl: int) -> Any:
    cached = memory_cache.get(key)
    if cached is not None:
        return cached
    r = await get_redis()
    if r is not None:
        try:
            raw = await r.get(key)
            if raw is not None:
                data = json.loads(raw)
                memory_cache.set(key, data, min(ttl, 120))
                return data
        except Exception as exc:
            logger.warning("Ошибка чтения Redis (%s): %s", key, exc)
    data = await fetch_fn()
    memory_cache.set(key, data, min(ttl, 120))
    if r is not None:
        try:
            await r.setex(key, ttl, json.dumps(data, ensure_ascii=False))
        except Exception as exc:
            logger.warning("Ошибка записи Redis (%s): %s", key, exc)
    return data


async def get_bookable_view_cached(sheet: str) -> dict:
    return await get_cached(
        f"bookable_view:{sheet}",
        lambda: get_bookable_view(sheet),
        ttl=90,
    )


async def get_free_slots_cached(sheet: str) -> list[dict]:
    data = await get_bookable_view_cached(sheet)
    return data.get("slots", [])


async def get_settings_cached() -> dict:
    cached = memory_cache.get("settings:cache")
    if cached is not None:
        return cached
    return await get_cached("settings:cache", sheets_client.get_settings, ttl=300)


async def get_employees_cached() -> list[dict]:
    cached = memory_cache.get("employees:cache")
    if cached is not None:
        return cached
    return await get_cached("employees:cache", sheets_client.get_employees, ttl=60)


async def refresh_employees() -> list[dict]:
    memory_cache.delete("employees:cache")
    r = await get_redis()
    if r is not None:
        try:
            await r.delete("employees:cache")
        except Exception as exc:
            logger.warning("Не удалось сбросить кэш сотрудников: %s", exc)

    employees = await sheets_client.get_employees()
    memory_cache.set("employees:cache", employees, ttl=60)
    if r is not None:
        try:
            await r.setex("employees:cache", 60, json.dumps(employees, ensure_ascii=False))
        except Exception as exc:
            logger.warning("Не удалось обновить кэш сотрудников: %s", exc)
    return employees


async def list_schedule_sheets_cached() -> list[str]:
    cached = memory_cache.get("schedule_sheets:cache")
    if cached is not None:
        return cached
    return await get_cached("schedule_sheets:cache", sheets_client.list_schedule_sheets, ttl=120)


async def refresh_schedule_sheets() -> list[str]:
    memory_cache.delete("schedule_sheets:cache")
    r = await get_redis()
    if r is not None:
        try:
            await r.delete("schedule_sheets:cache")
        except Exception as exc:
            logger.warning("Не удалось сбросить кэш листов: %s", exc)
    sheets = await sheets_client.list_schedule_sheets()
    memory_cache.set("schedule_sheets:cache", sheets, ttl=120)
    if r is not None:
        try:
            await r.setex("schedule_sheets:cache", 120, json.dumps(sheets, ensure_ascii=False))
        except Exception as exc:
            logger.warning("Не удалось обновить кэш листов: %s", exc)
    return sheets


async def invalidate_free_slots(sheet: str) -> None:
    memory_cache.delete(f"bookable_view:{sheet}")
    memory_cache.delete(f"free_slots:{sheet}")
    r = await get_redis()
    if r is None:
        return
    try:
        await r.delete(f"free_slots:{sheet}")
        await r.delete(f"bookable_view:{sheet}")
    except Exception as exc:
        logger.warning("Не удалось инвалидировать кэш %s: %s", sheet, exc)


async def get_opening_time(sheet: str) -> str | None:
    local = get_opening_time_local(sheet)
    if local:
        return local
    r = await get_redis()
    if r is None:
        return None
    try:
        return await r.get(f"opening_time:{sheet}")
    except Exception:
        return None


async def set_opening_time(sheet: str, opening_time: str) -> None:
    from services.bootstrap_cache import _opening_times
    _opening_times[sheet] = opening_time
    r = await get_redis()
    if r is None:
        return
    try:
        await r.set(f"opening_time:{sheet}", opening_time)
    except Exception as exc:
        logger.warning("Не удалось сохранить opening_time: %s", exc)


def _metadata_row(row: dict | list) -> tuple[str, str, bool] | None:
    if isinstance(row, dict):
        sheet = str(row.get("sheet_name", "")).strip()
        opening = str(row.get("opening_time", "")).strip()
        is_active = str(row.get("is_active", "TRUE")).upper() not in ("FALSE", "0")
        return sheet, opening, is_active
    if isinstance(row, (list, tuple)) and row:
        sheet = str(row[0]).strip() if len(row) > 0 else ""
        opening = str(row[1]).strip() if len(row) > 1 else ""
        is_active = True
        if len(row) > 2:
            is_active = str(row[2]).upper() not in ("FALSE", "0")
        return sheet, opening, is_active
    return None


async def restore_metadata_from_sheets() -> None:
    from services.bootstrap_cache import apply_bootstrap
    try:
        data = await sheets_client.get_bootstrap()
        apply_bootstrap(data)
    except Exception as exc:
        logger.warning("Bootstrap недоступен, пробуем metadata: %s", exc)
        try:
            metadata = await sheets_client.get_metadata()
        except Exception as exc2:
            logger.warning("Не удалось загрузить метаданные: %s", exc2)
            return
        for row in metadata:
            parsed = _metadata_row(row)
            if parsed is None:
                continue
            sheet, opening, is_active = parsed
            if sheet.lower() in ("sheet_name", "название"):
                continue
            if sheet and opening and is_active:
                await set_opening_time(sheet, opening)


async def is_sheet_open_for_booking(sheet: str) -> bool:
    from services.timezone_utils import now_msk
    opening_raw = await get_opening_time(sheet)
    if not opening_raw:
        return False
    try:
        opening_dt = parse_opening_time(opening_raw)
    except ValueError:
        return False
    return now_msk() >= opening_dt


async def mark_notified(telegram_id: int, shift_key: str, ttl_seconds: int) -> bool:
    r = await get_redis()
    if r is None:
        return True
    key = f"notified:{telegram_id}:{shift_key}"
    try:
        was_set = await r.set(key, "1", nx=True, ex=ttl_seconds)
        return bool(was_set)
    except Exception:
        return True
