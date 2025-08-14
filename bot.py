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

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN", "8234250977:AAFSjY7Ci-xajOeB-JqRgWB2vTVtQaW9UCc")
# Public HTTPS URL to open inside Telegram WebApp (e.g. Cloudflare/Ngrok tunnel)
BACKEND_PUBLIC_URL = os.getenv("BACKEND_PUBLIC_URL", "https://your-domain.com")
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

if not BOT_TOKEN:
    logger.error("BOT_TOKEN environment variable is not set!")
    exit(1)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

class SendStates(StatesGroup):
    waiting_support = State()
    waiting_nickname = State()

# Клавиатуры
main_kb = ReplyKeyboardMarkup(keyboard=[
    [KeyboardButton(text="💌 Отправить поддержку")],
    [KeyboardButton(text="🔥 Получить поддержку")],
    [KeyboardButton(text="🌐 Открыть мини-приложение")]
], resize_keyboard=True)

def webapp_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(
            text="🚀 Открыть мини‑приложение", 
            web_app=WebAppInfo(url=f"{BACKEND_PUBLIC_URL}/")
        )
    ]])

async def make_request(endpoint: str, data: dict):
    """Выполняет HTTP запрос к бэкенду с обработкой ошибок"""
    try:
        timeout = aiohttp.ClientTimeout(total=10)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(f"{BACKEND_URL}/{endpoint}", json=data) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    logger.error(f"HTTP {response.status} error for {endpoint}: {await response.text()}")
                    return {"status": "error", "message": f"HTTP {response.status}"}
    except aiohttp.ClientError as e:
        logger.error(f"Network error for {endpoint}: {e}")
        return {"status": "error", "message": "Ошибка сети"}
    except Exception as e:
        logger.error(f"Unexpected error for {endpoint}: {e}")
        return {"status": "error", "message": "Неизвестная ошибка"}

@dp.message(Command("start"))
async def start(message: types.Message, state: FSMContext):
    """Команда /start - приветствие и начало работы"""
    user_id = message.from_user.id
    logger.info(f"User {user_id} started the bot")
    
    # Проверяем, есть ли пользователь в базе
    profile_response = await make_request("profile", {"user_id": user_id})
    
    if profile_response.get("status") == "ok":
        # Пользователь уже зарегистрирован
        await message.answer(
            f"👋 С возвращением, {profile_response.get('nickname', 'друг')}!\n\n"
            "🌟 Выбери, что хочешь сделать:",
            reply_markup=main_kb
        )
        await state.clear()
    else:
        # Новый пользователь
        await message.answer(
            "👋 Привет! Это бот поддержки.\n\n"
            "💝 Здесь можно:\n"
            "• Отправить поддержку тому, кто в ней нуждается\n"
            "• Получить тёплые слова, когда нужно\n\n"
            "🎯 Сначала придумай себе уникальный никнейм (только буквы и цифры):",
            reply_markup=webapp_kb()
        )
        await state.set_state(SendStates.waiting_nickname)

@dp.message(SendStates.waiting_nickname)
async def handle_nickname(message: types.Message, state: FSMContext):
    """Обработка установки никнейма"""
    nickname = message.text.strip()

    if not nickname or len(nickname) < 3:
        await message.answer("❌ Никнейм должен быть не короче 3 символов. Попробуй снова:")
        return

    if not nickname.replace('_', '').isalnum():
        await message.answer("❌ Ник должен содержать только буквы, цифры и подчеркивание. Попробуй снова:")
        return

    if len(nickname) > 20:
        await message.answer("❌ Никнейм слишком длинный (максимум 20 символов). Попробуй снова:")
        return

    user_data = {
        "user_id": message.from_user.id,
        "nickname": nickname
    }
    
    # Добавляем дополнительную информацию если доступна
    if message.from_user.first_name:
        user_data["photo_url"] = ""  # Можно добавить логику получения фото профиля
    
    response = await make_request("set_nickname", user_data)

    if response.get("status") == "success":
        await message.answer(
            f"✅ Отлично! Никнейм '{nickname}' установлен!\n\n"
            "🌟 Теперь можешь пользоваться ботом. Выбери действие:",
            reply_markup=main_kb
        )
        await state.clear()
        logger.info(f"Nickname '{nickname}' set for user {message.from_user.id}")
    else:
        error_msg = response.get("message", "неизвестная ошибка")
        if "already taken" in error_msg.lower():
            await message.answer("⚠️ Такой ник уже занят. Попробуй другой:")
        else:
            await message.answer(f"❌ Ошибка: {error_msg}\nПопробуй другой никнейм:")

