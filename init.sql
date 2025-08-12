CREATE TABLE IF NOT EXISTS users (
    user_id BIGINT PRIMARY KEY,
    nickname TEXT UNIQUE NOT NULL
);

CREATE TABLE IF NOT EXISTS support_messages (
    id SERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    message_text TEXT,
    file_id TEXT,
    type TEXT NOT NULL CHECK (type IN ('text', 'voice')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS user_received_messages (
    id SERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL,
    message_id INT NOT NULL REFERENCES support_messages(id) ON DELETE CASCADE,
    received_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (user_id, message_id)
);


