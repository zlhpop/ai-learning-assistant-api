import os
import sqlite3
from pathlib import Path
from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from rag import add_document, get_document_status, search_documents
from openai import OpenAI
from pydantic import BaseModel

load_dotenv()

app = FastAPI(
    title="AI 学习助手 API",
    description="一个接入 DeepSeek 大模型的学习助手。",
    version="0.4.0",
)

STATIC_DIRECTORY = Path(__file__).resolve().parent / "static"

app.mount(
    "/static",
    StaticFiles(directory=STATIC_DIRECTORY),
    name="static",
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


# 用于 POST /documents/search
class SearchRequest(BaseModel):
    query: str
    top_k: int = 3


# 用于 POST /rag/chat
class RAGChatRequest(BaseModel):
    session_id: str
    message: str
    top_k: int = 3


@app.get("/", include_in_schema=False)
def web_app():
    return FileResponse(STATIC_DIRECTORY / "index.html")


@app.get("/health", summary="查看服务状态")
def health():
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

@app.post("/documents/upload", summary="上传知识库文档")
async def upload_document(file: UploadFile = File(...)):
    try:
        content = await file.read()
        return add_document(file.filename, content)

    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        ) from error


@app.get("/documents", summary="查看知识库状态")
def show_documents():
    return get_document_status()

# 从知识库中检索与问题相关的文档片段
@app.post("/documents/search", summary="检索知识库文档")
def search_knowledge(request: SearchRequest):
    # 调用 rag.py 中的检索函数
    results = search_documents(
        query=request.query,
        top_k=request.top_k,
    )

    # 把检索结果返回给用户
    return {
        "问题": request.query,
        "检索数量": len(results),
        "相关片段": results,
    }

# 根据知识库资料回答问题
@app.post("/rag/chat", summary="根据知识库回答问题")
def rag_chat(request: RAGChatRequest):
    api_key = os.getenv("DEEPSEEK_API_KEY")

    if not api_key:
        raise HTTPException(
            status_code=500,
            detail="未找到 DeepSeek API Key，请检查 .env 文件。",
        )

    # 检索和用户问题相关的文档片段
    results = search_documents(
        query=request.message,
        top_k=request.top_k,
    )

    # 没有资料时，不让模型随意编造
    if not results:
        raise HTTPException(
            status_code=404,
            detail="知识库中没有找到相关资料。",
        )

    # 把检索到的片段整理成上下文
    context = "\n\n".join(
        f"[来源 {index}] 文件：{item['filename']}\n{item['text']}"
        for index, item in enumerate(results, start=1)
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
                "content": (
                    "你是一名知识库助手。"
                    "只能根据提供的知识库资料回答问题。"
                    "如果资料不足，必须明确说明资料中没有答案。"
                    "回答时请标明引用来源。"
                ),
            }
        ]

        messages += history

        # 把知识库资料和用户问题交给 DeepSeek
        messages.append(
            {
                "role": "user",
                "content": (
                    f"知识库资料：\n{context}\n\n"
                    f"用户问题：{request.message}"
                ),
            }
        )

        completion = client.chat.completions.create(
            model="deepseek-chat",
            messages=messages,
        )

        reply = completion.choices[0].message.content

        save_message(
            request.session_id,
            "user",
            request.message,
        )

        save_message(
            request.session_id,
            "assistant",
            reply,
        )

        return {
            "会话 ID": request.session_id,
            "用户问题": request.message,
            "助手回答": reply,
            "引用来源": [
                {
                    "文件名": item["filename"],
                    "片段编号": item["chunk_id"],
                    "匹配分数": item["score"],
                }
                for item in results
            ],
        }

    except Exception as error:
        raise HTTPException(
            status_code=502,
            detail=f"RAG 问答失败：{error}",
        ) from error