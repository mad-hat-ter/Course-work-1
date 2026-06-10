import pytest
from services.sheets_client import parse_employees_from_raw


def test_parse_employees_valid_rows():
    data = [
        {"telegram_id": 123, "full_name": " Аня ", "role": "", "is_active": "TRUE"},
        {"telegram_id": 456.0, "full_name": "Иван", "role": "admin", "is_active": True},
    ]
    employees = parse_employees_from_raw(data)
    assert len(employees) == 2
    assert employees[0]["telegram_id"] == 123
    assert employees[0]["full_name"] == "Аня"
    assert employees[0]["role"] == "curator"
    assert employees[1]["role"] == "admin"


def test_parse_employees_skips_empty_telegram_id():
    data = [{"telegram_id": "", "full_name": "X", "role": "curator", "is_active": True}]
    assert parse_employees_from_raw(data) == []


def test_parse_employees_skips_invalid_telegram_id():
    data = [{"telegram_id": "abc", "full_name": "X", "role": "curator", "is_active": True}]
    assert parse_employees_from_raw(data) == []


def test_parse_employees_inactive_values():
    data = [
        {"telegram_id": 1, "full_name": "A", "role": "curator", "is_active": "FALSE"},
        {"telegram_id": 2, "full_name": "B", "role": "curator", "is_active": "0"},
        {"telegram_id": 3, "full_name": "C", "role": "curator", "is_active": "НЕТ"},
        {"telegram_id": 4, "full_name": "D", "role": "curator", "is_active": "TRUE"},
    ]
    employees = parse_employees_from_raw(data)
    assert [e["telegram_id"] for e in employees] == [1, 2, 3, 4]
    assert employees[0]["is_active"] is False
    assert employees[3]["is_active"] is True


def test_parse_employees_from_list_rows():
    data = [
        ["telegram_id", "full_name", "role", "is_active"],
        [777, "Test", "accountant", True],
    ]
    employees = parse_employees_from_raw(data)
    assert employees[0]["telegram_id"] == 777
    assert employees[0]["role"] == "accountant"
