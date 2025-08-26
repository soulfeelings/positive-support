#!/bin/bash

# Скрипт для запуска системы напоминаний

echo "🔔 Запуск системы ежедневных напоминаний..."

# Проверяем наличие Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 не найден. Установите Python3 для продолжения."
    exit 1
fi

# Проверяем наличие файла напоминаний
if [ ! -f "reminder_scheduler.py" ]; then
    echo "❌ Файл reminder_scheduler.py не найден"
    exit 1
fi

# Запускаем планировщик напоминаний
echo "🚀 Запуск планировщика напоминаний..."
python3 start_reminders.py

echo "📴 Система напоминаний остановлена"
