import re
from datetime import datetime, timedelta
from services.timezone_utils import MSK, now_msk

SHEET_WEEK_START_RE = re.compile(r"^(\d{2})\.(\d{2})")
DASHES_RE = re.compile(r"[\u2013\u2014\u2212-]")


def normalize_sheet_key(name: str) -> str:
    return DASHES_RE.sub("-", name.strip())


def resolve_sheet_keys(selected: list[str], available: list[str]) -> list[str]:
    by_key = {normalize_sheet_key(name): name for name in available}
    resolved: list[str] = []
    seen: set[str] = set()
    for name in selected:
        canonical = by_key.get(normalize_sheet_key(name), name)
        if canonical not in seen:
            seen.add(canonical)
            resolved.append(canonical)
    return resolved


def parse_sheet_week_start(sheet_name: str, reference: datetime | None = None) -> datetime | None:
    match = SHEET_WEEK_START_RE.match(sheet_name.strip())
    if not match:
        return None
    ref = reference or now_msk()
    day = int(match.group(1))
    month = int(match.group(2))
    year = ref.year
    sheet_date = datetime(year, month, day, tzinfo=MSK)
    if sheet_date > ref + timedelta(days=180):
        sheet_date = datetime(year - 1, month, day, tzinfo=MSK)
    if ref - sheet_date > timedelta(days=400):
        sheet_date = datetime(year + 1, month, day, tzinfo=MSK)
    return sheet_date


def sort_schedule_sheets(sheets: list[str], reference: datetime | None = None) -> list[str]:
    ref = reference or now_msk()

    def sort_key(name: str) -> datetime:
        parsed = parse_sheet_week_start(name, ref)
        return parsed or datetime.max.replace(tzinfo=MSK)
    return sorted(sheets, key=sort_key)
