import logging
from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from config.keyboards import BTN_MY_STATS, main_menu_keyboard
from config.week_keyboards import multi_week_keyboard, selected_week_names
from services.auth import require_role
from services.cache import get_settings_cached, refresh_schedule_sheets
from services.payment import calc_week_payment, count_shifts_for_person, format_money
from services.sheet_names import sort_schedule_sheets
from services.sheets_client import get_sheet_data
from services.shift_sort import sort_shift_entries

logger = logging.getLogger(__name__)
router = Router()

SELECT_PROMPT = "Выберите одну или несколько недель, затем нажмите «Показать отчёт»:"


class StatsStates(StatesGroup):
    choosing_sheet = State()


async def _load_week_names() -> list[str]:
    return sort_schedule_sheets(await refresh_schedule_sheets())


async def _build_stats_message(full_name: str, sheet_keys: list[str]) -> str | None:
    if not sheet_keys:
        return None

    settings = await get_settings_cached()
    relevant = sheet_keys
    total_main = 0
    total_reserve = 0
    total_payment = 0.0
    lines: list[str] = []

    for sheet in relevant:
        try:
            data = await get_sheet_data(sheet)
        except Exception:
            logger.exception("Не удалось загрузить лист %s", sheet)
            continue
        cells = [str(e.get("value", "")) for e in data.get("entries", []) if e.get("value")]
        main, reserve = count_shifts_for_person(cells, full_name)
        if main == 0 and reserve == 0:
            continue
        week_payment = calc_week_payment(main, settings["BASE_RATE"], settings["PREMIUM_RATE"])
        total_main += main
        total_reserve += reserve
        total_payment += week_payment

        user_entries = [
            e
            for e in data.get("entries", [])
            if full_name in str(e.get("value", "")).rstrip("*")
        ]
        shift_lines = [
            f"• {e.get('label', '')} — {'резерв' if e.get('is_reserve') else 'основная'}"
            for e in sort_shift_entries(user_entries)
        ]
        lines.append(f"<b>Неделя {sheet}</b>")
        lines.extend(shift_lines[:20])
        lines.append(f"Смен: {main + reserve} (осн: {main}) | Оплата: {format_money(week_payment)}")
        lines.append("")

    if total_main == 0 and total_reserve == 0:
        return None

    header = "<b>Ваша статистика</b>\n\n"
    body = "\n".join(lines)
    footer = (
        f"<b>Итого за период</b>\n<pre>Смен (осн.): {total_main}\n"
        f"Резервных: {total_reserve}\n"
        f"Оплата: {format_money(total_payment)}</pre>"
    )
    return header + body + footer


@router.message(F.text == BTN_MY_STATS)
@require_role("curator", "admin")
async def start_stats(message: Message, user: dict, state: FSMContext) -> None:
    await state.clear()
    weeks = await _load_week_names()
    if not weeks:
        await message.answer("В таблице нет листов с расписанием.")
        return

    await state.update_data(week_names=weeks, selected=[])
    await state.set_state(StatsStates.choosing_sheet)
    await message.answer(
        SELECT_PROMPT,
        reply_markup=multi_week_keyboard("stats:week", weeks, set()),
    )


@router.callback_query(StatsStates.choosing_sheet, F.data.startswith("stats:week:"))
@require_role("curator", "admin")
async def handle_week_selection(callback: CallbackQuery, user: dict, state: FSMContext) -> None:
    data = await state.get_data()
    weeks: list[str] = data.get("week_names", [])
    selected = set(data.get("selected", []))
    action = callback.data.split(":")[2]
    if action == "toggle":
        idx = int(callback.data.split(":")[-1])
        if idx in selected:
            selected.remove(idx)
        else:
            selected.add(idx)
        await callback.answer()
        await state.update_data(selected=sorted(selected))
        await callback.message.edit_reply_markup(reply_markup=multi_week_keyboard("stats:week", weeks, selected))
        return
    if action == "all":
        selected = set(range(len(weeks)))
        await callback.answer("Выбраны все недели")
        await state.update_data(selected=sorted(selected))
        await callback.message.edit_reply_markup(reply_markup=multi_week_keyboard("stats:week", weeks, selected))
        return

    if action == "done":
        if not selected:
            await callback.answer("Выберите хотя бы одну неделю", show_alert=True)
            return
        sheet_keys = selected_week_names(weeks, selected)
        await callback.answer("Формирую отчёт…")
        await state.clear()
        await callback.message.edit_text("Формирую отчёт… ⏳")
        try:
            text = await _build_stats_message(user["full_name"], sheet_keys)
        except Exception as exc:
            logger.exception("Ошибка статистики: %s", exc)
            await callback.message.edit_text("Произошла ошибка. Перезагрузите бота.")
            return

        if text is None:
            await callback.message.edit_text("Нет ваших смен на выбранных неделях.")
        else:
            await callback.message.edit_text(text, parse_mode="HTML")
        return

    await callback.answer()


@router.callback_query(StatsStates.choosing_sheet, F.data == "nav:back")
@require_role("curator", "admin")
async def cancel_stats(callback: CallbackQuery, user: dict, state: FSMContext) -> None:
    await state.clear()
    await callback.message.edit_text("Главное меню:")
    await callback.message.answer("Выберите действие:", reply_markup=main_menu_keyboard(user["role"]))
    await callback.answer()
