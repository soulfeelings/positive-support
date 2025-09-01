#!/usr/bin/env python3
"""
Тест интеграции фильтра с ботом
"""

from message_filter import get_message_filter

def test_filter_integration():
    """Тестирует интеграцию фильтра"""
    print("🧪 Тест интеграции фильтра с ботом\n")
    
    # Получаем экземпляр фильтра
    filter_instance = get_message_filter()
    
    # Тестовые сообщения
    test_messages = [
        "Привет!",
        "Блять, что за хрень",
        "https://example.com",
        "Ты идиот!",
        "Спасибо за помощь!"
    ]
    
    print("📝 Тестируем сообщения:\n")
    
    for i, message in enumerate(test_messages, 1):
        print(f"{i}. '{message}'")
        
        # Проверяем через фильтр
        result = filter_instance.check_message(12345, message, "text")
        
        if result.is_blocked:
            print(f"   ❌ ЗАБЛОКИРОВАНО: {result.reason}")
            print(f"   📋 Детали: {result.details}")
        else:
            print(f"   ✅ ПРОШЛО")
        
        print()
    
    print("✅ Тест завершен!")

if __name__ == "__main__":
    test_filter_integration()
