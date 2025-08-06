from fastapi import FastAPI
from dotenv import load_dotenv
from src.database.database import Base,engine
from src.routes.auth_routes import authRouter
from src.routes.chat_route import chatRouter
import os
from fastapi.middleware.cors import CORSMiddleware
load_dotenv()

Base.metadata.create_all(bind=engine)
app=FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(","),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Content-Type", "Authorization"],
)
app.include_router(authRouter,prefix="/auth")
app.include_router(chatRouter)


@app.get("/")
def hello():
    return "Hello World"