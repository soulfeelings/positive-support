#!/bin/bash

# Скрипт для деплоя приложения positive-support-test
# Использование: ./deploy.sh [environment]

set -e

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Конфигурация
ENVIRONMENT=${1:-dev}
PROJECT_DIR=$(pwd)
LOG_DIR="${PROJECT_DIR}/logs"
BACKUP_DIR="${PROJECT_DIR}/backups"
API_PORT=8000
API_HEALTH_URL="http://localhost:${API_PORT}/health"

echo -e "${BLUE}🚀 Deploying positive-support-test to ${ENVIRONMENT}${NC}"
echo "================================================================"

# Создаем необходимые директории
mkdir -p "${LOG_DIR}" "${BACKUP_DIR}"

# Функция для логирования
log() {
    echo -e "${BLUE}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1"
}

# Функция для проверки состояния процесса
check_process() {
    local process_name="$1"
    local process_file="$2"
    
    # Проверяем, есть ли systemd сервис
    local service_name=""
    if [[ "$process_name" == "API" ]]; then
        service_name="positive-support-api.service"
    elif [[ "$process_name" == "Bot" ]]; then
        service_name="positive-support-bot.service"
    elif [[ "$process_name" == "Admin Bot" ]]; then
        service_name="positive-support-admin-bot.service"
    fi
    
    if [ -n "$service_name" ] && systemctl list-unit-files | grep -q "$service_name"; then
        # Проверяем systemd сервис
        if systemctl is-active --quiet "$service_name"; then
            echo -e "${GREEN}✅ $process_name is running (systemd)${NC}"
            return 0
        else
            echo -e "${RED}❌ $process_name is not running (systemd)${NC}"
            return 1
        fi
    fi
    
    # Fallback: проверка прямых процессов
    if pgrep -f "$process_file" > /dev/null; then
        echo -e "${GREEN}✅ $process_name is running (direct)${NC}"
        return 0
    else
        echo -e "${RED}❌ $process_name is not running${NC}"
        return 1
    fi
}

# Функция для остановки процесса
stop_process() {
    local process_name="$1"
    local process_file="$2"
    
    log "Stopping $process_name..."
    
    # Проверяем, есть ли systemd сервис
    local service_name=""
    if [[ "$process_name" == "API" ]]; then
        service_name="positive-support-api.service"
    elif [[ "$process_name" == "Bot" ]]; then
        service_name="positive-support-bot.service"
    elif [[ "$process_name" == "Admin Bot" ]]; then
        service_name="positive-support-admin-bot.service"
    fi
    
    if [ -n "$service_name" ] && systemctl list-unit-files | grep -q "$service_name"; then
        # Останавливаем systemd сервис
        log "Stopping systemd service: $service_name"
        systemctl stop "$service_name" 2>/dev/null || true
        systemctl disable "$service_name" 2>/dev/null || true
        log "✅ $process_name stopped via systemd"
        return 0
    fi
    
    # Fallback: прямая остановка процесса
    local pids=$(pgrep -f "$process_file" || true)
    
    if [ -n "$pids" ]; then
        for pid in $pids; do
            log "Terminating process $pid ($process_name)"
            kill -TERM "$pid" 2>/dev/null || true
        done
        
        # Ждем завершения процессов
        sleep 5
        
        # Проверяем что процессы действительно завершились
        local remaining_pids=$(pgrep -f "$process_file" || true)
        if [ -n "$remaining_pids" ]; then
            log "Force killing remaining processes..."
            for pid in $remaining_pids; do
                kill -9 "$pid" 2>/dev/null || true
            done
            sleep 2
        fi
        
        echo -e "${GREEN}✅ $process_name stopped${NC}"
    else
        echo -e "${YELLOW}⚠️  $process_name was not running${NC}"
    fi
}

