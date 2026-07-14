from io import BytesIO
from pathlib import Path

from pypdf import PdfReader


# 暂时在内存中保存切分后的文档片段
knowledge_chunks = []


# 把长文本切分成多个小段
def split_text(text, chunk_size=500, overlap=100):
    chunks = []
    start = 0

    while start < len(text):
        end = min(start + chunk_size, len(text))
        chunk = text[start:end].strip()

        if chunk:
            chunks.append(chunk)

        if end == len(text):
            break

        start = end - overlap

    return chunks


# 根据文件类型提取文字
def extract_text(filename, content):
    suffix = Path(filename).suffix.lower()

    if suffix == ".txt":
        return content.decode("utf-8-sig")

    if suffix == ".pdf":
        reader = PdfReader(BytesIO(content))

        return "\n".join(
            page.extract_text() or ""
            for page in reader.pages
        )

    raise ValueError("目前只支持 TXT 和 PDF 文件。")


# 提取并保存文档片段
def add_document(filename, content):
    text = extract_text(filename, content).strip()

    if not text:
        raise ValueError("没有从文件中提取到文字。")

    chunks = split_text(text)

    for index, chunk in enumerate(chunks):
        knowledge_chunks.append(
            {
                "filename": filename,
                "chunk_id": index,
                "text": chunk,
            }
        )

    return {
        "文件名": filename,
        "文字数量": len(text),
        "片段数量": len(chunks),
    }


# 返回当前知识库状态
def get_document_status():
    filenames = sorted(
        {item["filename"] for item in knowledge_chunks}
    )

    return {
        "文档列表": filenames,
        "片段总数": len(knowledge_chunks),
    }