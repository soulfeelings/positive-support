import os
import asyncio
import logging
import aiohttp
import random
from datetime import datetime, time
from aiogram import Bot
from aiogram.exceptions import TelegramForbiddenError, TelegramBadRequest
import asyncpg

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Конфигурация
BOT_TOKEN = os.getenv("BOT_TOKEN", "8234250977:AAFSjY7Ci-xajOeB-JqRgWB2vTVtQaW9UCc")
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

# Конфигурация БД
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", "5432"))
DB_USER = os.getenv("DB_USER", "bot_user")
DB_PASSWORD = os.getenv("DB_PASSWORD", "8998")
DB_NAME = os.getenv("DB_NAME", "support_bot")

# Время работы напоминаний (12:00 - 20:00)
REMINDER_START_HOUR = 12
REMINDER_END_HOUR = 20

bot = Bot(token=BOT_TOKEN)

async def get_connection():
    """Подключение к БД"""
    try:
        conn = await asyncpg.connect(
            host=DB_HOST, port=DB_PORT,
            user=DB_USER, password=DB_PASSWORD,
            database=DB_NAME
        )
        return conn
    except Exception as e:
        logger.error(f"❌ Database connection failed: {e}")
        raise

async def api_request(endpoint: str, data: dict):
    """HTTP запрос к API"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(f"{BACKEND_URL}/{endpoint}", json=data) as response:
                if response.status != 200:
                    logger.error(f"API returned status {response.status} for {endpoint}")
                    return {"status": "error", "message": f"HTTP {response.status}"}
                result = await response.json()
                return result
    except Exception as e:
        logger.error(f"API error for {endpoint}: {e}")
        return {"status": "error", "message": str(e)}

async def get_users_for_reminders():
    """Получение пользователей с включенными напоминаниями"""
    try:
        conn = await get_connection()
        users = await conn.fetch("""
            SELECT user_id, nickname, last_reminder_message_id 
            FROM users 
            WHERE reminders_enabled = TRUE AND is_blocked = FALSE
        """)
        await conn.close()
        return users
    except Exception as e:
        logger.error(f"Error getting users for reminders: {e}")
        return []

async def send_reminder_to_user(user_id: int, nickname: str):
    """Отправка напоминания конкретному пользователю"""
    try:
        # Получаем сообщение для напоминания через API
        result = await api_request("get_reminder_message", {"user_id": user_id})
        
        if result.get("status") == "ok":
            message_text = result.get("message")
            author_nickname = result.get("nickname")
            message_id = result.get("message_id")
            
            # Формируем текст напоминания
            reminder_text = f"""💝 **Ежедневная поддержка для тебя!**

💬 _{message_text}_

👤 От: **{author_nickname}**

