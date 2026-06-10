from services.shift_sort import shift_entry_day_index, shift_entry_start_minutes, sort_shift_entries, sorted_day_labels


def test_sort_shift_entries_chronological():
    entries = [
        {"label": "Ср 12:00", "day": 2, "hour": "12:00", "datetime": "2026-06-11T12:00:00"},
        {"label": "Пн 16:00", "day": 0, "hour": "16:00", "datetime": "2026-06-09T16:00:00"},
        {"label": "Ср 16:00", "day": 2, "hour": "16:00", "datetime": "2026-06-11T16:00:00"},
        {"label": "Пт 17:00", "day": 4, "hour": "17:00", "datetime": "2026-06-13T17:00:00"},
        {"label": "Ср 19:00", "day": 2, "hour": "19:00", "datetime": "2026-06-11T19:00:00"},
    ]
    labels = [e["label"] for e in sort_shift_entries(entries)]
    assert labels == ["Пн 16:00", "Ср 12:00", "Ср 16:00", "Ср 19:00", "Пт 17:00"]


def test_sorted_day_labels():
    days_map = {
        "Сб": [{"day": 5}],
        "Ср": [{"day": 2}],
        "Пт": [{"day": 4}],
    }
    assert sorted_day_labels(days_map) == ["Ср", "Пт", "Сб"]


def test_shift_entry_day_index_from_label():
    assert shift_entry_day_index({"label": "Чт 10:00"}) == 3


def test_shift_entry_day_index_unknown():
    assert shift_entry_day_index({"label": "XX 10:00"}) == 99


def test_shift_entry_start_minutes_from_hour():
    assert shift_entry_start_minutes({"hour": "9:00"}) == 9 * 60


def test_shift_entry_start_minutes_from_label():
    assert shift_entry_start_minutes({"label": "Пн 09:30"}) == 9 * 60 + 30


def test_shift_entry_start_minutes_invalid_datetime_fallback():
    assert shift_entry_start_minutes({"datetime": "bad", "hour": "10:00"}) == 600
