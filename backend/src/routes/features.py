from fastapi import APIRouter,Depends
from sqlalchemy.orm import Session
from ..config.database import get_db
from ..controllers.dependencies import current_user,roles
from ..constants.roles import Role
from ..schemas.feature import FeatureOutput
from ..services.feature_service import list_features
router=APIRouter(tags=['features'])
@router.get('/studies/{sid}/features',response_model=list[FeatureOutput])
def index(sid:int,db:Session=Depends(get_db),user=Depends(current_user)):return list_features(db,sid)
