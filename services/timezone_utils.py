from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

MSK = ZoneInfo("Europe/Moscow")


def now_msk() -> datetime:
    return datetime.now(MSK)


def min_bookable_time() -> datetime:
    current = now_msk().replace(minute=0, second=0, microsecond=0)
    return current + timedelta(hours=1)


def is_slot_bookable(slot_start: datetime) -> bool:
    if slot_start.tzinfo is None:
        slot_start = slot_start.replace(tzinfo=MSK)
    return slot_start >= min_bookable_time()


def parse_opening_time(value: str) -> datetime:
    value = value.strip()
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%d.%m.%Y %H:%M"):
        try:
            dt = datetime.strptime(value, fmt)
            return dt.replace(tzinfo=MSK)
        except ValueError:
            continue
    raise ValueError(f"Не удалось разобрать дату: {value}")
