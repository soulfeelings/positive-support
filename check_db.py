import asyncpg
import asyncio

# Настройки подключения (измените пароль на свой)
DB_HOST = "localhost"
DB_PORT = 5432
DB_USER = "postgres"
DB_PASSWORD = "8998"  # Замените на ваш пароль
DB_NAME = "support_bot"

async def check_database():
    """Проверка содержимого базы данных"""
    try:
        conn = await asyncpg.connect(
            host=DB_HOST, port=DB_PORT,
            user=DB_USER, password=DB_PASSWORD,
            database=DB_NAME
        )
        
        print("🔍 Проверка базы данных...")
        print("=" * 50)
        
        # Проверяем пользователей
        users = await conn.fetch("SELECT user_id, nickname, created_at FROM users ORDER BY created_at")
        print(f"👥 Пользователи ({len(users)}):")
        for user in users:
            print(f"  • {user['nickname']} (ID: {user['user_id']}) - {user['created_at']}")
        
        print()
        
        # Проверяем сообщения поддержки
        support_msgs = await conn.fetch("""
            SELECT m.id, m.text, m.message_type, u.nickname, m.created_at 
            FROM messages m 
            JOIN users u ON m.user_id = u.user_id 
            WHERE m.type = 'support' 
            ORDER BY m.created_at DESC
        """)
        print(f"💝 Сообщения поддержки ({len(support_msgs)}):")
        for msg in support_msgs:
            text = msg['text'][:50] + "..." if msg['text'] and len(msg['text']) > 50 else msg['text']
            msg_type = "🎤" if msg['message_type'] == 'voice' else "📝"
            print(f"  • {msg_type} {msg['nickname']}: {text or '[голосовое]'}")
        
        print()
        
        # Проверяем запросы помощи
        help_requests = await conn.fetch("""
            SELECT m.id, m.text, m.message_type, u.nickname, m.created_at 
            FROM messages m 
            JOIN users u ON m.user_id = u.user_id 
            WHERE m.type = 'request' 
            ORDER BY m.created_at DESC
        """)
        print(f"🆘 Запросы помощи ({len(help_requests)}):")
        for req in help_requests:
            text = req['text'][:50] + "..." if req['text'] and len(req['text']) > 50 else req['text']
            msg_type = "🎤" if req['message_type'] == 'voice' else "📝"
            print(f"  • {msg_type} {req['nickname']}: {text or '[голосовое]'}")
        
        print()
        
        # Проверяем активные запросы (которые еще не получили ответ)
        print("🔍 Статус запросов помощи:")
        if help_requests:
            print(f"  • Всего создано: {len(help_requests)}")
            print("  • Все активные запросы показаны выше")
            print("  • ℹ️ Запросы удаляются после получения ответа")
        else:
            print("  • Нет активных запросов помощи")
        
        print()
        print("=" * 50)
        print(f"📊 Итого: {len(users)} пользователей, {len(support_msgs)} поддержки, {len(help_requests)} активных запросов")
        
        await conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return False

async def main():
    print("Проверка сохранности данных в базе...")
    await check_database()

if __name__ == "__main__":
    asyncio.run(main())
