import logging
from services import memory_cache
from services.gas_parse import normalize_metadata
from services.sheets_client import get_bootstrap, get_metadata, parse_employees_from_raw

logger = logging.getLogger(__name__)
_opening_times: dict[str, str] = {}


def get_opening_time_local(sheet: str) -> str | None:
    return _opening_times.get(sheet)


def apply_bootstrap(data: dict) -> None:
    memory_cache.set("bootstrap", data, ttl=300)
    metadata = normalize_metadata(data.get("metadata", []))
    for row in metadata:
        sheet = str(row.get("sheet_name", "")).strip()
        opening = str(row.get("opening_time", "")).strip()
        is_active = str(row.get("is_active", "TRUE")).upper() not in ("FALSE", "0")
        if sheet and opening and is_active:
            _opening_times[sheet] = opening
    employees = parse_employees_from_raw(data.get("employees", []))
    if employees:
        memory_cache.set("employees:cache", employees, ttl=300)
    if isinstance(data.get("settings"), dict):
        memory_cache.set("settings:cache", data["settings"], ttl=300)
    sheets = data.get("schedule_sheets") or data.get("sheets")
    if isinstance(sheets, list):
        memory_cache.set("schedule_sheets:cache", sheets, ttl=300)


async def _load_metadata_fallback() -> None:
    metadata = await get_metadata()
    for row in normalize_metadata(metadata):
        sheet = str(row.get("sheet_name", "")).strip()
        opening = str(row.get("opening_time", "")).strip()
        is_active = str(row.get("is_active", "TRUE")).upper() not in ("FALSE", "0")
        if sheet.lower() in ("sheet_name", "название"):
            continue
        if sheet and opening and is_active:
            _opening_times[sheet] = opening


async def warm_cache() -> None:
    try:
        data = await get_bootstrap()
        apply_bootstrap(data)
    except Exception as exc:
        logger.warning("Bootstrap недоступен (%s), загружаем metadata", exc)
        try:
            await _load_metadata_fallback()
            logger.info("Время открытия загружено из metadata")
        except Exception as exc2:
            logger.warning("Не удалось получить кэш: %s", exc2)
