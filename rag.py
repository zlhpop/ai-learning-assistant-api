from io import BytesIO
from pathlib import Path

from pypdf import PdfReader


knowledge_chunks = []


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

def add_document(filename, content):
    text = extract_text(filename, content).strip()

    if not text:
        raise ValueError("没有从文件中提取到文字。")

    chunks = split_text(text)

    # 再次上传同名文件时，先删除旧片段，避免重复
    knowledge_chunks[:] = [
        item
        for item in knowledge_chunks
        if item["filename"] != filename
    ]

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

    return {
        "文件名": filename,
        "文字数量": len(text),
        "片段数量": len(chunks),
    }


def get_document_status():
    filenames = sorted(
        {item["filename"] for item in knowledge_chunks}
    )

    return {
        "文档列表": filenames,
        "片段总数": len(knowledge_chunks),
    }


# 本次新增：把文本转换成连续两个字符组成的关键词集合
def create_terms(text):
    normalized = "".join(
        character.lower()
        for character in text
        if character.isalnum()
    )

    if len(normalized) < 2:
        return {normalized} if normalized else set()

    return {
        normalized[index:index + 2]
        for index in range(len(normalized) - 1)
    }


# 本次新增：根据关键词重合程度检索相关文档片段
def search_documents(query, top_k=3):
    query_terms = create_terms(query)
    results = []

    if not query_terms:
        return results

    for item in knowledge_chunks:
        chunk_terms = create_terms(item["text"])
        matched_terms = query_terms & chunk_terms
        score = len(matched_terms) / len(query_terms)

        if score > 0:
            results.append(
                {
                    "filename": item["filename"],
                    "chunk_id": item["chunk_id"],
                    "text": item["text"],
                    "score": round(score, 4),
                }
            )

    results.sort(
        key=lambda item: item["score"],
        reverse=True,
    )

    return results[:top_k]