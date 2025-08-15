from sqlalchemy import Column,Integer,String

from src.database.database import Base

# creating tabel in database

class User(Base):
    __tablename__="users"   
    id=Column(Integer,primary_key=True,index=True)
    username=Column(String,unique=True,index=True)
    email=Column(String,unique=True,index=True)
    hashed_password=Column(String,index=True)
