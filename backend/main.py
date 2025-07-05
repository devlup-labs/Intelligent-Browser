from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app= FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class loginreq(BaseModel):
    email:str
    password:str

class signupreq(BaseModel):
    email:str
    password:str    


@app.post("/login")
def login(data:loginreq):
    if data.email== "text@gmail.com" and data.password =="abc123":
        return {"token": "fake-jwt-token"}

    else:
        raise HTTPException(status_code= 401, detail="invalid credentials")  



@app.post("/signup")
def signup(user: signupreq):
    print(f"Creating account with {user.email}")
    return {"message": "Signup successful"}      