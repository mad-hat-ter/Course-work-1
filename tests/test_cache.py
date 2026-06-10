from datetime import datetime
from unittest.mock import patch
import pytest
from services import memory_cache
from services.auth import get_user
from services.bootstrap_cache import _opening_times
from services.cache import  _metadata_row, get_opening_time, invalidate_free_slots, is_sheet_open_for_booking, refresh_employees,  refresh_schedule_sheets,  set_opening_time
from services.timezone_utils import MSK


def test_metadata_row_from_dict():
    assert _metadata_row(
        {"sheet_name": "08.06–14.06", "opening_time": "2026-06-08 12:00:00", "is_active": True}
    ) == ("08.06–14.06", "2026-06-08 12:00:00", True)


def test_metadata_row_from_list():
    assert _metadata_row(["08.06–14.06", "2026-06-08 12:00:00", "FALSE"]) == (
        "08.06–14.06",
        "2026-06-08 12:00:00",
        False,
    )


def test_metadata_row_invalid():
    assert _metadata_row(None) is None
    assert _metadata_row([]) is None


@pytest.mark.asyncio
async def test_set_and_get_opening_time_local():
    await set_opening_time("08.06–14.06", "2026-06-08 12:00:00")
    assert await get_opening_time("08.06–14.06") == "2026-06-08 12:00:00"
    assert _opening_times["08.06–14.06"] == "2026-06-08 12:00:00"


@pytest.mark.asyncio
async def test_is_sheet_open_for_booking_true():
    await set_opening_time("08.06–14.06", "2020-01-01 00:00:00")
    assert await is_sheet_open_for_booking("08.06–14.06") is True


@pytest.mark.asyncio
async def test_is_sheet_open_for_booking_false_without_opening_time():
    assert await is_sheet_open_for_booking("missing") is False


@pytest.mark.asyncio
async def test_is_sheet_open_for_booking_false_for_future_opening():
    await set_opening_time("future", "2099-01-01 00:00:00")
    assert await is_sheet_open_for_booking("future") is False


@pytest.mark.asyncio
async def test_is_sheet_open_for_booking_false_for_invalid_date():
    await set_opening_time("bad", "invalid-date")
    assert await is_sheet_open_for_booking("bad") is False


@pytest.mark.asyncio
async def test_is_sheet_open_for_booking_respects_current_time():
    await set_opening_time("week", "2026-06-10 12:00:00")
    with patch("services.timezone_utils.now_msk") as mock_now:
        mock_now.return_value = datetime(2026, 6, 10, 11, 0, tzinfo=MSK)
        assert await is_sheet_open_for_booking("week") is False
        mock_now.return_value = datetime(2026, 6, 10, 12, 0, tzinfo=MSK)
        assert await is_sheet_open_for_booking("week") is True


@pytest.mark.asyncio
async def test_refresh_schedule_sheets_updates_memory(monkeypatch):
    calls = {"count": 0}
    async def fake_list():
        calls["count"] += 1
        return ["08.06–14.06", "01.06–07.06"]
    async def fake_redis():
        return None
    monkeypatch.setattr("services.cache.sheets_client.list_schedule_sheets", fake_list)
    monkeypatch.setattr("services.cache.get_redis", fake_redis)
    sheets = await refresh_schedule_sheets()
    assert sheets == ["08.06–14.06", "01.06–07.06"]
    assert memory_cache.get("schedule_sheets:cache") == sheets
    assert calls["count"] == 1


@pytest.mark.asyncio
async def test_refresh_employees_updates_memory(monkeypatch):
    calls = {"count": 0}
    async def fake_employees():
        calls["count"] += 1
        return [{"telegram_id": 1, "full_name": "A", "role": "admin", "is_active": True}]
    async def fake_redis():
        return None
    monkeypatch.setattr("services.cache.sheets_client.get_employees", fake_employees)
    monkeypatch.setattr("services.cache.get_redis", fake_redis)
    employees = await refresh_employees()
    assert employees[0]["role"] == "admin"
    assert memory_cache.get("employees:cache") == employees
    assert calls["count"] == 1


@pytest.mark.asyncio
async def test_get_user_uses_fresh_employees(monkeypatch):
    roles = iter(["admin", "accountant"])
    async def fake_refresh():
        return [
            {
                "telegram_id": 919872447,
                "full_name": "Аня Фролова",
                "role": next(roles),
                "is_active": True,
            }
        ]

    monkeypatch.setattr("services.auth.refresh_employees", fake_refresh)
    user = await get_user(919872447)
    assert user["role"] == "admin"
    user = await get_user(919872447)
    assert user["role"] == "accountant"


@pytest.mark.asyncio
async def test_invalidate_free_slots_clears_memory(monkeypatch):
    memory_cache.set("bookable_view:test", {"slots": []}, ttl=60)
    async def fake_redis():
        return None
    monkeypatch.setattr("services.cache.get_redis", fake_redis)
    await invalidate_free_slots("test")
    assert memory_cache.get("bookable_view:test") is None
