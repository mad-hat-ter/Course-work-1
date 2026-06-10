from datetime import datetime
from services.sheet_names import normalize_sheet_key, parse_sheet_week_start, resolve_sheet_keys, sort_schedule_sheets
from services.timezone_utils import MSK


def test_sort_schedule_sheets():
    ref = datetime(2026, 6, 9, 12, 0, tzinfo=MSK)
    sheets = ["15.06–21.06", "08.06–14.06", "01.06–07.06"]
    assert sort_schedule_sheets(sheets, ref) == ["01.06–07.06", "08.06–14.06", "15.06–21.06"]


def test_parse_sheet_week_start_year_rollover():
    ref = datetime(2026, 1, 5, 12, 0, tzinfo=MSK)
    parsed = parse_sheet_week_start("29.12–04.01", ref)
    assert parsed is not None
    assert parsed.year == 2025
    assert parsed.month == 12
    assert parsed.day == 29


def test_parse_sheet_week_start_invalid_name():
    assert parse_sheet_week_start("Настройки") is None


def test_sort_schedule_sheets_puts_unknown_last():
    ref = datetime(2026, 6, 9, 12, 0, tzinfo=MSK)
    sheets = ["08.06–14.06", "invalid", "01.06–07.06"]
    sorted_sheets = sort_schedule_sheets(sheets, ref)
    assert sorted_sheets[0] == "01.06–07.06"
    assert sorted_sheets[1] == "08.06–14.06"
    assert sorted_sheets[2] == "invalid"


def test_parse_sheet_week_start_supports_hyphen():
    ref = datetime(2026, 6, 9, 12, 0, tzinfo=MSK)
    parsed = parse_sheet_week_start("08.06-14.06", ref)
    assert parsed == datetime(2026, 6, 8, tzinfo=MSK)


def test_normalize_sheet_key():
    assert normalize_sheet_key("08.06–14.06") == "08.06-14.06"
    assert normalize_sheet_key("08.06-14.06") == "08.06-14.06"


def test_resolve_sheet_keys_matches_dashes():
    available = ["08.06–14.06", "01.06–07.06"]
    selected = ["08.06-14.06", "01.06–07.06"]
    assert resolve_sheet_keys(selected, available) == available
