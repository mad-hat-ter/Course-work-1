from functools import wraps
from typing import Callable, ParamSpec, TypeVar
from aiogram.types import CallbackQuery, Message
from services.cache import refresh_employees

P = ParamSpec("P")
R = TypeVar("R")


async def get_user(tg_id: int) -> dict | None:
    employees = await refresh_employees()
    for emp in employees:
        if emp["telegram_id"] == tg_id and emp.get("is_active", True):
            return emp
    return None


async def get_access_message(tg_id: int) -> str:
    employees = await refresh_employees()
    if not employees:
        return (
            "У вас нет доступа к боту.\n\n"
            "Бот не смог загрузить список сотрудников из Google Таблицы.\n"
            "Проверьте GAS_WEBAPP_URL и доступность веб-приложения."
        )
    return (
        f"У вас нет доступа к боту.\n\n"
        f"Ваш Telegram ID: {tg_id}\n"
        f"Обратитесь к администратору, чтобы добавить вас на лист «Сотрудники»."
    )


def require_role(*roles: str) -> Callable[[Callable[P, R]], Callable[P, R]]:
    def decorator(handler: Callable[P, R]) -> Callable[P, R]:
        @wraps(handler)
        async def wrapper(event: Message | CallbackQuery, *args: P.args, **kwargs: P.kwargs):
            user = await get_user(event.from_user.id)
            if user is None:
                text = await get_access_message(event.from_user.id)
                if isinstance(event, CallbackQuery):
                    await event.answer(text, show_alert=True)
                else:
                    await event.answer(text)
                return None
            if roles and user["role"] not in roles:
                text = "Недостаточно прав для этого действия."
                if isinstance(event, CallbackQuery):
                    await event.answer(text, show_alert=True)
                else:
                    await event.answer(text)
                return None
            kwargs["user"] = user
            return await handler(event, *args, **kwargs)
        return wrapper
    return decorator
