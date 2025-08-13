import os
import asyncio
import logging
import aiohttp
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import KeyboardButton, ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

BOT_TOKEN = os.getenv("BOT_TOKEN", "8234250977:AAFSjY7Ci-xajOeB-JqRgWB2vTVtQaW9UCc")
# Public HTTPS URL to open inside Telegram WebApp (e.g. Cloudflare/Ngrok tunnel to http://localhost:8000)
BACKEND_PUBLIC_URL = os.getenv("BACKEND_PUBLIC_URL", "https://xh3l8y-78-36-243-206.ru.tuna.am")
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

class SendStates(StatesGroup):
    waiting_support = State()
    waiting_nickname = State()

main_kb = ReplyKeyboardMarkup(keyboard=[
    [KeyboardButton(text="💌 Отправить поддержку")],
    [KeyboardButton(text="📥 Получить поддержку")],
], resize_keyboard=True)

def webapp_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Открыть мини‑приложение", web_app=WebAppInfo(url=f"{BACKEND_PUBLIC_URL}/"))]])

async def make_request(endpoint: str, data: dict):
    async with aiohttp.ClientSession() as s:
        async with s.post(f"{BACKEND_URL}/{endpoint}", json=data) as r:
            return await r.json()

@dp.message(Command("start"))
async def start(message: types.Message, state: FSMContext):
    await message.answer(
        "👋 Привет! Это бот поддержки. Можешь пользоваться через мини‑приложение (кнопка ниже) или прямо в чате.\n\nСначала придумай себе уникальный никнейм.",
        reply_markup=webapp_kb()
    )
    await state.set_state(SendStates.waiting_nickname)

@dp.message(SendStates.waiting_nickname)
async def handle_nickname(message: types.Message, state: FSMContext):
    nickname = message.text.strip()

    if not nickname.isalnum():
        await message.answer("❌ Ник должен содержать только буквы и цифры. Попробуй снова.")
        return

    response = await make_request("set_nickname", {
        "user_id": message.from_user.id,
        "nickname": nickname
    })

    if response.get("status") == "success":
        await message.answer("✅ Ник установлен! Открой мини‑приложение по кнопке выше или выбери действие ниже:", reply_markup=main_kb)
        await state.clear()
    else:
        await message.answer("⚠️ Такой ник уже занят. Попробуй другой:")

@dp.message(F.text == "💌 Отправить поддержку")
async def send_support(message: types.Message, state: FSMContext):
    await message.answer("Отправь текст или голосовое сообщение:")
    await state.set_state(SendStates.waiting_support)

@dp.message(SendStates.waiting_support)
async def handle_support_message(message: types.Message, state: FSMContext):
    if message.voice:
        payload = {
            "user_id": message.from_user.id,
            "text": None,
            "file_id": message.voice.file_id,
            "type": "voice"
        }
    elif message.text:
        payload = {
            "user_id": message.from_user.id,
            "text": message.text,
            "file_id": None,
            "type": "text"
        }
    else:
        await message.answer("❌ Отправьте текст или голосовое сообщение.")
        return

    response = await make_request("send_support", payload)
    if response.get("status") == "success":
        await message.answer("✅ Поддержка отправлена!")
    else:
        await message.answer(f"⚠️ Ошибка: {response.get('message', 'Неизвестная ошибка')}")
    await state.clear()

@dp.message(F.text == "📥 Получить поддержку")
async def get_support(message: types.Message):
    response = await make_request("get_support", {"user_id": message.from_user.id})

    if response.get("status") == "text":
        await message.answer(f"💬 {response['message']}\n\n👤 От: {response['nickname']}")
    elif response.get("status") == "voice":
        await bot.send_voice(
            chat_id=message.chat.id,
            voice=response["file_id"],
            caption=f"🎧 Голосовое сообщение от: {response['nickname']}"
        )
    else:
        await message.answer("❌ Пока нет доступных сообщений.")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
