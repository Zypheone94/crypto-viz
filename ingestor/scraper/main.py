from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.routes import health
import os
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '../../.env'))

app = FastAPI()

angular_port = os.getenv("ANGULAR_PORT")
origins = [
    f'http://localhost:{angular_port}'
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)



app.include_router(health.router)

@app.get("/")
async def root():
    return {"message": "Hello World"}