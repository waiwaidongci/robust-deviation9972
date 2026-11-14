import numpy as np

def upper_tail_p(calibration,test):
    try:cal=np.asarray(calibration,dtype=float);scores=np.asarray(test,dtype=float)
    except (TypeError,ValueError,OverflowError):raise ValueError("校准/测试分数须有限")
    if cal.ndim!=1 or scores.ndim!=1 or len(cal)<1 or len(scores)<1 or not np.isfinite(cal).all() or not np.isfinite(scores).all() or np.any(cal<0) or np.any(scores<0):raise ValueError("校准和测试须为非空有限非负平方距离")
    ge=len(cal)-np.searchsorted(np.sort(cal),scores,side='left')
    return {"p":((1+ge)/(len(cal)+1)).tolist(),"cal_ge_count":ge.tolist(),"m":len(cal),"resolution":1/(len(cal)+1),"tail":"上尾含等号：p=(1+#cal D²≥test D²)/(m+1)，同值保守"}
