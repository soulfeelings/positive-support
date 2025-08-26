# 🧪 Быстрое тестирование системы напоминаний

## Для проверки готовности системы

```bash
# Полный тест всех компонентов
python test_reminders.py

# Если все тесты прошли - система готова к работе!
```

## Ручная проверка в боте

1. **Откройте бота в Telegram**
2. **Перейдите в профиль:** кнопка "👤 Профиль"
3. **Проверьте наличие кнопок:**
   - "🔔 Включить напоминание" (если выключены)
   - "🔕 Выключить напоминание" (если включены)
4. **Переключите настройку** и убедитесь, что статус обновился

## Тест отправки напоминаний

```bash
# Отправить напоминания прямо сейчас (игнорируя время)
python reminder_scheduler.py test
```

## Что должно произойти:

✅ **Успешный тест покажет:**
- Database Connection: OK
- Database Schema: OK  
- API Connection: OK
- Profile API: OK
- Reminder Settings API: OK
- Reminder Message API: OK
- Reminder Users: OK
- "All tests passed! Reminder system is ready to use."

❌ **При ошибках:**
- Проверьте, что база данных запущена
- Проверьте, что API сервер работает (python main.py)
- Обновите схему БД: `python setup_db_manual.py`

## Проблемы и решения

### "Database connection failed"
```bash
# Запустите PostgreSQL
# Проверьте настройки в переменных окружения
# Или обновите setup_db_manual.py с правильными настройками
```

### "API connection failed"  
```bash
# Запустите API сервер
python main.py
# Или uvicorn main:app --host 0.0.0.0 --port 8000
```

### "Missing reminder fields"
```bash
# Обновите схему базы данных
python setup_db_manual.py
```

## После успешного тестирования

Запустите систему напоминаний:

**Windows:**
```bash
start_reminders.bat
```

**Linux/macOS:**
```bash
./start_reminders.sh
```

Система будет работать с 12:00 до 20:00 каждый день и отправлять напоминания пользователям каждый час.
