from pydantic import BaseModel,Field,constr


class UserCreateSignup(BaseModel):
    username:str = Field(...,min_length=1,) #...-->required with min length 1
    email:str = constr(strip_whitespace=True,min_length=1) # much better validation
    password:str= constr(strip_whitespace=True,min_length=1)

class UserOutput(BaseModel):
    id:int
    username:str
    email:str

    class Config:
        orm_mode = True #imp so that you can access user.username user.id otherwise error dega

class Token(BaseModel):
    access_token:str
    token_type:str


    