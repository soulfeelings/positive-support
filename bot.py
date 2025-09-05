import os
import asyncio
import logging
import aiohttp
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import KeyboardButton, ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from message_filter import get_message_filter, FilterResult


load_dotenv()

# Настройка логирования
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")
BACKEND_URL = os.getenv("BACKEND_URL")

if not BOT_TOKEN:
    logger.error("BOT_TOKEN not set!")
    exit(1)

if not BACKEND_URL:
    logger.error("BACKEND_URL not set!")
    exit(1)

logger.info(f"🤖 Bot starting with token: {BOT_TOKEN[:10]}...")
logger.info(f"🌐 Backend URL: {BACKEND_URL}")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# Инициализируем фильтр сообщений
message_filter = get_message_filter()

class UserStates(StatesGroup):
    waiting_nickname = State()
    waiting_message = State()
    viewing_help_request = State()
    changing_nickname = State()

# Главная клавиатура
main_kb = ReplyKeyboardMarkup(keyboard=[
    [KeyboardButton(text="💌 Отправить поддержку"), KeyboardButton(text="🔥 Получить поддержку")],
    [KeyboardButton(text="🆘 Нужна помощь"), KeyboardButton(text="🤝 Помочь кому-нибудь")],
    [KeyboardButton(text="👤 Профиль"), KeyboardButton(text="🏆 Топлист")]
], resize_keyboard=True)

# Inline клавиатура для запросов помощи
def get_help_inline_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="❤️ Помочь", callback_data="help_respond"),
            InlineKeyboardButton(text="➡️ Дальше", callback_data="help_next")
        ],
        [
            InlineKeyboardButton(text="🏠 Главное меню", callback_data="help_menu"),
            InlineKeyboardButton(text="❌ Пожаловаться", callback_data="help_complaint")
        ]
    ])

# Inline клавиатура для профиля
def get_profile_inline_kb():
    buttons = [
        [InlineKeyboardButton(text="✏️ Сменить никнейм", callback_data="change_nickname")]
    ]
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)



def escape_markdown(text: str) -> str:
    """Экранирует специальные символы для Markdown"""
    if not text:
        return text
    return text.replace('_', '\\_').replace('*', '\\*').replace('[', '\\[').replace(']', '\\]').replace('`', '\\`')

async def check_user_blocked(user_id: int) -> bool:
    """Проверяет заблокирован ли пользователь"""
    try:
        profile = await api_request("profile", {"user_id": user_id})
        return profile.get("status") == "ok" and profile.get("is_blocked", False)
    except Exception as e:
        logger.error(f"Error checking user block status: {e}")
        return False

async def send_blocked_message(message: types.Message):
    """Отправляет сообщение о блокировке"""
    blocked_text = """🚫 **Доступ заблокирован**

К сожалению, ваш аккаунт заблокирован за нарушение правил сообщества.

📞 **Для разблокировки обратитесь к администрации**

ℹ️ _Блокировка может быть связана с:_
• Нарушением правил сообщества
• Множественными жалобами на ваши сообщения
• Неподобающим поведением"""
    
    await message.answer(blocked_text, parse_mode='Markdown')

async def handle_filter_violation(message: types.Message, filter_result: FilterResult):
    """Обрабатывает нарушение фильтра сообщений"""
    user_id = message.from_user.id
    
    logger.info(f"🚫 Блокируем сообщение пользователя {user_id}: {filter_result.reason}")
    
    # Просто блокируем сообщение и показываем причину
    block_text = f"""🚫 **Сообщение заблокировано**

{filter_result.details}

📝 **Правила сообщества:**
• Запрещены нецензурные выражения
• Запрещены оскорбления
• Запрещены ссылки и реклама
• Запрещен спам

💡 _Сообщение не было отправлено_"""
    
    await message.answer(block_text, parse_mode='Markdown')
    logger.warning(f"User {user_id} message blocked for {filter_result.reason}: {filter_result.details}")

async def send_blocked_callback(callback: types.CallbackQuery):
    """Отправляет сообщение о блокировке для callback"""
    blocked_text = """🚫 **Доступ заблокирован**

К сожалению, ваш аккаунт заблокирован за нарушение правил сообщества.

📞 **Для разблокировки обратитесь к администрации**"""
    
    await callback.message.answer(blocked_text, parse_mode='Markdown')
    await callback.answer()

