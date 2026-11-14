"""Train-only scaling and seeded FastMCD; no calibration/test data accepted by fit."""
import warnings
import numpy as np
from sklearn.covariance import MinCovDet
SUPPORT_FRACTION=.8
CONDITION_LIMIT=1e10

def finite_matrix(values,label):
    try:
        raw=np.asarray(values,dtype=object)
        if any(isinstance(v,(bool,np.bool_,complex,np.complexfloating)) for v in raw.flat):raise ValueError(label+"不接受布尔或复数")
        X=np.asarray(values,dtype=float)
    except (ValueError,TypeError,OverflowError):raise ValueError(label+"须为有限数值矩阵")
    if X.ndim!=2 or X.shape[0]<1 or not 2<=X.shape[1]<=6 or not np.isfinite(X).all() or np.max(np.abs(X))>1e9:raise ValueError(label+"要求非空2–6列有限矩阵，绝对值不超过1e9")
    return X

def training_scale(train):
    X=finite_matrix(train,"训练值");n,p=X.shape
    if n<max(20,2*p+4):raise ValueError("训练行过少，至少20且大于2p+4")
    mean=X.mean(axis=0);D=X-mean;maxdev=np.max(np.abs(D),axis=0)
    if np.any(maxdev==0):raise ValueError("训练存在常量特征，拒绝奇异拟合")
    scale=maxdev*np.sqrt(np.mean((D/maxdev)**2,axis=0))
    if np.any(scale<=0) or not np.isfinite(scale).all():raise ValueError("训练定标不可分辨")
    Z=D/scale;s=np.linalg.svd(Z,compute_uv=False);rank=int(np.sum(s>max(Z.shape)*np.finfo(float).eps*s[0]))
    if rank<p:raise ValueError("训练特征秩亏，拒绝奇异协方差")
    return Z,mean,scale,rank

def mahalanobis_squared(values,center,covariance):
    X=finite_matrix(values,"评分值");p=X.shape[1]
    try:center=np.asarray(center,dtype=float);C=np.asarray(covariance,dtype=float)
    except (TypeError,ValueError,OverflowError):raise ValueError("中心/协方差须为有限数值")
    if center.shape!=(p,) or C.shape!=(p,p) or not np.isfinite(center).all() or not np.isfinite(C).all() or not np.allclose(C,C.T,rtol=1e-12,atol=1e-14):raise ValueError("中心/协方差形状或对称性非法")
    eig=np.linalg.eigvalsh(C)
    if eig[-1]<=0 or eig[0]<=p*np.finfo(float).eps*eig[-1] or eig[-1]/eig[0]>CONDITION_LIMIT:raise ValueError("协方差奇异或条件数超过1e10，拒绝不稳定距离")
    try:L=np.linalg.cholesky(C);whitened=np.linalg.solve(L,(X-center).T)
    except np.linalg.LinAlgError:raise ValueError("协方差非正定")
    d=np.sum(whitened*whitened,axis=0)
    if not np.isfinite(d).all():raise ValueError("距离溢出，无法输出可靠结果")
    return d

def fit_train(train,seed=2026):
    if type(seed) is not int or not 0<=seed<=2147483647:raise ValueError("seed须为非负32位整数")
    Z,mean,scale,rank=training_scale(train)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter('always');est=MinCovDet(support_fraction=SUPPORT_FRACTION,random_state=seed,assume_centered=False).fit(Z)
    mahalanobis_squared(Z,est.raw_location_,est.raw_covariance_)
    distances=mahalanobis_squared(Z,est.location_,est.covariance_)
    eig=np.linalg.eigvalsh(est.covariance_)
    return {"scaler_mean":mean.tolist(),"scaler_scale":scale.tolist(),"location_scaled":est.location_.tolist(),"covariance_scaled":est.covariance_.tolist(),"raw_location_scaled":est.raw_location_.tolist(),"raw_covariance_scaled":est.raw_covariance_.tolist(),"location_original":(mean+scale*est.location_).tolist(),"covariance_original":(est.covariance_*np.outer(scale,scale)).tolist(),"raw_location_original":(mean+scale*est.raw_location_).tolist(),"raw_covariance_original":(est.raw_covariance_*np.outer(scale,scale)).tolist(),"raw_support_mask":est.raw_support_.tolist(),"support_mask":est.support_.tolist(),"raw_support_count":int(est.raw_support_.sum()),"support_count":int(est.support_.sum()),"support_fraction":SUPPORT_FRACTION,"rank":rank,"condition_number":float(eig[-1]/eig[0]),"train_distances":distances.tolist(),"warnings":[str(w.message) for w in caught],"fit_note":"FastMCD近似搜索、修正与重加权；.8控制raw支持，最终支持比例可不同。支持掩码仅描述训练拟合，不是新样本标签。"}

def score_with_fit(values,fit):
    X=finite_matrix(values,"评分值");mean=np.asarray(fit['scaler_mean']);scale=np.asarray(fit['scaler_scale'])
    if X.shape[1]!=len(mean):raise ValueError("评分特征维数不匹配")
    Z=(X-mean)/scale
    return mahalanobis_squared(Z,fit['location_scaled'],fit['covariance_scaled'])
