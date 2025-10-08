# Scraper Service

The **`scraper`** service contains the main API of the application.

## Structure

- `scraper/api/` – contains the API endpoints and related logic.  
- `scraper/main.py` – **entry point of the API**.

## Dependencies

- The `scraper` service uses dependencies defined in the **`pyproject.toml`** at the root of the project.  
- These dependencies are **shared with the `builder` service**, avoiding duplication.

## Running the API

The service runs via **FastAPI** and can be started using Docker Compose:

Inside the Docker container, the app listens on port **8000**, which is mapped to **8080** on your host machine.  

- Access the API at: [http://localhost:port]

## Documentation

FastAPI automatically provides **Swagger UI** for testing the API:

- Swagger UI: [http://localhost:port/docs]