import logging
from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from config.keyboards import BTN_DEPT_STATS, main_menu_keyboard, main_menu_keyboard
from config.week_keyboards import multi_week_keyboard, selected_week_names
from services.auth import require_role
from services.cache import get_settings_cached, refresh_schedule_sheets
from services.payment import calc_week_payment, count_shifts_for_person, format_money
from services.sheet_names import sort_schedule_sheets
from services.sheets_client import get_sheet_data

logger = logging.getLogger(__name__)
router = Router()

SELECT_PROMPT = "Выберите одну или несколько недель, затем нажмите «Показать отчёт»:"


class AccountantStates(StatesGroup):
    choosing_sheet = State()


async def _load_week_names() -> list[str]:
    return sort_schedule_sheets(await refresh_schedule_sheets())


def _report_title(sheet_keys: list[str]) -> str:
    if len(sheet_keys) == 1:
        return f"Отчёт по сменам — неделя {sheet_keys[0]}"
    return f"Отчёт по сменам — {len(sheet_keys)} нед."


async def _build_department_report(sheet_keys: list[str]) -> str | None:
    if not sheet_keys:
        return None

    settings = await get_settings_cached()
    relevant = sheet_keys
    weekly_counts: dict[str, list[int]] = {}
    for sheet in relevant:
        try:
            data = await get_sheet_data(sheet)
        except Exception:
            logger.exception("Не удалось загрузить лист %s", sheet)
            continue
        cells = [str(e.get("value", "")) for e in data.get("entries", []) if e.get("value")]
        names = {str(v).rstrip("*").strip() for v in cells if v}
        for name in names:
            main, _ = count_shifts_for_person(cells, name)
            if main > 0:
                weekly_counts.setdefault(name, []).append(main)

    if not weekly_counts:
        return None

    lines = [f"<b>{_report_title(relevant)}</b>\n"]
    grand_total = 0.0

    for name in sorted(weekly_counts.keys()):
        week_counts = weekly_counts[name]
        shift_total = sum(week_counts)
        payment = sum(
            calc_week_payment(wc, settings["BASE_RATE"], settings["PREMIUM_RATE"])
            for wc in week_counts
        )
        grand_total += payment
        lines.append(f"• <b>{name}</b>: {shift_total} смен — {format_money(payment)}")
    lines.append(f"\n<b>Итого начислений:</b> {format_money(grand_total)}")
    return "\n".join(lines)


@router.message(F.text == BTN_DEPT_STATS)
@require_role("accountant")
async def start_dept_stats(message: Message, user: dict, state: FSMContext) -> None:
    await state.clear()
    weeks = await _load_week_names()
    if not weeks:
        await message.answer("В таблице нет листов с расписанием.")
        return
    await state.update_data(week_names=weeks, selected=[])
    await state.set_state(AccountantStates.choosing_sheet)
    await message.answer(SELECT_PROMPT, reply_markup=multi_week_keyboard("acct:week", weeks, set()))


@router.callback_query(AccountantStates.choosing_sheet, F.data.startswith("acct:week:"))
@require_role("accountant")
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
        await callback.message.edit_reply_markup(reply_markup=multi_week_keyboard("acct:week", weeks, selected))
        return

    if action == "all":
        selected = set(range(len(weeks)))
        await callback.answer("Выбраны все недели")
        await state.update_data(selected=sorted(selected))
        await callback.message.edit_reply_markup(reply_markup=multi_week_keyboard("acct:week", weeks, selected))
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
            text = await _build_department_report(sheet_keys)
        except Exception as exc:
            logger.exception("Ошибка отчёта: %s", exc)
            await callback.message.edit_text("Не удалось получить информацию о сменах.")
            return

        if text is None:
            await callback.message.edit_text("Нет смен на выбранных неделях.")
        else:
            await callback.message.edit_text(text, parse_mode="HTML")
        return

    await callback.answer()


@router.callback_query(AccountantStates.choosing_sheet, F.data == "nav:back")
@require_role("accountant")
async def cancel_dept_stats(callback: CallbackQuery, user: dict, state: FSMContext) -> None:
    await state.clear()
    await callback.message.edit_text("Главное меню:")
    await callback.message.answer("Выберите действие:", reply_markup=main_menu_keyboard(user["role"]))
    await callback.answer()
