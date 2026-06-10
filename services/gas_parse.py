from __future__ import annotations
from typing import Any


def _is_header_row(values: list[Any], expected: tuple[str, ...]) -> bool:
    if len(values) < len(expected):
        return False
    normalized = [str(v).strip().lower() for v in values[: len(expected)]]
    return normalized == list(expected)


def rows_to_dicts(
    data: Any,
    fields: tuple[str, ...],
    *,
    skip_header: bool = True,
) -> list[dict[str, Any]]:
    if data is None:
        return []

    if isinstance(data, dict):
        for key in ("rows", "data", "items", "metadata", "employees"):
            if key in data and isinstance(data[key], list):
                return rows_to_dicts(data[key], fields, skip_header=skip_header)
        if all(field in data for field in fields):
            return [data]
        return []
    if not isinstance(data, list):
        return []
    if not data:
        return []
    if isinstance(data[0], dict):
        return [row for row in data if isinstance(row, dict)]

    result: list[dict[str, Any]] = []
    start = 0
    if skip_header and _is_header_row(data[0], fields):
        start = 1
    for row in data[start:]:
        if not isinstance(row, (list, tuple)):
            continue
        if not any(cell not in (None, "") for cell in row):
            continue
        item = {}
        for idx, field in enumerate(fields):
            item[field] = row[idx] if idx < len(row) else None
        result.append(item)
    return result


def normalize_metadata(data: Any) -> list[dict[str, Any]]:
    return rows_to_dicts(data, ("sheet_name", "opening_time", "is_active"))


def normalize_employees(data: Any) -> list[dict[str, Any]]:
    return rows_to_dicts(data, ("telegram_id", "full_name", "role", "is_active"))


def normalize_settings(data: Any) -> dict[str, Any]:
    if isinstance(data, dict) and "BASE_RATE" in data:
        return data
    defaults = {"BASE_RATE": 400, "PREMIUM_RATE": 600, "NOTIFY_MINUTES": 15}
    if isinstance(data, list) and data:
        if isinstance(data[0], dict):
            merged = defaults.copy()
            merged.update(data[0])
            return merged
        if isinstance(data[0], (list, tuple)) and len(data[0]) >= 3:
            return {
                "BASE_RATE": data[0][0],
                "PREMIUM_RATE": data[0][1],
                "NOTIFY_MINUTES": data[0][2],
            }
    return defaults

def normalize_schedule_sheets(data: Any) -> list[str]:
    if isinstance(data, dict):
        sheets = data.get("sheets", [])
        return [str(s) for s in sheets if s]
    if isinstance(data, list):
        if data and isinstance(data[0], str):
            return [str(s) for s in data if s]
        names: list[str] = []
        for row in data:
            if isinstance(row, (list, tuple)) and row:
                names.append(str(row[0]))
            elif isinstance(row, dict) and row.get("sheet_name"):
                names.append(str(row["sheet_name"]))
        return names
    return []
