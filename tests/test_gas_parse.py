import pytest
from services.gas_parse import (
    normalize_employees,
    normalize_metadata,
    normalize_schedule_sheets,
    normalize_settings,
)


def test_normalize_metadata_from_lists():
    data = [
        ["sheet_name", "opening_time", "is_active"],
        ["02.06–08.06", "2026-06-07 09:00:00", True],
    ]
    rows = normalize_metadata(data)
    assert len(rows) == 1
    assert rows[0]["sheet_name"] == "02.06–08.06"


def test_normalize_metadata_from_dicts():
    data = [{"sheet_name": "Test", "opening_time": "2026-01-01 10:00:00", "is_active": True}]
    rows = normalize_metadata(data)
    assert rows[0]["sheet_name"] == "Test"


def test_normalize_metadata_keeps_row_with_empty_sheet_name():
    data = [
        ["sheet_name", "opening_time", "is_active"],
        ["", "2026-06-07 09:00:00", True],
    ]
    rows = normalize_metadata(data)
    assert len(rows) == 1
    assert rows[0]["sheet_name"] == ""


def test_normalize_metadata_wrapped_in_dict():
    data = {"metadata": [{"sheet_name": "A", "opening_time": "t", "is_active": True}]}
    rows = normalize_metadata(data)
    assert rows[0]["sheet_name"] == "A"


def test_normalize_employees():
    data = [
        ["telegram_id", "full_name", "role", "is_active"],
        [123, "Аня", "curator", True],
    ]
    rows = normalize_employees(data)
    assert rows[0]["telegram_id"] == 123
    assert rows[0]["full_name"] == "Аня"


def test_normalize_employees_from_dict_list():
    data = [{"telegram_id": 1, "full_name": "X", "role": "admin", "is_active": False}]
    rows = normalize_employees(data)
    assert rows[0]["role"] == "admin"


def test_normalize_settings_defaults():
    assert normalize_settings([])["BASE_RATE"] == 400


def test_normalize_settings_from_dict():
    data = {"BASE_RATE": 500, "PREMIUM_RATE": 700, "NOTIFY_MINUTES": 20}
    settings = normalize_settings(data)
    assert settings["BASE_RATE"] == 500
    assert settings["NOTIFY_MINUTES"] == 20


def test_normalize_settings_from_list_row():
    data = [[450, 650, 10]]
    settings = normalize_settings(data)
    assert settings["BASE_RATE"] == 450


def test_normalize_schedule_sheets_from_dict():
    data = {"sheets": ["08.06–14.06", "01.06–07.06"]}
    assert normalize_schedule_sheets(data) == ["08.06–14.06", "01.06–07.06"]


def test_normalize_schedule_sheets_from_string_list():
    assert normalize_schedule_sheets(["A", "B"]) == ["A", "B"]


def test_normalize_schedule_sheets_from_rows():
    data = [["08.06–14.06"], ["01.06–07.06"]]
    assert normalize_schedule_sheets(data) == ["08.06–14.06", "01.06–07.06"]


def test_normalize_schedule_sheets_from_metadata_rows():
    data = [{"sheet_name": "08.06–14.06"}, {"sheet_name": "01.06–07.06"}]
    assert normalize_schedule_sheets(data) == ["08.06–14.06", "01.06–07.06"]


def test_normalize_schedule_sheets_empty():
    assert normalize_schedule_sheets(None) == []
    assert normalize_schedule_sheets({}) == []
    assert normalize_schedule_sheets([]) == []
