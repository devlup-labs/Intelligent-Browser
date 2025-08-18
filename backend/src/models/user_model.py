from sqlalchemy import Column,Integer,String,ForeignKey
from sqlalchemy.orm import relationship
from src.database.database import Base

# creating tabel in database

class User(Base):
    __tablename__="users"   
    id=Column(Integer,primary_key=True,index=True)
    username=Column(String,unique=True,index=True)
    email=Column(String,unique=True,index=True)
    hashed_password=Column(String,index=True)
    chats = relationship("Chat", back_populates="user")

class Chat(Base):
    __tablename__="chats"
    id=Column(Integer,primary_key=True,index=True)
    user_id=Column(Integer,ForeignKey("users.id"))
    user_request=Column(String,index=True)
    crewai_response=Column(String,index=True)
    user=relationship("User",back_populates="chats")