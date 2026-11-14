import json
import numpy as np
from src.config.database import Base,engine,SessionLocal
from src.models import User,ArchiveStudy,ClimateWindow,FeatureSpec,DeviationRun,ReviewNote
from src.utils.security import hash_password
from src.services.study_service import create_snapshot
from src.services.analysis_service import analyze_deviation

def seed():
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        for role,name in [('admin','沈棠 · 材料负责人'),('analyst','温砚 · 联合量研究员'),('viewer','秦禾 · 补测阅读者')]:
            email=role+'@shuangleng.demo'
            if not db.query(User).filter_by(email=email).first():db.add(User(email=email,name=name,role=role,password_hash=hash_password('Shuangleng2026!')))
        definitions=[('temperature','温度','°C','固定窗口温度均值'),('humidity','相对湿度','%RH','固定窗口相对湿度均值'),('particles','颗粒浓度','μg/m³','固定窗口颗粒浓度均值'),('variation','温度波动','°C','固定窗口温度标准差')];studies=[]
        mean=np.array([19.5,47.,18.,.35]);scale=np.array([1.5,5.,4.,.12]);R=np.array([[1,.55,.25,.2],[.55,1,.35,.1],[.25,.35,1,.3],[.2,.1,.3,1]])
        for k,(code,name) in enumerate([('SL-01','主群 · 独立窗口观察'),('SL-02','污染训练 · 稳健对照'),('SL-03','退化协方差 · 拒绝边界')]):
            study=db.query(ArchiveStudy).filter_by(code=code).first()
            if not study:study=ArchiveStudy(code=code,name=name,description='450个独立合成窗口，预先固定train200/cal150/test100；四量口径先于测试冻结。SL-02仅训练含20个极端值，cal/test仍同分布独立；SL-03训练四量线性退化。',source='sl-archive-climate-202611.csv',default_alpha=.05);db.add(study);db.flush()
            for i,(fc,label,unit,meaning) in enumerate(definitions):
                if not db.query(FeatureSpec).filter_by(study_id=study.id,code=fc).first():db.add(FeatureSpec(study_id=study.id,code=fc,label=label,unit=unit,position=i,meaning=meaning))
            rng=np.random.default_rng(260+k);X=mean+rng.multivariate_normal(np.zeros(4),R,450)*scale
            if k==1:X[:20]+=np.array([12,30,28,.9])
            if k==2:X[:,3]=.1*X[:,0]+.01*X[:,1]
            for i,row in enumerate(X):
                split='train' if i<200 else 'cal' if i<350 else 'test';wc=f'{code}-W{i+1:03}'
                if not db.query(ClimateWindow).filter_by(study_id=study.id,code=wc).first():db.add(ClimateWindow(study_id=study.id,code=wc,split=split,values={fc:float(v) for (fc,*_),v in zip(definitions,row)},note='合成独立窗口；train/cal/test预先分配，不是连续时间序列或实时风险告警。'))
            db.flush();studies.append(study)
        if not db.query(DeviationRun).filter_by(name='主群四量 · 固定拆分基线').first():
            study=studies[0];snapshot=create_snapshot(db,study);result=analyze_deviation(snapshot,.05,2026);run=DeviationRun(name='主群四量 · 固定拆分基线',study_id=study.id,alpha=.05,seed=2026,input_snapshot=snapshot,status='completed',result=result,owner='温砚 · 联合量研究员');db.add(run);db.flush();db.add(ReviewNote(run_id=run.id,title='首批联合偏离补测说明',interpretation='训练支持不是新样本标签；cal/test交换时的边际误报控制不等于条件保证、FDR或危险诊断。',proposal='对预设alpha筛选窗口独立补测，保留四量定义与新窗口独立性。',status='approved',owner='温砚 · 联合量研究员',reviewer='沈棠 · 材料负责人',review_note='批准研究归档；保持固定特征与独立补测，不把训练支持或低p当危险事实。'))
        db.commit();print(json.dumps({m.__tablename__:db.query(m).count() for m in [User,ArchiveStudy,ClimateWindow,FeatureSpec,DeviationRun,ReviewNote]},ensure_ascii=False))
if __name__=='__main__':seed()
