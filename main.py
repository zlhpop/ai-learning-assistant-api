import os
import sqlite3
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from openai import OpenAI
from pydantic import BaseModel

load_dotenv()

app = FastAPI(
    title="AI 学习助手 API",
    description="一个接入 DeepSeek 大模型的学习助手。",
    version="0.4.0",
)

DATABASE_PATH = "chat_history.db"


def init_database():
    with sqlite3.connect(DATABASE_PATH) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )


def save_message(session_id, role, content):
    with sqlite3.connect(DATABASE_PATH) as connection:
        connection.execute(
            """
            INSERT INTO messages (session_id, role, content)
            VALUES (?, ?, ?)
            """,
            (session_id, role, content),
        )


def get_history(session_id, limit=10):
    with sqlite3.connect(DATABASE_PATH) as connection:
        rows = connection.execute(
            """
            SELECT role, content
            FROM messages
            WHERE session_id = ?
            ORDER BY id DESC
            LIMIT ?
            """,
            (session_id, limit),
        ).fetchall()

    rows.reverse()

    return [
        {"role": role, "content": content}
        for role, content in rows
    ]


def count_messages(session_id):
    with sqlite3.connect(DATABASE_PATH) as connection:
        result = connection.execute(
            """
            SELECT COUNT(*)
            FROM messages
            WHERE session_id = ?
            """,
            (session_id,),
        ).fetchone()

    return result[0]


def clear_history(session_id):
    with sqlite3.connect(DATABASE_PATH) as connection:
        connection.execute(
            """
            DELETE FROM messages
            WHERE session_id = ?
            """,
            (session_id,),
        )


init_database()


class ChatRequest(BaseModel):
    session_id: str
    message: str


class ResetRequest(BaseModel):
    session_id: str


@app.get("/", summary="查看服务状态")
def home():
    return {"message": "AI 学习助手已启动"}


@app.post("/chat", summary="与 DeepSeek 学习助手聊天")
def chat(request: ChatRequest):
    api_key = os.getenv("DEEPSEEK_API_KEY")

    if not api_key:
        raise HTTPException(
            status_code=500,
            detail="未找到 DeepSeek API Key，请检查 .env 文件。",
        )

    client = OpenAI(
        api_key=api_key,
        base_url="https://api.deepseek.com",
    )

    try:
        history = get_history(request.session_id)

        messages = [
            {
                "role": "system",
                "content": "你是一名耐心的 AI 应用开发老师，用中文简洁回答。",
            }
        ]

        messages += history

        messages.append(
            {
                "role": "user",
                "content": request.message,
            }
        )

        completion = client.chat.completions.create(
            model="deepseek-chat",
            messages=messages,
        )

        reply = completion.choices[0].message.content

        save_message(request.session_id, "user", request.message)
        save_message(request.session_id, "assistant", reply)

        return {
            "会话 ID": request.session_id,
            "用户问题": request.message,
            "助手回答": reply,
            "已保存消息数": count_messages(request.session_id),
        }

    except Exception as error:
        raise HTTPException(
            status_code=502,
            detail=f"调用 DeepSeek 失败：{error}",
        ) from error


@app.post("/reset", summary="清空聊天记忆")
def reset_chat(request: ResetRequest):
    clear_history(request.session_id)

    return {
        "message": "指定会话的聊天记忆已清空",
        "会话 ID": request.session_id,
    }


@app.get("/history/{session_id}", summary="查看聊天记录")
def show_history(session_id: str):
    return {
        "会话 ID": session_id,
        "聊天记录": get_history(session_id, limit=50),
    }