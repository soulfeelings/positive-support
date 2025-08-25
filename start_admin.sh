#!/bin/bash

echo "🔧 Запуск админ-бота для разблокировки пользователей..."

# Проверяем наличие Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 не найден! Установите Python3 и попробуйте снова."
    exit 1
fi

# Проверяем наличие файла .env
if [ ! -f ".env" ]; then
    echo "❌ ОШИБКА: Файл .env не найден!"
    echo "Создайте файл .env на основе env.example"
    echo "И установите ADMIN_BOT_TOKEN и ADMIN_ID"
    exit 1
fi

# Загружаем переменные окружения
export $(grep -v '^#' .env | xargs)

# Проверяем обязательные переменные
if [ -z "$ADMIN_BOT_TOKEN" ]; then
    echo "❌ ОШИБКА: ADMIN_BOT_TOKEN не установлен в .env файле!"
    exit 1
fi

if [ -z "$ADMIN_ID" ]; then
    echo "❌ ОШИБКА: ADMIN_ID не установлен в .env файле!"
    exit 1
fi

echo "✅ Настройки:"
echo "   - Админ бот токен: ${ADMIN_BOT_TOKEN:0:10}..."
echo "   - Админ ID: $ADMIN_ID"
echo "   - База данных: ${DB_HOST:-localhost}:${DB_PORT:-5432}/${DB_NAME:-support_bot}"
echo ""

echo "🚀 Запуск админ-бота..."
python3 admin_bot.py

if [ $? -ne 0 ]; then
    echo ""
    echo "❌ ОШИБКА: Админ-бот завершился с ошибкой!"
    echo "Возможные причины:"
    echo "1. Неверный токен админ-бота"
    echo "2. Проблемы с подключением к базе данных"
    echo "3. Отсутствие интернет-соединения"
    echo "4. Не установлены зависимости (pip install -r requirements.txt)"
    exit 1
fi

echo "✅ Админ-бот завершен."
