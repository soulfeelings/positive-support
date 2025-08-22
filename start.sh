#!/bin/bash

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 Запуск Positive Support Bot...${NC}"

# Функция для логирования
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR: $1${NC}"
}

warn() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING: $1${NC}"
}

# Проверка переменных окружения
check_env() {
    log "🔍 Проверка переменных окружения..."
    
    if [ -z "$BOT_TOKEN" ]; then
        error "BOT_TOKEN не установлен!"
        exit 1
    fi
    
    if [ -z "$DB_HOST" ]; then
        warn "DB_HOST не установлен, используется localhost"
        export DB_HOST="localhost"
    fi
    
    log "✅ Переменные окружения проверены"
}

# Ожидание доступности базы данных
wait_for_db() {
    log "🗄️ Ожидание подключения к базе данных..."
    
    while ! python -c "
import asyncio
import asyncpg
import sys
import os

async def check_db():
    try:
        conn = await asyncpg.connect(
            host=os.getenv('DB_HOST', 'localhost'),
            port=int(os.getenv('DB_PORT', '5432')),
            user=os.getenv('DB_USER', 'postgres'),
            password=os.getenv('DB_PASSWORD', '8998'),
            database=os.getenv('DB_NAME', 'support_bot')
        )
        await conn.close()
        return True
    except:
        return False

if not asyncio.run(check_db()):
    sys.exit(1)
" 2>/dev/null; do
        warn "База данных недоступна, ожидание..."
        sleep 5
    done
    
    log "✅ База данных доступна"
}

# Инициализация базы данных
init_db() {
    log "🗄️ Инициализация базы данных..."
    
    python setup_db_manual.py
    
    if [ $? -eq 0 ]; then
        log "✅ База данных инициализирована"
    else
        error "Ошибка инициализации базы данных"
        exit 1
    fi
}

# Определение режима запуска
if [ "$1" = "api" ]; then
    log "🌐 Запуск API сервера..."
    check_env
    wait_for_db
    init_db
    exec uvicorn main:app --host 0.0.0.0 --port 8000
elif [ "$1" = "bot" ]; then
    log "🤖 Запуск Telegram бота..."
    check_env
    wait_for_db
    exec python bot.py
else
    # По умолчанию запускаем API
    log "🌐 Запуск API сервера (по умолчанию)..."
    check_env
    wait_for_db
    init_db
    exec uvicorn main:app --host 0.0.0.0 --port 8000
fi