# Функция для запуска процесса в фоне
start_process() {
    local process_name="$1"
    local process_file="$2"
    local log_file="$3"
    
    log "Starting $process_name..."
    
    # Проверяем, есть ли systemd сервис
    local service_name=""
    if [[ "$process_name" == "API" ]]; then
        service_name="positive-support-api.service"
    elif [[ "$process_name" == "Bot" ]]; then
        service_name="positive-support-bot.service"
    elif [[ "$process_name" == "Admin Bot" ]]; then
        service_name="positive-support-admin-bot.service"
    fi
    
    if [ -n "$service_name" ] && systemctl list-unit-files | grep -q "$service_name"; then
        # Используем systemd сервис
        log "Using systemd service: $service_name"
        systemctl start "$service_name"
        systemctl enable "$service_name"
        
        # Ждем запуска сервиса
        sleep 3
        
        # Проверяем статус
        if systemctl is-active --quiet "$service_name"; then
            log "$process_name started via systemd service"
            return 0
        else
            log "Failed to start $service_name, falling back to direct process"
        fi
    fi
    
    # Fallback: прямой запуск процесса (для случаев когда systemd недоступен)
    log "Starting $process_name directly..."
    if [ -f ".env" ]; then
        export $(grep -v '^#' .env | xargs)
    fi
    nohup env $(grep -v '^#' .env | xargs) python3 "$process_file" > "$log_file" 2>&1 &
    local pid=$!
    
    echo "$pid" > "${process_file}.pid"
    log "$process_name started with PID $pid"
    
    # Даем время на запуск
    sleep 3
    
    # Проверяем что процесс все еще работает
    if kill -0 "$pid" 2>/dev/null; then
        echo -e "${GREEN}✅ $process_name started successfully${NC}"
        return 0
    else
        echo -e "${RED}❌ $process_name failed to start${NC}"
        cat "$log_file" | tail -10
        return 1
    fi
}

# Функция для проверки здоровья API
check_api_health() {
    log "Checking API health..."
    
    for i in {1..30}; do
        if curl -f -s "$API_HEALTH_URL" > /dev/null 2>&1; then
            echo -e "${GREEN}✅ API is healthy${NC}"
            return 0
        fi
        
        if [ $((i % 5)) -eq 0 ]; then
            log "Waiting for API to become ready... ($i/30)"
        fi
        sleep 2
    done
    
    echo -e "${RED}❌ API health check failed${NC}"
    return 1
}

# Функция для создания systemd сервисов
setup_systemd_services() {
    log "Setting up systemd services..."
    
    # Проверяем права root
    if [ "$EUID" -ne 0 ]; then
        echo -e "${RED}❌ This command requires root privileges (sudo)${NC}"
        exit 1
    fi
    
    # Создаем сервис для API
    cat > /etc/systemd/system/positive-support-api.service << EOF
[Unit]
Description=Positive Support API
After=network.target postgresql.service
Wants=postgresql.service

[Service]
Type=simple
User=root
WorkingDirectory=$PROJECT_DIR
Environment=PATH=/usr/local/bin:/usr/bin:/bin
ExecStart=/usr/bin/python3 main.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

    # Создаем сервис для Bot
    cat > /etc/systemd/system/positive-support-bot.service << EOF
[Unit]
Description=Positive Support Bot
After=network.target positive-support-api.service
Wants=positive-support-api.service

[Service]
Type=simple
User=root
WorkingDirectory=$PROJECT_DIR
Environment=PATH=/usr/local/bin:/usr/bin:/bin
ExecStart=/usr/bin/python3 bot.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

    # Создаем сервис для админ-бота (если файл существует)
    if [ -f "$PROJECT_DIR/admin_bot.py" ]; then
        cat > /etc/systemd/system/positive-support-admin-bot.service << EOF
[Unit]
Description=Positive Support Admin Bot
After=network.target positive-support-api.service
Wants=positive-support-api.service

[Service]
Type=simple
User=root
WorkingDirectory=$PROJECT_DIR
Environment=PATH=/usr/local/bin:/usr/bin:/bin
EnvironmentFile=-$PROJECT_DIR/.env
ExecStart=/usr/bin/python3 admin_bot.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF
        log "Admin bot service created"
    fi

    # Перезагружаем systemd и включаем сервисы
    systemctl daemon-reload
    systemctl enable positive-support-api.service
    systemctl enable positive-support-bot.service
    
    # Включаем админ-бот если он существует
    if [ -f "$PROJECT_DIR/admin_bot.py" ]; then
        systemctl enable positive-support-admin-bot.service
        log "Admin bot service enabled"
    fi
    
    log "✅ Systemd services created and enabled"
    log "Use 'systemctl start positive-support-api' and 'systemctl start positive-support-bot' to start services"
}

