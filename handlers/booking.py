import logging
from datetime import datetime
import httpx
from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from config.keyboards import (
    BTN_FREE_SHIFTS,
    BTN_MAIN_MENU,
    confirm_keyboard,
    inline_from_items,
    main_menu_keyboard,
)
from services.auth import require_role
from services.cache import (
    get_bookable_view_cached,
    invalidate_free_slots,
    is_sheet_open_for_booking,
    refresh_schedule_sheets,
)
from services.sheets_client import book_shift
from services.shift_sort import shift_entry_start_minutes, sorted_day_labels
from services.timezone_utils import is_slot_bookable

logger = logging.getLogger(__name__)
router = Router()


class BookingStates(StatesGroup):
    choosing_week = State()
    choosing_day = State()
    choosing_hour = State()
    confirming = State()


async def _available_weeks() -> list[tuple[str, str]]:
    sheets = await refresh_schedule_sheets()
    result: list[tuple[str, str]] = []
    for sheet in sheets:
        if await is_sheet_open_for_booking(sheet):
            result.append((sheet, sheet))
    return result


def _slot_key(slot: dict) -> tuple[str, str]:
    day = str(slot.get("day_label") or "").strip()
    hour = str(slot.get("hour") or "").strip()
    if (not day or not hour) and slot.get("label"):
        parts = str(slot["label"]).split()
        if len(parts) >= 2:
            day, hour = parts[0], parts[1]
    return day, hour


def _user_booked_keys(entries: list[dict], full_name: str) -> set[tuple[str, str]]:
    name = full_name.strip()
    keys: set[tuple[str, str]] = set()
    for entry in entries:
        value = str(entry.get("value", "")).strip()
        if value.rstrip("*").strip() != name:
            continue
        keys.add(_slot_key(entry))
    return keys


async def _load_bookable_slots(sheet: str, full_name: str | None = None) -> list[dict]:
    data = await get_bookable_view_cached(sheet)
    slots = data.get("slots", [])
    booked_keys: set[tuple[str, str]] = set()
    if full_name:
        booked_keys = _user_booked_keys(data.get("entries", []), full_name)
    bookable = []
    for slot in slots:
        start_raw = slot.get("datetime")
        if not start_raw:
            continue
        start = datetime.fromisoformat(start_raw)
        if not is_slot_bookable(start):
            continue
        if _slot_key(slot) in booked_keys:
            continue
        bookable.append(slot)
    return bookable


def _sorted_day_items(days_map: dict[str, list[dict]]) -> list[tuple[str, str]]:
    return [(label, label) for label in sorted_day_labels(days_map)]


def _group_slots_by_hour(slots: list[dict]) -> list[tuple[str, list[dict]]]:
    groups: dict[str, list[dict]] = {}
    for slot in slots:
        label = slot.get("label") or slot.get("hour") or "?"
        groups.setdefault(label, []).append(slot)
    sorted_labels = sorted(groups.keys(), key=lambda label: shift_entry_start_minutes(groups[label][0]))
    return [(label, groups[label]) for label in sorted_labels]


@router.message(F.text == BTN_FREE_SHIFTS)
@require_role("curator", "admin")
async def start_booking(message: Message, user: dict, state: FSMContext) -> None:
    await state.clear()
    wait_msg = await message.answer("Загружаю… ⏳")
    try:
        weeks = await _available_weeks()
    except httpx.HTTPError as exc:
        logger.exception("Ошибка связи с таблицей: %s", exc)
        await wait_msg.edit_text(
            "Не удалось связаться с Google Таблицей. Попробуйте через минуту."
        )
        return

    if not weeks:
        await wait_msg.edit_text("Нет свободных смен для записи.", reply_markup=main_menu_keyboard(user["role"]))
        return

    await state.update_data(weeks=weeks)
    await state.set_state(BookingStates.choosing_week)
    await wait_msg.edit_text("Выберите неделю:", reply_markup=inline_from_items("book:week", weeks))


@router.callback_query(BookingStates.choosing_week, F.data.startswith("book:week:"))
@require_role("curator", "admin")
async def choose_week(callback: CallbackQuery, user: dict, state: FSMContext) -> None:
    idx = int(callback.data.split(":")[-1])
    data = await state.get_data()
    weeks: list[tuple[str, str]] = data["weeks"]
    label, sheet = weeks[idx]
    await callback.answer()
    await callback.message.edit_text(f"Загружаю {label}… ⏳")
    try:
        slots = await _load_bookable_slots(sheet, user["full_name"])
    except httpx.HTTPError as exc:
        logger.exception("Ошибка загрузки слотов: %s", exc)
        await callback.message.edit_text("Не удалось загрузить расписание. Попробуйте через минуту.")
        await state.clear()
        return
    except Exception as exc:
        logger.exception("Ошибка загрузки слотов: %s", exc)
        await callback.message.edit_text("Произошла ошибка. Перезагрузите бота.")
        await state.clear()
        return

    if not slots:
        await callback.message.edit_text("Нет свободных смен для записи на этой неделе.")
        await state.clear()
        return
    days_map: dict[str, list[dict]] = {}
    for slot in slots:
        day = slot.get("day_label") or slot.get("day") or "?"
        days_map.setdefault(day, []).append(slot)
    day_items = _sorted_day_items(days_map)
    await state.update_data(sheet=sheet, sheet_label=label, days_map=days_map, day_items=day_items)
    await state.set_state(BookingStates.choosing_day)
    await callback.message.edit_text(
        f"Неделя {label}\nВыберите день:",
        reply_markup=inline_from_items("book:day", day_items),
    )


