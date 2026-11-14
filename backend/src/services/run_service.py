import csv,io
from redis import Redis
from fastapi import HTTPException
from ..models import DeviationRun,ReviewNote
from ..config.settings import REDIS_URL
from ..utils.serialize import record
from .study_service import get_study,create_snapshot
from .analysis_service import prepare_snapshot
from .audit_service import log
queue=Redis.from_url(REDIS_URL,decode_responses=True)
def list_runs(db):return [record(r) for r in db.query(DeviationRun).order_by(DeviationRun.id.desc())]
def get_run(db,rid):
    row=db.get(DeviationRun,rid)
    if not row:raise HTTPException(404,"偏离研究不存在")
    return row
def create_run(db,data,user):
    study=get_study(db,data.study_id);snapshot=create_snapshot(db,study)
    try:prepare_snapshot(snapshot)
    except ValueError as e:raise HTTPException(422,str(e))
    row=DeviationRun(**data.model_dump(),input_snapshot=snapshot,owner=user.name);db.add(row);db.flush();log(db,user.email,"deviation.enqueue",row.id);db.commit()
    try:queue.rpush('deviation:jobs',row.id)
    except Exception:row.status='failed';row.error='队列不可用，请重提';db.commit();raise HTTPException(503,row.error)
    return record(row)
def export_run(db,rid):
    row=get_run(db,rid)
    if row.status!='completed' or not db.query(ReviewNote).filter_by(run_id=rid,status='approved').first():raise HTTPException(403,'仅获批完成研究可导出')
    o=io.StringIO();w=csv.writer(o);features=row.result['features'];w.writerow(['window','split',*[f['code'] for f in features],'D_squared','cal_ge_count','upper_tail_p','preset_alpha','selected','cal_m','seed','fit_hash','input_hash'])
    for x in row.result['test']:v=x['window'];w.writerow([v['code'],v['split'],*[v['values'][f['code']] for f in features],x['d2'],x['cal_ge_count'],x['p'],row.alpha,x['selected'],row.result['counts']['cal'],row.seed,row.result['fit_hash'],row.result['input_hash']])
    return o.getvalue()
