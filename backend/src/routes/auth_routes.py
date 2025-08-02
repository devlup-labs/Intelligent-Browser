from fastapi import APIRouter,Depends,HTTPException,status
from sqlalchemy.orm import Session 
from fastapi.security import OAuth2PasswordRequestForm
from src.controllers import auth
from src.models.user_model import User
from src.schema import schema
from src.database.database import SessionLocal
from sqlalchemy import or_


authRouter=APIRouter()

def get_db():
    db=SessionLocal()
    try:
        yield db
    finally:
        db.close()



@authRouter.post("/signup",response_model=schema.UserOutput) 
def signup(user:schema.UserCreateSignup,db:Session=Depends(get_db)): 
    existing_user=db.query(User).filter(or_(
        User.username==user.username,
        User.email==user.email
    )).first()
    if(existing_user):
        raise HTTPException(
    
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username or Email already Exists!"
        )
    #No user Exist means new user
    hashedPassword=auth.hash_password(user.password)

    new_user = User(
        username=user.username,
        email=user.email,
        hashed_password=hashedPassword,
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user) #updates the object with DB-generated fields like id
    print("New user Created")
	
    return new_user # response_model filters the output

# NOTE: OAuth2PasswordRequestForm expects 'username' field - frontend should send email as username
@authRouter.post("/login",response_model=schema.Token)
def login(form_data:OAuth2PasswordRequestForm=Depends(),db:Session=Depends(get_db)):


    if not form_data.username.strip() or not form_data.password.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email and Password cannot be empty! "
        )
    user=db.query(User).filter(User.email==form_data.username).first()

    if not user or not auth.verify_password(form_data.password,user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,detail="Invalid Credentials")
    
    access_token=auth.generate_access_token({
        "subject":{
            "username":user.username,
            "userid":user.id
        }
        })
    # Frontend should store this securely (consider httpOnly cookies for better security)  
    return {
        "access_token":access_token,
        "token_type":"bearer"
    }