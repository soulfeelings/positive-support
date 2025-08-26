import asyncpg
import asyncio
import os

# Настройки подключения из переменных окружения
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", "5432"))
DB_USER = os.getenv("DB_USER", "bot_user")
DB_PASSWORD = os.getenv("DB_PASSWORD", "8998")
DB_NAME = os.getenv("DB_NAME", "support_bot")

async def setup_database():
    print("Настройка базы данных...")
    
    try:
        # Подключаемся к базе данных (предполагаем что база уже создана)
        print("Подключение к PostgreSQL...")
        conn = await asyncpg.connect(
            host=DB_HOST, port=DB_PORT,
            user=DB_USER, password=DB_PASSWORD,
            database=DB_NAME
        )
        
        print("Создание таблиц...")
        
        # Создаем таблицы
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id BIGINT PRIMARY KEY,
                nickname VARCHAR(50) UNIQUE NOT NULL,
                is_blocked BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT NOW()
            )
        """)
        
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id SERIAL PRIMARY KEY,
                user_id BIGINT REFERENCES users(user_id),
                text TEXT,
                file_id TEXT,
                message_type VARCHAR(20) NOT NULL DEFAULT 'text' CHECK (message_type IN ('text', 'voice', 'video_note')),
                type VARCHAR(20) NOT NULL CHECK (type IN ('support', 'request')),
                created_at TIMESTAMP DEFAULT NOW()
            )
        """)
        
        # Создаем таблицу жалоб
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS complaints (
                id SERIAL PRIMARY KEY,
                message_id INTEGER,
                original_user_id BIGINT,
                complainer_user_id BIGINT REFERENCES users(user_id),
                text TEXT,
                file_id TEXT,
                message_type VARCHAR(20) NOT NULL DEFAULT 'text' CHECK (message_type IN ('text', 'voice', 'video_note')),
                created_at TIMESTAMP DEFAULT NOW(),
                complaint_date TIMESTAMP DEFAULT NOW()
            )
        """)
        
        # Создаем таблицу рейтингов
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS ratings (
                user_id BIGINT PRIMARY KEY REFERENCES users(user_id),
                rating INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT NOW(),
                updated_at TIMESTAMP DEFAULT NOW()
            )
        """)
        
        # Добавляем недостающие столбцы в существующие таблицы
        try:
            await conn.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS is_blocked BOOLEAN DEFAULT FALSE")
            print("✅ Столбец is_blocked добавлен в таблицу users")
        except Exception as e:
            print(f"ℹ️ Столбец is_blocked уже существует: {e}")
        
        # Добавляем поля для напоминаний
        try:
            await conn.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS reminders_enabled BOOLEAN DEFAULT TRUE")
            print("✅ Столбец reminders_enabled добавлен в таблицу users")
        except Exception as e:
            print(f"ℹ️ Столбец reminders_enabled уже существует: {e}")
        
        try:
            await conn.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS last_reminder_message_id INTEGER DEFAULT 0")
            print("✅ Столбец last_reminder_message_id добавлен в таблицу users")
        except Exception as e:
            print(f"ℹ️ Столбец last_reminder_message_id уже существует: {e}")
        
        # Создаем индексы
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_messages_type ON messages(type)")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_messages_user_id ON messages(user_id)")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_complaints_original_user_id ON complaints(original_user_id)")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_complaints_complainer_user_id ON complaints(complainer_user_id)")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_users_blocked ON users(is_blocked)")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_ratings_user_id ON ratings(user_id)")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_ratings_rating ON ratings(rating)")
        
        await conn.close()
        print("✅ Таблицы созданы/обновлены успешно!")
        
        # Проверяем подключение
        print("Проверка подключения...")
        conn = await asyncpg.connect(
            host=DB_HOST, port=DB_PORT,
            user=DB_USER, password=DB_PASSWORD,
            database=DB_NAME
        )
        
        result = await conn.fetchval("SELECT 1")
        await conn.close()
        
        if result == 1:
            print("✅ База данных настроена и работает!")
        else:
            print("❌ Ошибка проверки базы данных")
            
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        print("\nВозможные причины:")
        print("1. PostgreSQL не запущен")
        print("2. Неверный пароль (измените DB_PASSWORD в этом файле)")
        print("3. PostgreSQL не установлен")
        return False
    
    return True

async def main():
    success = await setup_database()
    if success:
        print("\n🎉 Готово! Теперь можно запускать бота")
    else:
        print("\n❌ Настройка не завершена. Исправьте ошибки и попробуйте снова")

if __name__ == "__main__":
    asyncio.run(main())
