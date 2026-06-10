import httpx
from aiogram import types, Dispatcher, Bot
from aiogram.filters import Command
import os
import asyncio
from urllib.parse import urlparse
from dotenv import load_dotenv
load_dotenv()
from aiogram import Bot, Dispatcher
from aiogram.client.session.aiohttp import AiohttpSession 
session = AiohttpSession(proxy="socks5://162.240.96.211:1080") 

TOKEN = os.getenv("BOT_TOKEN")
TABLE_URL = "https://script.google.com/macros/s/AKfycbyI_sRk_J9i98e2ggCEDY7OMOc_IAiNqAFZ8wyAznhCXQHvl3a-xDwRbfhL1z4IniHN/exec"

bot = Bot(token=TOKEN, session=session)
dp = Dispatcher()

@dp.message(Command("save"))
async def save_to_table(message: types.Message):
    text_to_save = message.text.replace("/save ", "")
    payload = {
        "name": message.from_user.full_name,
        "text": text_to_save
    }
    await message.answer("Связываюсь с таблицей... 🐾")
    async with httpx.AsyncClient() as client:
        response = await client.post(TABLE_URL, json=payload, follow_redirects=True)
        if response.status_code == 200:
            await message.answer("Готово! Я всё записал в Google Таблицу. ✨")
        else:
            await message.answer("Ой, что-то пошло не так при записи.")

@dp.message(Command("read"))
async def read_from_table(message: types.Message):
    async with httpx.AsyncClient() as client:
        response = await client.get(TABLE_URL, follow_redirects=True)
        print("Реальный ответ от Google:", response.text)  
        data = response.json()
        last_rows = data[-3:]
        text = "Последние записи из таблицы:\n"
        for row in last_rows:
            text += f"📅 {row[0][:10]} | 👤 {row[1]}: {row[2]}\n"
        await message.answer(text)


async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
