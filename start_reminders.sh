#!/bin/bash

# Скрипт для запуска системы напоминаний

# Загружаем переменные окружения
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

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
python3 reminder_scheduler.py

echo "📴 Система напоминаний остановлена"
