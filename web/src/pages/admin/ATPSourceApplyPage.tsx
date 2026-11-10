import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import type { ReactNode } from 'react'
import { useContext, useEffect, useState } from 'react'
import { Link, UNSAFE_DataRouterContext } from 'react-router-dom'
import {
  getBranchWorkingDraft,
  getRunPackageState, listRunBranches, listRunContainers,
  saveRunPackageWorkingDraft
} from '../../api/client'
import type { ATPReferenceCatalog, ATPReferenceChild, ATPReferencePreview } from '../../api/atpReferencePackages'
import type { confirmATPReference } from '../../api/client'
import type { RunBranch, RunContainer } from '../../api/types'
import { useLanguage } from '../../i18n/LanguageContext'
import { AdminTransitionBlocker } from '../../navigation/AdminTransitionBlocker'
import { formatApiError } from '../../utils/apiErrors'

type ApplyCatalog = Pick<ATPReferenceCatalog, 'reference_span' | 'source_fingerprint'> & {
  children: Array<Omit<ATPReferenceChild, 'package_type'> & { package_type: string }>
}

type ApplyProps<Catalog extends ApplyCatalog> = {
  queryPrefix: string
  setupId: string
  title: { cs: string; en: string }
  subtitle: { cs: string; en: string }
  getCatalog: () => Promise<Catalog>
  getPreview: (runId: string, branchId: string) => Promise<ATPReferencePreview>
  confirmReference: typeof confirmATPReference
  isReviewed: (catalog: Catalog, preview: ATPReferencePreview, runId: string, branchId: string) => boolean
  renderSourceSummary?: (catalog: Catalog, cs: boolean) => ReactNode
  renderSourceDetails?: (catalog: Catalog | undefined, sourceReady: boolean) => ReactNode
}

type Resolution = 'keep_run' | 'use_source'
type PendingSave = {runId:string;branchId:string;version:number;fingerprint:string;head:string}
const writableRun = (run:RunContainer):boolean =>
  run.storage_kind==='custom_local'&&!run.read_only&&
  ['working','active','completed'].includes(run.status)
const writableBranch = (branch:RunBranch,runId:string):boolean =>
  branch.run_id===runId && branch.status==='active' &&
  !branch.read_only && Boolean(branch.saved_head_revision_id)

/**
 * ATP references are deliberately opaque: this is NOT an event/score/points
 * import or a playable Calendar. Only the existing generic Run Package
 * transaction and explicit Working Draft Save can write anything.
 */
