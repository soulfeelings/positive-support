#!/usr/bin/env python3
"""
Тестовый скрипт для проверки автофильтра сообщений

Запуск: python test_filter.py
"""

import asyncio
from message_filter import get_message_filter

def test_message_filter():
    """Тестирует фильтр сообщений"""
    print("🧪 Тестирование автофильтра сообщений\n")
    
    # Получаем экземпляр фильтра
    filter_instance = get_message_filter()
    
    # Тестовые сообщения
    test_messages = [
        # Нормальные сообщения
        ("Привет! Как дела?", "Нормальное сообщение"),
        ("Спасибо за помощь!", "Сообщение с благодарностью"),
        ("Мне нужна поддержка", "Запрос поддержки"),
        
        # Нецензурные выражения
        ("Блять, что за хрень", "Сообщение с матом"),
        ("Это полная хуйня", "Сообщение с матом"),
        ("Fuck this shit", "Английский мат"),
        
        # Оскорбления
        ("Ты идиот!", "Оскорбление"),
        ("Какой же ты дебил", "Оскорбление"),
        ("You are stupid", "Английское оскорбление"),
        
        # Ссылки
        ("Посмотри https://example.com", "HTTP ссылка"),
        ("Мой Instagram @username", "Упоминание"),
        ("Хештег #support", "Хештег"),
        ("Сокращенная ссылка bit.ly/abc123", "Сокращенная ссылка"),
        
        # Спам
        ("!!!!!!!!!!!!!", "Множественные знаки"),
        ("ВСЕ ЗАГЛАВНЫЕ БУКВЫ", "Все заглавные"),
        ("а б в г д е ё ж з и й к л м н о п р с т у ф х ц ч ш щ ъ ы ь э ю я", "Короткие слова"),
        ("!@#$%^&*()", "Много спецсимволов"),
        
        # Смешанные случаи
        ("Помогите мне, пожалуйста! Спасибо!", "Смешанное сообщение"),
        ("Это не работает, блять! https://example.com", "Мат + ссылка"),
    ]
    
    print("📝 Тестируем сообщения:\n")
    
    for i, (message, description) in enumerate(test_messages, 1):
        print(f"{i:2d}. {description}:")
        print(f"    Сообщение: '{message}'")
        
        # Проверяем сообщение
        result = filter_instance.check_message(12345, message, "text")
        
        if result.is_blocked:
            print(f"    ❌ ЗАБЛОКИРОВАНО: {result.reason}")
            print(f"    📋 Детали: {result.details}")
            print(f"    ⚠️  Уровень: {result.severity}")
        else:
            print(f"    ✅ ПРОШЛО")
        
        print()
    
    # Тестируем настройки
    print("\n⚙️  Текущие настройки фильтра:")
    print(f"   Максимум сообщений в минуту: {filter_instance.max_messages_per_minute}")
    
    # Тестируем слова-исключения
    print("\n🔍 Тестируем слова-исключения:")
    exception_tests = [
        "Спасибо за помощь!",
        "Мне нужна поддержка",
        "Хорошо, понял",
        "Плохо себя чувствую"
    ]
    
    for message in exception_tests:
        result = filter_instance.check_message(12345, message, "text")
        if result.is_blocked:
            print(f"   ❌ '{message}' - заблокировано")
        else:
            print(f"   ✅ '{message}' - прошло")

def test_filter_config():
    """Тестирует конфигурацию фильтра"""
    print("\n🔧 Тестируем конфигурацию:\n")
    
    try:
        from filter_config import (
            get_filter_settings, get_bad_words, get_offensive_words,
            get_link_patterns, get_spam_patterns, get_exception_words
        )
        
        # Получаем настройки
        settings = get_filter_settings()
        print("✅ Настройки загружены:")
        for key, value in settings.items():
            print(f"   {key}: {value}")
        
        # Получаем списки слов
        bad_words = get_bad_words()
        offensive_words = get_offensive_words()
        exception_words = get_exception_words()
        
        print(f"\n✅ Списки слов загружены:")
        print(f"   Нецензурных слов: {len(bad_words)}")
        print(f"   Оскорбительных слов: {len(offensive_words)}")
        print(f"   Слов-исключений: {len(exception_words)}")
        
        # Получаем паттерны
        link_patterns = get_link_patterns()
        spam_patterns = get_spam_patterns()
        
        print(f"\n✅ Паттерны загружены:")
        print(f"   Паттернов ссылок: {len(link_patterns)}")
        print(f"   Паттернов спама: {len(spam_patterns)}")
        
    except ImportError as e:
        print(f"❌ Ошибка импорта: {e}")
    except Exception as e:
        print(f"❌ Ошибка: {e}")

if __name__ == "__main__":
    print("🚀 Запуск тестирования автофильтра сообщений\n")
    
    try:
        # Тестируем основной функционал
        test_message_filter()
        
        # Тестируем конфигурацию
        test_filter_config()
        
        print("\n✅ Тестирование завершено успешно!")
        
    except Exception as e:
        print(f"\n❌ Ошибка во время тестирования: {e}")
        import traceback
        traceback.print_exc()
