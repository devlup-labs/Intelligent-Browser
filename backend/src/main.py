from fastapi import FastAPI
from dotenv import load_dotenv
from src.database.database import Base,engine
from src.routes.auth_routes import authRouter

from fastapi.middleware.cors import CORSMiddleware
load_dotenv()

Base.metadata.create_all(bind=engine)
app=FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(authRouter,prefix="/auth")



@app.get("/")
def hello():
    return "Hello World"