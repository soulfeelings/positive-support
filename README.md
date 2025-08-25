# Бот поддержки positive-support-test

Telegram бот для взаимной поддержки и помощи с автоматизированным деплоем через GitHub Actions.

## 🚀 CI/CD и автоматизированный деплой

### ⚠️ Важно: Решение проблемы с завершением процессов

GitHub Actions автоматически убивает все процессы после завершения workflow. Для решения этой проблемы используется **systemd сервисы**.

**Автоматическое решение:**
- Workflow создает systemd сервисы перед деплоем
- Сервисы работают независимо от GitHub Actions
- Процессы продолжают работать после завершения деплоя

**Подробности:** [SYSTEMD_SETUP.md](SYSTEMD_SETUP.md)

### Быстрая настройка автоматического деплоя
```bash
# Клонируем проект и настраиваем CI/CD за 5 минут
git clone https://github.com/YOUR_USERNAME/positive-support-test.git
cd positive-support-test
chmod +x *.sh
sudo ./setup-github-runner.sh YOUR_USERNAME REPO_NAME RUNNER_TOKEN
```

**Документация по деплою:**
- 📚 [Подробное руководство](DEPLOYMENT_GUIDE.md) - полная настройка CI/CD
- ⚡ [Быстрый старт](QUICK_START.md) - настройка за 5 минут
- 🔐 [Настройка GitHub Secrets](#github-secrets)

### Файлы CI/CD системы
- `.github/workflows/dev-deploy.yml` - GitHub Actions workflow
- `setup-github-runner.sh` - установка self-hosted runner
- `deploy.sh` - основной скрипт деплоя  
- `setup-services.sh` - создание systemd сервисов
- `manage-services.sh` - управление сервисами

## 🔧 Админ-бот для управления блокировками

Проект включает отдельного админ-бота для разблокировки пользователей.

**Быстрая настройка:**
1. Создайте админ-бота через [@BotFather](https://t.me/BotFather)
2. Добавьте `ADMIN_BOT_TOKEN` и `ADMIN_ID` в файл `.env`
3. Запустите: `start_admin.bat` (Windows) или `./start_admin.sh` (Linux)

**Документация:** [ADMIN_BOT_GUIDE.md](ADMIN_BOT_GUIDE.md)

**Возможности:**
- 🔍 Поиск пользователей по никнейму
- 📊 Просмотр истории жалоб и блокировок
- ✅ Разблокировка пользователей
- 📈 Статистика администрирования

## 📋 Локальный запуск (для разработки)

### 1. Установить PostgreSQL
- Скачать: https://www.postgresql.org/download/
- Запомнить пароль для пользователя `postgres`

### 2. Настроить базу данных
```bash
python setup_db_manual.py
```
(Не забудьте поменять пароль в файле!)

### 3. Запустить
```bash
run.bat
```

## Файлы проекта

- `bot.py` - Telegram бот
- `main.py` - API сервер
- `setup_db_manual.py` - настройка базы данных
- `clear_bot.py` - очистка конфликтов бота
- `requirements.txt` - зависимости Python
- `run.bat` - автозапуск

## Проверка работы

- API: http://localhost:8000/health
- Бот: найти в Telegram и написать `/start`

## Функции бота

- 💌 Отправить поддержку
- 🔥 Получить поддержку  
- 🆘 Нужна помощь
- 🤝 Помочь кому-нибудь
- 👤 Профиль - просмотр статистики

## Сохранность данных

### Проверка данных
```bash
python check_db.py
```
Показывает все данные в базе.

### Создание бэкапа
```bash
python backup_db.py
```
Создает файл `backup_YYYYMMDD_HHMMSS.json`.

### Восстановление
```bash
python backup_db.py restore backup_file.json
```

## Файлы бэкапа

- `bot_backup_full_profile.py` - полная версия бота с функцией смены никнейма
- `bot.py` - текущая версия (профиль без смены никнейма)

### Восстановление полной версии:
```bash
copy bot_backup_full_profile.py bot.py
```

### База данных сохраняется автоматически
- Все данные остаются после перезапуска бота
- PostgreSQL хранит данные на диске
- Используется автокоммит для гарантии сохранения

## 🔐 GitHub Secrets

Для работы автоматического деплоя нужно настроить секреты в репозитории (`Settings` → `Secrets and variables` → `Actions`):

### Обязательные секреты:
| Название | Описание | Пример |
|----------|----------|---------|
| `BOT_TOKEN` | Токен Telegram бота | `123456:ABC-DEF...` |
| `DB_PASSWORD` | Пароль базы данных | `secure_password` |

### Дополнительные секреты (опционально):
| Название | Описание | По умолчанию |
|----------|----------|--------------|
| `DB_HOST` | Хост базы данных | `localhost` |
| `DB_USER` | Пользователь БД | `postgres` |
| `DB_NAME` | Название БД | `support_bot` |
| `BACKEND_URL` | URL API | `http://localhost:8000` |

## 🛠️ Управление в продакшене

### Управление сервисами:
```bash
./manage-services.sh start    # Запуск всех сервисов
./manage-services.sh stop     # Остановка всех сервисов
./manage-services.sh restart  # Перезапуск всех сервисов
./manage-services.sh status   # Статус всех сервисов
./manage-services.sh logs     # Просмотр логов
```

### Команды деплоя:
```bash
./deploy.sh          # Полный деплой
./deploy.sh status   # Проверка статуса
./deploy.sh stop     # Остановка сервисов
./deploy.sh restart  # Перезапуск сервисов
```

### Мониторинг:
```bash
# Проверка здоровья API
curl http://localhost:8000/health

# Статус systemd сервисов
sudo systemctl status positive-support-api
sudo systemctl status positive-support-bot

# Логи сервисов
sudo journalctl -u positive-support-api -f
sudo journalctl -u positive-support-bot -f
```

## 🔄 Workflow автоматического деплоя

1. **Push в ветку `dev`** → Автоматический trigger GitHub Actions
2. **GitHub Actions** → Запуск workflow на self-hosted runner
3. **Self-hosted runner** → Выполнение деплоя на сервере:
   - Остановка старых сервисов
   - Обновление кода из репозитория
   - Установка/обновление зависимостей
   - Проверка базы данных и миграции
   - Запуск новых сервисов
   - Health check и проверка работоспособности

**Время деплоя:** ~2-3 минуты  
**Downtime:** ~10-15 секунд (время перезапуска сервисов)