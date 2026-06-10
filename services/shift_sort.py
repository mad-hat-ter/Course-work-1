import re
from datetime import datetime

DAY_LABELS = ("Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс")


def shift_entry_day_index(entry: dict) -> int:
    day = entry.get("day")
    if isinstance(day, int) and 0 <= day <= 6:
        return day
    label = str(entry.get("day_label") or "").strip()
    if label in DAY_LABELS:
        return DAY_LABELS.index(label)
    full = str(entry.get("label") or "").strip()
    if full:
        day_part = full.split()[0]
        if day_part in DAY_LABELS:
            return DAY_LABELS.index(day_part)
    return 99


def shift_entry_start_minutes(entry: dict) -> int:
    dt_raw = entry.get("datetime")
    if dt_raw:
        try:
            dt = datetime.fromisoformat(str(dt_raw))
            return dt.hour * 60 + dt.minute
        except ValueError:
            pass
    hour_raw = str(entry.get("hour") or "").strip()
    if not hour_raw and entry.get("label"):
        parts = str(entry["label"]).split()
        hour_raw = parts[-1] if parts else ""
    match = re.match(r"(\d{1,2}):(\d{2})", hour_raw)
    if match:
        return int(match.group(1)) * 60 + int(match.group(2))
    return 0


def sort_shift_entries(entries: list[dict]) -> list[dict]:
    return sorted(entries, key=lambda entry: (shift_entry_day_index(entry), shift_entry_start_minutes(entry)))


def sorted_day_labels(days_map: dict[str, list[dict]]) -> list[str]:
    return sorted(days_map.keys(), key=lambda label: min(shift_entry_day_index(entry) for entry in days_map[label]))
