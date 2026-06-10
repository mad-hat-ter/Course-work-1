import logging
from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message
from config.keyboards import BTN_ADD_SCHEDULE, main_menu_keyboard
from services.auth import require_role
from services.cache import refresh_schedule_sheets, set_opening_time
from services.sheets_client import register_sheet
from services.timezone_utils import parse_opening_time

logger = logging.getLogger(__name__)
router = Router()


class AdminStates(StatesGroup):
    waiting_sheet_name = State()
    waiting_opening_time = State()


@router.message(F.text == BTN_ADD_SCHEDULE)
@require_role("admin")
async def add_schedule_start(message: Message, user: dict, state: FSMContext) -> None:
    await state.set_state(AdminStates.waiting_sheet_name)
    await message.answer(
        "Введите точное название листа с расписанием\n"
        "(например: 02.06–08.06):"
    )


@router.message(AdminStates.waiting_sheet_name)
@require_role("admin")
async def add_schedule_sheet(message: Message, user: dict, state: FSMContext) -> None:
    sheet_name = message.text.strip()
    await state.update_data(sheet_name=sheet_name)
    await state.set_state(AdminStates.waiting_opening_time)
    await message.answer(
        "Введите дату и время открытия записи по МСК.\n"
        "Формат: ДД.ММ.ГГГГ ЧЧ:ММ\n"
        "Пример: 07.06.2026 09:00"
    )


@router.message(AdminStates.waiting_opening_time)
@require_role("admin")
async def add_schedule_time(message: Message, user: dict, state: FSMContext) -> None:
    data = await state.get_data()
    sheet_name = data["sheet_name"]
    raw_time = message.text.strip()
    try:
        opening_dt = parse_opening_time(raw_time)
    except ValueError:
        await message.answer("Неверный формат даты. Пример: 07.06.2026 09:00")
        return
    opening_str = opening_dt.strftime("%Y-%m-%d %H:%M:%S")
    try:
        result = await register_sheet(sheet_name, opening_str)
    except Exception as exc:
        logger.exception("Ошибка регистрации листа: %s", exc)
        await message.answer("Произошла ошибка. Перезагрузите бота.")
        await state.clear()
        return

    if not result.get("success"):
        reason = result.get("reason", "unknown")
        if reason == "sheet_not_found":
            await message.answer("Не удалось найти лист для добавления.")
        else:
            await message.answer("Не удалось добавить расписание.")
        await state.clear()
        return

    await set_opening_time(sheet_name, opening_str)
    await refresh_schedule_sheets()
    await state.clear()
    await message.answer(
        f"Расписание «{sheet_name}» добавлено.\n"
        f"Запись откроется: {opening_dt.strftime('%d.%m.%Y %H:%M')} (МСК).",
        reply_markup=main_menu_keyboard(user["role"]),
    )
