@echo off
echo Запуск админ-бота для разблокировки пользователей...

REM Проверяем наличие Python
python --version >nul 2>&1
if errorlevel 1 (
    echo Python не найден! Установите Python и попробуйте снова.
    pause
    exit /b 1
)

REM Проверяем наличие файла .env
if not exist ".env" (
    echo ОШИБКА: Файл .env не найден!
    echo Создайте файл .env на основе env.example
    echo И установите ADMIN_BOT_TOKEN и ADMIN_ID
    pause
    exit /b 1
)

REM Загружаем переменные окружения из .env файла
for /f "tokens=1,2 delims==" %%i in (.env) do (
    if not "%%j"=="" (
        set "%%i=%%j"
    )
)

REM Проверяем обязательные переменные
if "%ADMIN_BOT_TOKEN%"=="" (
    echo ОШИБКА: ADMIN_BOT_TOKEN не установлен в .env файле!
    pause
    exit /b 1
)

if "%ADMIN_ID%"=="" (
    echo ОШИБКА: ADMIN_ID не установлен в .env файле!
    pause
    exit /b 1
)

echo Настройки:
echo - Админ бот токен: %ADMIN_BOT_TOKEN:~0,10%...
echo - Админ ID: %ADMIN_ID%
echo - База данных: %DB_HOST%:%DB_PORT%/%DB_NAME%
echo.

echo Запуск админ-бота...
python admin_bot.py

if errorlevel 1 (
    echo.
    echo ОШИБКА: Админ-бот завершился с ошибкой!
    echo Возможные причины:
    echo 1. Неверный токен админ-бота
    echo 2. Проблемы с подключением к базе данных
    echo 3. Отсутствие интернет-соединения
    echo 4. Не установлены зависимости (pip install -r requirements.txt)
    pause
    exit /b 1
)

echo Админ-бот завершен.
pause
