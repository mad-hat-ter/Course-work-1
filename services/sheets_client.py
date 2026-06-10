import logging
from typing import Any
import httpx
from config.settings import settings
from services.gas_parse import normalize_employees, normalize_metadata, normalize_schedule_sheets, normalize_settings

logger = logging.getLogger(__name__)

_HTTP_TIMEOUT = httpx.Timeout(45.0, connect=15.0)
_client: httpx.AsyncClient | None = None


def _get_client() -> httpx.AsyncClient:
    global _client
    if _client is None:
        _client = httpx.AsyncClient(timeout=_HTTP_TIMEOUT, follow_redirects=True)
    return _client


async def close_client() -> None:
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None


async def _request_get(params: dict[str, str]) -> Any:
    client = _get_client()
    response = await client.get(settings.GAS_WEBAPP_URL, params=params)
    response.raise_for_status()
    return response.json()


async def _request_post(payload: dict) -> Any:
    client = _get_client()
    response = await client.post(settings.GAS_WEBAPP_URL, json=payload)
    response.raise_for_status()
    return response.json()


def parse_employees_from_raw(data: Any) -> list[dict]:
    employees = []
    for row in normalize_employees(data):
        tg_raw = row.get("telegram_id")
        if tg_raw in (None, ""):
            continue
        try:
            telegram_id = int(float(str(tg_raw).strip()))
        except (TypeError, ValueError):
            continue
        employees.append(
            {
                "telegram_id": telegram_id,
                "full_name": str(row.get("full_name", "")).strip(),
                "role": str(row.get("role", "curator")).strip() or "curator",
                "is_active": str(row.get("is_active", "TRUE")).upper() not in ("FALSE", "0", "НЕТ"),
            }
        )
    return employees


async def get_bootstrap() -> dict:
    data = await _request_get({"action": "bootstrap"})
    if not isinstance(data, dict):
        return {}
    settings_raw = data.get("settings", {})
    if isinstance(settings_raw, dict):
        normalized = normalize_settings(settings_raw)
        data["settings"] = {
            "BASE_RATE": float(normalized["BASE_RATE"]),
            "PREMIUM_RATE": float(normalized["PREMIUM_RATE"]),
            "NOTIFY_MINUTES": int(normalized["NOTIFY_MINUTES"]),
        }
    sheets = data.get("schedule_sheets") or data.get("sheets")
    if sheets is not None:
        data["schedule_sheets"] = normalize_schedule_sheets(sheets)
    if "metadata" in data:
        data["metadata"] = normalize_metadata(data["metadata"])
    return data


async def get_employees() -> list[dict]:
    data = await _request_get({"action": "employees"})
    return parse_employees_from_raw(data)


async def get_settings() -> dict:
    data = await _request_get({"action": "settings"})
    normalized = normalize_settings(data)
    return {
        "BASE_RATE": float(normalized["BASE_RATE"]),
        "PREMIUM_RATE": float(normalized["PREMIUM_RATE"]),
        "NOTIFY_MINUTES": int(normalized["NOTIFY_MINUTES"]),
    }


async def get_metadata() -> list[dict]:
    data = await _request_get({"action": "metadata"})
    return normalize_metadata(data)


async def get_bookable_view(sheet: str) -> dict:
    data = await _request_get({"action": "bookable_view", "sheet": sheet})
    if isinstance(data, dict):
        return data
    return {"sheet": sheet, "slots": [], "entries": []}


async def get_free_slots(sheet: str) -> list[dict]:
    data = await get_bookable_view(sheet)
    return data.get("slots", [])


async def get_sheet_data(sheet: str) -> dict:
    data = await get_bookable_view(sheet)
    return {"sheet": sheet, "entries": data.get("entries", [])}


async def get_shifts_at_hour(target_iso: str) -> list[dict]:
    data = await _request_get({"action": "shifts_at_hour", "target": target_iso})
    if isinstance(data, dict):
        return data.get("shifts", [])
    return []


async def book_shift(sheet: str, cell: str, name: str, tg_id: int) -> dict:
    payload = {
        "action": "book",
        "sheet": sheet,
        "cell": cell,
        "name": name,
        "tg_id": tg_id,
    }
    result = await _request_post(payload)
    if isinstance(result, dict):
        return result
    return {"success": False, "reason": "invalid_response"}


async def register_sheet(sheet: str, opening_time: str) -> dict:
    payload = {
        "action": "register_sheet",
        "sheet": sheet,
        "opening_time": opening_time,
    }
    result = await _request_post(payload)
    if isinstance(result, dict):
        return result
    return {"success": False, "reason": "invalid_response"}


async def list_schedule_sheets() -> list[str]:
    data = await _request_get({"action": "schedule_sheets"})
    return normalize_schedule_sheets(data)
