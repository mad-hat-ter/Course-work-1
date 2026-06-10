from services import memory_cache
from services.bootstrap_cache import apply_bootstrap, get_opening_time_local


def test_apply_bootstrap_populates_caches():
    data = {
        "employees": [{"telegram_id": 1, "full_name": "A", "role": "curator", "is_active": True}],
        "settings": {"BASE_RATE": 400, "PREMIUM_RATE": 600, "NOTIFY_MINUTES": 15},
        "metadata": [
            {"sheet_name": "08.06–14.06", "opening_time": "2026-06-08 12:00:00", "is_active": True},
            {"sheet_name": "01.06–07.06", "opening_time": "2026-06-01 12:00:00", "is_active": False},
        ],
        "schedule_sheets": ["08.06–14.06", "01.06–07.06"],
    }
    apply_bootstrap(data)

    assert memory_cache.get("employees:cache")[0]["full_name"] == "A"
    assert memory_cache.get("settings:cache")["BASE_RATE"] == 400
    assert memory_cache.get("schedule_sheets:cache") == ["08.06–14.06", "01.06–07.06"]
    assert get_opening_time_local("08.06–14.06") == "2026-06-08 12:00:00"
    assert get_opening_time_local("01.06–07.06") is None


def test_apply_bootstrap_uses_sheets_alias():
    apply_bootstrap({"sheets": ["A", "B"]})
    assert memory_cache.get("schedule_sheets:cache") == ["A", "B"]


def test_apply_bootstrap_empty_payload():
    apply_bootstrap({})
    assert memory_cache.get("bootstrap") == {}
