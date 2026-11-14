from pydantic import BaseModel
class StudyOutput(BaseModel):
    id:int
    code:str
    name:str
    description:str
    source:str
    default_alpha:float
    counts:dict
    feature_count:int
    supported:bool
    reason:str
