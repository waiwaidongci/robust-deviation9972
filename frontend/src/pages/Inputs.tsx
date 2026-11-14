import {useEffect,useState} from 'react';
import {useSearchParams} from 'react-router-dom';
import {useResearchData} from '../hooks/useResearch';
import {useAuth} from '../stores/auth';
import {useAction} from '../hooks/useAction';
import {StudySelector} from '../components/StudySelector';
import {DataTable} from '../components/common/DataTable';
import {Notice} from '../components/common/Notice';
import {annotateWindow,retractWindows} from '../api/windows';
import {number,time} from '../utils/format';
import {SplitRoles,RetractionStatus} from '../constants/enums';

export function Inputs(){
  const s=useResearchData(),{user}=useAuth(),a=useAction(),[params]=useSearchParams();
  const [id,setId]=useState(Number(params.get('study'))||0);
  const [role,setRole]=useState('train');
  const [selected,setSelected]=useState(0);
  const [note,setNote]=useState('');
  const [checked,setChecked]=useState<number[]>([]);
  const [reason,setReason]=useState('');
  const study=s.studies.find(x=>x.id===id)||s.studies[0];
  const rows=s.windows.filter(w=>w.split===role);
  const window=rows.find(w=>w.id===selected)||rows[0];
  const canWrite=user?.role==='admin'||user?.role==='analyst';
  const cleaning=s.retractions.some(r=>r.status!=='completed');
  const selectable=rows.filter(w=>!w.retracted);
  useEffect(()=>{if(study)s.loadStudy(study.id)},[study?.id,s.loadStudy]);
  useEffect(()=>setNote(window?.note||''),[window?.id,window?.note]);
  useEffect(()=>{setChecked([]);setReason('')},[study?.id,role]);
  useEffect(()=>{if(!cleaning||!study)return;const t=setInterval(()=>s.loadStudy(study.id),2000);return()=>clearInterval(t)},[cleaning,study?.id,s.loadStudy]);
  const toggle=(wid:number)=>setChecked(c=>c.includes(wid)?c.filter(x=>x!==wid):[...c,wid]);
  const retract=()=>a.execute(async()=>{await retractWindows(checked,reason);setChecked([]);setReason('');await s.loadStudy(study.id);await s.refresh()});
  return <div className="page">
    <div className="page-title"><div><p className="eyebrow">SOURCES & ROLE BOUNDARY / 02</p><h1>来源与严格拆分<span>四量预定义；训练、校准、测试各司其职。</span></h1></div></div>
    <Notice message={s.error||a.error} onRetry={s.refresh}/>
    <StudySelector studies={s.studies} value={study?.id||0} onChange={setId}/>
    {study&&<div className={'source-note '+(!study.supported?'warning':'')}><b>{study.reason}</b><p>{study.description}</p><small>{study.source}{study.retracted_count>0&&` · ${study.retracted_count}个窗口已撤回，原值清理后仅保留指纹与统计供追查`}</small></div>}
    <div className="section-heading"><h2>固定四量口径</h2><span>不使用test选择特征</span></div>
    <DataTable head={['次序','特征','单位','窗口口径']}>{s.features.map(x=><tr key={x.id}><td>{x.position+1}</td><td>{x.label}</td><td>{x.unit}</td><td>{x.meaning}</td></tr>)}</DataTable>
    {s.retractions.length>0&&<>
      <div className="section-heading"><h2>来源撤回与清理进度</h2><span>{s.retractions.length}条撤回记录{cleaning?' / 清理进行中，每2秒刷新':' / 各处原值均已清除'}</span></div>
      <DataTable head={['窗口','角色','撤回原因','原指纹','历史统计','清理进度','状态','操作者','时间']}>{s.retractions.map(r=><tr key={r.id}>
        <td>{r.code}</td><td>{SplitRoles[r.split]}</td><td className="reason-cell">{r.reason}</td><td className="fingerprint">{r.fingerprint.slice(0,16)}…</td>
        <td>运行{r.stats.runs_total} / 完成{r.stats.runs_completed} / 获批{r.stats.runs_approved}</td>
        <td>源值{r.progress.source?'已清':'待清'} · 冻结与结果档案{(r.progress.runs_done||[]).length}/{r.progress.runs_total??0}</td>
        <td><span className={'review-badge '+(r.status==='completed'?'approved':'cleaning')}>{RetractionStatus[r.status]||r.status}</span></td>
        <td>{r.actor}</td><td>{time(r.created_at)}</td>
      </tr>)}</DataTable>
    </>}
    <div className="source-grid">
      <section>
        <div className="section-heading"><h2>独立窗口清单</h2><span>{rows.length}条 / {role}{checked.length>0&&` / 已选${checked.length}条`}</span></div>
        <div className="mode-switch">{Object.entries(SplitRoles).map(([key,label])=><button className={role===key?'active':''} key={key} onClick={()=>{setRole(key);setSelected(0)}}>{label}</button>)}</div>
        <div className="compact-table"><DataTable head={[...(canWrite?[<input key="all" type="checkbox" aria-label="选择全部未撤回窗口" checked={selectable.length>0&&checked.length===selectable.length} onChange={()=>setChecked(checked.length===selectable.length?[]:selectable.map(w=>w.id))}/>]:[]),'窗口',...s.features.map(f=>f.label),'角色']}>
          {rows.map(w=><tr key={w.id} className={(window?.id===w.id?'active-row':'')+(w.retracted?' retracted-row':'')} onClick={()=>setSelected(w.id)}>
            {canWrite&&<td onClick={e=>e.stopPropagation()}>{w.retracted?'—':<input type="checkbox" aria-label={'选择 '+w.code} checked={checked.includes(w.id)} onChange={()=>toggle(w.id)}/>}</td>}
            <td>{w.code}{w.retracted&&<span className="review-badge rejected">已撤回</span>}</td>
            {s.features.map(f=><td key={f.code}>{number(w.values[f.code],3)}</td>)}
            <td>{w.split}</td>
          </tr>)}
        </DataTable></div>
        {canWrite&&checked.length>0&&<div className="approval-form">
          <label>撤回原因（将批量撤回{checked.length}个窗口）<textarea aria-label="撤回原因" value={reason} onChange={e=>setReason(e.target.value)} minLength={8} maxLength={1500} placeholder="记录来源失准的核对结论；撤回后引用研究立即停用，原值清理不可恢复"/></label>
          <div><button className="primary" disabled={a.busy||reason.length<8} onClick={retract}>批量撤回并清理原值</button><button className="outline" disabled={a.busy} onClick={()=>{setChecked([]);setReason('')}}>清空选择</button></div>
          <small>撤回立即停用引用研究并阻止新运行与获批下载；源值、冻结输入与结果档案中的原值逐步清理，保留原因、原指纹与历史统计供追查。</small>
        </div>}
      </section>
      <aside className="window-reading"><span className="eyebrow">SELECTED WINDOW</span><h2>{window?.code}</h2>
        <p>{window&&SplitRoles[window.split]}<br/>{window?.retracted?'该窗口来源已撤回，观测原值已清理，仅保留指纹与统计。':'不允许重分配角色或编辑观测值。'}</p>
        <label>窗口批注<textarea aria-label="窗口批注" value={note} disabled={!canWrite} onChange={e=>setNote(e.target.value)}/></label>
        {canWrite&&<button className="outline" disabled={a.busy||!window||note.length<8} onClick={()=>a.execute(async()=>{await annotateWindow(window.id,note);await s.loadStudy(study.id)})}>保存批注</button>}
        <small>批注进入后续快照；历史运行保持冻结值。</small>
      </aside>
    </div>
  </div>;
}
