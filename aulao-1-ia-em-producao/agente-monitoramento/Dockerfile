FROM python:3.13-slim AS base

WORKDIR /app

# Install system deps for FAISS
RUN apt-get update && \
    apt-get install -y --no-install-recommends build-essential && \
    rm -rf /var/lib/apt/lists/*

COPY pyproject.toml .
RUN pip install --no-cache-dir .

COPY . .

ENV PYTHONPATH=/app
ENV PIPELINE_MODE=full
ENV LOG_LEVEL=INFO
ENV LOG_FORMAT=json

EXPOSE 8080

CMD ["python", "-m", "scripts.run_demo"]
