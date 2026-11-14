from pydantic import BaseModel
class FeatureOutput(BaseModel):
    id:int
    study_id:int
    code:str
    label:str
    unit:str
    position:int
    meaning:str
