from fastapi import FastAPI
from api.routes import health

app = FastAPI()

app.include_router(health.router)

@app.get("/")
async def root():
    return {"message": "Hello World"}