async def api_request(endpoint: str, data: dict):
    """Простой HTTP запрос к API"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(f"{BACKEND_URL}/{endpoint}", json=data) as response:
                if response.status != 200:
                    logger.error(f"API returned status {response.status} for {endpoint}")
                    return {"status": "error", "message": f"HTTP {response.status}"}
                result = await response.json()
                logger.info(f"API {endpoint} response: {result}")
                return result
    except Exception as e:
        logger.error(f"API error for {endpoint}: {e}")
        return {"status": "error", "message": str(e)}

@dp.message(Command("start"))
async def start(message: types.Message, state: FSMContext):
    """Команда старт"""
    await state.clear()
    user_id = message.from_user.id
    
    # Проверяем профиль
    profile = await api_request("profile", {"user_id": user_id})
    
    # Проверяем черный список
    if await check_user_blocked(user_id):
        await send_blocked_message(message)
        return
    
    if profile.get("status") == "ok" and profile.get("nickname"):
        nickname = profile.get('nickname')
        welcome_text = f"""👋 **Добро пожаловать в бот поддержки, {escape_markdown(nickname)}!**

🤝 **Что умеет этот бот:**
• 💌 Отправлять сообщения поддержки другим людям
• 🔥 Получать слова поддержки от сообщества  
• 🆘 Просить помощи в трудные моменты
• 🤝 Помогать тем, кому нужна поддержка
• ⭐ Зарабатывать рейтинг за помощь другим

💝 **Здесь ты найдешь:**
• Добрые слова и поддержку
• Понимание и сочувствие
• Возможность помочь другим
• Дружелюбное сообщество

🌟 Выбери действие в меню ниже:"""

        await message.answer(
            welcome_text,
            reply_markup=main_kb,
            parse_mode='Markdown'
        )
    else:
        welcome_text = """👋 **Добро пожаловать в бот поддержки!**

🤝 **Здесь ты можешь:**
• 💌 Отправлять и получать поддержку
• 🆘 Просить помощи когда тяжело
• 🤝 Помогать другим людям
• ⭐ Зарабатывать рейтинг за добрые дела

💝 **Это место, где:**
• Тебя поймут и поддержат
• Можно помочь тем, кому трудно
• Царит атмосфера добра и взаимопомощи

