from fastapi.testclient import TestClient

from main import app


client = TestClient(app)


def test_health():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "message": "AI 学习助手已启动"
    }


def test_web_page():
    response = client.get("/")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "WorkBuddy" in response.text


def test_document_status():
    response = client.get("/documents")
    data = response.json()

    assert response.status_code == 200
    assert "文档列表" in data
    assert "片段总数" in data
    assert isinstance(data["文档列表"], list)
    assert isinstance(data["片段总数"], int)


def test_reset_conversation():
    response = client.post(
        "/reset",
        json={
            "session_id": "pytest-session",
        },
    )

    assert response.status_code == 200
    assert response.json()["会话 ID"] == "pytest-session"


def test_reject_unsupported_document():
    response = client.post(
        "/documents/upload",
        files={
            "file": (
                "example.docx",
                b"invalid document",
                "application/octet-stream",
            )
        },
    )

    assert response.status_code == 400


def test_rag_request_validation():
    response = client.post(
        "/rag/chat",
        json={},
    )

    assert response.status_code == 422