🌟 _Пусть этот день будет прекрасным!_"""

            # Отправляем сообщение
            await bot.send_message(
                chat_id=user_id,
                text=reminder_text,
                parse_mode='Markdown'
            )
            
            logger.info(f"✅ Reminder sent to user {user_id} ({nickname}), message_id: {message_id}")
            return True
            
        elif result.get("status") == "no_messages":
            # Если нет сообщений поддержки, отправляем мотивационное сообщение
            motivational_messages = [
                "💝 **Твой ежедневный заряд позитива!**\n\n🌟 _Помни: каждый день - это новая возможность сделать что-то хорошее!_",
                "💝 **Время для позитива!**\n\n✨ _Ты можешь изменить чей-то день к лучшему простым добрым словом!_",
                "💝 **Ежедневная поддержка!**\n\n🤗 _Сегодня отличный день, чтобы поделиться добротой с миром!_",
                "💝 **Заряд хорошего настроения!**\n\n💫 _Твоя улыбка может стать лучшей частью дня для кого-то!_"
            ]
            
            motivational_text = random.choice(motivational_messages)
            
            await bot.send_message(
                chat_id=user_id,
                text=motivational_text,
                parse_mode='Markdown'
            )
            
            logger.info(f"✅ Motivational reminder sent to user {user_id} ({nickname})")
            return True
            
        else:
            logger.warning(f"Failed to get reminder message for user {user_id}")
            return False
            
    except TelegramForbiddenError:
        logger.warning(f"User {user_id} ({nickname}) blocked the bot")
        return False
    except TelegramBadRequest as e:
        logger.warning(f"Bad request sending to user {user_id} ({nickname}): {e}")
        return False
    except Exception as e:
        logger.error(f"Error sending reminder to user {user_id} ({nickname}): {e}")
        return False

async def send_daily_reminders():
    """Отправка ежедневных напоминаний всем пользователям"""
    current_time = datetime.now().time()
    current_hour = current_time.hour
    
    # Проверяем, что мы в рабочем времени напоминаний
    if not (REMINDER_START_HOUR <= current_hour < REMINDER_END_HOUR):
        logger.info(f"Outside reminder hours ({current_hour}:00), skipping reminders")
        return
    
    logger.info(f"🔔 Starting daily reminder broadcast at {current_time}")
    
    # Получаем пользователей для напоминаний
    users = await get_users_for_reminders()
    
    if not users:
        logger.info("No users found for reminders")
        return
    
    logger.info(f"Found {len(users)} users for reminders")
    
    success_count = 0
    failure_count = 0
    
    # Отправляем напоминания с задержкой чтобы не нагружать API
    for user in users:
        user_id = user['user_id']
        nickname = user['nickname']
        
        try:
            success = await send_reminder_to_user(user_id, nickname)
            if success:
                success_count += 1
            else:
                failure_count += 1
                
            # Небольшая задержка между отправками
            await asyncio.sleep(0.5)
            
        except Exception as e:
            logger.error(f"Error processing user {user_id}: {e}")
            failure_count += 1
    
    logger.info(f"📊 Reminder broadcast completed: {success_count} success, {failure_count} failures")

async def schedule_reminders():
    """Планировщик напоминаний"""
    logger.info("🔔 Reminder scheduler started")
    
    # Отправляем напоминания каждый час в рабочее время
    while True:
        try:
            current_time = datetime.now()
            current_hour = current_time.hour
            
            # Проверяем рабочее время
            if REMINDER_START_HOUR <= current_hour < REMINDER_END_HOUR:
                # Проверяем, не отправляли ли мы уже в этом часу
                # Отправляем только в начале каждого часа (первые 5 минут)
                if current_time.minute < 5:
                    await send_daily_reminders()
                    # Ждем до следующего часа чтобы не отправлять дублирующие сообщения
                    next_hour = current_time.replace(minute=0, second=0, microsecond=0)
                    next_hour = next_hour.replace(hour=current_hour + 1)
                    wait_seconds = (next_hour - current_time).total_seconds()
                    logger.info(f"Waiting {wait_seconds} seconds until next reminder check")
                    await asyncio.sleep(wait_seconds)
                else:
                    # Ждем до следующего часа
                    next_hour = current_time.replace(minute=0, second=0, microsecond=0)
                    next_hour = next_hour.replace(hour=current_hour + 1)
                    wait_seconds = (next_hour - current_time).total_seconds()
                    await asyncio.sleep(wait_seconds)
            else:
                # Вне рабочего времени - ждем до начала следующего рабочего дня
                if current_hour >= REMINDER_END_HOUR:
                    # После 20:00 - ждем до 12:00 следующего дня
                    next_start = current_time.replace(hour=REMINDER_START_HOUR, minute=0, second=0, microsecond=0)
                    next_start = next_start.replace(day=current_time.day + 1)
                else:
                    # До 12:00 - ждем до 12:00 сегодня
                    next_start = current_time.replace(hour=REMINDER_START_HOUR, minute=0, second=0, microsecond=0)
                
                wait_seconds = (next_start - current_time).total_seconds()
                logger.info(f"Outside working hours, waiting {wait_seconds} seconds until {next_start}")
                await asyncio.sleep(wait_seconds)
                
        except Exception as e:
            logger.error(f"Error in reminder scheduler: {e}")
            # В случае ошибки ждем 5 минут и пробуем снова
            await asyncio.sleep(300)

async def test_reminders():
    """Тестовая функция для проверки напоминаний"""
    logger.info("🧪 Testing reminder system...")
    await send_daily_reminders()

async def main():
    """Главная функция"""
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        await test_reminders()
    else:
        await schedule_reminders()

if __name__ == "__main__":
    asyncio.run(main())
