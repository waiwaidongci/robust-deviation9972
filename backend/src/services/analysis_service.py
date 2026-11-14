import numpy as np
from .robust_algorithm import fit_train,score_with_fit,training_scale,finite_matrix
from .conformal_algorithm import upper_tail_p
from ..utils.fingerprint import fingerprint
VERSION='train-mcd-split-conformal-v1'
def prepare_snapshot(snapshot):
    features=sorted(snapshot['features'],key=lambda f:f['position']);codes=[f['code'] for f in features]
    if len(features)!=4 or len(set(codes))!=4 or len({f['position'] for f in features})!=4:raise ValueError("须固定4个预定义且不重复的特征")
    rows=sorted(snapshot['windows'],key=lambda w:w['code'])
    if not 25<=len(rows)<=2000 or len({w['code'] for w in rows})!=len(rows):raise ValueError("窗口数25–2000且编号不得重复")
    if len({w['id'] for w in rows})!=len(rows):raise ValueError("窗口身份重复，拆分不可交叠")
    groups={s:[] for s in ['train','cal','test']}
    for w in rows:
        if w['split'] not in groups:raise ValueError("窗口角色仅train/cal/test")
        if set(w['values'])!=set(codes):raise ValueError("每窗口必须完整包含预定义4量，不得用test选择特征")
        groups[w['split']].append(w)
    if len(groups['train'])<20 or len(groups['cal'])<4 or len(groups['test'])<1:raise ValueError("严格拆分要求train≥20/cal≥4/test≥1")
    matrices={s:finite_matrix([[w['values'][c] for c in codes] for w in g],s) for s,g in groups.items()}
    training_scale(matrices['train'])
    return features,rows,groups,matrices

def analyze_deviation(snapshot,alpha=.05,seed=2026):
    if type(alpha) not in (int,float) or not np.isfinite(alpha) or not .01<=alpha<=.2:raise ValueError("预设alpha须在.01–.2之间")
    features,rows,groups,X=prepare_snapshot(snapshot);fit=fit_train(X['train'],seed);cal=score_with_fit(X['cal'],fit);test=score_with_fit(X['test'],fit);tail=upper_tail_p(cal,test)
    fit['raw_support_codes']=[w['code'] for w,m in zip(groups['train'],fit['raw_support_mask']) if m];fit['support_codes']=[w['code'] for w,m in zip(groups['train'],fit['support_mask']) if m]
    scores=[{"window":w,"d2":float(d),"p":float(p),"cal_ge_count":int(k),"selected":bool(p<=alpha)} for w,d,p,k in zip(groups['test'],test,tail['p'],tail['cal_ge_count'])]
    ecdf_values,ecdf_counts=np.unique(cal,return_counts=True);ecdf_y=np.cumsum(ecdf_counts)/len(cal)
    canonical={"study":snapshot['study'],"features":features,"windows":rows};fit_hash=fingerprint({"version":VERSION,"features":features,"train":[{"code":w['code'],"values":w['values']} for w in groups['train']],"seed":seed,"support_fraction":.8})
    return {"algorithm_version":VERSION,"study":snapshot['study'],"features":features,"counts":{s:len(g) for s,g in groups.items()},"fit":fit,"fit_hash":fit_hash,"calibration":[{"window":w,"d2":float(d)} for w,d in zip(groups['cal'],cal)],"test":scores,"calibration_ecdf":[{"d2":float(d),"cdf":float(y)} for d,y in zip(ecdf_values,ecdf_y)],"alpha":alpha,"seed":seed,"selected_count":sum(x['selected'] for x in scores),"resolution":tail['resolution'],"tail":tail['tail'],"input_snapshot":canonical,"input_hash":fingerprint({"version":VERSION,"snapshot":canonical,"alpha":alpha,"seed":seed,"support_fraction":.8}),"assumptions":"MCD适用于单峰、近对称/椭圆主群，不适合多峰。定标与MCD只用train；固定训练且cal/test独立可交换时，上尾split-conformal提供边际误报控制，不是条件保证、FDR或危险诊断。","protocol":"四特征与alpha在运行前冻结；不以test选择特征、拟合、阈值或测试分位。筛选仅为人工独立补测线索。"}
