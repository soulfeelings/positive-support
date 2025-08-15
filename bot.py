import os
import asyncio
import logging
import aiohttp
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import KeyboardButton, ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = "8234250977:AAFSjY7Ci-xajOeB-JqRgWB2vTVtQaW9UCc"
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

if not BOT_TOKEN:
    logger.error("BOT_TOKEN not set!")
    exit(1)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

class UserStates(StatesGroup):
    waiting_nickname = State()
    waiting_message = State()
    viewing_help_request = State()

# Главная клавиатура
main_kb = ReplyKeyboardMarkup(keyboard=[
    [KeyboardButton(text="💌 Отправить поддержку"), KeyboardButton(text="🔥 Получить поддержку")],
    [KeyboardButton(text="🆘 Нужна помощь"), KeyboardButton(text="🤝 Помочь кому-нибудь")],
    [KeyboardButton(text="👤 Профиль")]
], resize_keyboard=True)

# Inline клавиатура для запросов помощи
def get_help_inline_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="❤️ Помочь", callback_data="help_respond"),
            InlineKeyboardButton(text="➡️ Дальше", callback_data="help_next")
        ],
        [InlineKeyboardButton(text="🏠 Главное меню", callback_data="help_menu")]
    ])



def escape_markdown(text: str) -> str:
    """Экранирует специальные символы для Markdown"""
    if not text:
        return text
    return text.replace('_', '\\_').replace('*', '\\*').replace('[', '\\[').replace(']', '\\]').replace('`', '\\`')

async def api_request(endpoint: str, data: dict):
    """Простой HTTP запрос к API"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(f"{BACKEND_URL}/{endpoint}", json=data) as response:
                    return await response.json()
    except Exception as e:
        logger.error(f"API error: {e}")
        return {"status": "error"}

@dp.message(Command("start"))
async def start(message: types.Message, state: FSMContext):
    """Команда старт"""
    user_id = message.from_user.id
    
    # Проверяем профиль
    profile = await api_request("profile", {"user_id": user_id})
    
    if profile.get("status") == "ok" and profile.get("nickname"):
        nickname = profile.get('nickname')
        await message.answer(
            f"👋 Привет, {nickname}!\nВыбери действие:",
            reply_markup=main_kb
        )
        await state.clear()
    else:
        await message.answer(
            "👋 Добро пожаловать!\nВведи свой никнейм (3-20 символов):"
        )
        await state.set_state(UserStates.waiting_nickname)

@dp.message(UserStates.waiting_nickname)
async def handle_nickname(message: types.Message, state: FSMContext):
    """Установка никнейма"""
    nickname = message.text.strip()

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

@dp.message(F.text == "💌 Отправить поддержку")
async def send_support(message: types.Message, state: FSMContext):
    """Отправить поддержку"""
    await message.answer("💝 Напиши сообщение поддержки:")
    await state.set_state(UserStates.waiting_message)
    await state.update_data(action="support")

@dp.message(F.text == "🆘 Нужна помощь")
async def need_help(message: types.Message, state: FSMContext):
    """Запросить помощь"""
    await message.answer(
        "💭 Расскажи, что случилось?\n\n"
        "📝 Можешь написать текстом или записать голосовое сообщение"
    )
    await state.set_state(UserStates.waiting_message)
    await state.update_data(action="help")

@dp.message(UserStates.waiting_message)
async def handle_message(message: types.Message, state: FSMContext):
    """Обработка текстовых и голосовых сообщений"""
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
    elif message.text:
        message_data = {
            "user_id": message.from_user.id,
            "text": message.text,
            "file_id": None,
            "message_type": "text"
        }
        content_description = "сообщение"
    else:
        await message.answer("❌ Пожалуйста, отправь текст или голосовое сообщение", reply_markup=main_kb)
        await state.clear()
        return
    
    # Отправляем в зависимости от действия
    if action == "support":
        help_recipient = data.get("help_recipient")
        
        if help_recipient:
            # Отправляем ответ конкретному человеку
            result = await api_request("send_support", message_data)
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

@dp.message(F.text == "🔥 Получить поддержку")
async def get_support(message: types.Message):
    """Получить поддержку"""
    result = await api_request("get_support", {"user_id": message.from_user.id})
    
    if result.get("status") == "text":
        await message.answer(f"💬 {result['message']}\n\n👤 От: {result['nickname']}")
    else:
        await message.answer("😔 Пока нет сообщений поддержки")

@dp.message(F.text == "🤝 Помочь кому-нибудь")
async def help_someone(message: types.Message, state: FSMContext):
    """Показать случайный запрос помощи"""
    result = await api_request("get_help_request", {"user_id": message.from_user.id})
    
    if result.get("status") == "ok":
        request_data = result["request"]
        
        # Сохраняем данные запроса в состоянии
        await state.update_data(current_request=request_data)
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
        else:
            # Отправляем текстовое сообщение
            # Экранируем никнейм и текст для Markdown
            safe_request_nickname = escape_markdown(request_data['nickname'])
            safe_request_text = escape_markdown(request_data['text'])
            await message.answer(
                f"🆘 **{safe_request_nickname}** просит помощи:\n\n"
                f"💭 _{safe_request_text}_\n\n"
                f"❤️ Хочешь помочь этому человеку?",
                reply_markup=get_help_inline_kb(),
                parse_mode='Markdown'
            )
    else:
        await message.answer(
            "😇 Пока никто не просит помощи!\n\n"
            "✨ Проверь позже.",
            reply_markup=main_kb
        )

@dp.message(F.text == "👤 Профиль")
async def show_profile(message: types.Message):
    """Показать профиль пользователя"""
    user_id = message.from_user.id
    
    # Получаем профиль пользователя
    profile = await api_request("profile", {"user_id": user_id})
    
    if profile.get("status") == "ok":
        nickname = profile.get("nickname", "Неизвестно")
        
        # Экранируем специальные символы в никнейме для Markdown
        safe_nickname = escape_markdown(nickname)
        
        profile_text = f"""👤 **Твой профиль**

