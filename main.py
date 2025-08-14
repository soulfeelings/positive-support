import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional
import asyncpg
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve static files (for MiniApp.jsx)
app.mount("/static", StaticFiles(directory=".", check_dir=False), name="static")

@app.middleware("http")
async def add_cache_headers(request, call_next):
    response = await call_next(request)
    if request.url.path.startswith("/static/"):
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
    return response

@app.get("/", response_class=HTMLResponse)
async def index():
    # Simple page to host the mini app with UMD React and Babel
    return """
    <!doctype html>
    <html lang="ru">
    <head>
      <meta charset="utf-8" />
      <meta name="viewport" content="width=device-width, initial-scale=1" />
      <meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate" />
      <meta http-equiv="Pragma" content="no-cache" />
      <meta http-equiv="Expires" content="0" />
      <title>SupportCircle</title>
      <link rel="preconnect" href="https://unpkg.com" />
      <style>html,body,#root{height:100%}body{margin:0;background:#fff}</style>
    </head>
    <body>
      <div id="root"></div>
      <script crossorigin src="https://unpkg.com/react@18/umd/react.production.min.js"></script>
      <script crossorigin src="https://unpkg.com/react-dom@18/umd/react-dom.production.min.js"></script>
      <script src="https://unpkg.com/@babel/standalone/babel.min.js"></script>
      <script type="text/babel" data-presets="react" src="/static/MiniApp.jsx?v=1"></script>
    </body>
    </html>
    """

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", "5432"))
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "8998")
DB_NAME = os.getenv("DB_NAME", "support_bot")

async def get_connection():
    try:
        return await asyncpg.connect(
            host=DB_HOST, port=DB_PORT,
            user=DB_USER, password=DB_PASSWORD,
            database=DB_NAME
        )
    except Exception as e:
        logger.error(f"Database connection error: {e}")
        raise

class SetNicknameRequest(BaseModel):
    user_id: int
    nickname: str
    photo_url: Optional[str] = None
    city: Optional[str] = None

class SupportMessage(BaseModel):
    user_id: int
    text: Optional[str] = None
    file_id: Optional[str] = None
    type: str  # "text" or "voice"

class UserId(BaseModel):
    user_id: int

@app.post("/set_nickname")
async def set_nickname(data: SetNicknameRequest):
    try:
        conn = await get_connection()
        
        # Проверяем, не занят ли никнейм другим пользователем
        exists = await conn.fetchrow(
            "SELECT 1 FROM users WHERE nickname = $1 AND user_id <> $2", 
            data.nickname, data.user_id
        )
        if exists:
            await conn.close()
            return JSONResponse(content={"status": "error", "message": "Nickname already taken"})

        # Вставляем или обновляем пользователя
        await conn.execute("""
            INSERT INTO users (user_id, nickname, photo_url, city)
            VALUES ($1, $2, $3, $4)
            ON CONFLICT (user_id) DO UPDATE SET
              nickname = EXCLUDED.nickname,
              photo_url = COALESCE(EXCLUDED.photo_url, users.photo_url),
              city = COALESCE(EXCLUDED.city, users.city)
        """, data.user_id, data.nickname, data.photo_url, data.city)
        
        await conn.close()
        logger.info(f"Nickname set for user {data.user_id}: {data.nickname}")
        return JSONResponse(content={"status": "success"})
        
    except Exception as e:
        logger.error(f"Error setting nickname: {e}")
        return JSONResponse(content={"status": "error", "message": str(e)}, status_code=500)

class UserProfile(BaseModel):
    user_id: int

@app.post("/profile")
async def get_profile(payload: UserProfile):
    try:
        conn = await get_connection()
        
        # Пытаемся найти пользователя
        row = await conn.fetchrow("""
            SELECT u.user_id, u.nickname, u.photo_url, u.city,
                   COALESCE((SELECT COUNT(*) FROM support_messages sm WHERE sm.user_id = u.user_id), 0) AS score
            FROM users u WHERE u.user_id = $1
        """, payload.user_id)
        
        if not row:
            # Пользователь не найден - создаем с дефолтными значениями
            default_nickname = f"user_{payload.user_id}"
            await conn.execute("""
                INSERT INTO users (user_id, nickname, photo_url, city)
                VALUES ($1, $2, $3, $4)
            """, payload.user_id, default_nickname, None, None)
            
            # Возвращаем дефолтный профиль
            await conn.close()
            return JSONResponse(content={
                "status": "ok",
                "user_id": payload.user_id,
                "nickname": default_nickname,
                "photo_url": None,
                "city": None,
                "score": 0,
            })
        
        await conn.close()
        return JSONResponse(content={
            "status": "ok",
            "user_id": row["user_id"],
            "nickname": row["nickname"],
            "photo_url": row["photo_url"],
            "city": row["city"],
            "score": row["score"],
        })
        
    except Exception as e:
        logger.error(f"Error getting profile: {e}")
        return JSONResponse(content={"status": "error", "message": str(e)}, status_code=500)

