from datetime import datetime
from unittest.mock import patch
import pytest
from services.timezone_utils import MSK, is_slot_bookable, min_bookable_time, now_msk, parse_opening_time


def test_now_msk_timezone():
    assert now_msk().tzinfo == MSK


def test_min_bookable_is_next_hour():
    with patch("services.timezone_utils.now_msk") as mock_now:
        mock_now.return_value = datetime(2026, 6, 7, 14, 30, tzinfo=MSK)
        assert min_bookable_time() == datetime(2026, 6, 7, 15, 0, tzinfo=MSK)


def test_slot_current_hour_not_bookable():
    with patch("services.timezone_utils.now_msk") as mock_now:
        mock_now.return_value = datetime(2026, 6, 7, 14, 30, tzinfo=MSK)
        slot = datetime(2026, 6, 7, 14, 0, tzinfo=MSK)
        assert is_slot_bookable(slot) is False


def test_slot_in_2_hours_bookable():
    with patch("services.timezone_utils.now_msk") as mock_now:
        mock_now.return_value = datetime(2026, 6, 7, 14, 30, tzinfo=MSK)
        slot = datetime(2026, 6, 7, 16, 0, tzinfo=MSK)
        assert is_slot_bookable(slot) is True


def test_slot_without_timezone_assumes_msk():
    with patch("services.timezone_utils.now_msk") as mock_now:
        mock_now.return_value = datetime(2026, 6, 7, 14, 30, tzinfo=MSK)
        slot = datetime(2026, 6, 7, 16, 0)
        assert is_slot_bookable(slot) is True


@pytest.mark.parametrize(
    "value,expected",
    [
        ("2026-06-08 12:00:00", datetime(2026, 6, 8, 12, 0, tzinfo=MSK)),
        ("2026-06-08 12:00", datetime(2026, 6, 8, 12, 0, tzinfo=MSK)),
        ("08.06.2026 09:00", datetime(2026, 6, 8, 9, 0, tzinfo=MSK)),
    ],
)
def test_parse_opening_time_valid_formats(value, expected):
    assert parse_opening_time(value) == expected


def test_parse_opening_time_strips_spaces():
    assert parse_opening_time("  2026-06-08 12:00:00  ") == datetime(
        2026, 6, 8, 12, 0, tzinfo=MSK
    )


def test_parse_opening_time_invalid_raises():
    with pytest.raises(ValueError, match="Не удалось разобрать дату"):
        parse_opening_time("not-a-date")
