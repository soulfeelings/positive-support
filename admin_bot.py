import os
import asyncio
import logging
import aiohttp
import asyncpg
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Конфигурация бота
ADMIN_BOT_TOKEN = os.getenv("ADMIN_BOT_TOKEN", "")
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

# Список ID администраторов (добавьте свой Telegram ID)
ADMIN_IDS = [
    int(os.getenv("ADMIN_ID", "0")),  # Основной админ из переменной окружения
    # Можно добавить еще администраторов:
    # 123456789,  # ID второго админа
    # 987654321,  # ID третьего админа
]

# Конфигурация БД
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", "5432"))
DB_USER = os.getenv("DB_USER", "bot_user")
DB_PASSWORD = os.getenv("DB_PASSWORD", "8998")
DB_NAME = os.getenv("DB_NAME", "support_bot")

if not ADMIN_BOT_TOKEN:
    logger.error("ADMIN_BOT_TOKEN not set!")
    exit(1)

logger.info(f"🔧 Admin Bot starting with token: {ADMIN_BOT_TOKEN[:10]}...")
logger.info(f"👥 Admin IDs: {ADMIN_IDS}")

bot = Bot(token=ADMIN_BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

class AdminStates(StatesGroup):
    waiting_nickname = State()
    viewing_user_info = State()

async def get_db_connection():
    """Подключение к БД"""
    try:
        conn = await asyncpg.connect(
            host=DB_HOST, port=DB_PORT,
            user=DB_USER, password=DB_PASSWORD,
            database=DB_NAME
        )
        return conn
    except Exception as e:
        logger.error(f"❌ Database connection failed: {e}")
        raise

async def is_admin(user_id: int) -> bool:
    """Проверка является ли пользователь администратором"""
    return user_id in ADMIN_IDS

def escape_markdown(text: str) -> str:
    """Экранирует специальные символы для Markdown"""
    if not text:
        return text
    return text.replace('_', '\\_').replace('*', '\\*').replace('[', '\\[').replace(']', '\\]').replace('`', '\\`')

def get_unblock_keyboard(user_id: int):
    """Создает клавиатуру для разблокировки"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Разблокировать", callback_data=f"unblock_{user_id}"),
            InlineKeyboardButton(text="❌ Оставить блокировку", callback_data=f"keep_block_{user_id}")
        ],
        [
            InlineKeyboardButton(text="🔄 Поиск другого пользователя", callback_data="new_search")
        ]
    ])

async def api_request(endpoint: str, data: dict):
    """HTTP запрос к API"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(f"{BACKEND_URL}/{endpoint}", json=data) as response:
                if response.status != 200:
                    logger.error(f"API returned status {response.status} for {endpoint}")
                    return {"status": "error", "message": f"HTTP {response.status}"}
                result = await response.json()
                return result
    except Exception as e:
        logger.error(f"API error for {endpoint}: {e}")
        return {"status": "error", "message": str(e)}

@dp.message(Command("start"))
async def start(message: types.Message, state: FSMContext):
    """Команда старт для админ-бота"""
    await state.clear()
    user_id = message.from_user.id
    
    if not await is_admin(user_id):
        await message.answer("❌ У вас нет доступа к админ-панели")
        return
    
    welcome_text = """🔧 **Админ-панель для разблокировки пользователей**

🛡️ **Что умеет этот бот:**
• Поиск заблокированных пользователей по никнейму
• Просмотр истории жалоб на пользователя
• Просмотр сообщений за которые получена блокировка
• Разблокировка пользователей

📝 **Как использовать:**
1. Введите команду /search и никнейм пользователя
2. Просмотрите причины блокировки
3. Примите решение о разблокировке

🎯 **Команды:**
• /search - поиск пользователя для разблокировки
• /stats - статистика заблокированных пользователей
• /help - справка"""
    
    await message.answer(welcome_text, parse_mode='Markdown')

@dp.message(Command("search"))
async def search_command(message: types.Message, state: FSMContext):
    """Команда поиска пользователя"""
    user_id = message.from_user.id
    
    if not await is_admin(user_id):
        await message.answer("❌ У вас нет доступа к админ-панели")
        return
    
    await state.clear()
    await message.answer("🔍 **Поиск пользователя для разблокировки**\n\nВведите никнейм пользователя:", parse_mode='Markdown')
    await state.set_state(AdminStates.waiting_nickname)

@dp.message(AdminStates.waiting_nickname)
async def handle_nickname_search(message: types.Message, state: FSMContext):
    """Обработка поиска по никнейму"""
    user_id = message.from_user.id
    
    if not await is_admin(user_id):
        await message.answer("❌ У вас нет доступа к админ-панели")
        await state.clear()
        return
    
    nickname = message.text.strip()
    
    try:
        conn = await get_db_connection()
        
        # Ищем пользователя по никнейму
        user = await conn.fetchrow(
            "SELECT user_id, nickname, is_blocked, created_at FROM users WHERE nickname ILIKE $1", 
            f"%{nickname}%"
        )
        
        if not user:
            await message.answer(f"❌ Пользователь с никнеймом '{nickname}' не найден")
            await conn.close()
            return
        
        user_info_id = user['user_id']
        user_nickname = user['nickname']
        is_blocked = user['is_blocked']
        created_at = user['created_at']
        
        # Получаем жалобы на пользователя
        complaints = await conn.fetch("""
            SELECT id, message_id, complainer_user_id, text, file_id, message_type, complaint_date,
                   u.nickname as complainer_nickname
            FROM complaints c
            LEFT JOIN users u ON c.complainer_user_id = u.user_id
            WHERE c.original_user_id = $1
            ORDER BY c.complaint_date DESC
        """, user_info_id)
        
        # Получаем количество жалоб
        complaints_count = len(complaints)
        
        await conn.close()
        
        # Формируем информацию о пользователе
        safe_nickname = escape_markdown(user_nickname)
        status = "🚫 **ЗАБЛОКИРОВАН**" if is_blocked else "✅ **Активен**"
        
        info_text = f"""👤 **Информация о пользователе**

📛 **Никнейм:** {safe_nickname}
🆔 **ID:** `{user_info_id}`
📊 **Статус:** {status}
📅 **Зарегистрирован:** {created_at.strftime('%d.%m.%Y %H:%M')}
🚨 **Жалоб получено:** {complaints_count}"""
        
        if complaints_count > 0:
            info_text += "\n\n📋 **Последние жалобы:**"
            
            for i, complaint in enumerate(complaints[:5]):  # Показываем последние 5 жалоб
                complaint_date = complaint['complaint_date'].strftime('%d.%m.%Y %H:%M')
                complainer_nick = complaint['complainer_nickname'] or f"ID:{complaint['complainer_user_id']}"
                
                if complaint['message_type'] == 'voice':
                    content_type = "🎤 Голосовое"
                    content = complaint['text'][:50] + "..." if complaint['text'] and len(complaint['text']) > 50 else "[голосовое сообщение]"
                elif complaint['message_type'] == 'video_note':
                    content_type = "🎥 Видео"
                    content = complaint['text'][:50] + "..." if complaint['text'] and len(complaint['text']) > 50 else "[видео кружок]"
                else:
                    content_type = "📝 Текст"
                    content = complaint['text'][:100] + "..." if complaint['text'] and len(complaint['text']) > 100 else complaint['text'] or "[текст сообщения]"
                
                safe_content = escape_markdown(content)
                safe_complainer = escape_markdown(complainer_nick)
                
                info_text += f"\n\n**{i+1}.** {content_type} ({complaint_date})"
                info_text += f"\n   _Жалоба от:_ {safe_complainer}"
                info_text += f"\n   _Содержание:_ {safe_content}"
        
        if not is_blocked:
            info_text += "\n\n✅ **Пользователь не заблокирован**"
            await message.answer(info_text, parse_mode='Markdown')
        else:
            info_text += f"\n\n🚫 **Пользователь заблокирован**"
            if complaints_count >= 5:
                info_text += "\n⚠️ _Автоматическая блокировка за превышение лимита жалоб_"
            
            await message.answer(info_text, parse_mode='Markdown', reply_markup=get_unblock_keyboard(user_info_id))
        
        await state.set_state(AdminStates.viewing_user_info)
        await state.update_data(user_id=user_info_id, nickname=user_nickname)
        
    except Exception as e:
        logger.error(f"Error searching user: {e}")
        await message.answer("❌ Ошибка при поиске пользователя")
        await state.clear()

@dp.callback_query(F.data.startswith("unblock_"))
async def handle_unblock(callback: types.CallbackQuery, state: FSMContext):
    """Обработка разблокировки пользователя"""
    if not await is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет доступа")
        return
    
    user_id_to_unblock = int(callback.data.split("_")[1])
    
    try:
        conn = await get_db_connection()
        
        # Получаем информацию о пользователе
        user = await conn.fetchrow(
            "SELECT nickname, is_blocked FROM users WHERE user_id = $1", 
            user_id_to_unblock
        )
        
        if not user:
            await callback.message.edit_text("❌ Пользователь не найден")
            await callback.answer()
            await conn.close()
            return
        
        if not user['is_blocked']:
            await callback.message.edit_text("✅ Пользователь уже разблокирован")
            await callback.answer()
            await conn.close()
            return
        
        # Разблокируем пользователя
        await conn.execute(
            "UPDATE users SET is_blocked = FALSE WHERE user_id = $1", 
            user_id_to_unblock
        )
        
        await conn.close()
        
        safe_nickname = escape_markdown(user['nickname'])
        success_text = f"""✅ **Пользователь разблокирован**

👤 **Никнейм:** {safe_nickname}
🆔 **ID:** `{user_id_to_unblock}`
👨‍💼 **Разблокирован администратором:** {escape_markdown(callback.from_user.first_name or 'Админ')}

🎉 Пользователь может снова пользоваться ботом"""
        
        await callback.message.edit_text(success_text, parse_mode='Markdown')
        await callback.answer("✅ Пользователь разблокирован")
        
        logger.info(f"Admin {callback.from_user.id} unblocked user {user_id_to_unblock} ({user['nickname']})")
        
    except Exception as e:
        logger.error(f"Error unblocking user: {e}")
        await callback.message.edit_text("❌ Ошибка при разблокировке")
        await callback.answer()
    
    await state.clear()

@dp.callback_query(F.data.startswith("keep_block_"))
async def handle_keep_block(callback: types.CallbackQuery, state: FSMContext):
    """Обработка оставления блокировки"""
    if not await is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет доступа")
        return
    
    user_id_to_keep = int(callback.data.split("_")[2])
    
    try:
        conn = await get_db_connection()
        
        user = await conn.fetchrow(
            "SELECT nickname FROM users WHERE user_id = $1", 
            user_id_to_keep
        )
        
        await conn.close()
        
        if not user:
            await callback.message.edit_text("❌ Пользователь не найден")
            await callback.answer()
            return
        
        safe_nickname = escape_markdown(user['nickname'])
        keep_text = f"""❌ **Блокировка оставлена**

👤 **Никнейм:** {safe_nickname}
🆔 **ID:** `{user_id_to_keep}`
👨‍💼 **Решение принял:** {escape_markdown(callback.from_user.first_name or 'Админ')}

🚫 Пользователь остается заблокированным"""
        
        await callback.message.edit_text(keep_text, parse_mode='Markdown')
        await callback.answer("❌ Блокировка оставлена")
        
        logger.info(f"Admin {callback.from_user.id} kept block for user {user_id_to_keep} ({user['nickname']})")
        
    except Exception as e:
        logger.error(f"Error keeping block: {e}")
        await callback.message.edit_text("❌ Ошибка")
        await callback.answer()
    
    await state.clear()

@dp.callback_query(F.data == "new_search")
async def handle_new_search(callback: types.CallbackQuery, state: FSMContext):
    """Начать новый поиск"""
    if not await is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет доступа")
        return
    
    await callback.message.edit_text("🔍 **Поиск пользователя для разблокировки**\n\nВведите никнейм пользователя:", parse_mode='Markdown')
    await state.set_state(AdminStates.waiting_nickname)
    await callback.answer()

@dp.message(Command("stats"))
async def stats_command(message: types.Message):
    """Статистика заблокированных пользователей"""
    user_id = message.from_user.id
    
    if not await is_admin(user_id):
        await message.answer("❌ У вас нет доступа к админ-панели")
        return
    
    try:
        conn = await get_db_connection()
        
        # Общая статистика
        total_users = await conn.fetchval("SELECT COUNT(*) FROM users") or 0
        blocked_users = await conn.fetchval("SELECT COUNT(*) FROM users WHERE is_blocked = TRUE") or 0
        total_complaints = await conn.fetchval("SELECT COUNT(*) FROM complaints") or 0
        
        # Топ пользователей по жалобам
        top_complained = await conn.fetch("""
            SELECT c.original_user_id, u.nickname, u.is_blocked, COUNT(*) as complaint_count
            FROM complaints c
            LEFT JOIN users u ON c.original_user_id = u.user_id
            GROUP BY c.original_user_id, u.nickname, u.is_blocked
            ORDER BY complaint_count DESC
            LIMIT 10
        """)
        
        await conn.close()
        
        stats_text = f"""📊 **Статистика админ-панели**

👥 **Общие данные:**
• Всего пользователей: **{total_users}**
• Заблокированных: **{blocked_users}**
• Всего жалоб: **{total_complaints}**

🚨 **Топ по жалобам:**"""
        
        for i, user in enumerate(top_complained, 1):
            nickname = user['nickname'] or f"ID:{user['original_user_id']}"
            safe_nickname = escape_markdown(nickname)
            status = "🚫" if user['is_blocked'] else "✅"
            complaint_count = user['complaint_count']
            
            stats_text += f"\n{i}. {status} {safe_nickname} - **{complaint_count}** жалоб"
        
        if not top_complained:
            stats_text += "\n_Пока нет жалоб_"
        
        await message.answer(stats_text, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        await message.answer("❌ Ошибка при получении статистики")

@dp.message(Command("help"))
async def help_command(message: types.Message):
    """Справка по админ-боту"""
    user_id = message.from_user.id
    
    if not await is_admin(user_id):
        await message.answer("❌ У вас нет доступа к админ-панели")
        return
    
    help_text = """🔧 **Справка по админ-панели**

📋 **Команды:**
• `/start` - главное меню
• `/search` - поиск пользователя для разблокировки
• `/stats` - статистика заблокированных пользователей
• `/help` - эта справка

🔍 **Поиск пользователей:**
• Введите никнейм полностью или частично
• Поиск не чувствителен к регистру
• Показывает информацию о блокировке и жалобах

⚖️ **Принятие решений:**
• Просмотрите все жалобы на пользователя
• Оцените содержание сообщений
• Примите решение о разблокировке

🛡️ **Безопасность:**
• Доступ только для администраторов
• Все действия логируются
• Возможность отменить решение"""
    
    await message.answer(help_text, parse_mode='Markdown')

@dp.message()
async def unknown(message: types.Message, state: FSMContext):
    """Неизвестные сообщения"""
    user_id = message.from_user.id
    
    if not await is_admin(user_id):
        await message.answer("❌ У вас нет доступа к админ-панели")
        return
    
    # Если мы в состоянии ожидания никнейма, обрабатываем как никнейм
    current_state = await state.get_state()
    if current_state == AdminStates.waiting_nickname.state:
        await handle_nickname_search(message, state)
        return
    
    await message.answer("🤔 Неизвестная команда. Используйте /help для справки")

async def main():
    """Запуск админ-бота"""
    logger.info("Starting admin bot...")
    await dp.start_polling(bot, skip_updates=True)

if __name__ == "__main__":
    asyncio.run(main())
