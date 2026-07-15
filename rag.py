import os
from hashlib import sha256
from io import BytesIO
from pathlib import Path

import chromadb
from pypdf import PdfReader
from sentence_transformers import SentenceTransformer


DEFAULT_DATABASE_DIRECTORY = (
    Path(__file__).resolve().parent / "chroma_db"
)

DATABASE_DIRECTORY = Path(
    os.getenv(
        "CHROMA_DIRECTORY",
        str(DEFAULT_DATABASE_DIRECTORY),
    )
)

embedding_model = SentenceTransformer("BAAI/bge-small-zh-v1.5")

chroma_client = chromadb.PersistentClient(
    path=str(DATABASE_DIRECTORY),
)

knowledge_collection = chroma_client.get_or_create_collection(
    name="knowledge_base",
    metadata={"hnsw:space": "cosine"},
)


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

    knowledge_collection.delete(
        where={"filename": filename},
    )

    embeddings = embedding_model.encode(
        chunks,
        normalize_embeddings=True,
    ).tolist()

    ids = []
    metadatas = []

    for index, chunk in enumerate(chunks):
        chunk_id = sha256(
            f"{filename}-{index}".encode("utf-8")
        ).hexdigest()

        ids.append(chunk_id)

        metadatas.append(
            {
                "filename": filename,
                "chunk_id": index,
            }
        )

    knowledge_collection.add(
        ids=ids,
        documents=chunks,
        embeddings=embeddings,
        metadatas=metadatas,
    )

    return {
        "文件名": filename,
        "文字数量": len(text),
        "片段数量": len(chunks),
    }


def get_document_status():
    stored_data = knowledge_collection.get(
        include=["metadatas"],
    )

    metadatas = stored_data.get("metadatas") or []

    filenames = sorted(
        {
            metadata["filename"]
            for metadata in metadatas
            if metadata and "filename" in metadata
        }
    )

    return {
        "文档列表": filenames,
        "片段总数": knowledge_collection.count(),
    }


def search_documents(query, top_k=3):
    if not query.strip():
        return []

    total_chunks = knowledge_collection.count()

    if total_chunks == 0:
        return []

    query_embedding = embedding_model.encode(
        query,
        normalize_embeddings=True,
    ).tolist()

    search_result = knowledge_collection.query(
        query_embeddings=[query_embedding],
        n_results=min(top_k, total_chunks),
        include=["documents", "metadatas", "distances"],
    )

    documents = search_result["documents"][0]
    metadatas = search_result["metadatas"][0]
    distances = search_result["distances"][0]

    results = []

    for document, metadata, distance in zip(
        documents,
        metadatas,
        distances,
    ):
        score = max(0.0, 1.0 - distance)

        results.append(
            {
                "filename": metadata["filename"],
                "chunk_id": metadata["chunk_id"],
                "text": document,
                "score": round(score, 4),
            }
        )

    return results