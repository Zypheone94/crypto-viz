FROM python:3.12-slim

WORKDIR /app
ENV PYTHONPATH=/app

COPY ingestor/pyproject.toml .

RUN pip install --upgrade pip

RUN pip install --no-cache-dir -e .

RUN pip install duckdb --only-binary=:all:

COPY ingestor/scraper ./ingestor/scraper