@dp.message(F.text == "💌 Отправить поддержку")
async def send_support(message: types.Message, state: FSMContext):
    """Начало отправки сообщения поддержки"""
    await message.answer(
        "💝 Отправь текст или голосовое сообщение:\n\n"
        "💡 Совет: короткие тёплые слова часто помогают больше длинных речей"
    )
    await state.set_state(SendStates.waiting_support)

@dp.message(SendStates.waiting_support)
async def handle_support_message(message: types.Message, state: FSMContext):
    """Обработка сообщения поддержки"""
    if message.voice:
        payload = {
            "user_id": message.from_user.id,
            "text": None,
            "file_id": message.voice.file_id,
            "type": "voice"
        }
        content_type = "голосовое сообщение"
    elif message.text:
        if len(message.text.strip()) < 5:
            await message.answer("❌ Сообщение слишком короткое. Напиши что-то более содержательное:")
            return
        payload = {
            "user_id": message.from_user.id,
            "text": message.text.strip(),
            "file_id": None,
            "type": "text"
        }
        content_type = "текстовое сообщение"
    else:
        await message.answer("❌ Отправь текст или голосовое сообщение.")
        return

    response = await make_request("send_support", payload)
    
    if response.get("status") == "success":
        await message.answer(
            f"✅ {content_type.capitalize()} отправлено!\n\n"
            "🌟 Твоя поддержка поможет кому-то почувствовать себя лучше.\n"
            "💎 +1 очко к твоему рейтингу!",
            reply_markup=main_kb
        )
        logger.info(f"Support message sent by user {message.from_user.id}")
    else:
        error_msg = response.get('message', 'неизвестная ошибка')
        await message.answer(f"❌ Ошибка отправки: {error_msg}")
        logger.error(f"Failed to send support message: {error_msg}")
    
    await state.clear()

@dp.message(F.text == "🔥 Получить поддержку")
async def get_support(message: types.Message):
    """Получение сообщения поддержки"""
    user_id = message.from_user.id
    response = await make_request("get_support", {"user_id": user_id})

    if response.get("status") == "text":
        await message.answer(
            f"💬 {response['message']}\n\n"
            f"👤 От: {response['nickname']}\n\n"
            "❤️ Надеемся, это помогло!"
        )
        logger.info(f"Text support delivered to user {user_id}")
        
    elif response.get("status") == "voice":
        try:
            await bot.send_voice(
                chat_id=message.chat.id,
                voice=response["file_id"],
                caption=f"🎧 Голосовое сообщение от: {response['nickname']}\n\n❤️ Надеемся, это помогло!"
            )
            logger.info(f"Voice support delivered to user {user_id}")
        except Exception as e:
            logger.error(f"Failed to send voice message: {e}")
            await message.answer("❌ Не удалось воспроизвести голосовое сообщение")
            
    elif response.get("status") == "no_messages":
        await message.answer(
            "😔 Пока нет доступных сообщений поддержки.\n\n"
            "💡 Попробуй:\n"
            "• Проверить позже\n"
            "• Отправить свою поддержку — так в системе станет больше добрых слов!"
        )
    else:
        error_msg = response.get("message", "неизвестная ошибка")
        await message.answer(f"❌ Ошибка получения поддержки: {error_msg}")
        logger.error(f"Failed to get support: {error_msg}")

@dp.message(F.text == "🌐 Открыть мини-приложение")
async def open_webapp(message: types.Message):
    """Открытие веб-приложения"""
    await message.answer(
        "🚀 Нажми кнопку ниже, чтобы открыть мини-приложение с расширенным функционалом:",
        reply_markup=webapp_kb()
    )

