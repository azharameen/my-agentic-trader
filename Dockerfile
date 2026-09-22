# =============================================================================
# NIFTY 100 Swing Trading Assistant — application image
# Single service: LangGraph pipeline + Telegram long-polling bot.
# =============================================================================
FROM python:3.11-slim AS base

# Prevent Python from writing .pyc files and buffer stdout/stderr for logs.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Create a non-root user and give it ownership of the working dir.
RUN groupadd -r trader && useradd -r -g trader -d /app -s /bin/bash trader
WORKDIR /app

# Install dependencies first to leverage Docker layer caching.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application source and compiled frontend assets.
COPY config ./config
COPY app ./app
COPY frontend/dist ./frontend/dist

# Create the data & logs directories and hand ownership to the non-root user.
RUN mkdir -p /app/data /app/logs && chown -R trader:trader /app
USER trader

# Entrypoint: the trading engine (LangGraph pipeline + Telegram bot).
CMD ["python", "-m", "app.main", "serve"]