# Функция для создания бэкапа
create_backup() {
    if [ -f "main.py" ] && [ -f "bot.py" ]; then
        local backup_name="backup_$(date +%Y%m%d_%H%M%S)"
        local backup_path="${BACKUP_DIR}/${backup_name}"
        
        log "Creating backup: $backup_name"
        
        mkdir -p "$backup_path"
        cp -r *.py requirements.txt *.md "$backup_path/" 2>/dev/null || true
        
        echo -e "${GREEN}✅ Backup created: $backup_path${NC}"
        
        # Удаляем старые бэкапы (оставляем только последние 5)
        cd "$BACKUP_DIR"
        ls -t | tail -n +6 | xargs -r rm -rf
        cd "$PROJECT_DIR"
    fi
}

# Функция для проверки зависимостей
check_dependencies() {
    log "Checking dependencies..."
    
    # Проверяем Python
    if ! command -v python3 &> /dev/null; then
        echo -e "${RED}❌ Python 3 is not installed${NC}"
        exit 1
    fi
    
    # Проверяем pip
    if ! command -v pip3 &> /dev/null; then
        echo -e "${RED}❌ pip3 is not installed${NC}"
        exit 1
    fi
    
    # Проверяем requirements.txt
    if [ ! -f "requirements.txt" ]; then
        echo -e "${RED}❌ requirements.txt not found${NC}"
        exit 1
    fi
    
    echo -e "${GREEN}✅ Dependencies check passed${NC}"
}

# Функция для установки зависимостей
install_dependencies() {
    log "Installing/updating dependencies..."
    
    # Обновляем pip
    python3 -m pip install --upgrade pip
    
    # Устанавливаем зависимости
    pip3 install -r requirements.txt
    
    echo -e "${GREEN}✅ Dependencies installed${NC}"
}

# Функция для проверки базы данных
check_database() {
    log "Checking database..."
    
    if [ -f "check_db.py" ]; then
        python3 check_db.py || {
            echo -e "${YELLOW}⚠️  Database check returned non-zero exit code${NC}"
        }
    else
        echo -e "${YELLOW}⚠️  check_db.py not found, skipping database check${NC}"
    fi
}

# Функция для очистки логов
cleanup_logs() {
    log "Cleaning up old logs..."
    
    # Удаляем логи старше 7 дней
    find "$LOG_DIR" -name "*.log" -type f -mtime +7 -delete 2>/dev/null || true
    find . -name "*.log" -type f -mtime +7 -delete 2>/dev/null || true
    
    echo -e "${GREEN}✅ Log cleanup completed${NC}"
}

# Основная функция деплоя
main() {
    log "Starting deployment process..."
    
    # Проверяем зависимости
    check_dependencies
    
    # Создаем бэкап
    create_backup
    
    # Останавливаем сервисы
    stop_process "Bot" "bot.py"
    if [ -f "$PROJECT_DIR/admin_bot.py" ]; then
        stop_process "Admin Bot" "admin_bot.py"
    fi
    stop_process "API" "main.py"
    
    # Устанавливаем зависимости
    install_dependencies
    
    # Проверяем базу данных
    check_database
    
    # Запускаем API
    if start_process "API" "main.py" "${LOG_DIR}/api.log"; then
        # Проверяем здоровье API
        if check_api_health; then
            # Запускаем бота
            if start_process "Bot" "bot.py" "${LOG_DIR}/bot.log"; then
                # Запускаем админ-бота (если файл существует)
                if [ -f "$PROJECT_DIR/admin_bot.py" ]; then
                    log "Starting Admin Bot..."
                    
                    # Проверяем конфигурацию админ-бота
                    if python3 check_admin_config.py > /dev/null 2>&1; then
                        start_process "Admin Bot" "admin_bot.py" "${LOG_DIR}/admin_bot.log"
                    else
                        echo -e "${YELLOW}⚠️  Admin Bot configuration incomplete${NC}"
                        echo -e "${YELLOW}   Run: python3 check_admin_config.py${NC}"
                        echo -e "${YELLOW}   Or see: ADMIN_BOT_SETUP.md${NC}"
                    fi
                fi
                
                log "Waiting for services to stabilize..."
                sleep 10
                
                # Финальная проверка
                local all_services_ok=true
                if ! check_process "API" "main.py"; then
                    all_services_ok=false
                fi
                if ! check_process "Bot" "bot.py"; then
                    all_services_ok=false
                fi
                
                if [ "$all_services_ok" = true ]; then
                    echo ""
                    echo -e "${GREEN}🎉 Deployment completed successfully!${NC}"
                    echo ""
                    echo -e "${YELLOW}📋 Service status:${NC}"
                    check_process "API" "main.py"
                    check_process "Bot" "bot.py"
                    if [ -f "$PROJECT_DIR/admin_bot.py" ]; then
                        check_process "Admin Bot" "admin_bot.py"
                    fi
                    echo ""
                    echo -e "${BLUE}📊 Useful commands:${NC}"
                    echo "  Check API logs:    tail -f ${LOG_DIR}/api.log"
                    echo "  Check Bot logs:    tail -f ${LOG_DIR}/bot.log"
                    if [ -f "$PROJECT_DIR/admin_bot.py" ]; then
                        echo "  Check Admin logs:  tail -f ${LOG_DIR}/admin_bot.log"
                    fi
                    echo "  API health:        curl ${API_HEALTH_URL}"
                    echo "  Stop services:     ./deploy.sh stop"
                    echo ""
                else
                    echo -e "${RED}❌ Some services failed final check${NC}"
                    exit 1
                fi
            else
                echo -e "${RED}❌ Failed to start Bot${NC}"
                exit 1
            fi
        else
            echo -e "${RED}❌ API health check failed${NC}"
            exit 1
        fi
    else
        echo -e "${RED}❌ Failed to start API${NC}"
        exit 1
    fi
    
    # Очистка логов
    cleanup_logs
}

