#!/usr/bin/env python3
"""
Скрипт для запуска системы ежедневных напоминаний
"""

import asyncio
import logging
import signal
import sys
from reminder_scheduler import schedule_reminders

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('reminders.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

# Глобальная переменная для graceful shutdown
running = True

def signal_handler(signum, frame):
    """Обработчик сигналов для graceful shutdown"""
    global running
    logger.info(f"Received signal {signum}, shutting down...")
    running = False

async def main():
    """Главная функция"""
    # Регистрируем обработчики сигналов
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    logger.info("🔔 Starting reminder system...")
    
    try:
        # Запускаем планировщик напоминаний
        await schedule_reminders()
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
    except Exception as e:
        logger.error(f"Error in reminder system: {e}")
        raise
    finally:
        logger.info("📴 Reminder system stopped")

if __name__ == "__main__":
    asyncio.run(main())
