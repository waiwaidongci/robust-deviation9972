from fastapi import HTTPException
from ..models import DeviationRun,ReviewNote
from ..utils.serialize import record
from .audit_service import log

def list_notes(db):return [record(n) for n in db.query(ReviewNote).order_by(ReviewNote.id.desc())]
def create_note(db,data,user):
    run=db.get(DeviationRun,data.run_id)
    if not run or run.status!="completed":raise HTTPException(409,"只能对已完成偏离研究提交补测建议")
    row=ReviewNote(**data.model_dump(),owner=user.name,status="submitted")
    db.add(row);db.flush();log(db,user.email,"review.submit",row.id);db.commit();return record(row)
def review_note(db,nid,data,user):
    row=db.get(ReviewNote,nid)
    if not row:raise HTTPException(404,"补测建议不存在")
    if row.status!="submitted":raise HTTPException(409,"已审阅建议不可重复审批")
    row.status=data.status;row.reviewer=user.name;row.review_note=data.review_note
    log(db,user.email,"review."+data.status,row.id);db.commit();return record(row)
