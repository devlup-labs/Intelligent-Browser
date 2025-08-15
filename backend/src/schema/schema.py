from typing import List, Optional,Literal
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
        model_config = {
        "from_attributes": True
    } #imp so that you can access user.username user.id otherwise error dega

class Token(BaseModel):
    access_token:str
    token_type:str


class ChatInput(BaseModel):
    user_request:str


class ChatOutputFormat(BaseModel):
    status:str


    
class ExecutionOutput(BaseModel):

    status: Literal["SUCCESS", "FAILURE", "PARTIAL_FAILURE"] = Field(..., description="The execution status of the task.") #... means field required
    step_description: str
    result_summary: str 
    error_details: Optional[str] = Field(default=None)
    suggestions_for_planner: Optional[str] = Field(default=None)
    outputs_created: List[str] = Field(default_factory=list)
    next_step_context: Optional[str] = Field(default=None)

