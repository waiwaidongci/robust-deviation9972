from typing import Literal
from pydantic import BaseModel,Field
class WindowOutput(BaseModel):
    id:int
    study_id:int
    code:str
    split:Literal['train','cal','test']
    values:dict
    note:str
class WindowAnnotation(BaseModel):
    note:str=Field(min_length=8,max_length=1500)
