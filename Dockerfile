# Multi-stage Dockerfile for Supply Chain AI Platform
FROM python:3.12-slim

# Install system dependencies for PostgreSQL, build tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python requirements
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copy source tree
COPY . /app/

# Environment defaults
ENV PYTHONUNBUFFERED=1 \
    DJANGO_SETTINGS_MODULE=supply_chain_ai.settings

EXPOSE 8000

CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
