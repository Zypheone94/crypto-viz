FROM python:3.12-slim

WORKDIR app

COPY ingestor/pyproject.toml .

RUN pip install --upgrade pip

RUN pip install no-cache-dir -e .

COPY ingestor/builder ./ingestor/builder