#!/usr/bin/env python3
"""
Тестовый скрипт для проверки системы напоминаний
"""

import asyncio
import logging
import sys
import os

# Добавляем текущую директорию в path для импорта модулей
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from reminder_scheduler import (
    api_request, 
    get_users_for_reminders, 
    send_reminder_to_user,
    get_connection
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_database_connection():
    """Тест подключения к базе данных"""
    try:
        conn = await get_connection()
        result = await conn.fetchval("SELECT 1")
        await conn.close()
        if result == 1:
            logger.info("✅ Database connection: OK")
            return True
        else:
            logger.error("❌ Database connection: FAILED")
            return False
    except Exception as e:
        logger.error(f"❌ Database connection error: {e}")
        return False

async def test_api_connection():
    """Тест подключения к API"""
    try:
        result = await api_request("health", {})
        if result.get("status") == "healthy":
            logger.info("✅ API connection: OK")
            return True
        else:
            logger.error(f"❌ API connection: FAILED - {result}")
            return False
    except Exception as e:
        logger.error(f"❌ API connection error: {e}")
        return False

async def test_reminder_users():
    """Тест получения пользователей для напоминаний"""
    try:
        users = await get_users_for_reminders()
        logger.info(f"✅ Found {len(users)} users with reminders enabled")
        
        for user in users[:3]:  # Показываем первых 3 пользователей
            logger.info(f"   User: {user['nickname']} (ID: {user['user_id']}, last_msg_id: {user['last_reminder_message_id']})")
        
        if len(users) > 3:
            logger.info(f"   ... and {len(users) - 3} more users")
            
        return len(users) > 0
    except Exception as e:
        logger.error(f"❌ Error getting reminder users: {e}")
        return False

async def test_reminder_message_api():
    """Тест API для получения сообщений напоминаний"""
    try:
        # Тестируем с фиктивным пользователем
        test_user_id = 999999999
        result = await api_request("get_reminder_message", {"user_id": test_user_id})
        
        if result.get("status") in ["ok", "no_messages", "user_not_found"]:
            logger.info(f"✅ Reminder message API: OK (status: {result.get('status')})")
            return True
        else:
            logger.error(f"❌ Reminder message API: FAILED - {result}")
            return False
    except Exception as e:
        logger.error(f"❌ Reminder message API error: {e}")
        return False

async def test_profile_api():
    """Тест API профиля с новыми полями напоминаний"""
    try:
        # Тестируем с фиктивным пользователем
        test_user_id = 999999999
        result = await api_request("profile", {"user_id": test_user_id})
        
        if result.get("status") in ["ok", "not_found"]:
            if result.get("status") == "ok":
                has_reminders_field = "reminders_enabled" in result
                has_last_msg_field = "last_reminder_message_id" in result
                
                if has_reminders_field and has_last_msg_field:
                    logger.info("✅ Profile API with reminder fields: OK")
                    return True
                else:
                    logger.error(f"❌ Profile API missing reminder fields: reminders_enabled={has_reminders_field}, last_reminder_message_id={has_last_msg_field}")
                    return False
            else:
                logger.info("✅ Profile API: OK (user not found is expected)")
                return True
        else:
            logger.error(f"❌ Profile API: FAILED - {result}")
            return False
    except Exception as e:
        logger.error(f"❌ Profile API error: {e}")
        return False

async def test_reminder_settings_api():
    """Тест API настроек напоминаний"""
    try:
        # Тестируем с фиктивным пользователем
        test_user_id = 999999999
        
        # Тест включения напоминаний
        result = await api_request("set_reminder_settings", {
            "user_id": test_user_id,
            "reminders_enabled": True
        })
        
        if result.get("status") == "success":
            logger.info("✅ Reminder settings API: OK")
            return True
        else:
            logger.error(f"❌ Reminder settings API: FAILED - {result}")
            return False
    except Exception as e:
        logger.error(f"❌ Reminder settings API error: {e}")
        return False

async def check_database_schema():
    """Проверка схемы базы данных"""
    try:
        conn = await get_connection()
        
        # Проверяем наличие новых полей в таблице users
        columns = await conn.fetch("""
            SELECT column_name, data_type, column_default 
            FROM information_schema.columns 
            WHERE table_name = 'users'
        """)
        
        column_names = [col['column_name'] for col in columns]
        
        has_reminders_enabled = 'reminders_enabled' in column_names
        has_last_reminder_id = 'last_reminder_message_id' in column_names
        
        if has_reminders_enabled and has_last_reminder_id:
            logger.info("✅ Database schema: OK (reminder fields present)")
            
            # Показываем информацию о полях
            for col in columns:
                if col['column_name'] in ['reminders_enabled', 'last_reminder_message_id']:
                    logger.info(f"   {col['column_name']}: {col['data_type']} (default: {col['column_default']})")
            
            await conn.close()
            return True
        else:
            logger.error(f"❌ Database schema: MISSING FIELDS - reminders_enabled={has_reminders_enabled}, last_reminder_message_id={has_last_reminder_id}")
            await conn.close()
            return False
            
    except Exception as e:
        logger.error(f"❌ Database schema check error: {e}")
        return False

async def main():
    """Главная функция тестирования"""
    logger.info("🧪 Starting reminder system tests...")
    logger.info("=" * 50)
    
    tests = [
        ("Database Connection", test_database_connection),
        ("Database Schema", check_database_schema),
        ("API Connection", test_api_connection),
        ("Profile API", test_profile_api),
        ("Reminder Settings API", test_reminder_settings_api),
        ("Reminder Message API", test_reminder_message_api),
        ("Reminder Users", test_reminder_users),
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        logger.info(f"\n🔍 Running test: {test_name}")
        try:
            result = await test_func()
            if result:
                passed += 1
            else:
                failed += 1
        except Exception as e:
            logger.error(f"❌ Test {test_name} crashed: {e}")
            failed += 1
    
    logger.info("\n" + "=" * 50)
    logger.info(f"📊 Test Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        logger.info("🎉 All tests passed! Reminder system is ready to use.")
        return True
    else:
        logger.error("❌ Some tests failed. Please fix the issues before using the reminder system.")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
