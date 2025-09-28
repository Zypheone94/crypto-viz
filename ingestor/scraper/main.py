from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.routes import health
from api.utils.middleware import Middleware

app = FastAPI()

origins = [
    'http://localhost:4200'
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