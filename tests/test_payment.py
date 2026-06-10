import pytest
from services.payment import calc_week_payment, count_shifts_for_person, format_money


def test_premium_after_14():
    assert calc_week_payment(16, base_rate=400, premium_rate=600) == 6800


def test_only_base():
    assert calc_week_payment(10, base_rate=400, premium_rate=600) == 4000


def test_exactly_14():
    assert calc_week_payment(14, base_rate=400, premium_rate=600) == 5600


def test_zero_shifts():
    assert calc_week_payment(0, base_rate=400, premium_rate=600) == 0.0


def test_negative_shifts_treated_as_zero():
    assert calc_week_payment(-3, base_rate=400, premium_rate=600) == 0.0


def test_one_premium_shift():
    assert calc_week_payment(15, base_rate=400, premium_rate=600) == 6200


def test_reserve_not_counted_in_main():
    cells = ["Аня Фролова*", "Аня Фролова*", "Иван Петров"]
    main, reserve = count_shifts_for_person(cells, "Аня Фролова")
    assert main == 0
    assert reserve == 2


def test_main_shifts():
    cells = ["Аня Фролова", "Аня Фролова", "Аня Фролова*"]
    main, reserve = count_shifts_for_person(cells, "Аня Фролова")
    assert main == 2
    assert reserve == 1


def test_count_ignores_other_people():
    cells = ["Аня Фролова", "Иван Петров", "  Аня Фролова  "]
    main, reserve = count_shifts_for_person(cells, "Аня Фролова")
    assert main == 2
    assert reserve == 0


def test_count_skips_empty_cells():
    cells = ["", None, "Аня Фролова"]
    main, reserve = count_shifts_for_person(cells, "Аня Фролова")
    assert main == 1
    assert reserve == 0


def test_count_name_with_spaces():
    cells = ["Аня Фролова*"]
    main, reserve = count_shifts_for_person(cells, "  Аня Фролова  ")
    assert main == 0
    assert reserve == 1


def test_format_money():
    assert format_money(2000) == "2 000 ₽"


def test_format_money_large_value():
    assert format_money(1234567) == "1 234 567 ₽"
