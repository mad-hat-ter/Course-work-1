from datetime import datetime
from unittest.mock import patch
import pytest
from handlers.booking import _group_slots_by_hour, _load_bookable_slots, _slot_key, _sorted_day_items, _user_booked_keys
from services.timezone_utils import MSK


def test_slot_key_from_fields():
    slot = {"day_label": "Пн", "hour": "09:00"}
    assert _slot_key(slot) == ("Пн", "09:00")


def test_slot_key_from_label():
    slot = {"label": "Ср 12:00"}
    assert _slot_key(slot) == ("Ср", "12:00")


def test_user_booked_keys_filters_other_people():
    entries = [
        {"label": "Пн 16:00", "value": "Аня Фролова", "hour": "16:00", "day_label": "Пн"},
        {"label": "Вт 10:00", "value": "Иван Петров", "hour": "10:00", "day_label": "Вт"},
        {"label": "Ср 12:00", "value": "Аня Фролова*", "hour": "12:00", "day_label": "Ср"},
    ]
    keys = _user_booked_keys(entries, "Аня Фролова")
    assert keys == {("Пн", "16:00"), ("Ср", "12:00")}


def test_sorted_day_items_week_order():
    days_map = {
        "Сб": [{"day": 5, "day_label": "Сб"}],
        "Ср": [{"day": 2, "day_label": "Ср"}],
        "Пт": [{"day": 4, "day_label": "Пт"}],
    }
    assert [label for label, _ in _sorted_day_items(days_map)] == ["Ср", "Пт", "Сб"]


def test_group_slots_by_hour_chronological():
    slots = [
        {"label": "Пн 14:00", "hour": "14:00", "datetime": "2026-06-08T14:00:00"},
        {"label": "Пн 09:00", "hour": "09:00", "datetime": "2026-06-08T09:00:00"},
        {"label": "Пн 11:00", "hour": "11:00", "datetime": "2026-06-08T11:00:00"},
    ]
    labels = [label for label, _ in _group_slots_by_hour(slots)]
    assert labels == ["Пн 09:00", "Пн 11:00", "Пн 14:00"]


@pytest.mark.asyncio
async def test_load_bookable_slots_filters_past_and_booked(monkeypatch, sample_bookable_view):
    async def fake_view(sheet):
        return sample_bookable_view
    monkeypatch.setattr("handlers.booking.get_bookable_view_cached", fake_view)
    with patch("handlers.booking.is_slot_bookable") as mock_bookable:
        mock_bookable.side_effect = lambda dt: dt.hour >= 18
        slots = await _load_bookable_slots("08.06–14.06", "Аня Фролова")
    labels = [s["label"] for s in slots]
    assert labels == ["Ср 18:00"]


@pytest.mark.asyncio
async def test_load_bookable_slots_skips_without_datetime(monkeypatch):
    async def fake_view(sheet):
        return {"slots": [{"label": "Пн 09:00"}], "entries": []}
    monkeypatch.setattr("handlers.booking.get_bookable_view_cached", fake_view)
    slots = await _load_bookable_slots("08.06–14.06")
    assert slots == []
