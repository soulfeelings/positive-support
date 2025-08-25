# ⚡ Быстрый старт CI/CD

Краткое руководство по настройке автоматизированного деплоя для positive-support-test.

## 🎯 Что будет настроено

После выполнения этих шагов у вас будет:
- ✅ Self-hosted GitHub Runner на вашем сервере
- ✅ Автоматический деплой при push в ветку `dev`
- ✅ Системные сервисы для API и бота
- ✅ Мониторинг и логирование

## 🚀 Быстрая настройка (5 минут)

### 1. На сервере (Ubuntu/Debian)

```bash
# Клонируем репозиторий
git clone https://github.com/YOUR_USERNAME/positive-support-test.git
cd positive-support-test

# Делаем скрипты исполняемыми
chmod +x *.sh

# Устанавливаем зависимости системы
sudo apt update && sudo apt install -y python3 python3-pip postgresql curl jq git

# Устанавливаем Python зависимости
pip3 install -r requirements.txt
```

### 2. Настройка базы данных

```bash
# Если PostgreSQL не настроен
sudo -u postgres psql << EOF
CREATE DATABASE support_bot;
CREATE USER bot_user WITH PASSWORD 'your_secure_password';
GRANT ALL PRIVILEGES ON DATABASE support_bot TO bot_user;
\q
EOF
```

### 3. Получение токена для GitHub Runner

1. Откройте ваш репозиторий на GitHub
2. `Settings` → `Actions` → `Runners` → `New self-hosted runner`
3. Выберите Linux
4. Скопируйте токен из команды `./config.sh --url ... --token XXX`

### 4. Установка GitHub Runner

```bash
# Замените YOUR_USERNAME, REPO_NAME и RUNNER_TOKEN на свои значения
sudo ./setup-github-runner.sh YOUR_USERNAME REPO_NAME RUNNER_TOKEN
```

### 5. Настройка GitHub Secrets

Перейдите в `Settings` → `Secrets and variables` → `Actions` и добавьте:

| Secret | Значение |
|--------|----------|
| `BOT_TOKEN` | Ваш токен Telegram бота |
| `DB_PASSWORD` | Пароль базы данных |

### 6. Настройка переменных окружения

```bash
# Создаем .env файл
cp env.example .env

# Редактируем (замените на свои значения)
nano .env
```

### 7. Настройка systemd сервисов

```bash
# Создаем системные сервисы
sudo ./setup-services.sh
```

### 8. Первый деплой

```bash
# Создаем ветку dev (если её нет)
git checkout -b dev
git push origin dev

# Или просто делаем push в существующую ветку dev
git add .
git commit -m "Setup CI/CD"
git push origin dev
```

## ✅ Проверка работы

### 1. Проверка GitHub Runner
- Перейдите в `Settings` → `Actions` → `Runners`
- Ваш runner должен быть в статусе "Idle" 🟢

### 2. Проверка workflow
- Перейдите во вкладку `Actions` в репозитории
- Должен быть запущен workflow "Dev Deploy" 🔄

### 3. Проверка сервисов на сервере

```bash
# Статус сервисов
./manage-services.sh status

# Проверка API
curl http://localhost:8000/health

# Проверка логов
./manage-services.sh logs
```

## 🎛️ Управление

### Команды для управления сервисами:

```bash
./manage-services.sh start    # Запуск
./manage-services.sh stop     # Остановка
./manage-services.sh restart  # Перезапуск
./manage-services.sh status   # Статус
./manage-services.sh logs     # Просмотр логов
```

### Команды для деплоя:

```bash
./deploy.sh          # Полный деплой
./deploy.sh status   # Статус приложения
./deploy.sh stop     # Остановка
./deploy.sh restart  # Перезапуск
```

## 🔧 Что дальше?

После успешной настройки:

1. **Автоматический деплой готов** - каждый push в `dev` будет автоматически деплоиться
2. **Настройте мониторинг** - добавьте уведомления о статусе деплоя
3. **Добавьте тесты** - расширьте workflow проверками кода
4. **Настройте продакшен** - создайте отдельную ветку и workflow для production

## 🆘 Проблемы?

### Основные команды для диагностики:

```bash
# Статус GitHub Runner
sudo systemctl status github-runner

# Логи runner'а
sudo journalctl -u github-runner -f

# Статус приложения
./deploy.sh status

# Проверка базы данных
python3 check_db.py
```

### Частые проблемы:

1. **Runner не подключается** → Проверьте токен и перезапустите сервис
2. **API не запускается** → Проверьте базу данных и переменные окружения
3. **Workflow падает** → Проверьте логи в GitHub Actions и на сервере

Подробное руководство: [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)

---

**Время настройки:** ~5-10 минут  
**Сложность:** ⭐⭐☆☆☆ (Средняя)