# Функция для остановки всех сервисов
stop_all() {
    log "Stopping all services..."
    stop_process "Bot" "bot.py"
    if [ -f "$PROJECT_DIR/admin_bot.py" ]; then
        stop_process "Admin Bot" "admin_bot.py"
    fi
    stop_process "API" "main.py"
    echo -e "${GREEN}✅ All services stopped${NC}"
}

# Функция для показа статуса
show_status() {
    echo -e "${BLUE}📊 Service Status${NC}"
    echo "=================="
    check_process "API" "main.py"
    check_process "Bot" "bot.py"
    if [ -f "$PROJECT_DIR/admin_bot.py" ]; then
        check_process "Admin Bot" "admin_bot.py"
    fi
    
    # Показываем статус systemd сервисов если они есть
    if systemctl list-unit-files | grep -q "positive-support-api.service"; then
        echo ""
        echo -e "${YELLOW}🔧 Systemd Services Status:${NC}"
        systemctl status positive-support-api.service --no-pager -l | head -10
        echo ""
        systemctl status positive-support-bot.service --no-pager -l | head -10
        
        if systemctl list-unit-files | grep -q "positive-support-admin-bot.service"; then
            echo ""
            systemctl status positive-support-admin-bot.service --no-pager -l | head -10
        fi
    fi
    
    if [ -f "${LOG_DIR}/api.log" ]; then
        echo ""
        echo -e "${YELLOW}📄 Recent API logs:${NC}"
        tail -5 "${LOG_DIR}/api.log"
    fi
    
    if [ -f "${LOG_DIR}/bot.log" ]; then
        echo ""
        echo -e "${YELLOW}📄 Recent Bot logs:${NC}"
        tail -5 "${LOG_DIR}/bot.log"
    fi
    
    if [ -f "${LOG_DIR}/admin_bot.log" ]; then
        echo ""
        echo -e "${YELLOW}📄 Recent Admin Bot logs:${NC}"
        tail -5 "${LOG_DIR}/admin_bot.log"
    fi
}

# Обработка аргументов командной строки
case "${1:-deploy}" in
    "deploy"|"dev"|"production")
        main
        ;;
    "stop")
        stop_all
        ;;
    "status")
        show_status
        ;;
    "restart")
        stop_all
        sleep 3
        main
        ;;
    "setup-systemd")
        setup_systemd_services
        ;;
    "help"|"-h"|"--help")
        echo "Usage: $0 [command]"
        echo ""
        echo "Commands:"
        echo "  deploy     - Deploy application (default)"
        echo "  stop       - Stop all services"
        echo "  status     - Show service status"
        echo "  restart    - Restart all services"
        echo "  setup-systemd - Create systemd services"
        echo "  help       - Show this help"
        echo ""
        echo "Environment: ${ENVIRONMENT}"
        ;;
    *)
        echo -e "${RED}❌ Unknown command: $1${NC}"
        echo "Use '$0 help' for usage information"
        exit 1
        ;;
esac

