FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends libgomp1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements-prod.txt .

RUN python -m pip install --upgrade pip \
    && python -m pip install torch --index-url https://download.pytorch.org/whl/cpu \
    && python -m pip install -r requirements-prod.txt
    
COPY main.py rag.py ./
COPY static ./static
COPY sample_docs ./sample_docs

RUN useradd --create-home appuser \
    && mkdir -p /app/data \
    && chown -R appuser:appuser /app

ENV DATABASE_PATH=/app/data/chat_history.db
ENV CHROMA_DIRECTORY=/app/data/chroma_db
ENV HF_HOME=/app/data/huggingface

USER appuser

EXPOSE 8000

HEALTHCHECK \
    --interval=30s \
    --timeout=5s \
    --start-period=90s \
    --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=3)"

CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]