from fastapi import HTTPException
from ..models import ClimateWindow
from ..utils.serialize import record
from .study_service import get_study
from .audit_service import log
from .retraction_service import retracted_window_ids

def list_windows(db,sid):
    get_study(db,sid);retracted=retracted_window_ids(db,sid)
    return [{**record(w),"retracted":w.id in retracted} for w in db.query(ClimateWindow).filter_by(study_id=sid).order_by(ClimateWindow.code)]
def annotate(db,wid,data,user):
    row=db.get(ClimateWindow,wid)
    if not row:raise HTTPException(404,"窗口不存在")
    row.note=data.note;log(db,user.email,"window.annotate",wid);db.commit();return record(row)