@app.post("/send_support")
async def send_support(msg: SupportMessage):
    try:
        conn = await get_connection()
        
        # Проверяем, что пользователь существует, если нет - создаем
        user_exists = await conn.fetchrow("SELECT 1 FROM users WHERE user_id = $1", msg.user_id)
        if not user_exists:
            # Создаем пользователя с дефолтным никнеймом
            default_nickname = f"user_{msg.user_id}"
            await conn.execute("""
                INSERT INTO users (user_id, nickname, photo_url, city)
                VALUES ($1, $2, $3, $4)
            """, msg.user_id, default_nickname, None, None)
            logger.info(f"Created new user {msg.user_id} with default nickname {default_nickname}")
        
        # Вставляем сообщение поддержки
        await conn.execute("""
            INSERT INTO support_messages (user_id, message_text, file_id, type)
            VALUES ($1, $2, $3, $4)
        """, msg.user_id, msg.text, msg.file_id, msg.type)
        
        await conn.close()
        logger.info(f"Support message sent by user {msg.user_id}")
        return JSONResponse(content={"status": "success"})
        
    except Exception as e:
        logger.error(f"Error sending support: {e}")
        return JSONResponse(content={"status": "error", "message": str(e)}, status_code=500)

@app.post("/get_support")
async def get_support(data: UserId):
    try:
        conn = await get_connection()
        row = await conn.fetchrow("""
            SELECT sm.id, sm.message_text, sm.file_id, sm.type, u.nickname
            FROM support_messages sm
            JOIN users u ON sm.user_id = u.user_id
            WHERE sm.user_id != $1
            AND sm.id NOT IN (
                SELECT message_id FROM user_received_messages WHERE user_id = $1
            )
            ORDER BY RANDOM()
            LIMIT 1
        """ , data.user_id)

        if not row:
            await conn.close()
            return JSONResponse(content={"status": "no_messages"})

        # Отмечаем сообщение как полученное
        await conn.execute("""
            INSERT INTO user_received_messages (user_id, message_id)
            VALUES ($1, $2)
            ON CONFLICT (user_id, message_id) DO NOTHING
        """, data.user_id, row["id"])
        await conn.close()

        return JSONResponse(content={
            "status": row["type"],
            "message": row["message_text"],
            "file_id": row["file_id"],
            "nickname": row["nickname"]
        })
        
    except Exception as e:
        logger.error(f"Error getting support: {e}")
        return JSONResponse(content={"status": "error", "message": str(e)}, status_code=500)

class QueueRequest(BaseModel):
    user_id: int

@app.post("/queue_next")
async def queue_next(payload: QueueRequest):
    try:
        conn = await get_connection()
        
        # Проверяем, что пользователь существует, если нет - создаем
        user_exists = await conn.fetchrow("SELECT 1 FROM users WHERE user_id = $1", payload.user_id)
        if not user_exists:
            # Создаем пользователя с дефолтным никнеймом
            default_nickname = f"user_{payload.user_id}"
            await conn.execute("""
                INSERT INTO users (user_id, nickname, photo_url, city)
                VALUES ($1, $2, $3, $4)
            """, payload.user_id, default_nickname, None, None)
            logger.info(f"Created new user {payload.user_id} with default nickname {default_nickname}")
        
        # Получаем следующее сообщение из очереди
        row = await conn.fetchrow(
            """
            SELECT sm.id, sm.message_text, sm.file_id, sm.type, sm.created_at,
                   u.user_id as author_id, u.nickname, u.photo_url, u.city
            FROM support_messages sm
            JOIN users u ON sm.user_id = u.user_id
            WHERE sm.user_id <> $1
              AND sm.id NOT IN (
                SELECT message_id FROM user_received_messages 
                WHERE user_id = $1 AND message_id IS NOT NULL
              )
            ORDER BY sm.created_at DESC
            LIMIT 1
            """,
            payload.user_id,
        )

        if not row:
            await conn.close()
            return JSONResponse(content={"status": "empty"})

        # Отмечаем как показанное пользователю
        await conn.execute(
            """
            INSERT INTO user_received_messages (user_id, message_id)
            VALUES ($1, $2)
            ON CONFLICT (user_id, message_id) DO NOTHING
            """,
            payload.user_id,
            row["id"],
        )
        await conn.close()

        item = {
            "id": row["id"],
            "need": row["message_text"],
            "type": row["type"],
            "file_id": row["file_id"],
            "author_id": row["author_id"],
            "nickname": row["nickname"],
            "photo_url": row["photo_url"],
            "city": row["city"],
            "created_at": row["created_at"].isoformat() if row["created_at"] else None,
            "tags": [],  # Можно добавить систему тегов позже
        }
        
        logger.info(f"Queue item provided for user {payload.user_id}: message {row['id']}")
        return JSONResponse(content={"status": "ok", "item": item})
        
    except Exception as e:
        logger.error(f"Error getting queue next: {e}")
        return JSONResponse(content={"status": "error", "message": str(e)}, status_code=500)

@app.get("/health")
async def health_check():
    """Проверка состояния сервиса"""
    try:
        conn = await get_connection()
        await conn.fetchval("SELECT 1")
        await conn.close()
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        return JSONResponse(
            content={"status": "unhealthy", "database": "disconnected", "error": str(e)}, 
            status_code=503
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)