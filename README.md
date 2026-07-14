# AI 学习助手 API

基于 FastAPI、DeepSeek API 和 SQLite 开发的 AI 学习助手后端。

## 功能

- 调用 DeepSeek 大模型进行对话
- 支持多轮聊天记忆
- 使用 session_id 隔离不同会话
- 使用 SQLite 永久保存聊天记录
- 支持查看和清空聊天记录
- 自动生成 Swagger API 文档

## 技术栈

- Python
- FastAPI
- DeepSeek API
- SQLite
- Uvicorn

## 启动项目

安装依赖：

```powershell
python -m pip install -r requirements.txt