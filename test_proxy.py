import asyncio
import os

import httpx
from dotenv import load_dotenv

load_dotenv()

PROXIES_TO_TEST = [
    os.getenv("PROXY_URL", "").strip(),
    "socks5://149.62.186.244:1080",
    "socks5://162.240.96.211:1080",
    "socks5://144.124.232.204:443",
]
PROXIES_TO_TEST = [p for p in PROXIES_TO_TEST if p]


async def test_proxy(proxy_url: str) -> bool:
    token = os.getenv("BOT_TOKEN", "")
    if not token:
        print("Укажите BOT_TOKEN в .env")
        return False

    test_url = f"https://api.telegram.org/bot{token}/getMe"
    print(f"Тестируем прокси: {proxy_url}")
    try:
        async with httpx.AsyncClient(proxy=proxy_url, timeout=15) as client:
            response = await client.get(test_url)
            response.raise_for_status()
            data = response.json()
            if data.get("ok"):
                print(f"OK: прокси работает — {proxy_url}")
                return True
            print(f"Странный ответ: {data}")
    except httpx.ProxyError:
        print(f"Прокси отклонил соединение: {proxy_url}")
    except httpx.ConnectError:
        print(f"Не удалось подключиться к прокси: {proxy_url}")
    except httpx.ReadTimeout:
        print(f"Таймаут: {proxy_url}")
    except httpx.HTTPStatusError as exc:
        print(f"HTTP {exc.response.status_code}: {proxy_url}")
    except Exception as exc:
        print(f"Ошибка {type(exc).__name__}: {proxy_url}")
    return False


async def main() -> None:
    working_proxy = None
    for proxy_url in PROXIES_TO_TEST:
        if await test_proxy(proxy_url):
            working_proxy = proxy_url
            break

    if working_proxy:
        print(f"\nРабочий прокси: {working_proxy}")
        print("Вставьте его в .env → PROXY_URL=...")
    else:
        print("\nНи один прокси не работает. Нужен другой SOCKS5 или VPN.")


if __name__ == "__main__":
    asyncio.run(main())
