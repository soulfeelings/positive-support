from fastapi import FastAPI
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional
import asyncpg

app = FastAPI()

DB_HOST = "localhost"
DB_PORT = 5432
DB_USER = "postgres"
DB_PASSWORD = "8998"
DB_NAME = "support_bot"

async def get_connection():
    return await asyncpg.connect(
        host=DB_HOST, port=DB_PORT,
        user=DB_USER, password=DB_PASSWORD,
        database=DB_NAME
    )

class SetNicknameRequest(BaseModel):
    user_id: int
    nickname: str

class SupportMessage(BaseModel):
    user_id: int
    text: Optional[str] = None
    file_id: Optional[str] = None
    type: str  # "text" or "voice"

class UserId(BaseModel):
    user_id: int

@app.post("/set_nickname")
async def set_nickname(data: SetNicknameRequest):
    conn = await get_connection()
    exists = await conn.fetchrow("SELECT 1 FROM users WHERE nickname = $1", data.nickname)
    if exists:
        await conn.close()
        return JSONResponse(content={"status": "error", "message": "Nickname already taken"})

    await conn.execute("""
        INSERT INTO users (user_id, nickname)
        VALUES ($1, $2)
        ON CONFLICT (user_id) DO UPDATE SET nickname = EXCLUDED.nickname
    """, data.user_id, data.nickname)
    await conn.close()
    return JSONResponse(content={"status": "success"})

@app.post("/send_support")
async def send_support(msg: SupportMessage):
    try:
        conn = await get_connection()
        await conn.execute("""
            INSERT INTO support_messages (user_id, message_text, file_id, type)
            VALUES ($1, $2, $3, $4)
        """, msg.user_id, msg.text, msg.file_id, msg.type)
        await conn.close()
        return JSONResponse(content={"status": "success"})
    except Exception as e:
        return JSONResponse(content={"status": "error", "message": str(e)}, status_code=500)

@app.post("/get_support")
async def get_support(data: UserId):
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

    await conn.execute("""
        INSERT INTO user_received_messages (user_id, message_id)
        VALUES ($1, $2)
    """, data.user_id, row["id"])
    await conn.close()

    return JSONResponse(content={
        "status": row["type"],
        "message": row["message_text"],
        "file_id": row["file_id"],
        "nickname": row["nickname"]
    })
