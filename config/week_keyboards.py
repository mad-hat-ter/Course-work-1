from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from config.keyboards import BTN_BACK

BTN_BACK_CALLBACK = "nav:back"


def multi_week_keyboard(prefix: str, weeks: list[str], selected: set[int]) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    for idx, week in enumerate(weeks):
        mark = "✅ " if idx in selected else ""
        rows.append(
            [
                InlineKeyboardButton(
                    text=f"{mark}{week}",
                    callback_data=f"{prefix}:toggle:{idx}",
                )
            ]
        )

    actions: list[InlineKeyboardButton] = []
    if len(weeks) > 1:
        actions.append(InlineKeyboardButton(text="Все недели", callback_data=f"{prefix}:all"))
    actions.append(InlineKeyboardButton(text="Показать отчёт", callback_data=f"{prefix}:done"))
    rows.append(actions)
    rows.append(
        [InlineKeyboardButton(text=BTN_BACK, callback_data=BTN_BACK_CALLBACK)]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def selected_week_names(weeks: list[str], selected: set[int]) -> list[str]:
    return [weeks[idx] for idx in sorted(selected) if 0 <= idx < len(weeks)]
