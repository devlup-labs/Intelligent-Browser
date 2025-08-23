from fastapi import APIRouter,Depends,HTTPException,status,WebSocket,WebSocketDisconnect
from sqlalchemy.orm import Session 
from src.schema import schema
from src.database.database import SessionLocal
from sqlalchemy import or_
from src.schema import schema
from fastapi.responses import JSONResponse
from src.middleware.get_current_user import getCurrentUser
from src.agents.main import run
# Update the import path below if connection_manager.py is in a different location
from src.utils.connection_manager import manager

import nest_asyncio

nest_asyncio.apply()

chatRouter=APIRouter()



def get_db():
    db=SessionLocal()
    try:
        yield db #iterator hai
    finally:
        db.close()



@chatRouter.websocket("/websocket")
async def websocket_endpoint(websocket:WebSocket):
    print("Came to correct place")
    await manager.connect(websocket)

    try:
        while True:
            user_request=await websocket.receive_text()
            await run(user_request)

    except WebSocketDisconnect:
        manager.disconnect(websocket)

        



# @chatRouter.post("/chat")
# async def ChatResult(user_request:schema.ChatInput,db:Session=Depends(get_db),user:dict=Depends(getCurrentUser)):
#     print("Request By:",user)
#     result = await run(user_request)
#     output=result
#     return JSONResponse(content=result)