📛 Никнейм: **{safe_nickname}**
⭐ Рейтинг: _временно не доступно_
🏆 Лига: _временно не доступно_
📊 Статус: _временно не доступно_

💌 Отправлено сообщений: _временно не доступно_
🤝 Помогли людям: _временно не доступно_"""
        
        await message.answer(
            profile_text,
            parse_mode='Markdown'
        )
        logger.info(f"Profile shown for user {user_id}: {nickname}")
    else:
        await message.answer(
            "❌ Не удалось загрузить профиль.\n"
            "Возможно, ты не зарегистрирован. Используй /start",
            reply_markup=main_kb
        )

@dp.message(Command("help"))
async def help_command(message: types.Message):
    """Справка"""
    await message.answer(
        "🆘 **Справка:**\n\n"
        "💌 Отправить поддержку - помочь кому-то\n"
        "🔥 Получить поддержку - получить добрые слова\n"
        "🆘 Нужна помощь - попросить поддержку\n"
        "🤝 Помочь кому-нибудь - ответить на чей-то запрос помощи\n"
        "👤 Профиль - посмотреть свою статистику",
        parse_mode='Markdown'
    )

@dp.callback_query(F.data == "help_respond")
async def handle_help_respond(callback: types.CallbackQuery, state: FSMContext):
    """Обработка кнопки 'Помочь'"""
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
    # Показываем следующий запрос
    await help_someone(callback.message, state)
    await callback.answer()

@dp.callback_query(F.data == "help_menu")
async def handle_help_menu(callback: types.CallbackQuery, state: FSMContext):
    """Обработка кнопки 'Главное меню'"""
    await callback.message.answer("🏠 Главное меню", reply_markup=main_kb)
    await state.clear()
    await callback.answer()



@dp.message()
async def unknown(message: types.Message):
    """Неизвестные сообщения"""
    await message.answer("🤔 Используй кнопки меню", reply_markup=main_kb)

async def main():
    """Запуск бота"""
    logger.info("Starting bot...")
    await dp.start_polling(bot, skip_updates=True)

if __name__ == "__main__":
    asyncio.run(main())