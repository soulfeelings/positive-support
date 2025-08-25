#!/bin/bash

# Скрипт для экстренной очистки всех процессов бота
# Использование: ./cleanup_processes.sh

echo "🔧 Экстренная очистка процессов positive-support..."

# Останавливаем systemd сервисы
echo "Останавливаем systemd сервисы..."
systemctl stop positive-support-api.service 2>/dev/null || true
systemctl stop positive-support-bot.service 2>/dev/null || true
systemctl stop positive-support-admin-bot.service 2>/dev/null || true

# Ждем немного
sleep 2

# Убиваем процессы по имени файла
echo "Убиваем процессы Python..."
pkill -f "main.py" 2>/dev/null || true
pkill -f "bot.py" 2>/dev/null || true  
pkill -f "admin_bot.py" 2>/dev/null || true

# Убиваем процессы на порту 8000
echo "Освобождаем порт 8000..."
lsof -ti:8000 | xargs -r kill -9 2>/dev/null || true

# Убиваем все Python процессы связанные с проектом
echo "Убиваем все процессы в директории проекта..."
PROJECT_DIR=$(pwd)
pgrep -f "$PROJECT_DIR" | xargs -r kill -9 2>/dev/null || true

# Ждем завершения
sleep 3

# Проверяем что все очищено
echo "Проверяем результаты..."

API_PROCESSES=$(pgrep -f "main.py" || true)
BOT_PROCESSES=$(pgrep -f "bot.py" || true)
ADMIN_PROCESSES=$(pgrep -f "admin_bot.py" || true)
PORT_PROCESSES=$(lsof -ti:8000 2>/dev/null || true)

if [ -z "$API_PROCESSES" ] && [ -z "$BOT_PROCESSES" ] && [ -z "$ADMIN_PROCESSES" ] && [ -z "$PORT_PROCESSES" ]; then
    echo "✅ Все процессы успешно очищены!"
    echo ""
    echo "Теперь можно безопасно запустить:"
    echo "  ./deploy.sh restart"
else
    echo "⚠️  Некоторые процессы остались:"
    [ -n "$API_PROCESSES" ] && echo "  API: $API_PROCESSES"
    [ -n "$BOT_PROCESSES" ] && echo "  Bot: $BOT_PROCESSES" 
    [ -n "$ADMIN_PROCESSES" ] && echo "  Admin: $ADMIN_PROCESSES"
    [ -n "$PORT_PROCESSES" ] && echo "  Port 8000: $PORT_PROCESSES"
    echo ""
    echo "Попробуйте запустить скрипт еще раз или перезагрузите сервер"
fi
