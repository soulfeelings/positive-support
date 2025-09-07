-- Инициализация базы данных для Positive Support Bot
-- Этот файл выполняется при первом запуске PostgreSQL контейнера

-- Создание базы данных если она не существует
-- (PostgreSQL в Docker уже создает БД из POSTGRES_DB)

-- Установка кодировки
ALTER DATABASE support_bot SET client_encoding TO 'utf8';
ALTER DATABASE support_bot SET default_text_search_config TO 'pg_catalog.russian';

-- Создание расширений
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Создание таблиц для системы достижений
CREATE TABLE IF NOT EXISTS achievements (
    id VARCHAR(50) PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    description TEXT NOT NULL,
    type VARCHAR(50) NOT NULL,
    condition_data JSONB NOT NULL,
    icon VARCHAR(10) NOT NULL DEFAULT '🏆',
    created_at TIMESTAMP DEFAULT NOW()
);

-- Таблица достижений пользователей
CREATE TABLE IF NOT EXISTS user_achievements (
    id SERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL,
    achievement_id VARCHAR(50) NOT NULL,
    earned_at TIMESTAMP NOT NULL DEFAULT NOW(),
    FOREIGN KEY (achievement_id) REFERENCES achievements(id) ON DELETE CASCADE,
    UNIQUE(user_id, achievement_id)
);


-- Индексы для оптимизации
CREATE INDEX IF NOT EXISTS idx_user_achievements_user_id ON user_achievements(user_id);
CREATE INDEX IF NOT EXISTS idx_user_achievements_achievement_id ON user_achievements(achievement_id);
CREATE INDEX IF NOT EXISTS idx_user_achievements_earned_at ON user_achievements(earned_at);

-- Вставка базовых достижений
INSERT INTO achievements (id, name, description, type, condition_data, icon) VALUES
-- Первая помощь
('first_help_1', '🆘 Первая помощь', 'Помогли кому-то в первый раз', 'first_help', '{"action": "help_given", "count": 1}', '🆘'),

-- Рейтинговые вехи
('rating_10', '🥉 Бронзовый помощник', 'Достигли рейтинга 10', 'rating_milestone', '{"action": "rating_reached", "value": 10}', '🥉'),
('rating_50', '🥈 Серебряный помощник', 'Достигли рейтинга 50', 'rating_milestone', '{"action": "rating_reached", "value": 50}', '🥈'),
('rating_100', '🥇 Золотой помощник', 'Достигли рейтинга 100', 'rating_milestone', '{"action": "rating_reached", "value": 100}', '🥇'),
('rating_500', '💎 Алмазный помощник', 'Достигли рейтинга 500', 'rating_milestone', '{"action": "rating_reached", "value": 500}', '💎'),
('rating_1000', '👑 Король помощи', 'Достигли рейтинга 1000', 'rating_milestone', '{"action": "rating_reached", "value": 1000}', '👑'),

-- Отправленные сообщения
('messages_10', '💬 Общительный', 'Отправили 10 сообщений поддержки', 'messages_sent', '{"action": "messages_sent", "count": 10}', '💬'),
('messages_50', '📢 Голос поддержки', 'Отправили 50 сообщений поддержки', 'messages_sent', '{"action": "messages_sent", "count": 50}', '📢'),
('messages_100', '📣 Мегафон добра', 'Отправили 100 сообщений поддержки', 'messages_sent', '{"action": "messages_sent", "count": 100}', '📣'),
('messages_500', '📡 Радио поддержки', 'Отправили 500 сообщений поддержки', 'messages_sent', '{"action": "messages_sent", "count": 500}', '📡'),

-- Особые достижения
('first_day', '🎉 Добро пожаловать!', 'Зарегистрировались в боте', 'special', '{"action": "registration"}', '🎉'),
('top_1', '🏆 Чемпион', 'Заняли первое место в рейтинге', 'special', '{"action": "top_position", "position": 1}', '🏆'),
('helper_1000', '🎖️ Мастер помощи', 'Помогли 1000 людям', 'special', '{"action": "help_given", "count": 1000}', '🎖️')

ON CONFLICT (id) DO NOTHING;

-- Логирование
\echo 'Инициализация базы данных завершена'
