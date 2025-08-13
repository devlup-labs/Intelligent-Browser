from argon2 import PasswordHasher, exceptions
#better than bcrypt. Bycrpt is a hasing algorithm manlo aage jake algo change karna ho to isliye hum ye use karte
from datetime import datetime,timedelta
from fastapi import HTTPException
from jose import jwt,JWTError,ExpiredSignatureError
import os
from dotenv import load_dotenv


load_dotenv()


# need to create a context ki kaunse algo se password hash hoga 
  #bycrpt khudse salt add karke round decide karke hash kar dega and later on agar hashing algo change hua to sare password jo bycrpt se hue the vo deprecate ho jayenge aur dusre algo ke acc change ho jayenge



ph = PasswordHasher()

def hash_password(password: str) -> str:
    return ph.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return ph.verify(hashed_password, plain_password)
    except exceptions.VerifyMismatchError:
        return False

# ALGORITHM=(os.getenv("ALGORITHM"))
# EXPIRY_TIME=(int)(os.getenv("ACCESS_TOKEN_EXPIRY"))
SECRET_KEY=os.getenv("SECRET_KEY")

def generate_access_token(data:dict):  #dictionary python ka json hota hai ek tarah se object jaisa key:value pair . data user ki info like username ya userid
    payload=data.copy() #copy isliye kar rahe taki og me change na aaye
    #need to add expiry date here only in payload
    expiry_time = datetime.utcnow() + timedelta(minutes=30) #jab issue kia tabse 30 min
    payload.update({"exp":expiry_time})
    access_token=jwt.encode(payload,SECRET_KEY,algorithm="HS256")   
    print("AccessToken Giving:",access_token) 
    return access_token

#NOTE:So JWTs are passed around and stored as strings — nothing fancy. having three parts header.payload.signature
def validate_token(access_token:str):
    try:
        payload=jwt.decode(access_token,SECRET_KEY,algorithms=os.getenv("ALGORITHM"))
        return payload.get("subject") #ye data jis format me bheja se vaha se aayega {"subject":{"username":"aryan","id":"12324354657"}}        
    except ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired!Login Again")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token.Login Again")
    
