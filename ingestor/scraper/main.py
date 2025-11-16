from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.routes import health
from api.routes.analytics import metrics
from api.routes.algo import average
from api.utils.middleware import Middleware
import os
from dotenv import load_dotenv

app = FastAPI()

env_path = os.path.join(os.path.dirname(__file__), '../../../.env')
load_dotenv(env_path)

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

app.add_middleware(Middleware)

app.include_router(health.router)
app.include_router(metrics.router)
app.include_router(average.router)
"""
REMINDER : You must start your api path by : 
- API (if you do something with the api, health, etc...)
- Scraper (if your working with the scraper)
- Builder (if your working with the scraper)
it is necessary for the service in the logger to work
"""


@app.get("/")
async def root():
    return {"message": "Hello World"}