import logging
from datetime import timedelta
from aiogram import Bot
from aiogram.exceptions import TelegramForbiddenError
from config.settings import settings
from services.cache import get_employees_cached, get_settings_cached, mark_notified
from services.sheets_client import get_shifts_at_hour
from services.timezone_utils import now_msk

logger = logging.getLogger(__name__)


async def check_upcoming_shifts(bot: Bot) -> None:
    try:
        cfg = await get_settings_cached()
    except Exception as exc:
        logger.warning("Не удалось загрузить настройки для уведомлений: %s", exc)
        return

    notify_min = int(cfg["NOTIFY_MINUTES"])
    now = now_msk()
    target = (now + timedelta(minutes=notify_min)).replace(minute=0, second=0, microsecond=0)
    target_iso = target.isoformat()
    try:
        shifts = await get_shifts_at_hour(target_iso)
    except Exception as exc:
        logger.warning("Не удалось получить смены на %s: %s", target_iso, exc)
        return
    if not shifts:
        return
    try:
        employees_list = await get_employees_cached()
    except Exception as exc:
        logger.warning("Не удалось загрузить сотрудников: %s", exc)
        return
    by_name = {e["full_name"]: e for e in employees_list}
    for item in shifts:
        raw_name = str(item.get("name", "")).strip()
        if not raw_name:
            continue
        name = raw_name.rstrip("*").strip()
        emp = by_name.get(name)
        if not emp:
            continue
        shift_key = str(item.get("shift_key", target_iso))
        ttl = notify_min * 60 + 3600
        if not await mark_notified(emp["telegram_id"], shift_key, ttl):
            continue
        try:
            await bot.send_message(emp["telegram_id"], "Привет! Пора на смену")
        except TelegramForbiddenError:
            admin_id = settings.ADMIN_TELEGRAM_ID
            if admin_id:
                try:
                    await bot.send_message(
                        admin_id,
                        f"⚠️ Ошибка: Не удалось оповестить {emp['full_name']} "
                        f"(ID: {emp['telegram_id']}), сотрудник заблокировал бота!",
                    )
                except Exception as notify_exc:
                    logger.warning("Не удалось уведомить админа: %s", notify_exc)
        except Exception as exc:
            logger.warning(
                "Ошибка отправки уведомления %s: %s",
                emp["telegram_id"],
                exc,
            )
