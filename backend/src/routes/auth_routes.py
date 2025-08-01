from fastapi import APIRouter,Depends,HTTPException,status
from sqlalchemy.orm import Session #database a session create karne ke liye (ek tarah se ye type hai db session ka)
from fastapi.security import OAuth2PasswordRequestForm # (form-data lane ke liye)
#  OAuth2AuthorizationCodeBearer: Used for third-party OAuth2 flows like Google, GitHub, etc.
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

#NOTE:signup me pydantic model hi use kar rahe jsime json data accpet kar rahe par login me stricly form-data le rahe jo standard hai in like with google github me bhi kaam kar jaye isliye
    # login ke liye bhi pydnatic model define karke json data le sakte hai ye method jyada compatible hai      

#since yaha pe db call lagegi db ka session chaiye to use it as middleware
@authRouter.post("/signup",response_model=schema.UserOutput) #ye response_model will check ki jo fields UserOutput me diye hai bas vahi jaye baki sensitive info like password na jaye aur ye json ke tarah bhi usko parse kar deta hai
def signup(user:schema.UserCreateSignup,db:Session=Depends(get_db)): # get_db database ka sesssion return karega of type Session jo ki db me assign ho jayega
    #no need to check if all fields present as pydantic already did that

    print("In signup backend : ",user)
    existing_user=db.query(User).filter(or_(
        User.username==user.username,
        User.email==user.email
    )).first()  #very imp to do .first varna sql query return kar dega jaisa node me await na use  karne par hota hai
    # print("existing_user",existing_user.username)
    if(existing_user):
        print("User Exist")
        raise HTTPException(
    
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username or Email already Exists!"
        )
    print("No existing User")
    hashedPassword=auth.hash_password(user.password)

    new_user = User(
        username=user.username,
        email=user.email,
        hashed_password=hashedPassword,
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    print("New user Created")
	# Re-fetches the object from the DB and updates it in memory varna shayd id none reh jaye jasie apan nodejs me vapas fetch karte the taki updated user mile
    return new_user # only those fields allowed by pydantic model will be returned


#NOTE:OAuth2PasswordRequestForm internally needs username and password only to agar email bhi bhejna hai under username hi bhejna padega in frontend
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
    #store this in local storage in frontend    
    return {
        "access_token":access_token,
        "token_type":"bearer"
    }