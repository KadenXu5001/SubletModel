FROM node:20-bookworm-slim AS frontend-builder

WORKDIR /app/frontend

COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

COPY frontend/ ./
RUN npm run build


FROM python:3.13-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PORT=5000

RUN apt-get update \
    && apt-get install -y --no-install-recommends libgomp1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py main.py zillow_data.py zillow_json_to_csv.py count_zillow_area.py Procfile README.md ./
COPY models ./models
COPY data ./data
COPY templates ./templates
COPY --from=frontend-builder /app/frontend/dist ./frontend/dist

CMD ["sh", "-c", "gunicorn --bind 0.0.0.0:${PORT} app:app"]