🎯 **Для начала введи свой никнейм (3-20 символов):**"""

        await message.answer(welcome_text, parse_mode='Markdown')
        await state.set_state(UserStates.waiting_nickname)

@dp.message(UserStates.waiting_nickname)
async def handle_nickname(message: types.Message, state: FSMContext):
    """Установка никнейма"""
    if await check_user_blocked(message.from_user.id):
        await send_blocked_message(message)
        await state.clear()
        return
    
    nickname = message.text.strip()

    # Проверяем никнейм через фильтр
    filter_result = message_filter.check_message(message.from_user.id, nickname, "text")
    if filter_result.is_blocked:
        await handle_filter_violation(message, filter_result)
        return

    if len(nickname) < 3 or len(nickname) > 20:
        await message.answer("❌ Никнейм должен быть 3-20 символов:")
        return

    logger.info(f"Attempting to set nickname '{nickname}' for user {message.from_user.id}")
    
    result = await api_request("set_nickname", {
        "user_id": message.from_user.id,
        "nickname": nickname
    })
    
    logger.info(f"Set nickname result: {result}")
    
    if result.get("status") == "success":
        await message.answer(f"✅ Никнейм {nickname} установлен!", reply_markup=main_kb)
        await state.clear()
        logger.info(f"✅ Nickname '{nickname}' successfully set for user {message.from_user.id}")
    else:
        error_msg = result.get("message", "неизвестная ошибка")
        logger.warning(f"❌ Failed to set nickname '{nickname}' for user {message.from_user.id}: {error_msg}")
        await message.answer(f"❌ Ошибка: {error_msg}. Попробуй другой никнейм:")

@dp.message(UserStates.changing_nickname)
async def handle_nickname_change(message: types.Message, state: FSMContext):
    """Смена никнейма"""
    if await check_user_blocked(message.from_user.id):
        await send_blocked_message(message)
        await state.clear()
        return
    
    nickname = message.text.strip()

    # Проверяем никнейм через фильтр
    filter_result = message_filter.check_message(message.from_user.id, nickname, "text")
    if filter_result.is_blocked:
        await handle_filter_violation(message, filter_result)
        return

    if len(nickname) < 3 or len(nickname) > 20:
        await message.answer("❌ Никнейм должен быть 3-20 символов. Попробуй еще раз:")
        return

    logger.info(f"Attempting to change nickname to '{nickname}' for user {message.from_user.id}")
    
    result = await api_request("set_nickname", {
        "user_id": message.from_user.id,
        "nickname": nickname
    })
    
    logger.info(f"Change nickname result: {result}")
    
    if result.get("status") == "success":
        await message.answer(
            f"✅ Никнейм успешно изменен на **{escape_markdown(nickname)}**!",
            reply_markup=main_kb,
            parse_mode='Markdown'
        )
        await state.clear()
        logger.info(f"✅ Nickname successfully changed to '{nickname}' for user {message.from_user.id}")
    else:
        error_msg = result.get("message", "неизвестная ошибка")
        logger.warning(f"❌ Failed to change nickname to '{nickname}' for user {message.from_user.id}: {error_msg}")
        if "already taken" in error_msg.lower() or "занят" in error_msg.lower():
            await message.answer(f"❌ Никнейм **{escape_markdown(nickname)}** уже занят. Попробуй другой:", parse_mode='Markdown')
        else:
            await message.answer(f"❌ Ошибка: {error_msg}. Попробуй другой никнейм:")

async def send_support(message: types.Message, state: FSMContext):
    """Отправить поддержку"""
    if await check_user_blocked(message.from_user.id):
        await send_blocked_message(message)
        return
    
    await state.clear()
    await message.answer("💝 Напиши сообщение поддержки:")
    await state.set_state(UserStates.waiting_message)
    await state.update_data(action="support")

async def need_help(message: types.Message, state: FSMContext):
    """Запросить помощь"""
    if await check_user_blocked(message.from_user.id):
        await send_blocked_message(message)
        return
    
    await state.clear()
    await message.answer(
        "💭 Расскажи, что случилось?\n\n"
        "📝 Можешь написать текстом, записать голосовое сообщение или отправить видео кружок"
    )
    await state.set_state(UserStates.waiting_message)
    await state.update_data(action="help")

# Обработчики кнопок меню с высоким приоритетом (работают даже в состоянии waiting_message)
@dp.message(F.text == "👤 Профиль")
async def handle_profile_button(message: types.Message, state: FSMContext):
    """Обработка кнопки Профиль с высоким приоритетом"""
    await state.clear()  # Очищаем состояние
    await show_profile(message, state)

@dp.message(F.text == "🏆 Топлист")
async def handle_toplist_button(message: types.Message, state: FSMContext):
    """Обработка кнопки Топлист с высоким приоритетом"""
    await state.clear()  # Очищаем состояние
    await show_toplist(message, state)

@dp.message(F.text == "💌 Отправить поддержку")
async def handle_send_support_button(message: types.Message, state: FSMContext):
    """Обработка кнопки Отправить поддержку с высоким приоритетом"""
    await state.clear()  # Очищаем состояние
    await send_support(message, state)

@dp.message(F.text == "🔥 Получить поддержку")
async def handle_get_support_button(message: types.Message, state: FSMContext):
    """Обработка кнопки Получить поддержку с высоким приоритетом"""
    await state.clear()  # Очищаем состояние
    await get_support(message, state)

@dp.message(F.text == "🆘 Нужна помощь")
async def handle_need_help_button(message: types.Message, state: FSMContext):
    """Обработка кнопки Нужна помощь с высоким приоритетом"""
    await state.clear()  # Очищаем состояние
    await need_help(message, state)

@dp.message(F.text == "🤝 Помочь кому-нибудь")
async def handle_help_someone_button(message: types.Message, state: FSMContext):
    """Обработка кнопки Помочь кому-нибудь с высоким приоритетом"""
    await state.clear()  # Очищаем состояние
    await help_someone(message, state)

@dp.message(UserStates.waiting_message)
async def handle_message(message: types.Message, state: FSMContext):
    """Обработка текстовых, голосовых сообщений и видео кружков"""
    if await check_user_blocked(message.from_user.id):
        await send_blocked_message(message)
        await state.clear()
        return
    
    data = await state.get_data()
    action = data.get("action")
    
    # Определяем тип сообщения и данные
    if message.voice:
        message_data = {
            "user_id": message.from_user.id,
            "text": None,
            "file_id": message.voice.file_id,
            "message_type": "voice"
        }
        content_description = "голосовое сообщение"
    elif message.video_note:
        message_data = {
            "user_id": message.from_user.id,
            "text": None,
            "file_id": message.video_note.file_id,
            "message_type": "video_note"
        }
        content_description = "видео кружок"
    elif message.text:
        # Проверяем сообщение через фильтр
        filter_result = message_filter.check_message(message.from_user.id, message.text, "text")
        if filter_result.is_blocked:
            await handle_filter_violation(message, filter_result)
            return
            
        message_data = {
            "user_id": message.from_user.id,
            "text": message.text,
            "file_id": None,
            "message_type": "text"
        }
        content_description = "сообщение"
    else:
        await message.answer("❌ Пожалуйста, отправь текст, голосовое сообщение или видео кружок", reply_markup=main_kb)
        await state.clear()
        return
    
    # Отправляем в зависимости от действия
    if action == "support":
        help_recipient = data.get("help_recipient")
        
        if help_recipient:
            # Отправляем ответ конкретному человеку
            result = await api_request("send_support", message_data)
            logger.info(f"Send support API result: {result}")
            if result.get("status") == "success":
                # Экранируем никнейм для Markdown
                safe_recipient_nickname = escape_markdown(help_recipient['nickname'])
                await message.answer(
                    f"✅ {content_description.capitalize()} отправлено пользователю **{safe_recipient_nickname}**!\n\n"
                    f"💝 Твоя поддержка поможет этому человеку.",
                    reply_markup=main_kb,
                    parse_mode='Markdown'
                )
        
                # Отправляем сообщение получателю
                try:
                    if message_data["message_type"] == "voice":
                        await bot.send_voice(
                            chat_id=help_recipient["user_id"],
                            voice=message_data["file_id"],
                            caption="💝 Для тебя пришло сообщение поддержки!\n\n🤗 Кто-то откликнулся на твой запрос."
                        )
                    elif message_data["message_type"] == "video_note":
                        await bot.send_video_note(
                            chat_id=help_recipient["user_id"],
                            video_note=message_data["file_id"]
                        )
                        await bot.send_message(
                            chat_id=help_recipient["user_id"],
                            text="💝 Для тебя пришло сообщение поддержки!\n\n🤗 Кто-то откликнулся на твой запрос."
                        )
                    else:
                        # Экранируем текст для Markdown
                        safe_message_text = escape_markdown(message_data['text'])
                        await bot.send_message(
                            chat_id=help_recipient["user_id"],
                            text=f"💝 Для тебя пришло сообщение поддержки!\n\n"
                                 f"💬 _{safe_message_text}_\n\n"
                                 f"🤗 Кто-то откликнулся на твой запрос. Надеемся, это поможет!",
                            parse_mode='Markdown'
                        )
                    logger.info(f"Help response delivered from {message.from_user.id} to {help_recipient['user_id']}")
                    
                    # Увеличиваем рейтинг пользователя за помощь
                    rating_result = await api_request("increment_rating", {"user_id": message.from_user.id})
                    if rating_result.get("status") == "success":
                        new_rating = rating_result.get("new_rating", 0)
                        logger.info(f"Rating incremented for user {message.from_user.id}, new rating: {new_rating}")
                    else:
                        logger.warning(f"Failed to increment rating for user {message.from_user.id}")
                    
                    # Удаляем запрос помощи из базы данных
                    delete_result = await api_request("delete_help_request", {
                        "request_id": help_recipient["id"],
                        "user_id": help_recipient["user_id"]
                    })
                    if delete_result.get("status") == "success":
                        logger.info(f"Help request {help_recipient['id']} deleted after response")
                    else:
                        logger.warning(f"Failed to delete help request {help_recipient['id']}")
                        
                except Exception as e:
                    logger.error(f"Failed to deliver help response: {e}")
                    await message.answer("⚠️ Сообщение сохранено, но возникла проблема с доставкой.")
            else:
                await message.answer("❌ Ошибка отправки", reply_markup=main_kb)
        else:
            # Обычная поддержка в общий пул
            result = await api_request("send_support", message_data)
            if result.get("status") == "success":
                await message.answer(f"✅ {content_description.capitalize()} поддержки отправлено!", reply_markup=main_kb)
            else:
                await message.answer("❌ Ошибка отправки", reply_markup=main_kb)
    
    elif action == "help":
        result = await api_request("send_request", message_data)
        logger.info(f"Send request API result: {result}")
        if result.get("status") == "success":
            await message.answer(
                f"✅ Твой запрос о помощи ({content_description}) отправлен!\n\n"
                "🤗 Кто-то из сообщества обязательно откликнется и поможет тебе.", 
                reply_markup=main_kb
            )
            logger.info(f"Help request sent: user_id={message.from_user.id}, type={message_data['message_type']}")
        else:
            await message.answer("❌ Ошибка отправки", reply_markup=main_kb)
    
    await state.clear()

async def get_support(message: types.Message, state: FSMContext):
    """Получить поддержку"""
    if await check_user_blocked(message.from_user.id):
        await send_blocked_message(message)
        return
    
    await state.clear()
    result = await api_request("get_support", {"user_id": message.from_user.id})
    
    if result.get("status") == "text":
        await message.answer(f"💬 {result['message']}\n\n👤 От: {result['nickname']}")
    else:
        await message.answer("😔 Пока нет сообщений поддержки")

async def help_someone(message: types.Message, state: FSMContext):
    """Показать запрос помощи (начинаем сначала)"""
    if await check_user_blocked(message.from_user.id):
        await send_blocked_message(message)
        return
    
    await state.clear()
    # Сбрасываем last_seen_id для начала с самого первого сообщения
    await state.update_data(last_seen_help_id=0)
    await show_help_request_simple(message, state)

async def show_help_request_simple(message: types.Message, state: FSMContext):
    """Показать запрос помощи по порядку (FIFO)"""
    # Получаем последний просмотренный message_id из состояния
    data = await state.get_data()
    last_seen_id = data.get("last_seen_help_id", 0)
    
    logger.info(f"Requesting help request for user {message.from_user.id} with last_seen_id={last_seen_id}")
    result = await api_request("get_help_request", {
        "user_id": message.from_user.id,
        "last_seen_id": last_seen_id
    })
    
    if result.get("status") == "ok":
        request_data = result["request"]
        
        # Сохраняем данные запроса и обновляем last_seen_id в состоянии
        logger.info(f"Showing help request id={request_data['id']} to user {message.from_user.id}, updating last_seen_help_id")
        await state.update_data(
            current_request=request_data,
            last_seen_help_id=request_data["id"]
        )
        await state.set_state(UserStates.viewing_help_request)
        
        # Формируем сообщение в зависимости от типа
        if request_data["message_type"] == "voice":
            # Отправляем голосовое сообщение
            try:
                # Экранируем никнейм для Markdown
                safe_request_nickname = escape_markdown(request_data['nickname'])
                await bot.send_voice(
                    chat_id=message.chat.id,
                    voice=request_data["file_id"],
                    caption=f"🆘 **{safe_request_nickname}** просит помощи:\n\n❤️ Хочешь помочь этому человеку?",
                    parse_mode='Markdown',
                    reply_markup=get_help_inline_kb()
                )
            except Exception as e:
                logger.error(f"Failed to send voice: {e}")
                # Экранируем никнейм для Markdown
                safe_request_nickname = escape_markdown(request_data['nickname'])
                await message.answer(
                    f"🆘 **{safe_request_nickname}** просит помощи:\n\n"
                    f"🎤 _Голосовое сообщение (не удалось воспроизвести)_\n\n"
                    f"❤️ Хочешь помочь этому человеку?",
                    reply_markup=get_help_inline_kb(),
                    parse_mode='Markdown'
                )
        elif request_data["message_type"] == "video_note":
            # Отправляем видео кружок
            try:
                # Экранируем никнейм для Markdown
                safe_request_nickname = escape_markdown(request_data['nickname'])
                await bot.send_video_note(
                    chat_id=message.chat.id,
                    video_note=request_data["file_id"]
                )
                await message.answer(
                    f"🆘 **{safe_request_nickname}** просит помощи:\n\n❤️ Хочешь помочь этому человеку?",
                    reply_markup=get_help_inline_kb(),
                    parse_mode='Markdown'
                )
            except Exception as e:
                logger.error(f"Failed to send video note: {e}")
                # Экранируем никнейм для Markdown
                safe_request_nickname = escape_markdown(request_data['nickname'])
                await message.answer(
                    f"🆘 **{safe_request_nickname}** просит помощи:\n\n"
                    f"🎥 _Видео кружок (не удалось воспроизвести)_\n\n"
                    f"❤️ Хочешь помочь этому человеку?",
                    reply_markup=get_help_inline_kb(),
                    parse_mode='Markdown'
                )
        else:
            # Отправляем текстовое сообщение
            # Экранируем никнейм и текст для Markdown
            safe_request_nickname = escape_markdown(request_data['nickname'])
            safe_request_text = escape_markdown(request_data['text'])
            await message.answer(
                f"🆘 **{safe_request_nickname}** просит помощи:\n\n"
                f"💭 _{safe_request_text}_\n\n"
                "❤️ Хочешь помочь этому человеку?",
                reply_markup=get_help_inline_kb(),
                parse_mode='Markdown'
            )
    else:
        await message.answer(
            "😇 Пока никто не просит помощи!\n\n"
            "✨ Проверь позже.",
            reply_markup=main_kb
        )

async def show_profile(message: types.Message, state: FSMContext):
    """Показать профиль пользователя"""
    if await check_user_blocked(message.from_user.id):
        await send_blocked_message(message)
        return
    
    # Очищаем состояние чтобы не было конфликтов
    await state.clear()
    
    user_id = message.from_user.id
    logger.info(f"Showing profile for user {user_id}")
    
    # Получаем профиль пользователя
    profile = await api_request("profile", {"user_id": user_id})
    
    if profile.get("status") == "ok":
        nickname = profile.get("nickname", "Неизвестно")
        rating = profile.get("rating", 0)
        complaints_count = profile.get("complaints_count", 0)
        
        # Экранируем специальные символы в никнейме для Markdown
        safe_nickname = escape_markdown(nickname)
        
        # Определяем лигу по рейтингу
        if rating < 20:
            league = "_нет лиги_"
        elif rating < 50:
            league = "🥉 **Бронзовая лига**"
        elif rating < 100:
            league = "🥈 **Серебряная лига**"
        else:
            league = "🥇 **Золотая лига**"
        
        # Определяем статус по количеству жалоб
        if complaints_count == 0:
            status_icon = "✅"
            status_text = "_отличная репутация_"
        elif complaints_count <= 2:
            status_icon = "⚠️"
            status_text = "_внимание к контенту_"
        elif complaints_count <= 5:
            status_icon = "🔴"
            status_text = "_множественные жалобы_"
        else:
            status_icon = "🚫"
            status_text = "_критическая репутация_"
        
        profile_text = f"""👤 **Твой профиль**

