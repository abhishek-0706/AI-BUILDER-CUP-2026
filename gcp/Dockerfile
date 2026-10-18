FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=8080

WORKDIR /app

COPY gcp/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# API and SQL
COPY gcp/main.py gcp/queries.sql gcp/fixtures.py gcp/synthetic.py ./

# Static frontend bundle
COPY index.html retail_data.js runtime-config.js commerce-api.js ./static/
COPY assets/ ./static/assets/
COPY brand/ ./static/brand/
# One small reference still supports the guided demo; no videos or tooling.
COPY demo/samples/shelf_compliant.jpg ./static/demo/samples/shelf_compliant.jpg

RUN useradd --create-home --uid 10001 retailiq \
    && chown -R retailiq:retailiq /app
USER retailiq

EXPOSE 8080

CMD exec uvicorn main:app --host 0.0.0.0 --port ${PORT} --workers 1 --timeout-keep-alive 65
