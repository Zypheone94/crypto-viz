FROM python:3

WORKDIR /app

ENV PYTHONUNBUFFERED=1

COPY ingestor/pyproject.toml ingestor/poetry.lock* ./ingestor/

RUN pip install --upgrade pip \
    && pip install --no-cache-dir ./ingestor \
    && pip install --no-cache-dir duckdb==0.10.3

COPY ingestor /app/ingestor

EXPOSE 8080

CMD ["uvicorn", "ingestor.scraper.main:app", "--host", "0.0.0.0", "--port", "8080"]