@router.callback_query(BookingStates.choosing_day, F.data.startswith("book:day:"))
@require_role("curator", "admin")
async def choose_day(callback: CallbackQuery, user: dict, state: FSMContext) -> None:
    idx = int(callback.data.split(":")[-1])
    data = await state.get_data()
    day_items: list[tuple[str, str]] = data["day_items"]
    day_label = day_items[idx][0]
    days_map: dict[str, list[dict]] = data["days_map"]
    slots = days_map[day_label]
    hour_groups = _group_slots_by_hour(slots)
    hour_items = [(label, label) for label, _ in hour_groups]
    await state.update_data(day_label=day_label, hour_groups=hour_groups, hour_items=hour_items)
    await state.set_state(BookingStates.choosing_hour)
    await callback.message.edit_text(f"{day_label}\nВыберите час:", reply_markup=inline_from_items("book:hour", hour_items))
    await callback.answer()


@router.callback_query(BookingStates.choosing_hour, F.data.startswith("book:hour:"))
@require_role("curator", "admin")
async def choose_hour(callback: CallbackQuery, user: dict, state: FSMContext) -> None:
    idx = int(callback.data.split(":")[-1])
    data = await state.get_data()
    hour_groups: list[tuple[str, list[dict]]] = data["hour_groups"]
    label, group_slots = hour_groups[idx]
    slot = group_slots[0]
    await state.update_data(cell=slot["cell"], slot_label=slot.get("label", slot.get("hour", "")))
    await state.set_state(BookingStates.confirming)
    await callback.message.edit_text(f"Записаться на смену {slot.get('label', '')}?", reply_markup=confirm_keyboard())
    await callback.answer()


@router.callback_query(BookingStates.confirming, F.data == "book:confirm:yes")
@require_role("curator", "admin")
async def confirm_booking(callback: CallbackQuery, user: dict, state: FSMContext) -> None:
    data = await state.get_data()
    slot_label = data.get("slot_label", "")
    try:
        sheet_data = await get_bookable_view_cached(data["sheet"])
        if _slot_key({"label": slot_label}) in _user_booked_keys(sheet_data.get("entries", []), user["full_name"]):
            await callback.message.edit_text(f"Вы уже записаны на смену {slot_label}.")
            await state.clear()
            await callback.answer()
            return
    except Exception as exc:
        logger.warning("Повторная проверка смены не удалась: %s", exc)

    try:
        result = await book_shift(
            sheet=data["sheet"],
            cell=data["cell"],
            name=user["full_name"],
            tg_id=callback.from_user.id,
        )
    except httpx.HTTPError as exc:
        logger.exception("Ошибка связи при записи: %s", exc)
        await callback.message.edit_text("Не удалось связаться с таблицей. Попробуйте через минуту.")
        await state.clear()
        await callback.answer()
        return
    except Exception as exc:
        logger.exception("Ошибка записи на смену: %s", exc)
        await callback.message.edit_text("Произошла ошибка. Перезагрузите бота.")
        await state.clear()
        await callback.answer()
        return
    if not result.get("success"):
        await callback.message.edit_text("Выбранная смена недоступна для записи.")
        await state.clear()
        await callback.answer()
        return
    await invalidate_free_slots(data["sheet"])
    cell = result.get("cell", data["cell"])
    await callback.message.edit_text(
        f"Вы записаны на смену {data.get('slot_label', '')} ✅\n"
        f"Ячейка: {cell}\n"
        f"Нажмите /menu для возврата в меню."
    )
    await state.clear()
    await callback.answer()


@router.callback_query(BookingStates.confirming, F.data == "book:confirm:no")
@require_role("curator", "admin")
async def cancel_booking(callback: CallbackQuery, user: dict, state: FSMContext) -> None:
    await state.clear()
    await callback.message.edit_text("Запись отменена. /menu — главное меню.")
    await callback.answer()


@router.callback_query(F.data == "nav:back")
async def navigate_back(callback: CallbackQuery, state: FSMContext) -> None:
    current = await state.get_state()
    data = await state.get_data()
    if current == BookingStates.confirming.state:
        hour_items = data.get("hour_items", [])
        await state.set_state(BookingStates.choosing_hour)
        await callback.message.edit_text(
            f"{data.get('day_label', '')}\nВыберите час:",
            reply_markup=inline_from_items("book:hour", hour_items),
        )
    elif current == BookingStates.choosing_hour.state:
        day_items = data.get("day_items", [])
        await state.set_state(BookingStates.choosing_day)
        await callback.message.edit_text(
            f"Неделя {data.get('sheet_label', '')}\nВыберите день:",
            reply_markup=inline_from_items("book:day", day_items),
        )
    elif current == BookingStates.choosing_day.state:
        weeks = data.get("weeks", [])
        await state.set_state(BookingStates.choosing_week)
        await callback.message.edit_text(
            "Выберите неделю:",
            reply_markup=inline_from_items("book:week", weeks),
        )
    else:
        await state.clear()
        await callback.message.edit_text("Действие отменено. /menu — главное меню.")

    await callback.answer()
