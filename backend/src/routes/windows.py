from fastapi import APIRouter,Depends
from sqlalchemy.orm import Session
from ..config.database import get_db
from ..controllers.dependencies import current_user,roles
from ..constants.roles import Role
from ..schemas.window import WindowOutput,WindowAnnotation
from ..schemas.retraction import RetractionInput,RetractionOutput
from ..services.window_service import list_windows,annotate
from ..services.retraction_service import retract_windows,list_retractions
router=APIRouter(tags=['windows'])
@router.get('/studies/{sid}/windows',response_model=list[WindowOutput])
def index(sid:int,db:Session=Depends(get_db),user=Depends(current_user)):return list_windows(db,sid)
@router.get('/studies/{sid}/retractions',response_model=list[RetractionOutput])
def retractions(sid:int,db:Session=Depends(get_db),user=Depends(current_user)):return list_retractions(db,sid)
@router.post('/windows/retract',response_model=list[RetractionOutput])
def retract(data:RetractionInput,db:Session=Depends(get_db),user=Depends(roles(Role.ADMIN,Role.ANALYST))):return retract_windows(db,data,user)
@router.patch('/windows/{wid}')
def update(wid:int,data:WindowAnnotation,db:Session=Depends(get_db),user=Depends(roles(Role.ADMIN,Role.ANALYST))):return annotate(db,wid,data,user)
