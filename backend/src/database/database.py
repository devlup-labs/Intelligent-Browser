from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker,declarative_base
from dotenv import load_dotenv
load_dotenv()
import os

#it tells ki multiple jagah se request nahi aayegi
engine=create_engine(os.getenv("DATABASE_URL"),connect_args={"check_same_thread": False})

SessionLocal=sessionmaker(bind=engine,autoflush=False,autocommit=False,)

Base=declarative_base()
