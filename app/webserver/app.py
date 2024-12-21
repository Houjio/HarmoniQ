from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient

from pathlib import Path

db_path = Path(__file__) / "db/db.sqlite"
db_uri = f"sqlite:///{db_path}"

app = FastAPI()

# Add CORS middleware
origins = [
    "http://localhost:8080",
    "http://0.0.0.0:8080",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    app.state.client = AsyncIOMotorClient(db_uri)
    app.state.db = app.state.client.harmoniq

@app.on_event("shutdown")
async def shutdown_event():
    app.state.client.close()

@app.get("/")
async def index():
    return {"ping": "pong"}