📛 Никнейм: **{safe_nickname}**
⭐ Рейтинг: **{rating}**
🏆 Лига: {league}
📊 Статус: {status_icon} {status_text}

💌 Отправлено сообщений: _временно не доступно_
🤝 Помогли людям: **{rating}**
🚨 Жалобы на вас: **{complaints_count}**"""
        
        await message.answer(
            profile_text,
            parse_mode='Markdown',
            reply_markup=get_profile_inline_kb()
        )
    else:
        await message.answer(
            "❌ Не удалось загрузить профиль.\n"
            "Возможно, ты не зарегистрирован. Используй /start",
            reply_markup=main_kb
        )

@dp.message(Command("help"))
async def help_command(message: types.Message):
    """Справка"""
    if await check_user_blocked(message.from_user.id):
        await send_blocked_message(message)
        return
    
    await message.answer(
        "🆘 **Справка:**\n\n"
        "💌 Отправить поддержку - помочь кому-то\n"
        "🔥 Получить поддержку - получить добрые слова\n"
        "🆘 Нужна помощь - попросить поддержку\n"
        "🤝 Помочь кому-нибудь - ответить на чей-то запрос помощи\n"
        "👤 Профиль - посмотреть свою статистику и изменить никнейм\n\n"
        "🛡️ **Автофильтр:**\n"
        "Бот автоматически проверяет все сообщения на:\n"
        "• Нецензурные выражения (блокировка)\n"
        "• Оскорбления (блокировка)\n"
        "• Ссылки и рекламу (блокировка)\n"
        "• Спам (блокировка)",
        parse_mode='Markdown'
    )

@dp.callback_query(F.data == "help_respond")
async def handle_help_respond(callback: types.CallbackQuery, state: FSMContext):
    """Обработка кнопки 'Помочь'"""
    if await check_user_blocked(callback.from_user.id):
        await send_blocked_callback(callback)
        return
    
    data = await state.get_data()
    current_request = data.get("current_request")
    
    if current_request:
        # Экранируем никнейм для Markdown
        safe_current_nickname = escape_markdown(current_request['nickname'])
        await callback.message.answer(
            f"💝 Напиши сообщение поддержки для **{safe_current_nickname}**:\n\n"
            "💡 Совет: короткие искренние слова часто помогают больше длинных советов\n\n"
            "ℹ️ _После твоего ответа запрос будет удален из очереди_",
            parse_mode='Markdown'
        )
        # Переводим в состояние написания сообщения поддержки
        await state.set_state(UserStates.waiting_message)
        await state.update_data(action="support", help_recipient=current_request)
    else:
        await callback.message.answer("❌ Ошибка: данные запроса потеряны", reply_markup=main_kb)
        await state.clear()
    
    await callback.answer()

@dp.callback_query(F.data == "help_next")
async def handle_help_next(callback: types.CallbackQuery, state: FSMContext):
    """Обработка кнопки 'Дальше'"""
    if await check_user_blocked(callback.from_user.id):
        await send_blocked_callback(callback)
        return
    
    # Удаляем последние 2 сообщения (видео кружок + текст или просто текст + предыдущий текст)
    try:
        # Получаем ID текущего сообщения с кнопками
        current_message_id = callback.message.message_id
        
        # Удаляем текущее сообщение
        await bot.delete_message(chat_id=callback.message.chat.id, message_id=current_message_id)
        logger.info(f"Deleted current help message {current_message_id}")
        
        # Удаляем предыдущее сообщение (может быть видео кружок)
        await bot.delete_message(chat_id=callback.message.chat.id, message_id=current_message_id - 1)
        logger.info(f"Deleted previous message {current_message_id - 1}")
        
    except Exception as e:
        logger.warning(f"Failed to delete previous messages: {e}")
    
    # Показываем следующий запрос
    await show_help_request_simple(callback.message, state)
    await callback.answer()

@dp.callback_query(F.data == "help_menu")
async def handle_help_menu(callback: types.CallbackQuery, state: FSMContext):
    """Обработка кнопки 'Главное меню'"""
    if await check_user_blocked(callback.from_user.id):
        await send_blocked_callback(callback)
        return
    
    await callback.message.answer("🏠 Главное меню", reply_markup=main_kb)
    await state.clear()
    await callback.answer()

@dp.callback_query(F.data == "help_complaint")
async def handle_help_complaint(callback: types.CallbackQuery, state: FSMContext):
    """Обработка кнопки 'Пожаловаться'"""
    data = await state.get_data()
    current_request = data.get("current_request")
    
    if current_request:
        # Отправляем жалобу через API
        complaint_data = {
            "request_id": current_request['id'],
            "complainer_user_id": callback.from_user.id
        }
        
        logger.info(f"🚨 Submitting complaint for message {current_request['id']} by user {callback.from_user.id}")
        
        response = await api_request("submit_complaint", complaint_data)
        
        if response and response.get("status") == "success":
            complaints_count = response.get("complaints_count", 0)
            auto_blocked = response.get("auto_blocked", False)
            
            if auto_blocked:
                message_text = f"""🚨 **Жалоба подана**

