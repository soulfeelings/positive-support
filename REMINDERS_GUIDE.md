# 🔔 Руководство по системе напоминаний

## Что это такое?

Система ежедневных напоминаний отправляет пользователям сообщения поддержки от других участников сообщества в автоматическом режиме.

## 👥 Для пользователей

### Как включить/выключить напоминания:

1. Откройте бота в Telegram
2. Нажмите кнопку "👤 Профиль"
3. Используйте кнопки:
   - "🔔 Включить напоминание" - для включения
   - "🔕 Выключить напоминание" - для выключения

### Когда приходят напоминания:

- **Время:** с 12:00 до 20:00 каждый день
- **Частота:** одно сообщение в час
- **По умолчанию:** напоминания включены для всех новых пользователей

### Что содержат напоминания:

- Сообщения поддержки от других пользователей
- Мотивационные сообщения (если нет пользовательского контента)
- Имя автора сообщения

## 🛠️ Для администраторов

### Запуск системы напоминаний:

**Windows:**
```bash
start_reminders.bat
```

**Linux/macOS:**
```bash
chmod +x start_reminders.sh
./start_reminders.sh
```

**Python напрямую:**
```bash
python start_reminders.py
```

### Тестирование системы:

```bash
# Тестовая отправка напоминаний всем пользователям (независимо от времени)
python reminder_scheduler.py test
```

### Мониторинг:

- **Логи:** все активности записываются в `reminders.log`
- **Формат логов:** время, уровень, сообщение
- **Что логируется:**
  - Запуск/остановка системы
  - Отправка напоминаний пользователям
  - Ошибки и предупреждения

### Пример логов:

```
2024-01-15 14:00:02 - INFO - 🔔 Starting daily reminder broadcast at 14:00:02.123456
2024-01-15 14:00:02 - INFO - Found 25 users for reminders
2024-01-15 14:00:03 - INFO - ✅ Reminder sent to user 123456789 (JohnDoe), message_id: 157
2024-01-15 14:00:05 - INFO - 📊 Reminder broadcast completed: 23 success, 2 failures
```

## ⚙️ Техническая документация

### Алгоритм выбора сообщений:

1. **Последовательный выбор:** система запоминает последний отправленный Message ID для каждого пользователя
2. **Следующее сообщение:** выбирается сообщение с ID больше последнего отправленного
3. **Циклический повтор:** когда сообщения заканчиваются, система начинает сначала с минимального ID
4. **Исключения:** пользователь не получает собственные сообщения

### База данных:

Добавлены новые поля в таблицу `users`:
- `reminders_enabled` (BOOLEAN) - включены ли напоминания (по умолчанию TRUE)
- `last_reminder_message_id` (INTEGER) - ID последнего отправленного сообщения (по умолчанию 0)

### API endpoints:

- `POST /set_reminder_settings` - включение/выключение напоминаний
- `POST /get_reminder_message` - получение следующего сообщения для напоминания
- Обновлен `POST /profile` - теперь возвращает настройки напоминаний

### Файлы системы:

- `reminder_scheduler.py` - основная логика планировщика
- `start_reminders.py` - обертка для запуска с логированием
- `start_reminders.sh` - bash скрипт для Linux/macOS
- `start_reminders.bat` - batch файл для Windows

## 🚨 Решение проблем

### Проблема: Напоминания не отправляются

**Причины:**
1. Система напоминаний не запущена
2. Время не входит в интервал 12:00-20:00
3. Нет пользователей с включенными напоминаниями
4. Проблемы с базой данных или API

**Решение:**
```bash
# Проверьте логи
tail -f reminders.log

# Проверьте API
curl http://localhost:8000/health

# Тестовый запуск
python reminder_scheduler.py test
```

### Проблема: Пользователи не получают напоминания

**Причины:**
1. Пользователь заблокировал бота
2. Пользователь выключил напоминания
3. Проблемы с токеном бота

**Решение:**
```bash
# Проверьте настройки пользователя в базе данных
python check_db.py

# Проверьте токен бота в переменных окружения
echo $BOT_TOKEN
```

### Проблема: Дублирующие сообщения

**Причины:**
1. Запущено несколько экземпляров планировщика
2. Проблемы с часовым интервалом

**Решение:**
```bash
# Остановите все процессы
pkill -f reminder_scheduler.py
pkill -f start_reminders.py

# Запустите заново
./start_reminders.sh
```

## 📈 Мониторинг эффективности

### Метрики для отслеживания:

1. **Количество отправленных напоминаний** - из логов
2. **Процент успешных доставок** - success vs failures в логах
3. **Количество пользователей с включенными напоминаниями** - из базы данных
4. **Активность пользователей после напоминаний** - анализ взаимодействий с ботом

### SQL запросы для анализа:

```sql
-- Количество пользователей с включенными напоминаниями
SELECT COUNT(*) FROM users WHERE reminders_enabled = TRUE AND is_blocked = FALSE;

-- Последние отправленные Message ID по пользователям
SELECT user_id, nickname, last_reminder_message_id 
FROM users 
WHERE reminders_enabled = TRUE 
ORDER BY last_reminder_message_id DESC;

-- Общее количество доступных сообщений для напоминаний
SELECT COUNT(*) FROM messages WHERE type = 'support';
```

## 🔧 Настройка для продакшена

### Запуск как системный сервис (Linux):

1. Создайте файл службы:
```bash
sudo nano /etc/systemd/system/positive-support-reminders.service
```

2. Содержимое файла:
```ini
[Unit]
Description=Positive Support Reminders
After=network.target

[Service]
Type=simple
User=your_user
WorkingDirectory=/path/to/positive-support
ExecStart=/usr/bin/python3 start_reminders.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

3. Активируйте службу:
```bash
sudo systemctl daemon-reload
sudo systemctl enable positive-support-reminders
sudo systemctl start positive-support-reminders
```

### Мониторинг службы:

```bash
# Статус
sudo systemctl status positive-support-reminders

# Логи
sudo journalctl -u positive-support-reminders -f

# Перезапуск
sudo systemctl restart positive-support-reminders
```
