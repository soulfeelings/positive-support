CREATE TABLE IF NOT EXISTS users (
    user_id BIGINT PRIMARY KEY,
    nickname TEXT UNIQUE NOT NULL,
    photo_url TEXT,
    city TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Safe migrations for existing DBs (no-op if columns already exist)
ALTER TABLE users ADD COLUMN IF NOT EXISTS photo_url TEXT;
ALTER TABLE users ADD COLUMN IF NOT EXISTS city TEXT;
ALTER TABLE users ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ NOT NULL DEFAULT NOW();

CREATE TABLE IF NOT EXISTS support_messages (
    id SERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    message_text TEXT,
    file_id TEXT,
    type TEXT NOT NULL CHECK (type IN ('text', 'voice')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_support_messages_user_id ON support_messages(user_id);

CREATE TABLE IF NOT EXISTS user_received_messages (
    id SERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL,
    message_id INT NOT NULL REFERENCES support_messages(id) ON DELETE CASCADE,
    received_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (user_id, message_id)
);


