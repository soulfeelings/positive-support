#!/usr/bin/env python3
"""
Тестовый скрипт для проверки работы антиспам фильтра
"""

import time
from message_filter import MessageFilter

def test_spam_filter():
    """Тестирует работу антиспам фильтра"""
    print("🧪 Тестирование антиспам фильтра...")
    
    # Создаем экземпляр фильтра
    filter_instance = MessageFilter()
    user_id = 12345
    
    print(f"📊 Лимит сообщений в минуту: {filter_instance.max_messages_per_minute}")
    print()
    
    # Тест 1: Отправляем сообщения в пределах лимита
    print("✅ Тест 1: Отправляем сообщения в пределах лимита")
    for i in range(1, filter_instance.max_messages_per_minute + 1):
        result = filter_instance.check_message(user_id, f"Тестовое сообщение {i}")
        print(f"  Сообщение {i}: {'❌ Заблокировано' if result.is_blocked else '✅ Разрешено'}")
        if result.is_blocked:
            print(f"    Причина: {result.details}")
    
    print()
    
    # Тест 2: Превышаем лимит
    print("🚫 Тест 2: Превышаем лимит")
    result = filter_instance.check_message(user_id, "Сообщение сверх лимита")
    print(f"  Сообщение {filter_instance.max_messages_per_minute + 1}: {'❌ Заблокировано' if result.is_blocked else '✅ Разрешено'}")
    if result.is_blocked:
        print(f"    Причина: {result.details}")
    
    print()
    
    # Тест 3: Симулируем прошедшую минуту
    print("⏰ Тест 3: Симулируем прошедшую минуту...")
    # Устанавливаем время последнего сообщения на 61 секунду назад
    filter_instance.user_last_message_time[user_id] = time.time() - 61
    
    result = filter_instance.check_message(user_id, "Сообщение после ожидания")
    print(f"  Сообщение после ожидания: {'❌ Заблокировано' if result.is_blocked else '✅ Разрешено'}")
    if result.is_blocked:
        print(f"    Причина: {result.details}")
    else:
        print("  ✅ Счетчик успешно сброшен!")
    
    print()
    
    # Тест 4: Проверяем счетчик
    print("📊 Тест 4: Проверяем текущий счетчик")
    current_count = filter_instance.user_message_count.get(user_id, 0)
    print(f"  Текущий счетчик: {current_count}")
    
    print()
    print("🎉 Тестирование завершено!")

if __name__ == "__main__":
    test_spam_filter()