Спасибо за обращение! Ваша жалоба рассмотрена.

🚫 **Пользователь автоматически заблокирован**
📊 Общее количество жалоб: **{complaints_count}**

💡 _Сообщение удалено из общей ленты_
🛡️ _Пользователь больше не сможет пользоваться ботом_"""
            else:
                message_text = f"""🚨 **Жалоба подана**

Спасибо за обращение! Мы рассмотрим ваше сообщение.

📊 Количество жалоб на этого пользователя: **{complaints_count}**

💡 _Сообщение удалено из общей ленты_"""
            
            await callback.message.answer(
                message_text,
                parse_mode='Markdown',
                reply_markup=main_kb
            )
            
            if auto_blocked:
                logger.warning(f"🚫 User auto-blocked notification sent for message {current_request['id']}, total complaints: {complaints_count}")
            else:
                logger.info(f"✅ Complaint successfully submitted for message {current_request['id']}, total complaints: {complaints_count}")
        else:
            await callback.message.answer(
                "❌ **Ошибка**\n\n"
                "Не удалось подать жалобу. Попробуйте позже.",
                parse_mode='Markdown',
                reply_markup=main_kb
            )
            logger.error(f"❌ Failed to submit complaint for message {current_request['id']}")
        
        await state.clear()
    else:
        await callback.message.answer("❌ Ошибка: данные сообщения потеряны", reply_markup=main_kb)
        await state.clear()
    
    await callback.answer()

@dp.callback_query(F.data == "change_nickname")
async def handle_change_nickname(callback: types.CallbackQuery, state: FSMContext):
    """Обработка кнопки 'Сменить никнейм'"""
    if await check_user_blocked(callback.from_user.id):
        await send_blocked_callback(callback)
        return
    
    # Отправляем новое сообщение для смены никнейма, не редактируя профиль
    await callback.message.answer(
        "✏️ **Смена никнейма**\n\n"
        "Введи новый никнейм (3-20 символов):\n\n"
        "💡 _Никнейм должен быть уникальным_",
        parse_mode='Markdown'
    )
    await state.set_state(UserStates.changing_nickname)
    await callback.answer()


async def show_toplist(message: types.Message, state: FSMContext):
    """Показать топ-лист пользователя"""
    if await check_user_blocked(message.from_user.id):
        await send_blocked_message(message)
        return
    
    user_id = message.from_user.id
    logger.info(f"Toplist button pressed by user {user_id}")
    
    # Получаем данные топ-листа через API с таймаутом
    try:
        result = await asyncio.wait_for(
            api_request("toplist", {"user_id": user_id}),
            timeout=10.0  # 10 секунд таймаут
        )
        logger.info(f"Toplist API result: {result}")
        
        if result.get("status") == "ok":
            toplist = result.get("toplist", [])
            user_position = result.get("user_position", 0)
            user_rating = result.get("user_rating", 0)
            
            # Формируем сообщение с топ-листом
            toplist_text = "🏆 **Топ лист лиги**\n\n"
            
            if toplist:
                for user in toplist:
                    position = user["position"]
                    nickname = escape_markdown(user["nickname"])
                    rating = user["rating"]
                    
                    # Добавляем эмодзи для первых трех мест
                    if position == 1:
                        position_emoji = "🥇"
                    elif position == 2:
                        position_emoji = "🥈"
                    elif position == 3:
                        position_emoji = "🥉"
                    else:
                        position_emoji = f"{position}."
                    
                    toplist_text += f"{position_emoji} **{nickname}** - {rating} ⭐\n"
            else:
                toplist_text += "_Пока никто не заработал рейтинг_\n"
            
            # Добавляем информацию о позиции пользователя
            if user_position > 10:
                toplist_text += f"\n📍 **Твое место:** {user_position} (рейтинг: {user_rating} ⭐)"
            elif user_position <= 10 and user_rating > 0:
                toplist_text += f"\n🎉 **Ты в топ-10!** (место: {user_position})"
            else:
                toplist_text += f"\n💪 **Твой рейтинг:** {user_rating} ⭐\n_Помогай людям, чтобы попасть в топ!_"
            
            await message.answer(
                toplist_text,
                parse_mode='Markdown',
                reply_markup=main_kb
            )
        else:
            # Если API вернул ошибку, показываем простое сообщение
            await message.answer(
                "🏆 **Топ лист**\n\n"
                "📊 Рейтинговая система в разработке.\n\n"
                "💡 _Помогай людям, чтобы заработать рейтинг!_",
                parse_mode='Markdown',
                reply_markup=main_kb
            )
    
    except asyncio.TimeoutError:
        logger.warning(f"Toplist API timeout for user {user_id}")
        await message.answer(
            "🏆 **Топ лист**\n\n"
            "⏰ Сервер временно недоступен.\n\n"
            "💡 _Попробуй позже!_",
            parse_mode='Markdown',
            reply_markup=main_kb
        )
    
    except Exception as e:
        logger.error(f"Toplist error for user {user_id}: {e}")
        await message.answer(
            "🏆 **Топ лист**\n\n"
            "📊 Рейтинговая система в разработке.\n\n"
            "💡 _Помогай людям, чтобы заработать рейтинг!_",
            parse_mode='Markdown',
            reply_markup=main_kb
        )












@dp.message()
async def unknown(message: types.Message, state: FSMContext):
    """Неизвестные сообщения"""
    if await check_user_blocked(message.from_user.id):
        await send_blocked_message(message)
        return
    
    # Проверяем все текстовые сообщения через фильтр
    if message.text:
        filter_result = message_filter.check_message(message.from_user.id, message.text, "text")
        if filter_result.is_blocked:
            await handle_filter_violation(message, filter_result)
            return
    
    await state.clear()
    await message.answer("🤔 Используй кнопки меню", reply_markup=main_kb)

async def main():
    """Запуск бота"""
    logger.info("Starting bot...")
    await dp.start_polling(bot, skip_updates=True)

if __name__ == "__main__":
    asyncio.run(main())