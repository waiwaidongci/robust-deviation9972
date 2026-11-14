from fastapi import HTTPException
from ..models import ArchiveStudy,ClimateWindow,FeatureSpec
from ..utils.serialize import record
from .analysis_service import prepare_snapshot

def get_study(db,sid):
    row=db.get(ArchiveStudy,sid)
    if not row:raise HTTPException(404,"研究不存在")
    return row
def create_snapshot(db,study):return {"study":record(study),"features":[record(f) for f in db.query(FeatureSpec).filter_by(study_id=study.id).order_by(FeatureSpec.position)],"windows":[record(w) for w in db.query(ClimateWindow).filter_by(study_id=study.id).order_by(ClimateWindow.code)]}
def list_studies(db):
    out=[]
    for s in db.query(ArchiveStudy).order_by(ArchiveStudy.code):
        snapshot=create_snapshot(db,s);supported=True;reason='拆分完整、训练满秩；可运行稳健研究'
        try:prepare_snapshot(snapshot)
        except ValueError as e:supported=False;reason=str(e)
        out.append({**record(s),"counts":{role:sum(w['split']==role for w in snapshot['windows']) for role in ['train','cal','test']},"feature_count":len(snapshot['features']),"supported":supported,"reason":reason})
    return out
