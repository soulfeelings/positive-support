#!/usr/bin/env python3
"""
Скрипт для проверки конфигурации админ-бота
"""

import os
import sys

def check_config():
    """Проверяет конфигурацию админ-бота"""
    print("🔧 Проверка конфигурации админ-бота...")
    print("=" * 50)
    
    # Проверяем файл .env
    if not os.path.exists(".env"):
        print("❌ Файл .env не найден!")
        print("   Создайте файл .env на основе env.example")
        return False
    
    # Загружаем переменные из .env
    env_vars = {}
    try:
        with open(".env", "r") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    env_vars[key.strip()] = value.strip()
    except Exception as e:
        print(f"❌ Ошибка чтения .env: {e}")
        return False
    
    # Проверяем обязательные переменные
    required_vars = ["ADMIN_BOT_TOKEN", "ADMIN_ID"]
    missing_vars = []
    
    for var in required_vars:
        if var not in env_vars or not env_vars[var]:
            missing_vars.append(var)
    
    if missing_vars:
        print("❌ Отсутствуют обязательные переменные:")
        for var in missing_vars:
            print(f"   • {var}")
        print("")
        print("📋 Добавьте в файл .env:")
        if "ADMIN_BOT_TOKEN" in missing_vars:
            print("   ADMIN_BOT_TOKEN=ВАШ_ТОКЕН_АДМИН_БОТА")
        if "ADMIN_ID" in missing_vars:
            print("   ADMIN_ID=ВАШ_TELEGRAM_ID")
        print("")
        print("💡 Инструкция: ADMIN_BOT_SETUP.md")
        return False
    
    # Проверяем токен
    token = env_vars["ADMIN_BOT_TOKEN"]
    if len(token) < 20 or ":" not in token:
        print("❌ ADMIN_BOT_TOKEN похоже неверный")
        print("   Токен должен быть вида: 1234567890:AABCDEFghijklmnop...")
        return False
    
    # Проверяем ID
    admin_id = env_vars["ADMIN_ID"]
    try:
        admin_id_int = int(admin_id)
        if admin_id_int <= 0:
            raise ValueError("Invalid ID")
    except ValueError:
        print("❌ ADMIN_ID должен быть числом больше 0")
        print(f"   Сейчас: {admin_id}")
        return False
    
    # Проверяем наличие admin_bot.py
    if not os.path.exists("admin_bot.py"):
        print("❌ Файл admin_bot.py не найден!")
        return False
    
    # Все проверки пройдены
    print("✅ Конфигурация админ-бота корректна!")
    print("")
    print("📋 Настройки:")
    print(f"   • Токен: {token[:10]}...")
    print(f"   • Админ ID: {admin_id}")
    print(f"   • Backend: {env_vars.get('BACKEND_URL', 'http://localhost:8000')}")
    print("")
    print("🚀 Команды для запуска:")
    print("   ./deploy.sh restart       # Перезапуск всех сервисов")
    print("   systemctl status positive-support-admin-bot  # Статус админ-бота")
    print("")
    return True

if __name__ == "__main__":
    if check_config():
        sys.exit(0)
    else:
        sys.exit(1)
