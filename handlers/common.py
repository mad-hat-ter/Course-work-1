from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from config.keyboards import BTN_MAIN_MENU, main_menu_keyboard
from services.auth import get_access_message, get_user

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext) -> None:
    await state.clear()
    user = await get_user(message.from_user.id)
    if user is None:
        await message.answer(await get_access_message(message.from_user.id))
        return
    await message.answer(
        f"Здравствуйте, {user['full_name']}!\nВыберите действие:",
        reply_markup=main_menu_keyboard(user["role"]),
    )


@router.message(Command("menu"))
@router.message(F.text == BTN_MAIN_MENU)
async def cmd_menu(message: Message, state: FSMContext) -> None:
    await state.clear()
    user = await get_user(message.from_user.id)
    if user is None:
        await message.answer(await get_access_message(message.from_user.id))
        return
    await message.answer("Главное меню:", reply_markup=main_menu_keyboard(user["role"]))
