@echo off
echo 🔔 Запуск системы ежедневных напоминаний...

REM Проверяем наличие Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python не найден. Установите Python для продолжения.
    pause
    exit /b 1
)

REM Проверяем наличие файла напоминаний
if not exist "reminder_scheduler.py" (
    echo ❌ Файл reminder_scheduler.py не найден
    pause
    exit /b 1
)

REM Запускаем планировщик напоминаний
echo 🚀 Запуск планировщика напоминаний...
python start_reminders.py

echo 📴 Система напоминаний остановлена
pause
