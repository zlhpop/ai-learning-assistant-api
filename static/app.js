const documentInput = document.querySelector("#document-input");
const documentList = document.querySelector("#document-list");
const documentCount = document.querySelector("#document-count");
const uploadStatus = document.querySelector("#upload-status");
const messageList = document.querySelector("#message-list");
const messageInput = document.querySelector("#message-input");
const sendButton = document.querySelector("#send-button");
const resetButton = document.querySelector("#reset-button");
const connectionStatus = document.querySelector("#connection-status");
const sourcePanel = document.querySelector("#source-panel");
const sourceList = document.querySelector("#source-list");
const closeSourcesButton = document.querySelector("#close-sources");

const sessionId =
    localStorage.getItem("workbuddy_session_id") ||
    crypto.randomUUID();

localStorage.setItem("workbuddy_session_id", sessionId);


async function requestJson(url, options = {}) {
    const response = await fetch(url, options);
    const data = await response.json();

    if (!response.ok) {
        throw new Error(data.detail || "请求失败");
    }

    return data;
}


function scrollToLatestMessage() {
    messageList.scrollTop = messageList.scrollHeight;
}


function formatMessage(content) {
    const escaped = content
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;");

    return escaped
        .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
        .replaceAll("\n", "<br>");
}


function createMessage(role, content) {
    const article = document.createElement("article");
    const roleElement = document.createElement("div");
    const contentElement = document.createElement("div");

    article.className = `message ${role}-message`;
    roleElement.className = "message-role";
    contentElement.className = "message-content";

    roleElement.textContent = role === "user" ? "你" : "AI 助手";
    contentElement.innerHTML = formatMessage(content);

    article.append(roleElement, contentElement);
    messageList.appendChild(article);

    scrollToLatestMessage();

    return article;
}

function showSources(sources) {
    sourceList.replaceChildren();

    for (const source of sources) {
        const item = document.createElement("div");
        const filename = document.createElement("strong");
        const details = document.createElement("p");

        item.className = "source-item";
        filename.textContent = source["文件名"];
        details.textContent =
            `片段 ${source["片段编号"]} · 匹配分数 ${source["匹配分数"]}`;

        item.append(filename, details);
        sourceList.appendChild(item);
    }

    sourcePanel.hidden = false;
}


function addSourceButton(messageElement, sources) {
    if (!sources || sources.length === 0) {
        return;
    }

    const button = document.createElement("button");

    button.type = "button";
    button.className = "source-button";
    button.textContent = `查看 ${sources.length} 个引用来源`;

    button.addEventListener("click", () => {
        showSources(sources);
    });

    messageElement.appendChild(button);
}


async function loadDocuments() {
    try {
        const data = await requestJson("/documents");
        const documents = data["文档列表"] || [];

        documentList.replaceChildren();
        documentCount.textContent = `${documents.length} 个文档`;

        if (documents.length === 0) {
            const emptyState = document.createElement("p");

            emptyState.className = "empty-state";
            emptyState.textContent = "暂时没有文档";
            documentList.appendChild(emptyState);

            return;
        }

        for (const filename of documents) {
            const item = document.createElement("div");

            item.className = "document-item";
            item.title = filename;
            item.textContent = filename;

            documentList.appendChild(item);
        }
    } catch (error) {
        uploadStatus.className = "upload-status error";
        uploadStatus.textContent = error.message;
    }
}


async function uploadDocument(file) {
    const formData = new FormData();

    formData.append("file", file);

    uploadStatus.className = "upload-status";
    uploadStatus.textContent = "正在处理文档...";

    try {
        const data = await requestJson("/documents/upload", {
            method: "POST",
            body: formData,
        });

        uploadStatus.textContent =
            `上传成功，共生成 ${data["片段数量"]} 个片段`;

        await loadDocuments();
    } catch (error) {
        uploadStatus.className = "upload-status error";
        uploadStatus.textContent = error.message;
    } finally {
        documentInput.value = "";
    }
}


async function sendMessage() {
    const message = messageInput.value.trim();

    if (!message || sendButton.disabled) {
        return;
    }

    createMessage("user", message);

    messageInput.value = "";
    messageInput.style.height = "auto";
    sendButton.disabled = true;
    sendButton.textContent = "等待";

    const loadingMessage = createMessage(
        "assistant",
        "正在检索知识库并生成回答..."
    );

    loadingMessage.classList.add("loading-message");

    try {
        const data = await requestJson("/rag/chat", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify({
                session_id: sessionId,
                message,
                top_k: 3,
            }),
        });

        loadingMessage.remove();

        const answerMessage = createMessage(
            "assistant",
            data["助手回答"]
        );

        addSourceButton(
            answerMessage,
            data["引用来源"]
        );
    } catch (error) {
        loadingMessage.remove();

        createMessage(
            "assistant",
            `请求失败：${error.message}`
        );
    } finally {
        sendButton.disabled = false;
        sendButton.textContent = "发送";
        messageInput.focus();
    }
}


async function resetConversation() {
    resetButton.disabled = true;
    resetButton.textContent = "正在清空...";

    try {
        await requestJson("/reset", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify({
                session_id: sessionId,
            }),
        });

        messageList.replaceChildren();

        createMessage(
            "assistant",
            "当前对话已经清空，可以开始新的问题。"
        );

        sourcePanel.hidden = true;
    } catch (error) {
        createMessage(
            "assistant",
            `清空失败：${error.message}`
        );
    } finally {
        resetButton.disabled = false;
        resetButton.textContent = "清空当前对话";
    }
}

async function loadHistory() {
    try {
        const data = await requestJson(
            `/history/${encodeURIComponent(sessionId)}`
        );

        const history = data["聊天记录"];

        if (!history || history.length === 0) {
            return;
        }

        messageList.replaceChildren();

        for (const message of history) {
            createMessage(message.role, message.content);
        }
    } catch (error) {
        console.error("加载聊天记录失败：", error);
    }
}



async function checkConnection() {
    try {
        await requestJson("/health");

        connectionStatus.textContent = "服务已连接";
        connectionStatus.className = "connected";
    } catch {
        connectionStatus.textContent = "服务连接失败";
        connectionStatus.className = "error";
    }
}


documentInput.addEventListener("change", () => {
    const file = documentInput.files[0];

    if (file) {
        uploadDocument(file);
    }
});


sendButton.addEventListener("click", sendMessage);


resetButton.addEventListener("click", resetConversation);


closeSourcesButton.addEventListener("click", () => {
    sourcePanel.hidden = true;
});


messageInput.addEventListener("keydown", (event) => {
    if (event.key === "Enter" && !event.shiftKey) {
        event.preventDefault();
        sendMessage();
    }
});


messageInput.addEventListener("input", () => {
    messageInput.style.height = "auto";
    messageInput.style.height =
        `${Math.min(messageInput.scrollHeight, 150)}px`;
});


checkConnection();
loadDocuments();
loadHistory();
messageInput.focus();