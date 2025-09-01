import re
import logging
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from filter_config import (
    get_filter_settings, get_bad_words, get_offensive_words,
    get_link_patterns, get_spam_patterns, get_exception_words
)

logger = logging.getLogger(__name__)

@dataclass
class FilterResult:
    """Результат проверки фильтра"""
    is_blocked: bool
    reason: str
    details: str
    severity: str  # 'warning', 'block', 'auto_block'

class MessageFilter:
    """Фильтр для проверки сообщений на мат, оскорбления, спам и ссылки"""
    
    def __init__(self):
        # Загружаем настройки из конфигурации
        self.settings = get_filter_settings()
        
        # Список нецензурных слов
        self.bad_words = get_bad_words()
        
        # Список оскорбительных слов
        self.offensive_words = get_offensive_words()
        
        # Паттерны для ссылок
        self.link_patterns = get_link_patterns()
        
        # Паттерны для спама
        self.spam_patterns = get_spam_patterns()
        
        # Слова-исключения
        self.exception_words = get_exception_words()
        
        # Счетчик сообщений для отслеживания спама
        self.user_message_count: Dict[int, int] = {}
        
        # Настройки из конфигурации
        self.max_messages_per_minute = self.settings["max_messages_per_minute"]
        
    def check_message(self, user_id: int, text: str, message_type: str = "text") -> FilterResult:
        """
        Проверяет сообщение на все типы нарушений
        
        Args:
            user_id: ID пользователя
            text: Текст сообщения
            message_type: Тип сообщения
            
        Returns:
            FilterResult с результатом проверки
        """
        if not text or message_type != "text":
            return FilterResult(False, "", "", "pass")
        
        # Сначала проверяем слова-исключения
        text_lower = text.lower()
        for exception_word in self.exception_words:
            if exception_word in text_lower:
                return FilterResult(False, "", "", "pass")
        
        # Проверяем на мат (если включено)
        if self.settings.get("enable_bad_words_check", True):
            mat_result = self._check_bad_words(text)
            if mat_result.is_blocked:
                return mat_result
        
        # Проверяем на оскорбления (если включено)
        if self.settings.get("enable_offensive_words_check", True):
            offensive_result = self._check_offensive_words(text)
            if offensive_result.is_blocked:
                return offensive_result
        
        # Проверяем на ссылки (если включено)
        if self.settings.get("enable_links_check", True):
            link_result = self._check_links(text)
            if link_result.is_blocked:
                return link_result
        
        # Проверяем на спам (если включено)
        if self.settings.get("enable_spam_check", True):
            spam_result = self._check_spam(user_id, text)
            if spam_result.is_blocked:
                return spam_result
        
        # Обновляем счетчик сообщений пользователя
        self._update_user_message_count(user_id)
        
        return FilterResult(False, "", "", "pass")
    
    def _check_bad_words(self, text: str) -> FilterResult:
        """Проверяет на нецензурные слова"""
        text_lower = text.lower()
        found_words = []
        
        for word in self.bad_words:
            if word in text_lower:
                found_words.append(word)
        
        if found_words:
            return FilterResult(
                is_blocked=True,
                reason="bad_words",
                details=f"Обнаружены нецензурные выражения: {', '.join(found_words[:3])}",
                severity="block"
            )
        
        return FilterResult(False, "", "", "pass")
    
    def _check_offensive_words(self, text: str) -> FilterResult:
        """Проверяет на оскорбительные слова"""
        text_lower = text.lower()
        found_words = []
        
        for word in self.offensive_words:
            if word in text_lower:
                found_words.append(word)
        
        if found_words:
            return FilterResult(
                is_blocked=True,
                reason="offensive_words",
                details=f"Обнаружены оскорбительные выражения: {', '.join(found_words[:3])}",
                severity="block"
            )
        
        return FilterResult(False, "", "", "pass")
    
    def _check_links(self, text: str) -> FilterResult:
        """Проверяет на ссылки и упоминания"""
        found_links = []
        
        for pattern in self.link_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            found_links.extend(matches)
        
        if found_links:
            return FilterResult(
                is_blocked=True,
                reason="links",
                details=f"Обнаружены ссылки или упоминания: {', '.join(found_links[:3])}",
                severity="block"
            )
        
        return FilterResult(False, "", "", "pass")
    
    def _check_spam(self, user_id: int, text: str) -> FilterResult:
        """Проверяет на спам"""
        # Проверяем паттерны спама в тексте
        for pattern in self.spam_patterns:
            if re.search(pattern, text):
                return FilterResult(
                    is_blocked=True,
                    reason="spam_pattern",
                    details="Обнаружен спам-паттерн в тексте",
                    severity="block"
                )
        
        # Проверяем частоту сообщений
        if self._is_user_spamming(user_id):
            return FilterResult(
                is_blocked=True,
                reason="spam_frequency",
                details="Слишком много сообщений за короткое время",
                severity="block"
            )
        
        return FilterResult(False, "", "", "pass")
    
    def _is_user_spamming(self, user_id: int) -> bool:
        """Проверяет, не спамит ли пользователь"""
        current_count = self.user_message_count.get(user_id, 0)
        return current_count >= self.max_messages_per_minute
    
    def _update_user_message_count(self, user_id: int):
        """Обновляет счетчик сообщений пользователя"""
        self.user_message_count[user_id] = self.user_message_count.get(user_id, 0) + 1
        
        # Сбрасываем счетчик через минуту (в реальном приложении лучше использовать Redis)
        # Здесь упрощенная логика - в реальности нужно использовать таймеры
    
    def reset_user_counters(self, user_id: int):
        """Сбрасывает счетчик сообщений пользователя"""
        self.user_message_count[user_id] = 0
    
    def add_custom_bad_word(self, word: str):
        """Добавляет кастомное нецензурное слово"""
        self.bad_words.add(word.lower())
    
    def add_custom_offensive_word(self, word: str):
        """Добавляет кастомное оскорбительное слово"""
        self.offensive_words.add(word.lower())
    
    def remove_custom_word(self, word: str, word_type: str = "bad"):
        """Удаляет кастомное слово"""
        word = word.lower()
        if word_type == "bad":
            self.bad_words.discard(word)
        elif word_type == "offensive":
            self.offensive_words.discard(word)

# Глобальный экземпляр фильтра
message_filter = MessageFilter()

def get_message_filter() -> MessageFilter:
    """Возвращает глобальный экземпляр фильтра сообщений"""
    return message_filter
