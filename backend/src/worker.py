import json,time,traceback
from pathlib import Path
from .config.database import Base,engine,SessionLocal
from .config.settings import ARTIFACTS_DIR
from .models import DeviationRun
from .constants.status import RunStatus
from .services.run_service import queue
from .services.analysis_service import analyze_deviation
from .services.audit_service import log
from .services.retraction_service import retracted_window_ids,purge_snapshot_windows,purge_result_windows,run_cleanup,retract_mutex

def tick_cleanup():
    """心跳并续跑未完成的撤回清理；清理中断后由后续心跳或重启恢复。"""
    Path(ARTIFACTS_DIR,"heartbeat").write_text(str(time.time()))
    with SessionLocal() as db:
        try:run_cleanup(db)
        except Exception:traceback.print_exc()

def save_result(db,run,result):
    """晚到保存：提交前复查撤回，命中即清理快照与结果，绝不恢复原值。"""
    with retract_mutex(wait=5):
        ids=retracted_window_ids(db,run.study_id)
        if ids:
            run.input_snapshot=purge_snapshot_windows(run.input_snapshot,ids)
            result=purge_result_windows(result,ids)
        run.result=result;run.status=RunStatus.COMPLETED
        Path(ARTIFACTS_DIR,f"run-{run.id}.json").write_text(json.dumps(run.result,ensure_ascii=False))
        log(db,"worker","deviation.completed",run.id);db.commit()

def execute_run(db,run):
    try:save_result(db,run,analyze_deviation(run.input_snapshot,run.alpha,run.seed))
    except Exception as e:run.status=RunStatus.FAILED;run.error=str(e);traceback.print_exc();db.commit()

def process_job(job):
    try:
        with SessionLocal() as db:
            run=db.get(DeviationRun,int(job[1]))
            if not run or run.status!=RunStatus.QUEUED:return
            with retract_mutex(wait=5):
                ids=retracted_window_ids(db,run.study_id)
                if ids:
                    run.input_snapshot=purge_snapshot_windows(run.input_snapshot,ids)
                    run.status=RunStatus.FAILED;run.error="来源窗口已撤回，研究已停用，排队运行取消"
                    log(db,"worker","deviation.retracted",run.id);db.commit();return
                run.status=RunStatus.RUNNING;db.commit()
            execute_run(db,run)
    except Exception:traceback.print_exc()

def main():
    Base.metadata.create_all(engine);Path(ARTIFACTS_DIR).mkdir(exist_ok=True)
    while True:
        tick_cleanup()
        job=queue.blpop("deviation:jobs",timeout=2)
        if job:process_job(job)

if __name__=="__main__":main()
