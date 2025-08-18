from fastapi import APIRouter,Depends,HTTPException,status
from sqlalchemy.orm import Session 
from src.schema import schema
from src.database.database import SessionLocal
from sqlalchemy import or_
from src.schema import schema
from fastapi.responses import JSONResponse
from src.middleware.get_current_user import getCurrentUser
from src.agents.main import run
import nest_asyncio, asyncio
from src.models.user_model import Chat



nest_asyncio.apply()

chatRouter=APIRouter()
def get_db():
    db=SessionLocal()
    try:
        yield db #iterator hai
    finally:
        db.close()




@chatRouter.post("/chat")
async def ChatResult(user_request:schema.ChatInput,db:Session=Depends(get_db),user:dict=Depends(getCurrentUser)):
    print("Request By:",user)
    result = await run(user_request)
    new_chat=Chat(
        user_id=user["userid"],
        user_request=user_request.user_request,
        crewai_response=result
    )
    db.add(new_chat)
    db.commit()
    db.refresh(new_chat)
    return new_chat


@chatRouter.get("/gettingChats")
async def gettingChats(db:Session=Depends(get_db),user:dict=Depends(getCurrentUser)):
    chats=db.query(Chat).filter(Chat.user_id==user["userid"]).all()
    result = []
    for chat in chats:
        result.append({
            "id": chat.id,
            "user_request": chat.user_request,
            "crewai_response": chat.crewai_response
        })
    return result




