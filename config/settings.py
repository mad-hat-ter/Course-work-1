import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    BOT_TOKEN: str
    GAS_WEBAPP_URL: str
    REDIS_URL: str
    ADMIN_TELEGRAM_ID: int | None
    PROXY_URL: str | None


def _parse_admin_id(value: str | None) -> int | None:
    if not value:
        return None
    return int(value)


settings = Settings(
    BOT_TOKEN=os.getenv("BOT_TOKEN", ""),
    GAS_WEBAPP_URL=os.getenv("GAS_WEBAPP_URL", ""),
    REDIS_URL=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
    ADMIN_TELEGRAM_ID=_parse_admin_id(os.getenv("ADMIN_TELEGRAM_ID")),
    PROXY_URL=os.getenv("PROXY_URL") or None,
)