@dp.message(Command("help"))
async def help_command(message: types.Message):
    """Справка по использованию бота"""
    help_text = """
🆘 **Справка по боту поддержки**

🔹 **💌 Отправить поддержку** - отправь текст или голосовое сообщение тому, кто нуждается в поддержке

🔹 **🔥 Получить поддержку** - получи тёплое сообщение от другого пользователя

🔹 **🌐 Мини-приложение** - полнофункциональный интерфейс с рейтингом, лигами и историей

**Как это работает?**
1️⃣ Ты отправляешь поддержку
2️⃣ Она попадает в общую очередь  
3️⃣ Другие пользователи получают твои слова
4️⃣ За каждое сообщение ты получаешь очки
5️⃣ Очки помогают подняться в лигах рейтинга

💡 **Совет**: короткие искренние слова часто помогают лучше длинных советов
    """
    
    await message.answer(help_text, parse_mode='Markdown')

@dp.message(Command("stats"))
async def stats_command(message: types.Message):
    """Показать статистику пользователя"""
    user_id = message.from_user.id
    response = await make_request("profile", {"user_id": user_id})
    
    if response.get("status") == "ok":
        score = response.get("score", 0)
        nickname = response.get("nickname", "Неизвестный")
        city = response.get("city", "не указан")
        
        # Определяем лигу
        leagues = [
            ("🥉 Бронзовая", 0, 49),
            ("🥈 Серебряная", 50, 199), 
            ("🥇 Золотая", 200, 499),
            ("💎 Платиновая", 500, 9999)
        ]
        
        current_league = "🥉 Бронзовая"
        for league_name, min_score, max_score in leagues:
            if min_score <= score <= max_score:
                current_league = league_name
                break
        
        stats_text = f"""
📊 **Твоя статистика**

👤 Никнейм: {nickname}
🏙️ Город: {city}
💎 Очки: {score}
🏆 Лига: {current_league}

💌 Отправлено сообщений поддержки: {score}
        """
        
        await message.answer(stats_text, parse_mode='Markdown')
    else:
        await message.answer("❌ Не удалось получить статистику. Возможно, ты не зарегистрирован.")

@dp.message(Command("profile"))
async def profile_command(message: types.Message):
    """Показать профиль пользователя и предложить его редактировать"""
    await message.answer(
        "👤 Для управления профилем используй мини-приложение - там есть полный функционал редактирования:",
        reply_markup=webapp_kb()
    )

# Обработчик неизвестных команд и сообщений
@dp.message()
async def unknown_message(message: types.Message):
    """Обработка неизвестных сообщений"""
    await message.answer(
        "🤔 Не понимаю эту команду.\n\n"
        "Используй кнопки меню или команды:\n"
        "• /help - справка\n"
        "• /stats - твоя статистика\n"
        "• /profile - управление профилем",
        reply_markup=main_kb
    )

async def on_startup():
    """Действия при запуске бота"""
    logger.info("Bot is starting...")
    
    # Проверяем подключение к бэкенду
    health_response = await make_request("health", {})
    if health_response.get("status") == "healthy":
        logger.info("Backend connection: OK")
    else:
        logger.warning(f"Backend connection issues: {health_response}")
    
    # Устанавливаем команды бота
    commands = [
        types.BotCommand(command="start", description="🚀 Начать работу"),
        types.BotCommand(command="help", description="🆘 Справка"),
        types.BotCommand(command="stats", description="📊 Моя статистика"),
        types.BotCommand(command="profile", description="👤 Мой профиль"),
    ]
    
    await bot.set_my_commands(commands)
    logger.info("Bot commands set successfully")

async def on_shutdown():
    """Действия при остановке бота"""
    logger.info("Bot is shutting down...")

async def main():
    """Главная функция запуска бота"""
    try:
        await on_startup()
        logger.info("Starting bot polling...")
        await dp.start_polling(bot, skip_updates=True)
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
    finally:
        await on_shutdown()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Program interrupted by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        exit(1)