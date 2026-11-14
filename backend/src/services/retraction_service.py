import json,time,uuid
from contextlib import contextmanager
from pathlib import Path
from redis import Redis
from fastapi import HTTPException
from ..models import ArchiveStudy,ClimateWindow,DeviationRun,ReviewNote,WindowRetraction
from ..config.settings import REDIS_URL,ARTIFACTS_DIR
from ..utils.serialize import record
from ..utils.fingerprint import fingerprint
from .audit_service import log

queue=Redis.from_url(REDIS_URL,decode_responses=True)
MUTEX_KEY="deviation:retract:mutex"

@contextmanager
def retract_mutex(wait=0):
    """撤回/清理/建运行/晚到保存共用的短互斥；Redis不可用时降级为无锁继续。"""
    token=uuid.uuid4().hex;acquired=False;deadline=time.monotonic()+wait
    try:
        while True:
            try:acquired=bool(queue.set(MUTEX_KEY,token,nx=True,ex=30))
            except Exception:acquired=True
            if acquired or time.monotonic()>=deadline:break
            time.sleep(.1)
        if not acquired:raise HTTPException(409,"另一批撤回正在清理，请稍后重试")
        yield
    finally:
        if acquired:
            try:
                if queue.get(MUTEX_KEY)==token:queue.delete(MUTEX_KEY)
            except Exception:pass

def retracted_window_ids(db,study_id):
    return {r.window_id for r in db.query(WindowRetraction).filter_by(study_id=study_id)}
def study_retracted_count(db,study_id):
    return db.query(WindowRetraction).filter_by(study_id=study_id).count()

def _window_fingerprint(w):
    return fingerprint({"id":w.id,"study_id":w.study_id,"code":w.code,"split":w.split,"values":w.values})
def _historical_stats(db,w):
    runs=db.query(DeviationRun).filter_by(study_id=w.study_id).all()
    approved=db.query(ReviewNote).join(DeviationRun,ReviewNote.run_id==DeviationRun.id).filter(DeviationRun.study_id==w.study_id,ReviewNote.status=="approved").count()
    return {"runs_total":len(runs),"runs_completed":sum(1 for r in runs if r.status=="completed"),"runs_approved":approved,"values_purged":len(w.values or {}),"feature_codes":sorted((w.values or {}).keys())}

def retract_windows(db,data,user):
    """批量撤回：已撤回的窗口跳过不重复留痕；先建档立即停用研究，再尽力同步清理。"""
    ids=list(dict.fromkeys(data.window_ids))
    with retract_mutex(wait=5):
        rows=db.query(ClimateWindow).filter(ClimateWindow.id.in_(ids)).all()
        if len(rows)!=len(ids):raise HTTPException(404,"部分窗口不存在")
        existing={r.window_id for r in db.query(WindowRetraction).filter(WindowRetraction.window_id.in_(ids))}
        created=[]
        for w in rows:
            if w.id in existing:continue
            r=WindowRetraction(window_id=w.id,study_id=w.study_id,code=w.code,split=w.split,reason=data.reason,fingerprint=_window_fingerprint(w),stats=_historical_stats(db,w),status="pending",progress={},actor=user.email)
            db.add(r);created.append(r)
        if created:
            db.flush();log(db,user.email,"source.retract","windows:"+",".join(str(r.window_id) for r in created))
        db.commit()
    if created:
        try:run_cleanup(db)
        except Exception:pass
    return [record(r) for r in db.query(WindowRetraction).filter(WindowRetraction.window_id.in_(ids)).order_by(WindowRetraction.id)]

def list_retractions(db,sid):
    if not db.get(ArchiveStudy,sid):raise HTTPException(404,"研究不存在")
    return [record(r) for r in db.query(WindowRetraction).filter_by(study_id=sid).order_by(WindowRetraction.id.desc())]

def purge_snapshot_windows(snapshot,window_ids):
    if not snapshot:return snapshot
    return {**snapshot,"windows":[({**w,"values":{}} if w.get("id") in window_ids else w) for w in snapshot.get("windows") or []]}

def purge_result_windows(result,window_ids):
    if not result:return result
    out=dict(result)
    def clean(entry):
        w=entry.get("window") or {}
        return {**entry,"window":{**w,"values":{}}} if w.get("id") in window_ids else entry
    for key in ("calibration","test"):
        if isinstance(out.get(key),list):out[key]=[clean(x) for x in out[key]]
    if isinstance(out.get("input_snapshot"),dict):out["input_snapshot"]=purge_snapshot_windows(out["input_snapshot"],window_ids)
    return out

def _result_purged(result,wid):
    if not result:return True
    for key in ("calibration","test"):
        for e in result.get(key) or []:
            w=e.get("window") or {}
            if w.get("id")==wid and w.get("values"):return False
    for w in (result.get("input_snapshot") or {}).get("windows") or []:
        if w.get("id")==wid and w.get("values"):return False
    return True

def _purge_run(db,run,window_ids):
    run.input_snapshot=purge_snapshot_windows(run.input_snapshot,window_ids)
    if run.result:run.result=purge_result_windows(run.result,window_ids)
    path=Path(ARTIFACTS_DIR)/f"run-{run.id}.json"
    if path.exists():
        data=json.loads(path.read_text())
        path.write_text(json.dumps(purge_result_windows(data,window_ids),ensure_ascii=False))

def _verify_purged(db,r):
    w=db.get(ClimateWindow,r.window_id)
    if w and w.values:return False
    for run in db.query(DeviationRun).filter_by(study_id=r.study_id):
        for win in (run.input_snapshot or {}).get("windows") or []:
            if win.get("id")==r.window_id and win.get("values"):return False
        if not _result_purged(run.result,r.window_id):return False
        path=Path(ARTIFACTS_DIR)/f"run-{run.id}.json"
        if path.exists():
            try:data=json.loads(path.read_text())
            except Exception:return False
            if not _result_purged(data,r.window_id):return False
    return True

def cleanup_step(db,rid):
    """单步清理并提交，中断后按已持久化的progress续跑；全部清除才置completed。"""
    r=db.get(WindowRetraction,rid)
    if not r or r.status=="completed":return False
    prog=dict(r.progress or {})
    if r.status!="cleaning":
        r.status="cleaning";r.progress=prog;db.commit();return True
    if not prog.get("source"):
        w=db.get(ClimateWindow,r.window_id)
        if w and w.values:w.values={}
        prog["source"]=True;prog.setdefault("runs_done",[])
        prog["runs_total"]=db.query(DeviationRun).filter_by(study_id=r.study_id).count()
        r.progress=prog;db.commit();return True
    done=set(prog.get("runs_done",[]))
    query=db.query(DeviationRun).filter_by(study_id=r.study_id)
    if done:query=query.filter(~DeviationRun.id.in_(done))
    run=query.order_by(DeviationRun.id).first()
    if run:
        _purge_run(db,run,{r.window_id})
        done.add(run.id);prog["runs_done"]=sorted(done);r.progress=prog;db.commit();return True
    if _verify_purged(db,r):
        r.status="completed";r.progress=prog
        log(db,"system","source.purged",f"{r.code}#{r.id}");db.commit();return True
    return False

def run_cleanup(db):
    """续跑所有未完成的撤回清理；与其它进程共用互斥，冲突时本轮跳过。"""
    try:
        with retract_mutex(wait=0):
            while True:
                ids=[r.id for r in db.query(WindowRetraction).filter(WindowRetraction.status!="completed").order_by(WindowRetraction.id)]
                if not ids:return
                if not any(cleanup_step(db,rid) for rid in ids):return
    except HTTPException:return
