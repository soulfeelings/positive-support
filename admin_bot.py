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
ADMIN_BOT_TOKEN = os.getenv("ADMIN_BOT_TOKEN", "8233417802:AAGyzmvx1m7MdhGFN-Jk3tTjJ7Q_NgV16h8")
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

# Список ID администраторов (добавьте свой Telegram ID)
ADMIN_IDS = [
    int(os.getenv("ADMIN_ID", "8166609254")),  # Основной админ из переменной окружения
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

logger.info(f"🔧 Admin Bot starting...")
logger.info(f"👥 Admin IDs: {ADMIN_IDS}")
logger.info(f"🌐 Backend URL: {BACKEND_URL}")
logger.info(f"📊 Database: {DB_HOST}:{DB_PORT}/{DB_NAME}")

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

def get_admin_keyboard(user_id: int):
    """Создает клавиатуру для управления пользователем"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📊 Изменить количество жалоб", callback_data=f"change_complaints_{user_id}")
        ],
        [
            InlineKeyboardButton(text="🔄 Поиск другого пользователя", callback_data="new_search")
        ]
    ])

def get_complaints_keyboard(user_id: int):
    """Создает клавиатуру для выбора количества жалоб"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="0️⃣ Обнулить жалобы", callback_data=f"set_complaints_{user_id}_0"),
            InlineKeyboardButton(text="1️⃣ Одна жалоба", callback_data=f"set_complaints_{user_id}_1")
        ],
        [
            InlineKeyboardButton(text="2️⃣ Две жалобы", callback_data=f"set_complaints_{user_id}_2"),
            InlineKeyboardButton(text="3️⃣ Три жалобы", callback_data=f"set_complaints_{user_id}_3")
        ],
        [
            InlineKeyboardButton(text="4️⃣ Четыре жалобы", callback_data=f"set_complaints_{user_id}_4"),
            InlineKeyboardButton(text="5️⃣ Пять жалоб", callback_data=f"set_complaints_{user_id}_5")
        ],
        [
            InlineKeyboardButton(text="❌ Отмена", callback_data="new_search")
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
    
    welcome_text = """🔧 **Админ-панель для управления пользователями**

🛡️ **Что умеет этот бот:**
• Поиск пользователей по никнейму
• Просмотр истории жалоб на пользователя
• Управление количеством жалоб (0-5)
• Автоматическая блокировка/разблокировка

📝 **Как использовать:**
1. Введите команду /search и никнейм пользователя
2. Просмотрите информацию и жалобы
3. Нажмите "Изменить количество жалоб"
4. Выберите нужное количество (0-5)

🎯 **Команды:**
• /search - поиск пользователя для управления
• /stats - статистика с кнопками управления
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
    await message.answer("🔍 **Поиск пользователя для управления**\n\nВведите никнейм пользователя:", parse_mode='Markdown')
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
        
        # Добавляем статус блокировки
        if is_blocked:
            info_text += f"\n\n🚫 **Пользователь заблокирован**"
            if complaints_count >= 5:
                info_text += "\n⚠️ _Автоматическая блокировка за превышение лимита жалоб_"
        else:
            info_text += "\n\n✅ **Пользователь не заблокирован**"
        
        # Всегда показываем кнопку управления
        await message.answer(info_text, parse_mode='Markdown', reply_markup=get_admin_keyboard(user_info_id))
        
        await state.set_state(AdminStates.viewing_user_info)
        await state.update_data(user_id=user_info_id, nickname=user_nickname)
        
    except Exception as e:
        logger.error(f"Error searching user: {e}")
        await message.answer("❌ Ошибка при поиске пользователя")
        await state.clear()

@dp.callback_query(F.data.startswith("change_complaints_"))
async def handle_change_complaints(callback: types.CallbackQuery, state: FSMContext):
    """Обработка изменения количества жалоб"""
    if not await is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет доступа")
        return
    
    user_id = int(callback.data.split("_")[2])
    
    try:
        conn = await get_db_connection()
        
        # Получаем информацию о пользователе
        user = await conn.fetchrow(
            "SELECT nickname FROM users WHERE user_id = $1", 
            user_id
        )
        
        await conn.close()
        
        if not user:
            await callback.message.edit_text("❌ Пользователь не найден")
            await callback.answer()
            return
        
        safe_nickname = escape_markdown(user['nickname'])
        choice_text = f"""📊 **Изменение количества жалоб**

👤 **Пользователь:** {safe_nickname}
🆔 **ID:** `{user_id}`

Выберите новое количество жалоб:"""
        
        await callback.message.edit_text(choice_text, parse_mode='Markdown', reply_markup=get_complaints_keyboard(user_id))
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Error showing complaints menu: {e}")
        await callback.message.edit_text("❌ Ошибка")
        await callback.answer()

@dp.callback_query(F.data.startswith("set_complaints_"))
async def handle_set_complaints(callback: types.CallbackQuery, state: FSMContext):
    """Обработка установки количества жалоб"""
    if not await is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет доступа")
        return
    
    parts = callback.data.split("_")
    user_id = int(parts[2])
    new_complaints_count = int(parts[3])
    
    try:
        conn = await get_db_connection()
        
        # Получаем информацию о пользователе
        user = await conn.fetchrow(
            "SELECT nickname, is_blocked FROM users WHERE user_id = $1", 
            user_id
        )
        
        if not user:
            await callback.message.edit_text("❌ Пользователь не найден")
            await callback.answer()
            await conn.close()
            return
        
        # Получаем текущее количество жалоб (используем правильное поле)
        current_complaints = await conn.fetchval(
            "SELECT COUNT(*) FROM complaints WHERE original_user_id = $1", 
            user_id
        ) or 0
        
        # Удаляем все текущие жалобы
        await conn.execute(
            "DELETE FROM complaints WHERE original_user_id = $1", 
            user_id
        )
        
        # Создаем новые "фиктивные" жалобы для достижения нужного количества
        if new_complaints_count > 0:
            # Получаем текущее время
            from datetime import datetime
            current_time = datetime.now()
            
            # Создаем или используем системного пользователя для административных записей
            system_user_id = 0
            
            # Проверяем существует ли системный пользователь
            system_exists = await conn.fetchval(
                "SELECT user_id FROM users WHERE user_id = $1", 
                system_user_id
            )
            
            if not system_exists:
                # Создаем системного пользователя
                await conn.execute(
                    """INSERT INTO users (user_id, nickname, is_blocked, created_at)
                       VALUES ($1, $2, $3, $4) 
                       ON CONFLICT (user_id) DO NOTHING""",
                    system_user_id,
                    "Система",
                    False,
                    current_time
                )
            
            complainer_id = system_user_id
            
            for i in range(new_complaints_count):
                await conn.execute(
                    """INSERT INTO complaints (original_user_id, complainer_user_id, text, message_type, created_at, complaint_date)
                       VALUES ($1, $2, $3, $4, $5, $6)""",
                    user_id,
                    complainer_id,
                    f"Административная корректировка #{i+1}",
                    'text',
                    current_time,
                    current_time
                )
        
        # Обновляем статус блокировки в зависимости от количества жалоб
        should_be_blocked = new_complaints_count >= 5
        await conn.execute(
            "UPDATE users SET is_blocked = $1 WHERE user_id = $2", 
            should_be_blocked, user_id
        )
        
        await conn.close()
        
        safe_nickname = escape_markdown(user['nickname'])
        block_status = "🚫 Заблокирован" if should_be_blocked else "✅ Разблокирован"
        
        # Определяем тип изменения
        if new_complaints_count == 0:
            action_description = "🧹 Полная амнистия - все жалобы обнулены"
        elif new_complaints_count < current_complaints:
            action_description = f"📉 Жалоб стало меньше (было {current_complaints} → стало {new_complaints_count})"
        elif new_complaints_count > current_complaints:
            action_description = f"📈 Жалоб стало больше (было {current_complaints} → стало {new_complaints_count})"
        else:
            action_description = f"📊 Количество жалоб осталось прежним ({new_complaints_count})"

        success_text = f"""📊 **Количество жалоб изменено**

👤 **Пользователь:** {safe_nickname}
🆔 **ID:** `{user_id}`
👨‍💼 **Изменил:** {escape_markdown(callback.from_user.first_name or 'Админ')}

{action_description}
🔄 **Новый статус:** {block_status}

{'⚠️ Пользователь автоматически заблокирован за 5+ жалоб' if should_be_blocked else '✅ Пользователь может пользоваться ботом'}"""
        
        await callback.message.edit_text(success_text, parse_mode='Markdown')
        await callback.answer("✅ Количество жалоб изменено")
        
        logger.info(f"Admin {callback.from_user.id} changed complaints for user {user_id} ({user['nickname']}) from {current_complaints} to {new_complaints_count}")
        
    except Exception as e:
        logger.error(f"Error setting complaints: {e}")
        logger.error(f"Error details: user_id={user_id}, new_count={new_complaints_count}")
        await callback.message.edit_text(f"❌ Ошибка при изменении жалоб: {str(e)[:100]}")
        await callback.answer()
    
    await state.clear()

@dp.callback_query(F.data == "new_search")
async def handle_new_search(callback: types.CallbackQuery, state: FSMContext):
    """Начать новый поиск"""
    if not await is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет доступа")
        return
    
    await callback.message.edit_text("🔍 **Поиск пользователя для управления**\n\nВведите никнейм пользователя:", parse_mode='Markdown')
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
        else:
            # Создаем кнопки для управления пользователями
            keyboard = InlineKeyboardMarkup(inline_keyboard=[])
            
            for i, user in enumerate(top_complained[:5], 1):  # Показываем только первые 5 для кнопок
                nickname = user['nickname'] or f"ID:{user['original_user_id']}"
                safe_nickname = escape_markdown(nickname)[:20]  # Ограничиваем длину для кнопки
                user_id = user['original_user_id']
                complaint_count = user['complaint_count']
                
                button_text = f"{i}. {safe_nickname} ({complaint_count})"
                keyboard.inline_keyboard.append([
                    InlineKeyboardButton(text=button_text, callback_data=f"change_complaints_{user_id}")
                ])
            
            stats_text += "\n\n💡 _Нажмите на пользователя чтобы изменить количество жалоб_"
            await message.answer(stats_text, parse_mode='Markdown', reply_markup=keyboard)
        
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
• `/search` - поиск пользователя для управления
• `/stats` - статистика пользователей с кнопками управления
• `/help` - эта справка

🔍 **Поиск пользователей:**
• Введите никнейм полностью или частично
• Поиск не чувствителен к регистру
• Показывает информацию о блокировке и жалобах

📊 **Управление жалобами:**
• Установка точного количества жалоб (0-5)
• Автоматическая блокировка при 5+ жалобах
• Работает с любыми пользователями (не только заблокированными)

⚖️ **Возможности:**
• Обнулить жалобы - полная "амнистия"
• Установить 1-4 жалобы - предупреждение
• Установить 5 жалоб - заблокировать пользователя

🛡️ **Безопасность:**
• Доступ только для администраторов
• Все действия логируются
• Показывается история изменений"""
    
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