export function ATPSourceApplyPage<Catalog extends ApplyCatalog>({
  queryPrefix, setupId, title, subtitle, getCatalog, getPreview, confirmReference,
  isReviewed, renderSourceSummary, renderSourceDetails,
}: ApplyProps<Catalog>): JSX.Element {
  const {language}=useLanguage(),cs=language==='cs'
  const dataRouter=useContext(UNSAFE_DataRouterContext)
  const qc=useQueryClient()
  const [runId,setRunId]=useState('')
  const [branchId,setBranchId]=useState('')
  const [approved,setApproved]=useState(false)
  const [resolutions,setResolutions]=useState<Record<string,Resolution>>({})
  const [hasApplied,setHasApplied]=useState(false)
  const [pendingSave,setPendingSave]=useState<PendingSave|null>(null)
  const [notice,setNotice]=useState('')
  const source=useQuery({
    queryKey:[`${queryPrefix}-catalog`],queryFn:getCatalog,retry:false
  })
  const runs=useQuery({
    queryKey:['run-containers'],queryFn:listRunContainers,retry:false
  })
  const possibleRuns=(runs.data?.run_containers??[]).filter(writableRun)
  const run=possibleRuns.find(x=>x.run_id===runId)
  const branches=useQuery({
    queryKey:['run-branches',runId],queryFn:()=>listRunBranches(runId),
    enabled:Boolean(run),retry:false
  })
  const possibleBranches=(branches.data?.run_branches??[]).filter(b=>writableBranch(b,runId))
  const branch=possibleBranches.find(b=>b.branch_id===branchId)
  const draft=useQuery({
    queryKey:['package-working-draft',runId,branchId],
    queryFn:()=>getBranchWorkingDraft(runId,branchId),
    enabled:Boolean(branch),retry:false
  })
  const state=useQuery({
    queryKey:['run-package-state',runId,branchId],
    queryFn:()=>getRunPackageState(runId,branchId),
    enabled:Boolean(branch),retry:false
  })
  const review=useQuery({
    queryKey:[`${queryPrefix}-preview`,runId,branchId],
    queryFn:()=>getPreview(runId,branchId),
    enabled:Boolean(branch && source.isSuccess && !hasApplied),
    retry:false,staleTime:0
  })
  const preview=review.data
  const contextCorrect=Boolean(
    source.isSuccess && review.isSuccess && runs.isSuccess && branches.isSuccess &&
    source.data && preview && run && branch && draft.isSuccess && state.isSuccess &&
    isReviewed(source.data,preview,runId,branchId) &&
    preview.saved_head_revision_id===branch.saved_head_revision_id &&
    preview.saved_head_revision_id===draft.data.base_saved_revision_id &&
    preview.draft_version===draft.data.draft_version &&
    preview.current_state_fingerprint===state.data.fingerprint &&
    !review.isFetching&&!draft.isFetching&&!state.isFetching&&!source.isFetching
  )
  const localDivergences=(preview?.conflicts??[])
    .filter(item=>item.endsWith(':local_divergence'))
    .map(item=>item.slice(0,-':local_divergence'.length))
  const hardConflicts=(preview?.conflicts??[]).filter(item=>!item.endsWith(':local_divergence'))
  const blocked=Boolean(
    !contextCorrect || (preview?.invalid.length??0)>0 ||
    (preview?.unresolved.length??0)>0 || hardConflicts.length ||
    localDivergences.some(label=>!resolutions[label])
  )
  const canConfirm=Boolean(!blocked&&approved&&!hasApplied&&!pendingSave)
  const stagedATP=Boolean(
    source.data && Array.isArray(state.data?.state?.package_versions) &&
    state.data?.state?.package_versions.some((item:unknown)=>
      Boolean(item && typeof item==='object' && !Array.isArray(item) &&
        (item as Record<string,unknown>).package_id===setupId &&
        (item as Record<string,unknown>).source_fingerprint===source.data?.source_fingerprint))
  )
  const canRecover=Boolean(
    stagedATP&&source.isSuccess&&branches.isSuccess&&draft.isSuccess&&state.isSuccess&&
    branch&&draft.data?.status==='dirty' &&
    draft.data.run_id===runId && draft.data.branch_id===branchId &&
    draft.data.base_saved_revision_id===branch.saved_head_revision_id &&
    state.data?.fingerprint&&!draft.isFetching&&!state.isFetching
  )
  const saveAllowed=Boolean(
    pendingSave&&run&&branch&&branches.isSuccess&&draft.isSuccess&&state.isSuccess&&
    draft.data?.status==='dirty' &&
    pendingSave.runId===runId && pendingSave.branchId===branchId &&
    pendingSave.version===draft.data.draft_version &&
    pendingSave.head===branch.saved_head_revision_id &&
    pendingSave.head===draft.data.base_saved_revision_id &&
    pendingSave.fingerprint===state.data?.fingerprint &&
    !draft.isFetching&&!state.isFetching
  )
  const pendingChanges=Boolean(
    approved||pendingSave ||
    (branch && draft.data?.status==='dirty')
  )

  useEffect(()=>{
    setApproved(false);setResolutions({});setHasApplied(false)
    setPendingSave(null);setNotice('')
  },[runId,branchId])

  const confirm=useMutation({
    mutationFn:async(current:ATPReferencePreview)=>{
      const result=await confirmReference(runId,branchId,{
        command_id:`${queryPrefix}-${crypto.randomUUID()}`,
        expected_head_revision_id:current.saved_head_revision_id,
        expected_draft_version:current.draft_version,
        expected_state_fingerprint:current.current_state_fingerprint,
        expected_preview_fingerprint:current.preview_fingerprint,
        conflict_resolutions:resolutions
      })
      if(!result.state||result.state.run_id!==runId||
         result.state.branch_id!==branchId||!result.state_fingerprint||
         !/^[0-9a-f]{64}$/.test(result.state_fingerprint)||
         result.draft_version<current.draft_version)
        throw new Error('ATP Run confirmation returned an inconsistent branch state.')
      return {result,current}
    },
    onSuccess:async({result,current})=>{
      setHasApplied(true);setApproved(false)
      setPendingSave(result.draft_version>current.draft_version?{
        runId,branchId,version:result.draft_version,
        fingerprint:result.state_fingerprint!,head:current.saved_head_revision_id
      }:null)
      setNotice(result.draft_version>current.draft_version
        ?(cs?'Reference ATP jsou ve Working Draftu; ulož je výslovně tlačítkem Save.':
           'ATP references are staged in Working Draft; explicitly Save the revision.')
        :(cs?'Tato verze už je v Runu. Žádná nová změna nebyla vytvořena.':
           'This source version is already in the Run. No new changes were staged.'))
      await Promise.all([
        qc.invalidateQueries({queryKey:['package-working-draft',runId,branchId]}),
        qc.invalidateQueries({queryKey:['run-package-state',runId,branchId]})
      ])
    },
    onError:()=>{
      setApproved(false)
      setNotice(cs?'Potvrzení selhalo. Načti znovu náhled a ověř konflikty.':
        'Confirmation failed. Refresh the preview and review conflicts.')
    }
  })
  const save=useMutation({
    mutationFn:async(p:PendingSave)=>{
      const result=await saveRunPackageWorkingDraft(p.runId,p.branchId,p.version)
      if(result.run_id!==p.runId||result.branch_id!==p.branchId||
         result.working_draft.status!=='clean'||
         result.working_draft.base_saved_revision_id!==result.saved_revision.revision_id)
        throw new Error('Saved Revision identity was not verified.')
      return result
    },
    onSuccess:async()=>{
      setPendingSave(null);setNotice(cs?'Nová Saved Revision byla uložena.':
        'A new Saved Revision has been saved.')
      await Promise.all([
        qc.invalidateQueries({queryKey:['package-working-draft',runId,branchId]}),
        qc.invalidateQueries({queryKey:['run-package-state',runId,branchId]}),
        qc.invalidateQueries({queryKey:['run-branches',runId]})
      ])
    }
  })
  function permitChange():boolean {
    return !pendingChanges || window.confirm(cs
      ? 'Tento Run může mít neuložený Working Draft. Změnit cíl? Serverový draft zůstane zachován.'
      : 'This Run may have an unsaved Working Draft. Switch target? The server draft is retained.')
  }
  function chooseRun(next:string):void {
    if(next===runId||!permitChange())return
    setRunId(next);setBranchId('')
  }
  function chooseBranch(next:string):void {
    if(next===branchId||!permitChange())return
    setBranchId(next)
  }
  function recover():void {
    if(!canRecover||!draft.data||!state.data?.fingerprint||!branch?.saved_head_revision_id)return
    setHasApplied(true);setApproved(false)
    setPendingSave({
      runId,branchId,version:draft.data.draft_version,
      fingerprint:state.data.fingerprint,head:branch.saved_head_revision_id
    })
    setNotice(cs
      ? 'Obnovený draft může obsahovat i jiné změny. Před Save prohlédni celý stav.'
      : 'Recovered draft may include unrelated changes. Inspect all state before Save.')
  }
  useEffect(()=>{
    const onBeforeUnload=(e:BeforeUnloadEvent)=>{
      if(!pendingChanges)return
      e.preventDefault();e.returnValue=''
    }
    window.addEventListener('beforeunload',onBeforeUnload)
    return ()=>window.removeEventListener('beforeunload',onBeforeUnload)
  },[pendingChanges])
  return <>
    {dataRouter&&<AdminTransitionBlocker isDirty={()=>pendingChanges||confirm.isPending||save.isPending}
      warning={cs?'Neuložené ATP reference nebo Working Draft. Opravdu opustit stránku?':
        'Unsaved ATP reference review or Working Draft. Leave the page?'}/>}
    <section className="panel package-apply">
      <p><Link to="/admin/packages">← {cs?'Balíčky':'Packages'}</Link></p>
      <div className="page-intro">
        <h2>{title[cs ? 'cs' : 'en']}</h2>
        <p className="subtitle">{subtitle[cs ? 'cs' : 'en']}</p>
      </div>
      {source.isPending&&<p role="status">{cs?'Načítám zdrojový manifest…':'Loading source manifest…'}</p>}
      {source.isError&&<p role="alert" className="error">{formatApiError(source.error)}
        <button type="button" onClick={()=>{void source.refetch()}}>{cs?'Znovu načíst':'Retry'}</button></p>}
      {source.data&&<div className="package-apply-step">
        <h3>{cs?'Zdroj balíčků':'Package source'}</h3>
        <p className="status">{source.data.reference_span.from}–{source.data.reference_span.to}
          {' · '}{cs?'2026 předběžný':'2026 provisional'}
          {' · '}{cs?'Pouze historická reference':'Historical reference only'}</p>
        {renderSourceSummary?.(source.data, cs)}
        <ul>{source.data.children.map(child=><li key={child.package_id}>
          <strong>{child.package_type}</strong> — {child.entity_count} {cs?'položek':'entities'}
          {' · '}v{child.source_version}</li>)}</ul>
        <details><summary>{cs?'Ověřitelné otisky zdroje':'Verifiable source fingerprints'}</summary>
          <p>Setup: <code>{source.data.source_fingerprint}</code></p>
          {source.data.children.map(child=><p key={child.package_id}>
            {child.package_id}: <code>{child.source_fingerprint}</code></p>)}
        </details>
      </div>}
      {renderSourceDetails?.(source.data, source.isSuccess)}
      <section className="package-apply-step">
        <h3>1. {cs?'Vybrat Run a Branch':'Choose Run and Branch'}</h3>
        {runs.isError&&<p role="alert" className="error">{formatApiError(runs.error)}</p>}
        <label>Run<select aria-label="Target Run" value={runId}
          disabled={confirm.isPending||save.isPending}
          onChange={e=>chooseRun(e.target.value)}>
          <option value="">{cs?'Vyber editovatelný Run':'Choose a writable Run'}</option>
          {possibleRuns.map(item=><option key={item.run_id} value={item.run_id}>
            {item.display_name||item.run_id}</option>)}
        </select></label>
        {runs.isSuccess&&possibleRuns.length===0&&<p>{cs
          ? 'Žádný editovatelný Run není dostupný.'
          : 'No writable Run is available.'}</p>}
        <p><Link to="/admin/runs/new">{cs?'Vytvořit nový Run':'Create a Run'}</Link></p>
        {run&&<>{branches.isError&&<p role="alert" className="error">{formatApiError(branches.error)}</p>}
          <label>Branch<select aria-label="Target Branch" value={branchId}
            disabled={confirm.isPending||save.isPending}
            onChange={e=>chooseBranch(e.target.value)}>
            <option value="">{cs?'Vyber editovatelnou Branch':'Choose a writable Branch'}</option>
            {possibleBranches.map(item=><option key={item.branch_id} value={item.branch_id}>
              {item.display_name}</option>)}
          </select></label></>}
        {branch&&<p className="status">{cs?'Uložená revize':'Saved head'}: {branch.saved_head_revision_id}
          {' · '}Working Draft: {draft.data?.status??'…'} (v{draft.data?.draft_version??'…'})</p>}
        {branch&&draft.isError&&<p role="alert">{formatApiError(draft.error)}</p>}
        {branch&&state.isError&&<p role="alert">{formatApiError(state.error)}</p>}
        {branch&&draft.data?.status==='dirty'&&!pendingSave&&<div className="package-apply-recovery">
          <p role="status">{cs
            ? 'Tato Branch už má neuložený Working Draft. Save může zahrnout i jiné změny.'
            : 'This Branch already has an unsaved Working Draft. Save may include other changes.'}</p>
          <details><summary>{cs?'Prohlédnout celý Working Draft':'Inspect entire Working Draft'}</summary>
            <pre>{JSON.stringify(state.data?.state,null,2)}</pre></details>
          {stagedATP&&<button type="button" disabled={!canRecover} onClick={recover}>
            {cs?'Obnovit Save pro ATP reference':'Recover ATP reference Save'}</button>}
        </div>}
      </section>
      {branch&&!hasApplied&&<section className="package-apply-step">
        <h3>2. {cs?'Náhled a konflikty':'Preview and conflicts'}</h3>
        {review.isPending&&<p role="status">{cs?'Načítám náhled…':'Loading preview…'}</p>}
        {review.isError&&<p role="alert" className="error">{formatApiError(review.error)}</p>}
        <button type="button" disabled={review.isFetching} onClick={()=>{
          setApproved(false);setResolutions({});void Promise.all([
            review.refetch(),draft.refetch(),state.refetch(),source.refetch()
          ])
        }}>{cs?'Obnovit celý náhled':'Refresh entire preview'}</button>
        {preview&&<><p className="status">{cs?'Přidávané':'Added'}: {preview.additions.length}
          {' · '}{cs?'Aktualizované':'Updated'}: {preview.updates.length}
          {' · '}{cs?'Beze změny':'Unchanged'}: {preview.unchanged.length}</p>
          <details><summary>{cs?'Položky dotčené změnou':'Changed source identities'}</summary>
            <ul>{[...preview.additions,...preview.updates].map(label=>
              <li key={label}><code>{label}</code></li>)}</ul></details>
          {hardConflicts.length>0&&<p role="alert" className="error">{cs
            ? 'Zdrojové konflikty blokují potvrzení.'
            : 'Source conflicts block confirmation.'}<br/>{hardConflicts.join('; ')}</p>}
          {preview.invalid.length>0&&<p role="alert" className="error">
            {cs?'Neplatný zdroj':'Invalid source'}: {preview.invalid.join('; ')}</p>}
          {preview.unresolved.length>0&&<p role="alert" className="error">
            {cs?'Nevyřešené odkazy':'Unresolved references'}: {preview.unresolved.join('; ')}</p>}
          {localDivergences.map(label=><label key={label}>{cs?'Lokální změna':'Local divergence'}: {label}
            <select aria-label={'Resolve '+label} value={resolutions[label]??''}
              onChange={e=>{setResolutions(v=>({...v,[label]:e.target.value as Resolution}));
                setApproved(false)}}>
              <option value="">{cs?'Vyžaduje rozhodnutí':'Decision required'}</option>
              <option value="keep_run">Keep Run</option>
              <option value="use_source">Use source</option>
            </select></label>)}
          {!contextCorrect&&<p role="alert" className="error">{cs
            ? 'Náhled neodpovídá aktuálnímu zdroji, Runu nebo Saved Head. Obnov jej.'
            : 'Preview does not match current source, Run or Saved Head. Refresh.'}</p>}
          <label className="package-apply-approval">
            <input type="checkbox" checked={approved} disabled={blocked||confirm.isPending}
              onChange={e=>setApproved(e.target.checked)}/>
            {cs
              ? 'Zkontroloval jsem změny a potvrzuji přidání obou historických referenčních balíčků.'
              : 'I reviewed the changes and confirm both historical reference packages.'}
          </label>
          <button type="button" disabled={!canConfirm||confirm.isPending}
            onClick={()=>{if(preview)confirm.mutate(preview)}}>
            {confirm.isPending?(cs?'Potvrzuji…':'Confirming…'):
              (cs?'Potvrdit do Working Draftu':'Confirm into Working Draft')}
          </button>
          {confirm.isError&&<p role="alert" className="error">{formatApiError(confirm.error)}</p>}
        </>}
      </section>}
      {hasApplied&&<section className="package-apply-step">
        <h3>3. {cs?'Výsledek a ruční Save':'Result and explicit Save'}</h3>
        {notice&&<p role="status">{notice}</p>}
        {pendingSave&&<><p className="status">{cs
          ? 'Zatím není v Saved Revision. Ruční Save uloží celý aktuální Working Draft.'
          : 'Not yet in a Saved Revision. Manual Save includes the entire Working Draft.'}</p>
          <button type="button" disabled={!saveAllowed||save.isPending}
            onClick={()=>save.mutate(pendingSave)}>
            {save.isPending?(cs?'Ukládám…':'Saving…'):(cs?'Uložit Saved Revision':'Save revision')}
          </button></>}
        {pendingSave&&!saveAllowed&&!draft.isFetching&&!state.isFetching&&
          <p role="alert" className="error">{cs
            ? 'Draft, otisk nebo Saved Head se změnily. Save je zablokovaný.'
            : 'Draft, fingerprint or Saved Head changed. Save is blocked.'}</p>}
        {save.isError&&<p role="alert" className="error">{formatApiError(save.error)}</p>}
        <p><Link to={'/admin/runs/'+encodeURIComponent(runId)+'?branch='+encodeURIComponent(branchId)}>
          {cs?'Otevřít Run':'Open Run'}</Link></p>
      </section>}
    </section>
  </>
}
