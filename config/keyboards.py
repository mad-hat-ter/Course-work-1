from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup

BTN_FREE_SHIFTS = "Просмотр свободных смен"
BTN_MY_STATS = "Мой график и статистика"
BTN_ADD_SCHEDULE = "Добавить расписание"
BTN_DEPT_STATS = "Просмотр статистики отдела"
BTN_BACK = "◀ Назад"
BTN_MAIN_MENU = "Главное меню"


def main_menu_keyboard(role: str) -> ReplyKeyboardMarkup:
    rows: list[list[KeyboardButton]] = []

    if role in ("curator", "admin"):
        rows.append([KeyboardButton(text=BTN_FREE_SHIFTS)])
        rows.append([KeyboardButton(text=BTN_MY_STATS)])

    if role == "admin":
        rows.append([KeyboardButton(text=BTN_ADD_SCHEDULE)])

    if role == "accountant":
        rows.append([KeyboardButton(text=BTN_DEPT_STATS)])

    rows.append([KeyboardButton(text=BTN_MAIN_MENU)])

    if not rows[:-1]:
        rows = [[KeyboardButton(text=BTN_MAIN_MENU)]]

    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True)


def back_inline() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=BTN_BACK, callback_data="nav:back")]]
    )


def inline_from_items(prefix: str, items: list[tuple[str, str]], back: bool = True) -> InlineKeyboardMarkup:
    rows = [[InlineKeyboardButton(text=label, callback_data=f"{prefix}:{idx}")] for idx, (label, _) in enumerate(items)]
    if back:
        rows.append([InlineKeyboardButton(text=BTN_BACK, callback_data="nav:back")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def confirm_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Да", callback_data="book:confirm:yes"),
                InlineKeyboardButton(text="❌ Нет", callback_data="book:confirm:no"),
            ],
            [InlineKeyboardButton(text=BTN_BACK, callback_data="nav:back")],
        ]
    )
