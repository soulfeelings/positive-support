#!/bin/bash

# 🔧 Скрипт быстрой настройки админ-бота
echo "🔧 Настройка переменных окружения для админ-бота..."

# Проверяем существует ли .env файл
if [ ! -f ".env" ]; then
    echo "📋 Создаем новый .env файл..."
    cp env.admin.example .env
else
    echo "📝 Обновляем существующий .env файл..."
    
    # Добавляем admin bot переменные если их нет
    if ! grep -q "ADMIN_BOT_TOKEN" .env; then
        echo "" >> .env
        echo "# Telegram Admin Bot (для разблокировки пользователей)" >> .env
        echo "ADMIN_BOT_TOKEN=8233417802:AAGyzmvx1m7MdhGFN-Jk3tTjJ7Q_NgV16h8" >> .env
    else
        # Обновляем существующий токен
        sed -i 's/ADMIN_BOT_TOKEN=.*/ADMIN_BOT_TOKEN=8233417802:AAGyzmvx1m7MdhGFN-Jk3tTjJ7Q_NgV16h8/' .env
    fi
    
    if ! grep -q "ADMIN_ID" .env; then
        echo "ADMIN_ID=8166609254" >> .env
    else
        # Обновляем существующий ID
        sed -i 's/ADMIN_ID=.*/ADMIN_ID=8166609254/' .env
    fi
fi

echo "✅ Конфигурация завершена!"
echo ""
echo "🔍 Проверяем настройки..."
python3 check_admin_config.py

if [ $? -eq 0 ]; then
    echo ""
    echo "🚀 Перезапускаем службы..."
    ./deploy.sh restart
else
    echo ""
    echo "❌ Ошибка в конфигурации. Проверьте файл .env"
fi
