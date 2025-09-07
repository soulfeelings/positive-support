import os
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional, List
import asyncpg
import logging
from achievements import AchievementSystem

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

# Конфигурация БД
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", "5432"))
DB_USER = os.getenv("DB_USER", "bot_user")
DB_PASSWORD = os.getenv("DB_PASSWORD", "8998")
DB_NAME = os.getenv("DB_NAME", "support_bot")

# Логируем конфигурацию при запуске
logger.info(f"📊 Database config: {DB_HOST}:{DB_PORT}, DB: {DB_NAME}, User: {DB_USER}")

async def get_connection():
    """Подключение к БД"""
    try:
        conn = await asyncpg.connect(
            host=DB_HOST, port=DB_PORT,
            user=DB_USER, password=DB_PASSWORD,
            database=DB_NAME
        )
        logger.info("🔗 Database connection successful")
        return conn
    except Exception as e:
        logger.error(f"❌ Database connection failed: {e}")
        raise

# Модели данных
class SetNickname(BaseModel):
    user_id: int
    nickname: str

class UserProfile(BaseModel):
    user_id: int

class HelpRequestQuery(BaseModel):
    user_id: int
    last_seen_id: Optional[int] = 0

class ToggleReminders(BaseModel):
    user_id: int

class ReminderMessageQuery(BaseModel):
    user_id: int
    last_seen_id: Optional[int] = 0

class Message(BaseModel):
    user_id: int
    text: Optional[str] = None
    file_id: Optional[str] = None
    message_type: str = "text"  # "text", "voice" или "video_note"

class ReminderSettings(BaseModel):
    user_id: int
    reminders_enabled: bool

class TopListQuery(BaseModel):
    user_id: int

class AchievementQuery(BaseModel):
    user_id: int

class CheckAchievementsQuery(BaseModel):
    user_id: int
    action: str
    data: Optional[dict] = {}

# API эндпоинты
@app.get("/")
async def index():
    return {"status": "API работает"}

@app.post("/set_nickname")
async def set_nickname(data: SetNickname):
    """Установка никнейма"""
    logger.info(f"🔍 API: Attempting to set nickname '{data.nickname}' for user {data.user_id}")
    
    try:
        conn = await get_connection()
        logger.info("🔗 Database connection established")
        
        # Проверяем, есть ли уже такой никнейм у другого пользователя
        existing_user = await conn.fetchrow(
            "SELECT user_id FROM users WHERE nickname = $1", 
            data.nickname
        )
        logger.info(f"🔍 Existing user check: {existing_user}")
        
        # Если никнейм занят другим пользователем - ошибка
        if existing_user and existing_user['user_id'] != data.user_id:
            await conn.close()
            logger.warning(f"❌ Nickname '{data.nickname}' already taken by user {existing_user['user_id']}")
            return {"status": "error", "message": "Nickname already taken"}
        
        # Если это тот же пользователь - просто обновляем (или ничего не делаем)
        if existing_user and existing_user['user_id'] == data.user_id:
            await conn.close()
            logger.info(f"✅ User already has this nickname: {data.user_id} -> {data.nickname}")
            return {"status": "success"}

        # Создание/обновление пользователя
        logger.info(f"💾 Creating/updating user {data.user_id} with nickname '{data.nickname}'")
        await conn.execute("""
            INSERT INTO users (user_id, nickname) VALUES ($1, $2)
            ON CONFLICT (user_id) DO UPDATE SET nickname = EXCLUDED.nickname
        """, data.user_id, data.nickname)
        
        # Проверяем, что данные действительно сохранились
        saved_user = await conn.fetchrow("SELECT nickname FROM users WHERE user_id = $1", data.user_id)
        logger.info(f"🔍 Verification check: {saved_user}")
        
        await conn.close()
        
        if saved_user and saved_user['nickname'] == data.nickname:
            logger.info(f"✅ User saved successfully: {data.user_id} -> {data.nickname}")
            return {"status": "success"}
        else:
            logger.error(f"❌ Failed to save user: {data.user_id}, saved: {saved_user}")
            return {"status": "error", "message": "Failed to save nickname"}
            
    except Exception as e:
        logger.error(f"❌ Exception in set_nickname: {type(e).__name__}: {e}")
        import traceback
        logger.error(f"❌ Traceback: {traceback.format_exc()}")
        return {"status": "error", "message": f"Database error: {str(e)}"}

