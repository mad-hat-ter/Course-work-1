WEEKLY_BASE_LIMIT = 14


def calc_week_payment(main_shifts: int, base_rate: float, premium_rate: float) -> float:
    if main_shifts <= 0:
        return 0.0
    base_count = min(main_shifts, WEEKLY_BASE_LIMIT)
    premium_count = max(0, main_shifts - WEEKLY_BASE_LIMIT)
    return base_count * base_rate + premium_count * premium_rate


def count_shifts_for_person(cells: list[str], full_name: str) -> tuple[int, int]:
    main, reserve = 0, 0
    normalized_name = full_name.strip()
    for value in cells:
        if not value:
            continue
        raw = str(value).strip()
        is_reserve = raw.endswith("*")
        name = raw.rstrip("*").strip()
        if name != normalized_name:
            continue
        if is_reserve:
            reserve += 1
        else:
            main += 1
    return main, reserve


def format_money(amount: float) -> str:
    return f"{amount:,.0f}".replace(",", " ") + " ₽"
