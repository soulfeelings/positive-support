#!/usr/bin/env python3
"""
Тест сброса счетчика антиспам фильтра
"""

import time
from message_filter import MessageFilter

def test_spam_reset():
    """Тестирует сброс счетчика спама"""
    print("🧪 Тестирование сброса счетчика спама...")
    
    # Создаем экземпляр фильтра
    filter_instance = MessageFilter()
    user_id = 12345
    
    print(f"📊 Лимит сообщений в минуту: {filter_instance.max_messages_per_minute}")
    print()
    
    # Шаг 1: Отправляем сообщения до лимита
    print("✅ Шаг 1: Отправляем сообщения до лимита")
    for i in range(1, filter_instance.max_messages_per_minute + 1):
        result = filter_instance.check_message(user_id, f"Тест {i}")
        print(f"  Сообщение {i}: {'❌ Заблокировано' if result.is_blocked else '✅ Разрешено'}")
    
    print(f"  Текущий счетчик: {filter_instance.user_message_count.get(user_id, 0)}")
    print()
    
    # Шаг 2: Превышаем лимит
    print("🚫 Шаг 2: Превышаем лимит")
    result = filter_instance.check_message(user_id, "Превышение")
    print(f"  Сообщение {filter_instance.max_messages_per_minute + 1}: {'❌ Заблокировано' if result.is_blocked else '✅ Разрешено'}")
    if result.is_blocked:
        print(f"    Причина: {result.details}")
    
    print(f"  Счетчик после блокировки: {filter_instance.user_message_count.get(user_id, 0)}")
    print()
    
    # Шаг 3: Симулируем прошедшую минуту
    print("⏰ Шаг 3: Симулируем прошедшую минуту...")
    old_time = filter_instance.user_last_message_time.get(user_id, 0)
    filter_instance.user_last_message_time[user_id] = time.time() - 61
    print(f"  Время последнего сообщения: {old_time} -> {filter_instance.user_last_message_time[user_id]}")
    
    # Шаг 4: Проверяем сброс
    print("🔄 Шаг 4: Проверяем сброс счетчика")
    result = filter_instance.check_message(user_id, "После сброса")
    print(f"  Сообщение после сброса: {'❌ Заблокировано' if result.is_blocked else '✅ Разрешено'}")
    if result.is_blocked:
        print(f"    Причина: {result.details}")
    else:
        print("  ✅ Счетчик успешно сброшен!")
    
    print(f"  Счетчик после сброса: {filter_instance.user_message_count.get(user_id, 0)}")
    print()
    
    # Шаг 5: Проверяем, что можно снова отправлять сообщения
    print("✅ Шаг 5: Проверяем возможность отправки новых сообщений")
    for i in range(1, 4):
        result = filter_instance.check_message(user_id, f"Новое {i}")
        print(f"  Новое сообщение {i}: {'❌ Заблокировано' if result.is_blocked else '✅ Разрешено'}")
    
    print(f"  Финальный счетчик: {filter_instance.user_message_count.get(user_id, 0)}")
    print()
    print("🎉 Тестирование сброса завершено!")

if __name__ == "__main__":
    test_spam_reset()
