"""
Планировщик напоминаний для бота поддержки.
Отправляет случайные сообщения поддержки пользователям в случайное время с 12:00 до 20:00.
"""

import asyncio
import os
import random
import requests
import logging
from datetime import datetime, timedelta
from typing import Dict, List
import pytz

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Конфигурация
BOT_TOKEN = os.getenv("BOT_TOKEN")
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
TIMEZONE = pytz.timezone('Europe/Moscow')  # Можно настроить под нужную временную зону

class ReminderScheduler:
    def __init__(self):
        self.user_last_seen_ids: Dict[int, int] = {}
        self.sent_today: set = set()
        self.last_reset_date = datetime.now(TIMEZONE).date()
        
    def reset_daily_tracking(self):
        """Сброс ежедневного отслеживания в полночь"""
        current_date = datetime.now(TIMEZONE).date()
        if current_date != self.last_reset_date:
            self.sent_today.clear()
            self.last_reset_date = current_date
            logger.info("🔄 Daily reminder tracking reset")
    
    def is_sending_time(self) -> bool:
        """Проверка, что текущее время в диапазоне 12:00-20:00"""
        now = datetime.now(TIMEZONE)
        return 12 <= now.hour < 20
    
    def get_random_delay_until_next_check(self) -> int:
        """Получить случайную задержку до следующей проверки (в секундах)"""
        # Проверяем каждые 30-90 минут в рабочее время
        if self.is_sending_time():
            return random.randint(30 * 60, 90 * 60)  # 30-90 минут
        else:
            # Вне рабочего времени проверяем реже - каждые 2-4 часа
            return random.randint(2 * 60 * 60, 4 * 60 * 60)  # 2-4 часа
    
    async def get_users_with_reminders(self) -> List[int]:
        """Получить список пользователей с включенными напоминаниями"""
        try:
            response = requests.get(f"{API_BASE_URL}/get_users_with_reminders", timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "ok":
                    return data.get("user_ids", [])
            return []
        except Exception as e:
            logger.error(f"Error getting users with reminders: {e}")
            return []
    
    async def get_reminder_message(self, user_id: int) -> dict:
        """Получить сообщение для напоминания пользователю"""
        try:
            last_seen_id = self.user_last_seen_ids.get(user_id, 0)
            
            response = requests.post(
                f"{API_BASE_URL}/get_reminder_message",
                json={"user_id": user_id, "last_seen_id": last_seen_id},
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "ok":
                    message_data = data.get("message", {})
                    # Обновляем last_seen_id для этого пользователя
                    self.user_last_seen_ids[user_id] = message_data.get("id", last_seen_id)
                    return message_data
            return {}
        except Exception as e:
            logger.error(f"Error getting reminder message for user {user_id}: {e}")
            return {}
    
    def format_message_text(self, message_data: dict) -> str:
        """Форматирование текста напоминания"""
        nickname = message_data.get("nickname", "Аноним")
        text = message_data.get("text", "")
        
        return f"💝 **Напоминание о поддержке**\n\n{text}\n\n_— {nickname}_\n\n💭 Помни: ты не один, и всё наладится! 🌟"
    
    async def send_telegram_message(self, user_id: int, text: str, file_id: str = None, message_type: str = "text"):
        """Отправка сообщения через Telegram Bot API"""
        try:
            if message_type == "voice" and file_id:
                # Отправляем голосовое сообщение с подписью
                url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendVoice"
                data = {
                    "chat_id": user_id,
                    "voice": file_id,
                    "caption": text,
                    "parse_mode": "Markdown"
                }
            elif message_type == "video_note" and file_id:
                # Отправляем видеосообщение с текстом отдельно
                # Сначала отправляем видео
                url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendVideoNote"
                data = {
                    "chat_id": user_id,
                    "video_note": file_id
                }
                response = requests.post(url, json=data, timeout=10)
                
                # Затем отправляем текст
                url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
                data = {
                    "chat_id": user_id,
                    "text": text,
                    "parse_mode": "Markdown"
                }
            else:
                # Обычное текстовое сообщение
                url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
                data = {
                    "chat_id": user_id,
                    "text": text,
                    "parse_mode": "Markdown"
                }
            
            response = requests.post(url, json=data, timeout=10)
            
            if response.status_code == 200:
                logger.info(f"✅ Reminder sent to user {user_id}")
                return True
            else:
                logger.error(f"❌ Failed to send reminder to user {user_id}: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending reminder to user {user_id}: {e}")
            return False
    
    async def send_reminder_to_user(self, user_id: int):
        """Отправить напоминание конкретному пользователю"""
        try:
            # Получаем сообщение для напоминания
            message_data = await self.get_reminder_message(user_id)
            
            if not message_data:
                logger.info(f"No reminder message available for user {user_id}")
                return False
            
            # Форматируем текст
            text = self.format_message_text(message_data)
            file_id = message_data.get("file_id")
            message_type = message_data.get("message_type", "text")
            
            # Отправляем напоминание
            success = await self.send_telegram_message(user_id, text, file_id, message_type)
            
            if success:
                self.sent_today.add(user_id)
                logger.info(f"📬 Reminder sent to user {user_id} (message_id: {message_data.get('id')})")
            
            return success
            
        except Exception as e:
            logger.error(f"Error sending reminder to user {user_id}: {e}")
            return False
    
    async def process_reminders(self):
        """Основной процесс отправки напоминаний"""
        self.reset_daily_tracking()
        
        if not self.is_sending_time():
            logger.info("⏰ Not in sending time window (12:00-20:00)")
            return
        
        # Получаем пользователей с включенными напоминаниями
        users = await self.get_users_with_reminders()
        
        if not users:
            logger.info("📭 No users with enabled reminders found")
            return
        
        # Фильтруем пользователей, которым сегодня еще не отправляли
        eligible_users = [user_id for user_id in users if user_id not in self.sent_today]
        
        if not eligible_users:
            logger.info("📫 All eligible users already received reminders today")
            return
        
        # Выбираем случайное количество пользователей (10-30% от доступных)
        max_users = max(1, len(eligible_users) // 3)  # Максимум треть пользователей
        num_users_to_send = random.randint(1, max_users)
        
        selected_users = random.sample(eligible_users, min(num_users_to_send, len(eligible_users)))
        
        logger.info(f"📤 Sending reminders to {len(selected_users)} users out of {len(eligible_users)} eligible")
        
        # Отправляем напоминания
        successful_sends = 0
        for user_id in selected_users:
            success = await self.send_reminder_to_user(user_id)
            if success:
                successful_sends += 1
            
            # Небольшая задержка между отправками
            await asyncio.sleep(random.uniform(1, 3))
        
        logger.info(f"✅ Successfully sent {successful_sends}/{len(selected_users)} reminders")
    
    async def run_scheduler(self):
        """Запуск планировщика"""
        logger.info("🚀 Reminder scheduler started")
        
        while True:
            try:
                await self.process_reminders()
                
                # Случайная задержка до следующей проверки
                delay = self.get_random_delay_until_next_check()
                next_check = datetime.now(TIMEZONE) + timedelta(seconds=delay)
                
                logger.info(f"⏳ Next reminder check at: {next_check.strftime('%H:%M:%S')} (in {delay//60} minutes)")
                
                await asyncio.sleep(delay)
                
            except Exception as e:
                logger.error(f"Error in reminder scheduler: {e}")
                # В случае ошибки ждем 10 минут и пытаемся снова
                await asyncio.sleep(600)

async def main():
    """Главная функция"""
    if not BOT_TOKEN:
        logger.error("❌ BOT_TOKEN environment variable is required")
        return
    
    scheduler = ReminderScheduler()
    await scheduler.run_scheduler()

if __name__ == "__main__":
    asyncio.run(main())