@app.post("/profile")
async def get_profile(data: UserProfile):
    """Получение профиля"""
    try:
        conn = await get_connection()
        
        # Проверяем, существует ли столбец reminders_enabled
        column_exists = await conn.fetchval("""
            SELECT EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE table_name = 'users' AND column_name = 'reminders_enabled'
            )
        """)
        
        if column_exists:
            user = await conn.fetchrow(
                "SELECT user_id, nickname, is_blocked, reminders_enabled FROM users WHERE user_id = $1", 
                data.user_id
            )
        else:
            user = await conn.fetchrow(
                "SELECT user_id, nickname, is_blocked FROM users WHERE user_id = $1", 
                data.user_id
            )
        
        # Получаем рейтинг из таблицы ratings
        try:
            rating_row = await conn.fetchrow(
                "SELECT rating FROM ratings WHERE user_id = $1", 
                data.user_id
            )
            rating = rating_row["rating"] if rating_row else 0
        except:
            rating = 0
        
        # Получаем количество жалоб на пользователя
        complaints_count = await conn.fetchval(
            "SELECT COUNT(*) FROM complaints WHERE original_user_id = $1", 
            data.user_id
        ) or 0
        
        await conn.close()
        
        if user:
            # Определяем значение reminders_enabled
            if column_exists and "reminders_enabled" in user:
                reminders_enabled = user["reminders_enabled"] if user["reminders_enabled"] is not None else True
            else:
                reminders_enabled = True  # По умолчанию включены
            
            return {
                "status": "ok",
                "user_id": user["user_id"],
                "nickname": user["nickname"],
                "rating": rating,
                "complaints_count": complaints_count,
                "is_blocked": user["is_blocked"],
                "reminders_enabled": reminders_enabled
            }
        else:
            return {"status": "not_found"}
    except Exception as e:
        logger.error(f"Error in get_profile: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return {"status": "error"}

@app.post("/send_support")
async def send_support(data: Message):
    """Отправка поддержки"""
    try:
        conn = await get_connection()
        result = await conn.execute(
            "INSERT INTO messages (user_id, text, file_id, message_type, type) VALUES ($1, $2, $3, $4, 'support')",
            data.user_id, data.text, data.file_id, data.message_type
        )
        await conn.close()
        logger.info(f"✅ Support message saved: user_id={data.user_id}, type={data.message_type}")
        return {"status": "success"}
    except Exception as e:
        logger.error(f"Error: {e}")
        return {"status": "error"}

@app.post("/send_request")
async def send_request(data: Message):
    """Запрос помощи"""
    try:
        conn = await get_connection()
        result = await conn.execute(
            "INSERT INTO messages (user_id, text, file_id, message_type, type) VALUES ($1, $2, $3, $4, 'request')",
            data.user_id, data.text, data.file_id, data.message_type
        )
        await conn.close()
        logger.info(f"✅ Help request saved: user_id={data.user_id}, type={data.message_type}")
        return {"status": "success"}
    except Exception as e:
        logger.error(f"Error: {e}")
        return {"status": "error"}

@app.post("/get_support")
async def get_support(data: UserProfile):
    """Получение поддержки"""
    try:
        conn = await get_connection()
        message = await conn.fetchrow("""
            SELECT m.text, u.nickname 
            FROM messages m
            JOIN users u ON m.user_id = u.user_id
            WHERE m.type = 'support' AND m.user_id != $1
            ORDER BY RANDOM() LIMIT 1
        """, data.user_id)
        await conn.close()
        
        if message:
            return {
                "status": "text",
                "message": message["text"],
                "nickname": message["nickname"]
            }
        else:
            return {"status": "no_messages"}
    except Exception as e:
        logger.error(f"Error: {e}")
        return {"status": "error"}

@app.post("/get_help_request")
async def get_help_request(data: HelpRequestQuery):
    """Получение запроса помощи по порядку (FIFO)"""
    try:
        conn = await get_connection()
        
        # Сначала пытаемся найти сообщение с id > last_seen_id
        request = await conn.fetchrow("""
            SELECT m.id, m.text, m.file_id, m.message_type, u.nickname, m.user_id 
            FROM messages m
            JOIN users u ON m.user_id = u.user_id
            WHERE m.type = 'request' AND m.user_id != $1 AND m.id > $2
            ORDER BY m.id ASC LIMIT 1
        """, data.user_id, data.last_seen_id)
        
        # Если не найдено сообщение с id > last_seen_id, начинаем сначала
        if not request:
            request = await conn.fetchrow("""
                SELECT m.id, m.text, m.file_id, m.message_type, u.nickname, m.user_id 
                FROM messages m
                JOIN users u ON m.user_id = u.user_id
                WHERE m.type = 'request' AND m.user_id != $1
                ORDER BY m.id ASC LIMIT 1
            """, data.user_id)
            
            if request:
                logger.info(f"No more messages after id {data.last_seen_id}, starting from beginning for user {data.user_id}")
        
        await conn.close()
        
        if request:
            logger.info(f"Showing help request id={request['id']} to user {data.user_id}, last_seen_id was {data.last_seen_id}")
            return {
                "status": "ok",
                "request": {
                    "id": request["id"],
                    "text": request["text"],
                    "file_id": request["file_id"],
                    "message_type": request["message_type"],
                    "nickname": request["nickname"],
                    "user_id": request["user_id"]
                }
            }
        else:
            return {"status": "no_requests"}
    except Exception as e:
        logger.error(f"Error: {e}")
        return {"status": "error"}

@app.post("/delete_help_request")
async def delete_help_request(data: dict):
    """Удаление запроса помощи после ответа"""
    try:
        request_id = data.get("request_id")
        user_id = data.get("user_id")  # ID автора запроса
        
        conn = await get_connection()
        
        # Удаляем запрос помощи
        result = await conn.execute(
            "DELETE FROM messages WHERE id = $1 AND user_id = $2 AND type = 'request'",
            request_id, user_id
        )
        await conn.close()
        
        logger.info(f"✅ Help request deleted: id={request_id}, user_id={user_id}")
        return {"status": "success"}
        
    except Exception as e:
        logger.error(f"Error deleting help request: {e}")
        return {"status": "error"}

@app.post("/submit_complaint")
async def submit_complaint(data: dict):
    """Подача жалобы на сообщение"""
    try:
        request_id = data.get("request_id")
        complainer_user_id = data.get("complainer_user_id")
        
        conn = await get_connection()
        
        # Получаем данные сообщения, на которое жалуются
        message_data = await conn.fetchrow("""
            SELECT id, user_id, text, file_id, message_type, created_at
            FROM messages 
            WHERE id = $1 AND type = 'request'
        """, request_id)
        
        if not message_data:
            await conn.close()
            return {"status": "message_not_found"}
        
        # Переносим сообщение в таблицу жалоб
        await conn.execute("""
            INSERT INTO complaints (message_id, original_user_id, complainer_user_id, text, file_id, message_type, created_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
        """, 
            message_data["id"], 
            message_data["user_id"], 
            complainer_user_id,
            message_data["text"], 
            message_data["file_id"], 
            message_data["message_type"], 
            message_data["created_at"]
        )
        
        # Удаляем оригинальное сообщение из таблицы messages
        await conn.execute("DELETE FROM messages WHERE id = $1", request_id)
        
        # Проверяем количество жалоб на пользователя
        original_user_id = message_data["user_id"]
        complaints_count = await conn.fetchval(
            "SELECT COUNT(*) FROM complaints WHERE original_user_id = $1", 
            original_user_id
        ) or 0
        
        # Автоматическая блокировка при 5 или более жалобах
        auto_blocked = False
        if complaints_count >= 5:
            # Проверяем, не заблокирован ли уже пользователь
            is_already_blocked = await conn.fetchval(
                "SELECT is_blocked FROM users WHERE user_id = $1", 
                original_user_id
            )
            
            if not is_already_blocked:
                # Блокируем пользователя
                await conn.execute(
                    "UPDATE users SET is_blocked = TRUE WHERE user_id = $1", 
                    original_user_id
                )
                auto_blocked = True
                logger.warning(f"🚫 AUTO-BLOCKED user {original_user_id} after {complaints_count} complaints")
        
        await conn.close()
        
        logger.info(f"✅ Complaint submitted: message_id={request_id}, by_user={complainer_user_id}, complaints_total={complaints_count}")
        
        result = {"status": "success", "complaints_count": complaints_count}
        if auto_blocked:
            result["auto_blocked"] = True
            result["message"] = f"Пользователь автоматически заблокирован после {complaints_count} жалоб"
        
        return result
        
    except Exception as e:
        logger.error(f"Error submitting complaint: {e}")
        return {"status": "error"}

@app.post("/increment_rating")
async def increment_rating(data: UserProfile):
    """Увеличение рейтинга пользователя на +1"""
    try:
        conn = await get_connection()
        
        # Увеличиваем рейтинг на 1, создаем запись если ее нет
        await conn.execute("""
            INSERT INTO ratings (user_id, rating) VALUES ($1, 1)
            ON CONFLICT (user_id) DO UPDATE SET rating = ratings.rating + 1
        """, data.user_id)
        
        # Получаем новый рейтинг
        new_rating = await conn.fetchval(
            "SELECT rating FROM ratings WHERE user_id = $1", 
            data.user_id
        )
        
        await conn.close()
        
        logger.info(f"✅ Rating incremented for user {data.user_id}, new rating: {new_rating}")
        return {"status": "success", "new_rating": new_rating}
        
    except Exception as e:
        logger.error(f"Error incrementing rating: {e}")
        return {"status": "error"}

@app.post("/toggle_reminders")
async def toggle_reminders(data: ToggleReminders):
    """Переключение настройки напоминаний"""
    try:
        conn = await get_connection()
        
        # Проверяем, существует ли столбец reminders_enabled
        column_exists = await conn.fetchval("""
            SELECT EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE table_name = 'users' AND column_name = 'reminders_enabled'
            )
        """)
        
        if not column_exists:
            # Если столбца нет, добавляем его
            await conn.execute("ALTER TABLE users ADD COLUMN reminders_enabled BOOLEAN DEFAULT TRUE")
            logger.info(f"Added reminders_enabled column to users table")
        
        # Получаем текущее состояние напоминаний
        current_state = await conn.fetchval(
            "SELECT reminders_enabled FROM users WHERE user_id = $1", 
            data.user_id
        )
        
        if current_state is None:
            # Пользователь не найден
            user_exists = await conn.fetchval("SELECT EXISTS(SELECT 1 FROM users WHERE user_id = $1)", data.user_id)
            if not user_exists:
                await conn.close()
                return {"status": "error", "message": "User not found"}
            else:
                # Пользователь есть, но reminders_enabled NULL - устанавливаем TRUE
                current_state = True
                await conn.execute(
                    "UPDATE users SET reminders_enabled = TRUE WHERE user_id = $1",
                    data.user_id
                )
        
        # Переключаем состояние
        new_state = not current_state
        await conn.execute(
            "UPDATE users SET reminders_enabled = $1 WHERE user_id = $2",
            new_state, data.user_id
        )
        
        await conn.close()
        
        logger.info(f"✅ Reminders toggled for user {data.user_id}: {current_state} -> {new_state}")
        return {"status": "success", "reminders_enabled": new_state}
        
    except Exception as e:
        logger.error(f"Error toggling reminders: {e}")
        return {"status": "error"}

@app.post("/get_reminder_message")
async def get_reminder_message(data: ReminderMessageQuery):
    """Получение сообщения поддержки для напоминания (аналогично get_help_request)"""
    try:
        conn = await get_connection()
        
        # Сначала пытаемся найти сообщение с id > last_seen_id
        message = await conn.fetchrow("""
            SELECT m.id, m.text, m.file_id, m.message_type, u.nickname, m.user_id 
            FROM messages m
            JOIN users u ON m.user_id = u.user_id
            WHERE m.type = 'support' AND m.user_id != $1 AND m.id > $2
            ORDER BY m.id ASC LIMIT 1
        """, data.user_id, data.last_seen_id)
        
        # Если не найдено сообщение с id > last_seen_id, начинаем сначала
        if not message:
            message = await conn.fetchrow("""
                SELECT m.id, m.text, m.file_id, m.message_type, u.nickname, m.user_id 
                FROM messages m
                JOIN users u ON m.user_id = u.user_id
                WHERE m.type = 'support' AND m.user_id != $1
                ORDER BY m.id ASC LIMIT 1
            """, data.user_id)
            
            if message:
                logger.info(f"No more support messages after id {data.last_seen_id}, starting from beginning for user {data.user_id}")
        
        await conn.close()
        
        if message:
            logger.info(f"Reminder message found for user {data.user_id}: message_id={message['id']}")
            return {
                "status": "ok",
                "message": {
                    "id": message["id"],
                    "text": message["text"],
                    "file_id": message["file_id"],
                    "message_type": message["message_type"],
                    "nickname": message["nickname"],
                    "user_id": message["user_id"]
                }
            }
        else:
            return {"status": "no_messages"}
    except Exception as e:
        logger.error(f"Error getting reminder message: {e}")
        return {"status": "error"}

@app.get("/get_users_with_reminders")
async def get_users_with_reminders():
    """Получение списка пользователей с включенными напоминаниями"""
    try:
        conn = await get_connection()
        
        # Проверяем, существует ли столбец reminders_enabled
        column_exists = await conn.fetchval("""
            SELECT EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE table_name = 'users' AND column_name = 'reminders_enabled'
            )
        """)
        
        if column_exists:
            users = await conn.fetch("""
                SELECT user_id FROM users 
                WHERE (reminders_enabled = TRUE OR reminders_enabled IS NULL) AND is_blocked = FALSE
            """)
        else:
            # Если столбца нет, считаем что у всех напоминания включены
            users = await conn.fetch("""
                SELECT user_id FROM users 
                WHERE is_blocked = FALSE
            """)
        
        await conn.close()
        
        user_ids = [user["user_id"] for user in users]
        logger.info(f"Found {len(user_ids)} users with enabled reminders")
        
        return {"status": "ok", "user_ids": user_ids}
    except Exception as e:
        logger.error(f"Error getting users with reminders: {e}")
        return {"status": "error"}

@app.post("/toplist")
async def get_toplist(data: TopListQuery):
    """Получение топ-10 пользователей по рейтингу"""
    try:
        conn = await get_connection()
        
        # Получаем топ-10 пользователей по рейтингу
        top_users = await conn.fetch("""
            SELECT u.nickname, r.rating, u.user_id
            FROM ratings r
            JOIN users u ON r.user_id = u.user_id
            WHERE u.is_blocked = FALSE
            ORDER BY r.rating DESC
            LIMIT 10
        """)
        
        # Получаем позицию текущего пользователя в рейтинге
        user_position = await conn.fetchval("""
            SELECT COUNT(*) + 1
            FROM ratings r
            JOIN users u ON r.user_id = u.user_id
            WHERE u.is_blocked = FALSE AND r.rating > (
                SELECT COALESCE(r2.rating, 0)
                FROM ratings r2
                WHERE r2.user_id = $1
            )
        """, data.user_id)
        
        # Получаем рейтинг текущего пользователя
        user_rating = await conn.fetchval("""
            SELECT COALESCE(rating, 0) FROM ratings WHERE user_id = $1
        """, data.user_id)
        
        await conn.close()
        
        # Формируем список топ-10
        toplist = []
        for i, user in enumerate(top_users, 1):
            toplist.append({
                "position": i,
                "nickname": user["nickname"],
                "rating": user["rating"],
                "user_id": user["user_id"]
            })
        
        return {
            "status": "ok",
            "toplist": toplist,
            "user_position": user_position,
            "user_rating": user_rating
        }
        
    except Exception as e:
        logger.error(f"Error getting toplist: {e}")
        return {"status": "error", "message": str(e)}

@app.get("/health")
async def health():
    """Проверка здоровья"""
    try:
        conn = await get_connection()
        await conn.fetchval("SELECT 1")
        await conn.close()
        return {"status": "healthy"}
    except Exception as e:
        return JSONResponse({"status": "unhealthy"}, status_code=503)

# Эндпоинты для системы достижений
@app.post("/check_achievements")
async def check_achievements(data: CheckAchievementsQuery):
    """Проверка и выдача достижений пользователю"""
    try:
        conn = await get_connection()
        achievement_system = AchievementSystem(conn)
        
        # Проверяем достижения
        new_achievements = await achievement_system.check_achievements(
            data.user_id, 
            data.action, 
            **data.data
        )
        
        await conn.close()
        
        return {
            "status": "success",
            "new_achievements": new_achievements,
            "count": len(new_achievements)
        }
        
    except Exception as e:
        logger.error(f"Error checking achievements: {e}")
        return {"status": "error", "message": str(e)}

@app.post("/get_user_achievements")
async def get_user_achievements(data: AchievementQuery):
    """Получение достижений пользователя"""
    try:
        conn = await get_connection()
        achievement_system = AchievementSystem(conn)
        
        achievements = await achievement_system.get_user_achievements(data.user_id)
        stats = await achievement_system.get_achievement_stats(data.user_id)
        
        await conn.close()
        
        return {
            "status": "success",
            "achievements": achievements,
            "stats": stats
        }
        
    except Exception as e:
        logger.error(f"Error getting user achievements: {e}")
        return {"status": "error", "message": str(e)}


@app.post("/get_recent_achievements")
async def get_recent_achievements(data: AchievementQuery):
    """Получение последних достижений пользователя"""
    try:
        conn = await get_connection()
        achievement_system = AchievementSystem(conn)
        
        recent_achievements = await achievement_system.get_recent_achievements(data.user_id, limit=5)
        
        await conn.close()
        
        return {
            "status": "success",
            "recent_achievements": recent_achievements
        }
        
    except Exception as e:
        logger.error(f"Error getting recent achievements: {e}")
        return {"status": "error", "message": str(e)}

@app.get("/get_all_achievements")
async def get_all_achievements():
    """Получение всех доступных достижений"""
    try:
        from achievements_config import get_all_achievements
        achievements = get_all_achievements()
        
        return {
            "status": "success",
            "achievements": achievements
        }
        
    except Exception as e:
        logger.error(f"Error getting all achievements: {e}")
        return {"status": "error", "message": str(e)}

@app.post("/check_achievements_dynamic")
async def check_achievements_dynamic(data: CheckAchievementsQuery):
    """Динамическая проверка достижений без сохранения в БД"""
    try:
        conn = await get_connection()
        achievement_system = AchievementSystem(conn)
        
        # Проверяем достижения без сохранения
        earned_achievements = await achievement_system.check_achievements_dynamic(
            data.user_id, 
            **data.data
        )
        
        await conn.close()
        
        return {
            "status": "success",
            "achievements": earned_achievements,
            "count": len(earned_achievements)
        }
        
    except Exception as e:
        logger.error(f"Error checking dynamic achievements: {e}")
        return {"status": "error", "message": str(e)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)