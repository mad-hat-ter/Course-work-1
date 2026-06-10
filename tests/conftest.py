import pytest
from services import memory_cache
from services.bootstrap_cache import _opening_times


@pytest.fixture(autouse=True)
def clear_memory_cache():
    memory_cache._store.clear()
    _opening_times.clear()
    yield
    memory_cache._store.clear()
    _opening_times.clear()


@pytest.fixture
def sample_settings():
    return {"BASE_RATE": 400.0, "PREMIUM_RATE": 600.0, "NOTIFY_MINUTES": 15}


@pytest.fixture
def sample_employees():
    return [
        {
            "telegram_id": 123,
            "full_name": "Аня Фролова",
            "role": "curator",
            "is_active": True,
        },
        {
            "telegram_id": 456,
            "full_name": "Иван Петров",
            "role": "admin",
            "is_active": True,
        },
        {
            "telegram_id": 789,
            "full_name": "Бухгалтер",
            "role": "accountant",
            "is_active": True,
        },
    ]


@pytest.fixture
def sample_sheet_entries():
    return {
        "08.06–14.06": {
            "entries": [
                {
                    "label": "Пн 16:00",
                    "value": "Аня Фролова",
                    "hour": "16:00",
                    "day": 0,
                    "datetime": "2026-06-09T16:00:00",
                    "is_reserve": False,
                },
                {
                    "label": "Ср 12:00",
                    "value": "Аня Фролова",
                    "hour": "12:00",
                    "day": 2,
                    "datetime": "2026-06-11T12:00:00",
                    "is_reserve": False,
                },
                {
                    "label": "Пт 17:00",
                    "value": "Иван Петров",
                    "hour": "17:00",
                    "day": 4,
                    "datetime": "2026-06-13T17:00:00",
                    "is_reserve": False,
                },
            ]
        },
        "01.06–07.06": {
            "entries": [
                {
                    "label": "Вт 10:00",
                    "value": "Аня Фролова*",
                    "hour": "10:00",
                    "day": 1,
                    "datetime": "2026-06-03T10:00:00",
                    "is_reserve": True,
                }
            ]
        },
    }


@pytest.fixture
def sample_bookable_view():
    return {
        "slots": [
            {
                "label": "Ср 18:00",
                "cell": "D10",
                "hour": "18:00",
                "day_label": "Ср",
                "day": 2,
                "datetime": "2026-06-11T18:00:00",
            },
            {
                "label": "Пн 09:00",
                "cell": "C5",
                "hour": "09:00",
                "day_label": "Пн",
                "day": 0,
                "datetime": "2026-06-09T09:00:00",
            },
        ],
        "entries": [
            {
                "label": "Пн 16:00",
                "value": "Аня Фролова",
                "hour": "16:00",
                "day_label": "Пн",
            }
        ],
    }
