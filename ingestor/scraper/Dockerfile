FROM python:3

WORKDIR app

COPY ingestor/pyproject.toml .

RUN pip install --upgrade pip

RUN pip install .

COPY ingestor/scraper ./ingestor/scraper