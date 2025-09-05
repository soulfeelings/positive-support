import re
import logging
import asyncio
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
        
        # Время последнего сообщения для каждого пользователя
        self.user_last_message_time: Dict[int, float] = {}
        
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
        
        logger.info(f"🔍 Проверяем сообщение пользователя {user_id}: '{text[:50]}...'")
        
        # Сначала проверяем слова-исключения
        text_lower = text.lower()
        for exception_word in self.exception_words:
            if exception_word in text_lower:
                logger.info(f"✅ Слово-исключение найдено: '{exception_word}'")
                return FilterResult(False, "", "", "pass")
        
        # Проверяем на мат (если включено)
        if self.settings.get("enable_bad_words_check", True):
            mat_result = self._check_bad_words(text)
            if mat_result.is_blocked:
                logger.warning(f"🚫 Мат обнаружен: {mat_result.details}")
                return mat_result
        
        # Проверяем на оскорбления (если включено)
        if self.settings.get("enable_offensive_words_check", True):
            offensive_result = self._check_offensive_words(text)
            if offensive_result.is_blocked:
                logger.warning(f"🚫 Оскорбление обнаружено: {offensive_result.details}")
                return offensive_result
        
        # Проверяем на ссылки (если включено)
        if self.settings.get("enable_links_check", True):
            link_result = self._check_links(text)
            if link_result.is_blocked:
                logger.warning(f"🚫 Ссылка обнаружена: {link_result.details}")
                return link_result
        
        # Проверяем на спам (если включено)
        if self.settings.get("enable_spam_check", True):
            spam_result = self._check_spam(user_id, text)
            if spam_result.is_blocked:
                logger.warning(f"🚫 Спам обнаружен: {spam_result.details}")
                return spam_result
        
        # Обновляем счетчик сообщений пользователя
        self._update_user_message_count(user_id)
        
        logger.info(f"✅ Сообщение прошло проверку")
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
        spam_check = self._check_spam_frequency(user_id)
        if spam_check["is_spamming"]:
            return FilterResult(
                is_blocked=True,
                reason="spam_frequency",
                details=spam_check["message"],
                severity="block"
            )
        
        return FilterResult(False, "", "", "pass")
    
    def _check_spam_frequency(self, user_id: int) -> dict:
        """Проверяет частоту сообщений и возвращает детальную информацию"""
        import time
        current_time = time.time()
        
        # Проверяем, прошла ли минута с последнего сообщения
        last_message_time = self.user_last_message_time.get(user_id, 0)
        if current_time - last_message_time >= 60:  # 60 секунд = 1 минута
            # Сбрасываем счетчик, если прошла минута
            self.user_message_count[user_id] = 0
            self.user_last_message_time[user_id] = current_time
            return {"is_spamming": False, "message": ""}
        
        current_count = self.user_message_count.get(user_id, 0)
        if current_count >= self.max_messages_per_minute:
            # Вычисляем оставшееся время
            time_remaining = 60 - (current_time - last_message_time)
            minutes = int(time_remaining // 60)
            seconds = int(time_remaining % 60)
            
            if minutes > 0:
                time_str = f"{minutes}м {seconds}с"
            else:
                time_str = f"{seconds}с"
            
            return {
                "is_spamming": True,
                "message": f"Слишком много сообщений за короткое время. Попробуйте через {time_str}"
            }
        
        return {"is_spamming": False, "message": ""}
    
    def _is_user_spamming(self, user_id: int) -> bool:
        """Проверяет, не спамит ли пользователь"""
        import time
        current_time = time.time()
        
        # Проверяем, прошла ли минута с последнего сообщения
        last_message_time = self.user_last_message_time.get(user_id, 0)
        if current_time - last_message_time >= 60:  # 60 секунд = 1 минута
            # Сбрасываем счетчик, если прошла минута
            self.user_message_count[user_id] = 0
            self.user_last_message_time[user_id] = current_time
            return False
        
        current_count = self.user_message_count.get(user_id, 0)
        return current_count >= self.max_messages_per_minute
    
    def _update_user_message_count(self, user_id: int):
        """Обновляет счетчик сообщений пользователя"""
        import time
        current_time = time.time()
        
        # Проверяем, прошла ли минута с последнего сообщения
        last_message_time = self.user_last_message_time.get(user_id, 0)
        if current_time - last_message_time >= 60:  # 60 секунд = 1 минута
            # Сбрасываем счетчик, если прошла минута
            self.user_message_count[user_id] = 0
        
        # Обновляем счетчик и время
        self.user_message_count[user_id] = self.user_message_count.get(user_id, 0) + 1
        self.user_last_message_time[user_id] = current_time
    
    def reset_user_counters(self, user_id: int):
        """Сбрасывает счетчик сообщений пользователя"""
        self.user_message_count[user_id] = 0
        self.user_last_message_time[user_id] = 0
    
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
    
    def _start_cleanup_task(self):
        """Запускает задачу периодической очистки счетчиков"""
        try:
            # Создаем задачу очистки, если она еще не создана
            if not hasattr(self, '_cleanup_task') or self._cleanup_task.done():
                self._cleanup_task = asyncio.create_task(self._cleanup_counters())
        except Exception as e:
            logger.error(f"Ошибка при запуске задачи очистки счетчиков: {e}")
    
    async def _cleanup_counters(self):
        """Периодически очищает счетчики пользователей"""
        import time
        while True:
            try:
                await asyncio.sleep(60)  # Проверяем каждую минуту
                current_time = time.time()
                
                # Удаляем счетчики пользователей, которые не писали больше минуты
                users_to_remove = []
                for user_id, last_time in self.user_last_message_time.items():
                    if current_time - last_time >= 60:  # 60 секунд
                        users_to_remove.append(user_id)
                
                # Удаляем неактивных пользователей
                for user_id in users_to_remove:
                    self.user_message_count.pop(user_id, None)
                    self.user_last_message_time.pop(user_id, None)
                
                if users_to_remove:
                    logger.info(f"Очищены счетчики для {len(users_to_remove)} неактивных пользователей")
                    
            except Exception as e:
                logger.error(f"Ошибка в задаче очистки счетчиков: {e}")
                await asyncio.sleep(60)  # Ждем минуту перед следующей попыткой

# Глобальный экземпляр фильтра
message_filter = MessageFilter()

def get_message_filter() -> MessageFilter:
    """Возвращает глобальный экземпляр фильтра сообщений"""
    return message_filter
