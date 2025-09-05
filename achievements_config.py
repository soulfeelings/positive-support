# -*- coding: utf-8 -*-
"""
Конфигурация системы достижений для бота поддержки
Легко редактируемый файл с настройками всех достижений
"""

# Типы достижений
ACHIEVEMENT_TYPES = {
    "first_help": "Первая помощь",
    "rating_milestone": "Рейтинговые вехи",
    "messages_sent": "Отправленные сообщения",
    "special": "Особые достижения"
}

# Конфигурация достижений
ACHIEVEMENTS = {
    # Первая помощь
    "first_help_1": {
        "id": "first_help_1",
        "name": "🆘 Первая помощь",
        "description": "Помогли кому-то в первый раз",
        "type": "first_help",
        "condition": {"action": "help_given", "count": 1},
        "icon": "🆘"
    },
    
    # Рейтинговые вехи
    "rating_10": {
        "id": "rating_10",
        "name": "🥉 Бронзовый помощник",
        "description": "Достигли рейтинга 10",
        "type": "rating_milestone", 
        "condition": {"action": "rating_reached", "value": 10},
        "icon": "🥉"
    },
    
    "rating_50": {
        "id": "rating_50",
        "name": "🥈 Серебряный помощник", 
        "description": "Достигли рейтинга 50",
        "type": "rating_milestone",
        "condition": {"action": "rating_reached", "value": 50},
        "icon": "🥈"
    },
    
    "rating_100": {
        "id": "rating_100",
        "name": "🥇 Золотой помощник",
        "description": "Достигли рейтинга 100", 
        "type": "rating_milestone",
        "condition": {"action": "rating_reached", "value": 100},
        "icon": "🥇"
    },
    
    "rating_500": {
        "id": "rating_500",
        "name": "💎 Алмазный помощник",
        "description": "Достигли рейтинга 500",
        "type": "rating_milestone", 
        "condition": {"action": "rating_reached", "value": 500},
        "icon": "💎"
    },
    
    "rating_1000": {
        "id": "rating_1000",
        "name": "👑 Король помощи",
        "description": "Достигли рейтинга 1000",
        "type": "rating_milestone",
        "condition": {"action": "rating_reached", "value": 1000}, 
        "icon": "👑"
    },
    
    # Отправленные сообщения
    "messages_10": {
        "id": "messages_10",
        "name": "💬 Общительный",
        "description": "Отправили 10 сообщений поддержки",
        "type": "messages_sent",
        "condition": {"action": "messages_sent", "count": 10},
        "icon": "💬"
    },
    
    "messages_50": {
        "id": "messages_50", 
        "name": "📢 Голос поддержки",
        "description": "Отправили 50 сообщений поддержки",
        "type": "messages_sent",
        "condition": {"action": "messages_sent", "count": 50},
        "icon": "📢"
    },
    
    "messages_100": {
        "id": "messages_100",
        "name": "📣 Мегафон добра", 
        "description": "Отправили 100 сообщений поддержки",
        "type": "messages_sent",
        "condition": {"action": "messages_sent", "count": 100},
        "icon": "📣"
    },
    
    "messages_500": {
        "id": "messages_500",
        "name": "📡 Радио поддержки",
        "description": "Отправили 500 сообщений поддержки", 
        "type": "messages_sent",
        "condition": {"action": "messages_sent", "count": 500},
        "icon": "📡"
    },
    
    # Особые достижения
    "first_day": {
        "id": "first_day",
        "name": "🎉 Добро пожаловать!",
        "description": "Зарегистрировались в боте",
        "type": "special",
        "condition": {"action": "registration"},
        "icon": "🎉"
    },
    
    "perfect_reputation": {
        "id": "perfect_reputation", 
        "name": "✨ Идеальная репутация",
        "description": "Никогда не получали жалоб",
        "type": "special",
        "condition": {"action": "no_complaints", "rating": 50},
        "icon": "✨"
    },
    
    "top_1": {
        "id": "top_1",
        "name": "🏆 Чемпион",
        "description": "Заняли первое место в рейтинге",
        "type": "special", 
        "condition": {"action": "top_position", "position": 1},
        "icon": "🏆"
    },
    
    "helper_1000": {
        "id": "helper_1000",
        "name": "🎖️ Мастер помощи",
        "description": "Помогли 1000 людям",
        "type": "special",
        "condition": {"action": "help_given", "count": 1000},
        "icon": "🎖️"
    }
}


def get_achievement_by_id(achievement_id: str) -> dict:
    """Получить достижение по ID"""
    return ACHIEVEMENTS.get(achievement_id)

def get_achievements_by_type(achievement_type: str) -> list:
    """Получить все достижения определенного типа"""
    return [achievement for achievement in ACHIEVEMENTS.values() 
            if achievement["type"] == achievement_type]

def get_all_achievements() -> dict:
    """Получить все достижения"""
    return ACHIEVEMENTS

def get_achievement_types() -> dict:
    """Получить типы достижений"""
    return ACHIEVEMENT_TYPES

