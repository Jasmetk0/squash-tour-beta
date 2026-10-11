import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useEffect, useMemo, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import {
  confirmWorldSelection, getBranchWorkingDraft, getRunPackageState, getWorldPackage,
  listRunBranches, listRunContainers, previewWorldSelection, saveRunPackageWorkingDraft
} from '../../api/client'
import type { RunBranch, RunContainer } from '../../api/types'
import { isExactWorldSelection } from '../../api/worldSelection'
import type { WorldSelectionRequest, WorldSelectionPreview } from '../../api/worldSelection'
import { useLanguage } from '../../i18n/LanguageContext'
import { formatApiError } from '../../utils/apiErrors'

type PendingSave = { runId:string; branchId:string; draftVersion:number; fingerprint:string; previousHead:string }
function runWritable(run:RunContainer):boolean {
  return run.storage_kind === 'custom_local' && !run.read_only && ['working','active','completed'].includes(run.status)
}
function branchWritable(branch:RunBranch,runId:string):boolean {
  return branch.run_id===runId && branch.status==='active' && !branch.read_only && Boolean(branch.saved_head_revision_id)
}
function jsonValue(value:unknown):string { return value===undefined?'—':JSON.stringify(value,null,2)??'—' }

export function WorldPackageApplyPage():JSX.Element {
  const {worldId=''}=useParams()
  const {language}=useLanguage(),cs=language==='cs',qc=useQueryClient()
  const [runId,setRunId]=useState(''),[branchId,setBranchId]=useState('')
  const [selected,setSelected]=useState<string[]>([])
  const [resolutions,setResolutions]=useState<WorldSelectionRequest['conflict_resolutions']>({})
  const [approved,setApproved]=useState(false)
  const [pendingSave,setPendingSave]=useState<PendingSave|null>(null)
  const [notice,setNotice]=useState('')
  const [hasApplied,setHasApplied]=useState(false)

  const source=useQuery({queryKey:['world-package',worldId],queryFn:()=>getWorldPackage(worldId),enabled:Boolean(worldId),retry:false})
  const runs=useQuery({queryKey:['run-containers'],queryFn:listRunContainers,retry:false})
  const candidates=(runs.data?.run_containers??[]).filter(runWritable)
  const run=candidates.find(item=>item.run_id===runId)
  const branches=useQuery({queryKey:['run-branches',runId],queryFn:()=>listRunBranches(runId),enabled:Boolean(runId),retry:false})
  const choices=(branches.data?.run_branches??[]).filter(item=>branchWritable(item,runId))
  const branch=choices.find(item=>item.branch_id===branchId)
  const draft=useQuery({queryKey:['package-working-draft',runId,branchId],queryFn:()=>getBranchWorkingDraft(runId,branchId),enabled:Boolean(branch),retry:false})
  const state=useQuery({queryKey:['run-package-state',runId,branchId],queryFn:()=>getRunPackageState(runId,branchId),enabled:Boolean(branch),retry:false})
  const normalized=[...selected].sort()
  const payload=useMemo<WorldSelectionRequest>(()=>({selected_entities:normalized,conflict_resolutions:resolutions}),
    // Selection order never changes the backend identity.
    [normalized.join('|'),JSON.stringify(resolutions)])
  const review=useQuery({
    queryKey:['world-selection',worldId,runId,branchId,payload],
    queryFn:()=>previewWorldSelection(runId,branchId,worldId,payload),
    enabled:Boolean(branch && source.data?.world_id===worldId && !hasApplied),
    retry:false,
    staleTime:0
  })
  const data=review.data
  const contextCorrect=Boolean(
    data && branch && run && draft.isSuccess && state.isSuccess &&
    isExactWorldSelection(data,worldId,runId,branchId,selected,resolutions) &&
    data.saved_head_revision_id===branch.saved_head_revision_id &&
    data.draft_version===draft.data.draft_version &&
    data.saved_head_revision_id===draft.data.base_saved_revision_id &&
    data.current_state_fingerprint===state.data.fingerprint &&
    !review.isFetching && !draft.isFetching && !state.isFetching
  )
  const canConfirm=Boolean(contextCorrect && data?.can_confirm && approved && !hasApplied && !pendingSave)
  const saveAllowed=Boolean(
    pendingSave && pendingSave.runId===runId && pendingSave.branchId===branchId &&
    branch && branch.saved_head_revision_id===pendingSave.previousHead &&
    draft.data?.base_saved_revision_id===pendingSave.previousHead &&
    draft.data?.draft_version===pendingSave.draftVersion && draft.data?.status==='dirty' &&
    state.data?.fingerprint===pendingSave.fingerprint && !draft.isFetching && !state.isFetching
  )

  useEffect(()=>{
    setSelected([]);setResolutions({});setApproved(false);setPendingSave(null);setNotice('');setHasApplied(false)
  },[worldId,runId,branchId])

  const confirm=useMutation({
    mutationFn:async(p:WorldSelectionPreview)=>{
      const result=await confirmWorldSelection(runId,branchId,worldId,{
        ...payload,command_id:'world-selection-'+crypto.randomUUID(),
        expected_head_revision_id:p.saved_head_revision_id,
        expected_draft_version:p.draft_version,
        expected_state_fingerprint:p.current_state_fingerprint,
        expected_preview_fingerprint:p.preview_fingerprint,
        expected_selection_fingerprint:p.selection_fingerprint
      })
      if(!result.state||result.state.run_id!==runId||result.state.branch_id!==branchId ||
         !result.state_fingerprint||result.draft_version<p.draft_version)
        throw new Error('Server did not verify the exact Run/Branch result.')
      return {preview:p,result}
    },
    onSuccess:async({preview:p,result})=>{
      setHasApplied(true);setApproved(false)
      setPendingSave(result.draft_version>p.draft_version?{
        runId,branchId,draftVersion:result.draft_version,
        fingerprint:result.state_fingerprint!,previousHead:p.saved_head_revision_id
      }:null)
      setNotice(result.draft_version>p.draft_version
        ?(cs?'Obsah je ve Working Draftu. Ručně ulož novou revizi.':'Content staged in Working Draft. Save a new revision manually.')
        :(cs?'Výběr nezměnil Working Draft.':'Selection did not change Working Draft.'))
      await Promise.all([
        qc.invalidateQueries({queryKey:['package-working-draft',runId,branchId]}),
        qc.invalidateQueries({queryKey:['run-package-state',runId,branchId]})
      ])
    },
    onError:()=>{setApproved(false);setNotice(cs?'Potvrzení se nezdařilo. Znovu načti náhled a ověř aktuální stav.':'Confirm failed. Refresh the preview and inspect current state.')}
  })
  const save=useMutation({
    mutationFn:async(p:PendingSave)=>{
      const result=await saveRunPackageWorkingDraft(p.runId,p.branchId,p.draftVersion)
      if(result.run_id!==p.runId||result.branch_id!==p.branchId||
         result.working_draft.status!=='clean'||result.working_draft.base_saved_revision_id!==result.saved_revision.revision_id)
        throw new Error('Save response did not verify the new immutable revision.')
      return result
    },
    onSuccess:async()=>{
      setPendingSave(null)
      setNotice(cs?'Uložena nová Saved Revision.':'New Saved Revision saved.')
      await Promise.all([
        qc.invalidateQueries({queryKey:['package-working-draft',runId,branchId]}),
        qc.invalidateQueries({queryKey:['run-package-state',runId,branchId]}),
        qc.invalidateQueries({queryKey:['run-branches',runId]}),
        qc.invalidateQueries({queryKey:['admin-run-branches',runId]})
      ])
    }
  })
  function changeSelection(next:string[]):void {
    setSelected([...new Set(next)].sort());setResolutions({});setApproved(false);setNotice('')
  }
  function chooseRun(next:string):void {setRunId(next);setBranchId('')}
  const scopeGroups=Object.entries((data?.available??[]).reduce<Record<string,string[]>>((acc,item)=>{
    (acc[item.scope]??=[]).push(item.label);return acc
  },{}))

  return <section className="panel package-apply">
    <p><Link to={'/admin/packages/world/'+encodeURIComponent(worldId)}>← {cs?'Detail balíčku':'Package detail'}</Link></p>
    <div className="page-intro"><h2>{cs?'Použít World Package v Runu':'Apply World Package to Run'}</h2>
      <p className="subtitle">{source.data?.name??worldId} · {cs?'výběrový import do nezávislého Working Draftu':'selective import into an independent Working Draft'}</p></div>
    {source.isError&&<p role="alert" className="error">{formatApiError(source.error)}</p>}
    <section className="package-apply-step">
      <h3>1. {cs?'Cílový Run a Branch':'Target Run and Branch'}</h3>
      {runs.isError&&<p role="alert" className="error">{formatApiError(runs.error)}</p>}
      <label>{cs?'Run':'Run'}<select aria-label="Target Run" value={runId} onChange={event=>chooseRun(event.target.value)}>
        <option value="">{cs?'Vyber uložený editovatelný Run':'Choose a writable saved Run'}</option>
        {candidates.map(candidate=><option key={candidate.run_id} value={candidate.run_id}>{candidate.display_name||candidate.run_id}</option>)}
      </select></label>
      {runs.isSuccess&&candidates.length===0&&<p className="status">{cs?'Žádný editovatelný Run není dostupný.':'No writable Run is available.'}</p>}
      <p><Link to="/admin/runs/new">{cs?'Vytvořit nový Run':'Create new Run'} →</Link> <span className="status">{cs?'(potom se vrať k tomuto balíčku)':'(then return to this package)'}</span></p>
      {runId&&<>{branches.isError&&<p role="alert" className="error">{formatApiError(branches.error)}</p>}
        <label>Branch<select aria-label="Target Branch" value={branchId} onChange={event=>setBranchId(event.target.value)}>
          <option value="">{cs?'Vyber editovatelnou branch':'Choose a writable Branch'}</option>
          {choices.map(item=><option key={item.branch_id} value={item.branch_id}>{item.display_name}</option>)}
        </select></label></>}
      {branch&&<p className="status">{cs?'Uložený základ':'Saved head'}: {branch.saved_head_revision_id} · {cs?'Working Draft':'Working Draft'}: {draft.data?.status??'…'} (v{draft.data?.draft_version??'…'})</p>}
    </section>
    {branch&&<section className="package-apply-step">
      <h3>2. {cs?'Vyber obsah':'Select contents'}</h3>
      {review.isPending&&<p role="status">{cs?'Přepočítávám náhled ze serveru…':'Recomputing server preview…'}</p>}
      {review.isError&&<p role="alert" className="error">{formatApiError(review.error)}</p>}
      {data&&!hasApplied&&<>
        <p className="status">{data.available.length} {cs?'zdrojových položek':'source entities'} · {selected.length} {cs?'vybráno':'selected'} · {data.excluded_entities.length} {cs?'vynecháno':'excluded'}</p>
        <div className="actions">
          <button type="button" onClick={()=>changeSelection(data.available.filter(o=>o.valid).map(o=>o.label))}>{cs?'Vybrat vše platné':'Select all valid'}</button>
          <button type="button" onClick={()=>changeSelection([])}>{cs?'Zrušit výběr':'Clear selection'}</button>
        </div>
        {scopeGroups.map(([scope,labels])=><details key={scope} className="package-apply-group" open={scope==='countries'}>
          <summary>{scope} · {labels.filter(id=>selected.includes(id)).length}/{labels.length}</summary>
          <div className="actions">
            <button type="button" onClick={()=>changeSelection([...selected,...labels.filter(id=>data.available.find(o=>o.label===id)?.valid)])}>{cs?'Vybrat skupinu':'Select group'}</button>
            <button type="button" onClick={()=>changeSelection(selected.filter(id=>!labels.includes(id)))}>{cs?'Odebrat skupinu':'Exclude group'}</button>
          </div>
          <div className="package-apply-items">{data.available.filter(o=>o.scope===scope).map(o=><label key={o.label}>
            <input type="checkbox" disabled={!o.valid} checked={selected.includes(o.label)}
              onChange={e=>changeSelection(e.target.checked?[...selected,o.label]:selected.filter(v=>v!==o.label))}/>
            <span>{o.label}</span><small className="status">{o.status}{o.local_divergence?' · local divergence':''}</small>
          </label>)}</div>
        </details>)}
      </>}
    </section>}
    {branch&&data&&!hasApplied&&<section className="package-apply-step">
      <h3>3. {cs?'Změny před → po a potvrzení':'Before → after review and confirm'}</h3>
      <p className="status">{cs?'Zdrojová verze':'Source version'}: {data.source.source_version} · fingerprint: <code>{data.source.source_fingerprint}</code></p>
      <p className="status">{cs?'Vybrané':'Selected'}: {data.selected_entities.length} · {cs?'Vynechané':'Excluded'}: {data.excluded_entities.length} · {cs?'Prohlédnutelné změny':'Reviewed changes'}: {data.changes.length}</p>
      {data.blockers.length>0&&<div role="alert" className="error"><strong>{cs?'Blokující konflikty':'Blocking conflicts'}</strong><ul>{data.blockers.map(b=><li key={b}>{b}</li>)}</ul></div>}
      {data.changes.map(row=><details key={row.label} className="package-apply-diff">
        <summary><strong>{row.label}</strong> · {row.status} · {row.fields.length} {cs?'změněných polí':'changed fields'}</summary>
        {row.local_divergence&&<label>{cs?'Řešení změn v Runu':'Resolve Run divergence'}
          <select value={resolutions[row.label]??''} aria-label={'Resolution '+row.label}
            onChange={e=>{setResolutions(prev=>{const next={...prev};if(e.target.value)next[row.label]=e.target.value as 'keep_run'|'use_source';else delete next[row.label];return next});setApproved(false)}}>
            <option value="">{cs?'Vyžaduje rozhodnutí':'Decision required'}</option><option value="keep_run">Keep Run</option><option value="use_source">Use source</option>
          </select></label>}
        {row.fields.length?<table><thead><tr><th>{cs?'Pole':'Field'}</th><th>{cs?'Před':'Before'}</th><th>{cs?'Po':'After'}</th></tr></thead>
          <tbody>{row.fields.map(f=><tr key={f.field}><td>{f.field}</td><td><pre>{jsonValue(f.before)}</pre></td><td><pre>{jsonValue(f.after)}</pre></td></tr>)}</tbody></table>:<p className="status">{cs?'Bez změny hodnot.':'No value change.'}</p>}
      </details>)}
      {!contextCorrect && <p role="alert" className="error">{cs?'Náhled se načítá nebo již neodpovídá aktuálnímu Runu a Working Draftu.':'Preview is loading or does not match the current Run and Working Draft.'}</p>}
      <label className="package-apply-approval"><input type="checkbox" checked={approved} disabled={!contextCorrect||!data.can_confirm||confirm.isPending}
        onChange={e=>setApproved(e.target.checked)}/>{cs?'Zkontroloval jsem přesný výběr, změny a cílovou branch.':'I reviewed the exact selection, changes and target Branch.'}</label>
      <button type="button" disabled={!canConfirm||confirm.isPending} onClick={()=>{if(data)confirm.mutate(data)}}>
        {confirm.isPending?(cs?'Potvrzuji…':'Applying…'):(cs?'Potvrdit do Working Draftu':'Confirm into Working Draft')}
      </button>
      {confirm.isError&&<p role="alert" className="error">{formatApiError(confirm.error)}</p>}
    </section>}
    {hasApplied&&<section className="package-apply-step">
      <h3>{cs?'Výsledek a uložení':'Result and saving'}</h3>
      {notice&&<p role="status">{notice}</p>}
      {pendingSave&&<><p className="status">{cs?'Změny jsou zatím pouze ve Working Draftu, ne v uložené revizi.':'Changes are staged in Working Draft, not yet in a Saved Revision.'}</p>
        <button type="button" disabled={!saveAllowed||save.isPending} onClick={()=>{if(pendingSave)save.mutate(pendingSave)}}>
          {cs?'Uložit Saved Revision':'Save revision'}
        </button></>}
      {save.isError&&<p role="alert" className="error">{formatApiError(save.error)}</p>}
      <p><Link to={'/admin/runs/'+encodeURIComponent(runId)+'?branch='+encodeURIComponent(branchId)}>{cs?'Otevřít cílový Run':'Open target Run'} →</Link></p>
    </section>}
  </section>
}
