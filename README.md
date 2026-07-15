# WorkBuddy AI 学习助手

基于 FastAPI、DeepSeek、Sentence Transformers 和 Chroma 构建的本地知识库问答系统。

用户可以上传 TXT 或 PDF 文档，系统会自动完成文本提取、文档切分、向量化和语义检索，并结合检索结果生成带引用来源的回答。

## 界面预览

### 知识库问答

![RAG 知识库问答页面](docs/images/chat-interface.png)

### 引用来源

![RAG 引用来源](docs/images/source-panel.png)

## 核心功能

- 支持 TXT 和 PDF 文档上传
- 自动提取并切分文档内容
- 使用 `BAAI/bge-small-zh-v1.5` 生成中文文本向量
- 使用 Chroma 持久化保存向量知识库
- 根据语义相似度检索相关文档片段
- 调用 DeepSeek 生成基于知识库的回答
- 返回引用文件、片段编号和匹配分数
- 使用 SQLite 保存多轮聊天记录
- 使用 `session_id` 隔离不同会话
- 提供知识库上传、问答和来源展示网页
- 自动生成 Swagger API 文档

## 技术栈

| 分类 | 技术 |
| --- | --- |
| 开发语言 | Python 3.12 |
| Web 框架 | FastAPI |
| ASGI 服务器 | Uvicorn |
| 大模型 | DeepSeek |
| Embedding 模型 | BAAI/bge-small-zh-v1.5 |
| 向量数据库 | Chroma |
| 数据库 | SQLite |
| 文档解析 | PyPDF |
| 前端 | HTML、CSS、JavaScript |
| API 文档 | Swagger UI |

## 系统流程

```mermaid
flowchart LR
    A[上传 TXT 或 PDF] --> B[提取文档文本]
    B --> C[文本切分]
    C --> D[Embedding 向量化]
    D --> E[保存到 Chroma]
    F[用户问题] --> G[问题向量化]
    G --> H[语义检索]
    E --> H
    H --> I[构建知识库上下文]
    I --> J[调用 DeepSeek]
    J --> K[生成回答和引用来源]
```

## 项目结构

```text
02_fastapi_intro/
├── static/
│   ├── app.js
│   ├── index.html
│   └── style.css
├── sample_docs/
│   └── rag_intro.txt
├── .env
├── .gitignore
├── main.py
├── rag.py
├── README.md
└── requirements.txt
```

`.env`、SQLite 数据库和 Chroma 本地数据不会提交到 GitHub。

## 安装项目

推荐使用 Python 3.12。

### 1. 创建虚拟环境

```powershell
py -3.12 -m venv .venv
```

### 2. 激活虚拟环境

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

### 3. 安装依赖

```powershell
python -m pip install -r requirements.txt
```

### 4. 配置环境变量

在项目根目录创建 `.env` 文件：

```env
DEEPSEEK_API_KEY=你的_DeepSeek_API_Key
```

请勿将真实 API Key 上传到 GitHub。

## 启动项目

```powershell
python -m uvicorn main:app --reload
```

启动后访问：

- 聊天网页：http://127.0.0.1:8000
- Swagger 文档：http://127.0.0.1:8000/docs
- 健康检查：http://127.0.0.1:8000/health

首次启动时需要加载 Embedding 模型，等待时间可能稍长。

## API 接口

| 请求方式 | 路径 | 功能 |
| --- | --- | --- |
| GET | `/health` | 查看服务状态 |
| POST | `/chat` | 普通 DeepSeek 多轮对话 |
| POST | `/reset` | 清空指定会话 |
| GET | `/history/{session_id}` | 查看聊天记录 |
| POST | `/documents/upload` | 上传知识库文档 |
| GET | `/documents` | 查看知识库状态 |
| POST | `/documents/search` | 语义检索文档 |
| POST | `/rag/chat` | 根据知识库回答问题 |

## RAG 问答示例

请求：

```json
{
  "session_id": "demo-user",
  "message": "怎样让人工智能参考自己的资料回答问题？",
  "top_k": 3
}
```

返回内容包括：

- 用户问题
- AI 助手回答
- 引用文件名
- 文档片段编号
- 语义匹配分数

## 项目亮点

- 从文档上传到回答生成，实现完整 RAG 数据链路
- 使用中文 Embedding 模型实现语义检索
- 使用 Chroma 持久化保存向量数据
- 通过来源信息提高回答的可追溯性
- 使用 SQLite 实现多轮会话记忆
- 同时提供 REST API 和可视化聊天页面
- 使用 Git 分支和 Pull Request 管理功能开发

## 后续计划

- 增加文档删除与知识库管理
- 增加流式回答
- 增加自动化测试
- 增加 Docker 部署
- 增加 Agent 工具调用能力