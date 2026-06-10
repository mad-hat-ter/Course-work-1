import asyncio
import logging
import sys
from aiogram import Bot, Dispatcher
from aiogram.exceptions import TelegramNetworkError
from aiogram.types import ErrorEvent
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from config.settings import settings
from handlers import accountant, admin, booking, common, stats
from scheduler.notify import check_upcoming_shifts
from services.bootstrap_cache import warm_cache
from services.sheets_client import close_client
from services.telegram_session import HttpxSession

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)


async def main() -> None:
    if not settings.BOT_TOKEN:
        raise SystemExit("Укажите BOT_TOKEN в файле .env")
    if not settings.GAS_WEBAPP_URL:
        raise SystemExit("Укажите GAS_WEBAPP_URL в файле .env")

    session = HttpxSession(proxy=settings.PROXY_URL) if settings.PROXY_URL else None
    bot = Bot(token=settings.BOT_TOKEN, session=session)
    dp = Dispatcher()
    dp.include_routers(common.router, booking.router, stats.router, admin.router,accountant.router)

    @dp.errors()
    async def on_error(event: ErrorEvent) -> None:
        logger.exception("Необработанная ошибка: %s", event.exception)
        update = event.update
        if update.message:
            await update.message.answer("Произошла ошибка. Попробуйте позже или нажмите /menu.")
        elif update.callback_query:
            await update.callback_query.answer("Произошла ошибка. Попробуйте позже.", show_alert=True)

    await warm_cache()

    try:
        me = await bot.get_me()
        logger.info("Telegram: @%s", me.username)
    except TelegramNetworkError as exc:
        raise SystemExit("Не удалось подключиться к Telegram.")


    scheduler = AsyncIOScheduler(timezone="Europe/Moscow")
    scheduler.add_job(
        check_upcoming_shifts,
        "cron",
        minute="*",
        args=[bot],
        id="shift_notifications",
        replace_existing=True,
    )
    scheduler.start()
    logger.info("Бот запущен")

    try:
        await dp.start_polling(bot)
    finally:
        scheduler.shutdown(wait=False)
        if session is not None:
            await session.close()
        await close_client()


if __name__ == "__main__":
    asyncio.run(main())
