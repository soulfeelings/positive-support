"""
Конфигурация фильтра сообщений

Здесь можно настроить правила фильтрации, добавить/убрать слова и изменить параметры
"""

# Настройки фильтра
FILTER_SETTINGS = {
    # Максимальное количество сообщений в минуту
    "max_messages_per_minute": 5,
    
    # Включить/выключить различные типы проверок
    "enable_bad_words_check": True,
    "enable_offensive_words_check": True,
    "enable_links_check": True,
    "enable_spam_check": False,  # Временно отключена блокировка за спам
    
    # Строгость фильтра (low, medium, high)
    "filter_strictness": "medium"
}

# Нецензурные слова (русский и английский)
BAD_WORDS = {
    'блять', 'хуй', 'пизда', 'ебать', 'сука', 'говно', 'заебал', 'нахуй',
    'fuck', 'shit', 'bitch', 'asshole', 'damn', 'hell', 'crap', 'piss',
    'хуя', 'пиздец', 'ебись', 'сучара', 'говнюк', 'заебись', 'нахуя',
    'fucking', 'shitty', 'bitchy', 'ass', 'damned', 'hellish'
}

# Оскорбительные слова
OFFENSIVE_WORDS = {
    'идиот', 'дебил', 'тупой', 'дурак', 'кретин', 'придурок', 'козел',
    'idiot', 'stupid', 'dumb', 'fool', 'moron', 'retard', 'ass',
    'тупица', 'болван', 'балбес', 'простофиля', 'недоумок', 'дегенерат',
    'stupid', 'idiotic', 'moronic', 'retarded', 'brainless'
}

# Паттерны для ссылок и упоминаний
LINK_PATTERNS = [
    r'https?://[^\s]+',
    r'www\.[^\s]+',
    r't\.me/[^\s]+',
    r'@[a-zA-Z0-9_]{5,}',
    r'#[a-zA-Z0-9_]+',
    r'bit\.ly/[^\s]+',
    r'tinyurl\.com/[^\s]+',
    r'goo\.gl/[^\s]+',
    r'youtu\.be/[^\s]+',
    r'instagram\.com/[^\s]+',
    r'facebook\.com/[^\s]+',
    r'twitter\.com/[^\s]+',
    r'vk\.com/[^\s]+',
    r'telegram\.me/[^\s]+'
]

# Паттерны для спама
SPAM_PATTERNS = [
    r'(.)\1{6,}',  # Повторяющиеся символы (7+ раз)
    r'[A-ZА-Я]{15,}',  # ВСЕ ЗАГЛАВНЫЕ БУКВЫ (15+ символов)
    r'[!?]{5,}',  # Множественные знаки препинания (5+ раз)
    r'[^\w\s]{12,}',  # Много специальных символов (12+ символов)
    r'(?:[а-яё]{1,2}\s*){20,}',  # Короткие слова подряд (20+ слов)
    r'(?:[a-z]{1,2}\s*){20,}',  # Короткие английские слова подряд (20+ слов)
]

# Слова-исключения (не будут блокироваться)
EXCEPTION_WORDS = {
    'помощь', 'поддержка', 'спасибо', 'благодарю', 'хорошо', 'плохо',
    'нужна', 'нужен', 'нужно', 'понял', 'поняла', 'понятно', 'ясно',
    'help', 'support', 'thanks', 'good', 'bad', 'okay', 'fine',
    'need', 'want', 'understand', 'clear', 'got', 'got it'
}

# Настройки для разных уровней строгости
STRICTNESS_LEVELS = {
    "low": {
        "max_messages_per_minute": 10,
        "enable_offensive_words_check": False,
        "enable_spam_check": False
    },
    "medium": {
        "max_messages_per_minute": 5,
        "enable_offensive_words_check": True,
        "enable_spam_check": True
    },
    "high": {
        "max_messages_per_minute": 3,
        "enable_offensive_words_check": True,
        "enable_spam_check": True
    }
}

def get_filter_settings():
    """Возвращает настройки фильтра с учетом уровня строгости"""
    strictness = FILTER_SETTINGS.get("filter_strictness", "medium")
    strictness_settings = STRICTNESS_LEVELS.get(strictness, STRICTNESS_LEVELS["medium"])
    
    # Объединяем базовые настройки с настройками уровня строгости
    settings = FILTER_SETTINGS.copy()
    settings.update(strictness_settings)
    
    return settings

def get_bad_words():
    """Возвращает список нецензурных слов"""
    return BAD_WORDS.copy()

def get_offensive_words():
    """Возвращает список оскорбительных слов"""
    return OFFENSIVE_WORDS.copy()

def get_link_patterns():
    """Возвращает паттерны для ссылок"""
    return LINK_PATTERNS.copy()

def get_spam_patterns():
    """Возвращает паттерны для спама"""
    return SPAM_PATTERNS.copy()

def get_exception_words():
    """Возвращает слова-исключения"""
    return EXCEPTION_WORDS.copy()
