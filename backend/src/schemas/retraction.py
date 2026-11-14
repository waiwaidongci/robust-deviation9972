from pydantic import BaseModel,Field,ConfigDict
class RetractionInput(BaseModel):
    model_config=ConfigDict(extra="forbid")
    window_ids:list[int]=Field(min_length=1,max_length=2000)
    reason:str=Field(min_length=8,max_length=1500)
class RetractionOutput(BaseModel):
    id:int
    window_id:int
    study_id:int
    code:str
    split:str
    reason:str
    fingerprint:str
    stats:dict
    status:str
    progress:dict
    actor:str
    created_at:str
