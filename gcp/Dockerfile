FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=8080

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# queries.sql is part of the runtime, not just documentation: main.py loads the
# named blocks from it at startup.
COPY main.py queries.sql ./

RUN useradd --create-home --uid 10001 retailiq \
    && chown -R retailiq:retailiq /app
USER retailiq

EXPOSE 8080

# Single worker: Cloud Run scales by instance, and streaming responses hold a
# connection for the length of a model call.
CMD exec uvicorn main:app --host 0.0.0.0 --port ${PORT} --workers 1 --timeout-keep-alive 65
