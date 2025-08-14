-- Создание таблицы пользователей
CREATE TABLE IF NOT EXISTS users (
    user_id BIGINT PRIMARY KEY,
    nickname TEXT UNIQUE NOT NULL,
    photo_url TEXT,
    city TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Безопасные миграции для существующих БД (no-op если колонки уже существуют)
ALTER TABLE users ADD COLUMN IF NOT EXISTS photo_url TEXT;
ALTER TABLE users ADD COLUMN IF NOT EXISTS city TEXT;
ALTER TABLE users ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ NOT NULL DEFAULT NOW();
ALTER TABLE users ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW();

-- Создание таблицы сообщений поддержки
CREATE TABLE IF NOT EXISTS support_messages (
    id SERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    message_text TEXT,
    file_id TEXT,
    type TEXT NOT NULL CHECK (type IN ('text', 'voice')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Индексы для оптимизации запросов
CREATE INDEX IF NOT EXISTS idx_support_messages_user_id ON support_messages(user_id);
CREATE INDEX IF NOT EXISTS idx_support_messages_created_at ON support_messages(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_support_messages_type ON support_messages(type);

-- Таблица для отслеживания полученных сообщений пользователями
CREATE TABLE IF NOT EXISTS user_received_messages (
    id SERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL,
    message_id INT NOT NULL REFERENCES support_messages(id) ON DELETE CASCADE,
    received_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (user_id, message_id)
);

-- Индексы для таблицы полученных сообщений
CREATE INDEX IF NOT EXISTS idx_user_received_messages_user_id ON user_received_messages(user_id);
CREATE INDEX IF NOT EXISTS idx_user_received_messages_message_id ON user_received_messages(message_id);
CREATE INDEX IF NOT EXISTS idx_user_received_messages_received_at ON user_received_messages(received_at DESC);

-- Триггер для автоматического обновления updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Применяем триггер к таблицам
DROP TRIGGER IF EXISTS update_users_updated_at ON users;
CREATE TRIGGER update_users_updated_at 
    BEFORE UPDATE ON users 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_support_messages_updated_at ON support_messages;
CREATE TRIGGER update_support_messages_updated_at 
    BEFORE UPDATE ON support_messages 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Представление для статистики пользователей
CREATE OR REPLACE VIEW user_stats AS
SELECT 
    u.user_id,
    u.nickname,
    u.city,
    u.created_at as registered_at,
    COUNT(sm.id) as messages_sent,
    COUNT(DISTINCT urm.message_id) as messages_received,
    MAX(sm.created_at) as last_message_sent,
    MAX(urm.received_at) as last_message_received
FROM users u
LEFT JOIN support_messages sm ON u.user_id = sm.user_id
LEFT JOIN user_received_messages urm ON u.user_id = urm.user_id
GROUP BY u.user_id, u.nickname, u.city, u.created_at;

-- Добавляем некоторые начальные данные для демонстрации (если таблица пуста)
INSERT INTO users (user_id, nickname, city) 
SELECT 999999, 'Демо пользователь', 'Москва'
WHERE NOT EXISTS (SELECT 1 FROM users WHERE user_id = 999999);

INSERT INTO support_messages (user_id, message_text, type)
SELECT 999999, 'Привет! Это демо сообщение для тестирования. Надеюсь, у всех всё хорошо!', 'text'
WHERE NOT EXISTS (SELECT 1 FROM support_messages WHERE user_id = 999999);

-- Комментарии к таблицам
COMMENT ON TABLE users IS 'Таблица пользователей Telegram bot';
COMMENT ON TABLE support_messages IS 'Сообщения поддержки от пользователей';
COMMENT ON TABLE user_received_messages IS 'Отслеживание какие сообщения получил каждый пользователь';

COMMENT ON COLUMN users.user_id IS 'Telegram user ID';
COMMENT ON COLUMN users.nickname IS 'Уникальный никнейм пользователя';
COMMENT ON COLUMN support_messages.type IS 'Тип сообщения: text или voice';
COMMENT ON COLUMN support_messages.file_id IS 'Telegram file_id для голосовых сообщений';