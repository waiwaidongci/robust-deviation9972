from fastapi import APIRouter,Depends
from sqlalchemy.orm import Session
from ..config.database import get_db
from ..controllers.dependencies import current_user,roles
from ..constants.roles import Role
from ..schemas.window import WindowOutput,WindowAnnotation
from ..services.window_service import list_windows,annotate
router=APIRouter(tags=['windows'])
@router.get('/studies/{sid}/windows',response_model=list[WindowOutput])
def index(sid:int,db:Session=Depends(get_db),user=Depends(current_user)):return list_windows(db,sid)
@router.patch('/windows/{wid}')
def update(wid:int,data:WindowAnnotation,db:Session=Depends(get_db),user=Depends(roles(Role.ADMIN,Role.ANALYST))):return annotate(db,wid,data,user)
