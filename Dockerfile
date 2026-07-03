FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
        gcc libpq-dev \
    && pip install --no-cache-dir uv \
    && apt-get purge -y gcc \
    && apt-get autoremove -y && apt-get clean && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY . /app

RUN uv sync --no-dev

EXPOSE 8000
ENTRYPOINT ["uv", "run", "sanic", "app.server:app", "--host", "0.0.0.0", "--port", "8000"]
