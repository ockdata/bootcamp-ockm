FROM python:3.11-slim AS base

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY shared/ shared/
COPY jobs/ jobs/

ARG JOB
ENV JOB=${JOB}

CMD ["sh", "-c", "python -m jobs.${JOB}.main"]
