#!/bin/bash

# Запуск планировщика напоминаний

# Загружаем переменные окружения
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

echo "🚀 Starting reminder scheduler..."

# Запускаем планировщик
python3 reminder_scheduler.py
