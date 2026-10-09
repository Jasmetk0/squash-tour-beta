import {useMutation,useQuery,useQueryClient} from '@tanstack/react-query'
import {useEffect,useState} from 'react'
import {Link} from 'react-router-dom'

import {
  adoptAuthoritativeWeekScheduleProposal,getBranchWorkingDraft,getRunContainer,
  inspectAuthoritativeWeekSchedule,inspectAuthoritativeWeekSchedulePreflight,
  listAuthoritativeMatchReplays,listRunBranches,previewAuthoritativeSimulationSave,
  proposeAuthoritativeWeekSchedule,saveAuthoritativeSimulation
} from '../api/client'
import type {AuthoritativeWeekScheduleProposal,AuthoritativeSimulationSavePreview} from '../api/types'
import {
  validFirstWeekScheduleProposal,validPersistedWeekSchedule,
  validCheckpointPreview,validSavedCheckpoint,verifiedTournamentMatchRows
} from '../api/runWeekMatchCheckpoint'
import {formatApiError} from '../utils/apiErrors'
import {SectionCard} from './RunScopedUi'

type ScheduleReview={
  runId:string;branchId:string;eventId:string;head:string;draftVersion:number
  preflightFingerprint:string;proposal:AuthoritativeWeekScheduleProposal;requestId:string
}
type CheckpointReview={
  runId:string;branchId:string;head:string;draftVersion:number
  preview:AuthoritativeSimulationSavePreview
}
export function RunWeekMatchCheckpointPanel({runId,branchId,eventId}:{
  runId:string;branchId:string;eventId:string
}):JSX.Element{
  const client=useQueryClient()
  const [scheduleReview,setScheduleReview]=useState<ScheduleReview|null>(null)
  const [scheduleConfirmed,setScheduleConfirmed]=useState(false)
  const [saveReview,setSaveReview]=useState<CheckpointReview|null>(null)
  const [saveConfirmed,setSaveConfirmed]=useState(false)
  const [savedRevision,setSavedRevision]=useState<string|null>(null)
  const [notice,setNotice]=useState('')

  const runQuery=useQuery({queryKey:['admin-run-container',runId],
    queryFn:()=>getRunContainer(runId),retry:false})
  const branchesQuery=useQuery({queryKey:['admin-run-branches',runId],
    queryFn:()=>listRunBranches(runId),retry:false})
  const draftQuery=useQuery({queryKey:['package-working-draft',runId,branchId],
    queryFn:()=>getBranchWorkingDraft(runId,branchId),retry:false})
  const preflightQuery=useQuery({
    queryKey:['authoritative-simulation-week-schedule-preflight',runId,branchId],
    queryFn:()=>inspectAuthoritativeWeekSchedulePreflight(runId,branchId),retry:false})
  const adopted=preflightQuery.data?.schedule_already_adopted===true
  const scheduleQuery=useQuery({
    queryKey:['authoritative-simulation-week-schedule',runId,branchId],
    queryFn:()=>inspectAuthoritativeWeekSchedule(runId,branchId),
    enabled:adopted,retry:false})
  const replaysQuery=useQuery({
    queryKey:['authoritative-match-replays',runId,branchId],
    queryFn:()=>listAuthoritativeMatchReplays(runId,branchId,100),
    enabled:adopted,retry:false})
  const previewQuery=useQuery({
    queryKey:['authoritative-simulation-save-preview',runId,branchId],
    queryFn:()=>previewAuthoritativeSimulationSave(runId,branchId),
    retry:false})

  const branch=branchesQuery.data?.run_branches.find(item=>
    item.run_id===runId&&item.branch_id===branchId)
  const head=branch?.saved_head_revision_id??''
  const draft=draftQuery.data?.run_id===runId&&
    draftQuery.data.branch_id===branchId?draftQuery.data:null
  const writable=Boolean(runQuery.data?.run_id===runId&&
    runQuery.data.storage_kind==='custom_local'&&!runQuery.data.read_only&&
    branch?.status==='active'&&!branch.read_only&&head&&draft&&
    draft.base_saved_revision_id===head)
  const preflight=preflightQuery.data?.run_id===runId&&
    preflightQuery.data.branch_id===branchId?preflightQuery.data:null
  const schedule=scheduleQuery.data?.run_id===runId&&
    scheduleQuery.data.branch_id===branchId?scheduleQuery.data:undefined
  const pending=runQuery.isFetching||branchesQuery.isFetching||
    draftQuery.isFetching||preflightQuery.isFetching||scheduleQuery.isFetching
  const canPropose=Boolean(writable&&draft?.status==='clean'&&
    preflight?.can_propose_schedule&&!preflight.schedule_already_adopted&&
    preflight.canonical_preparation_ready&&preflight.blockers.length===0&&
    preflight.event_ids.includes(eventId)&&!pending)
  const canSave=Boolean(writable&&
    validCheckpointPreview(previewQuery.data,head)&&
    previewQuery.data?.draft_version===draft?.draft_version&&
    !previewQuery.isFetching&&!pending)

  useEffect(()=>{
    setScheduleReview(null);setScheduleConfirmed(false)
    setSaveReview(null);setSaveConfirmed(false);setSavedRevision(null);setNotice('')
  },[runId,branchId,eventId])
  useEffect(()=>{
    setScheduleReview(null);setScheduleConfirmed(false)
    setSaveReview(null);setSaveConfirmed(false)
  },[head,draft?.draft_version,preflight?.preflight_fingerprint])

  const scheduleMutation=useMutation({
    mutationFn:async():Promise<ScheduleReview>=>{
      if(!canPropose||!draft||!preflight)
        throw new Error('Complete all authoritative Week prerequisites and save the current Working Draft first.')
      const proposal=await proposeAuthoritativeWeekSchedule(runId,branchId)
      if(!validFirstWeekScheduleProposal(preflight,proposal,runId,branchId,eventId))
        throw new Error('The full Week proposal does not match the current calendar or preflight.')
      return {runId,branchId,eventId,head,draftVersion:draft.draft_version,
        preflightFingerprint:preflight.preflight_fingerprint,
        proposal,requestId:`first-week-schedule-${crypto.randomUUID()}`}
    },
    onSuccess:review=>{setScheduleReview(review);setScheduleConfirmed(false);setNotice('')},
    onError:()=>{setScheduleReview(null);setScheduleConfirmed(false)}
  })
  const scheduleCurrent=Boolean(scheduleReview&&canPropose&&draft&&preflight&&
    scheduleReview.head===head&&scheduleReview.draftVersion===draft.draft_version&&
    scheduleReview.preflightFingerprint===preflight.preflight_fingerprint&&
    validFirstWeekScheduleProposal(preflight,scheduleReview.proposal,runId,branchId,eventId))
  const adoptMutation=useMutation({
    mutationFn:async(review:ScheduleReview)=>{
      const [freshPreflight,freshDraft,freshBranches,freshProposal]=await Promise.all([
        inspectAuthoritativeWeekSchedulePreflight(runId,branchId),
        getBranchWorkingDraft(runId,branchId),
        listRunBranches(runId),
        proposeAuthoritativeWeekSchedule(runId,branchId)
      ])
      const freshHead=freshBranches.run_branches.find(x=>x.run_id===runId&&
        x.branch_id===branchId)?.saved_head_revision_id
      if(freshHead!==review.head||
        freshDraft.run_id!==runId||freshDraft.branch_id!==branchId||
        freshDraft.status!=='clean'||
        freshDraft.base_saved_revision_id!==review.head||
        freshDraft.draft_version!==review.draftVersion||
        freshPreflight.preflight_fingerprint!==review.preflightFingerprint||
        !validFirstWeekScheduleProposal(freshPreflight,freshProposal,runId,branchId,eventId)||
        freshProposal.schedule_fingerprint!==review.proposal.schedule_fingerprint||
        freshProposal.position_fingerprint!==review.proposal.position_fingerprint)
        throw new Error('Week Schedule source changed; review the current Week again.')
      await adoptAuthoritativeWeekScheduleProposal(runId,branchId,{
        request_id:review.requestId,
        expected_week:review.proposal.schedule.week,
        expected_schedule_fingerprint:review.proposal.schedule_fingerprint,
        expected_position_fingerprint:review.proposal.position_fingerprint
      })
      const stored=await inspectAuthoritativeWeekSchedule(runId,branchId)
      if(!validPersistedWeekSchedule(stored,review.proposal,runId,branchId))
        throw new Error('Week Schedule may have committed but persisted readback differs. Inspect the saved Week before retrying.')
      return stored
    },
    onSuccess:async stored=>{
      setScheduleReview(null);setScheduleConfirmed(false)
      setNotice(`Week Schedule ${stored.schedule_fingerprint?.slice(0,16)}… saved and re-read. Run an eligible Match slot after saving any pending Working Draft.`)
      await Promise.all([
        client.invalidateQueries({queryKey:['authoritative-simulation-week-schedule',runId,branchId]}),
        client.invalidateQueries({queryKey:['authoritative-simulation-week-schedule-preflight',runId,branchId]}),
        client.invalidateQueries({queryKey:['authoritative-simulation-position',runId,branchId]}),
        client.invalidateQueries({queryKey:['authoritative-simulation-save-preview',runId,branchId]}),
        client.invalidateQueries({queryKey:['package-working-draft',runId,branchId]})
      ])
    },
    onError:async()=>{
      setScheduleReview(null);setScheduleConfirmed(false)
      await client.invalidateQueries({queryKey:['authoritative-simulation-week-schedule-preflight',runId,branchId]})
    }
  })
  const checkpointMutation=useMutation({
    mutationFn:async():Promise<CheckpointReview>=>{
      if(!canSave||!draft||!previewQuery.data)
        throw new Error('There are no verified unsaved sporting changes to checkpoint.')
      return {runId,branchId,head,draftVersion:draft.draft_version,
        preview:previewQuery.data}
    },
    onSuccess:r=>{setSaveReview(r);setSaveConfirmed(false)},
    onError:()=>{setSaveReview(null);setSaveConfirmed(false)}
  })
  const saveCurrent=Boolean(saveReview&&canSave&&draft&&
    saveReview.runId===runId&&saveReview.branchId===branchId&&
    saveReview.head===head&&saveReview.draftVersion===draft.draft_version&&
    saveReview.preview.simulation_fingerprint===previewQuery.data?.simulation_fingerprint)
  const saveMutation=useMutation({
    mutationFn:async(review:CheckpointReview)=>{
      const [freshPreview,freshDraft,freshBranches]=await Promise.all([
        previewAuthoritativeSimulationSave(runId,branchId),
        getBranchWorkingDraft(runId,branchId),listRunBranches(runId)
      ])
      const freshHead=freshBranches.run_branches.find(x=>x.run_id===runId&&
        x.branch_id===branchId)?.saved_head_revision_id
      if(freshHead!==review.head||freshDraft.run_id!==runId||
        freshDraft.branch_id!==branchId||freshDraft.base_saved_revision_id!==review.head||
        freshDraft.draft_version!==review.draftVersion||
        !validCheckpointPreview(freshPreview,review.head)||
        freshPreview.draft_version!==review.preview.draft_version||
        freshPreview.simulation_fingerprint!==review.preview.simulation_fingerprint)
        throw new Error('Sporting Save preview changed. Review the current Branch first.')
      const saved=await saveAuthoritativeSimulation(runId,branchId,{
        expected_draft_version:review.preview.draft_version,
        expected_simulation_fingerprint:review.preview.simulation_fingerprint
      })
      if(!validSavedCheckpoint(saved,runId,branchId,review.head))
        throw new Error('Save may have committed but its revision receipt differs. Inspect Branch head before retrying.')
      const [storedBranches,storedDraft,storedPreview]=await Promise.all([
        listRunBranches(runId),getBranchWorkingDraft(runId,branchId),
        previewAuthoritativeSimulationSave(runId,branchId)
      ])
      const actualHead=storedBranches.run_branches.find(x=>x.run_id===runId&&
        x.branch_id===branchId)?.saved_head_revision_id
      if(actualHead!==saved.saved_revision.revision_id||
        storedDraft.base_saved_revision_id!==actualHead||
        storedDraft.run_id!==runId||storedDraft.branch_id!==branchId||
        storedDraft.status!=='clean'||storedPreview.can_save||
        storedPreview.saved_head_revision_id!==actualHead)
        throw new Error('Saved Revision may exist but reload verification failed. Inspect revision history before retrying.')
      return actualHead
    },
    onSuccess:async revision=>{
      setSaveReview(null);setSaveConfirmed(false)
      setSavedRevision(revision)
      setNotice('Run sporting changes saved and reloaded from the current Branch head.')
      await Promise.all([
        client.invalidateQueries({queryKey:['admin-run-branches',runId]}),
        client.invalidateQueries({queryKey:['run-branches',runId]}),
        client.invalidateQueries({queryKey:['package-working-draft',runId,branchId]}),
        client.invalidateQueries({queryKey:['authoritative-simulation-save-preview',runId,branchId]}),
        client.invalidateQueries({queryKey:['authoritative-simulation-position',runId,branchId]}),
        client.invalidateQueries({queryKey:['saved-revisions',runId,branchId]})
      ])
    },
    onError:async()=>{
      setSaveReview(null);setSaveConfirmed(false)
      await Promise.all([
        client.invalidateQueries({queryKey:['admin-run-branches',runId]}),
        client.invalidateQueries({queryKey:['authoritative-simulation-save-preview',runId,branchId]})
      ])
    }
  })
  const rows=verifiedTournamentMatchRows(replaysQuery.data,schedule,runId,branchId,eventId)
  const scheduledGroups=schedule?.schedule?.slots.filter(x=>x.event_id===eventId)
    .flatMap(x=>x.group_ids)??[]
  const uniqueScheduled=new Set(scheduledGroups).size

  return <SectionCard title="Week Schedule, match progress and Save">
    <p className="status">A first Draw alone cannot start a match. The authoritative Week Schedule covers every simultaneous Event, not only this tournament. Match results appear only if stored, and Save creates a separately verifiable Saved Revision.</p>
    {!writable&&<p role="status">A writable Product Run, active Branch and correctly based Working Draft are required.</p>}
    {preflightQuery.error&&<p role="alert" className="error">Week Schedule preflight failed: {formatApiError(preflightQuery.error)}</p>}
    {preflight&&!preflight.schedule_already_adopted&&<p>Week Schedule pending · {preflight.group_ids.length} total eligible groups across {preflight.event_ids.length} events.</p>}
    {preflight?.blockers.length?<p role="status">Schedule blockers: {preflight.blockers.join(', ')}.</p>:null}
    {preflight&&!preflight.schedule_already_adopted&&<>
      <button type="button" disabled={!canPropose||scheduleMutation.isPending}
        onClick={()=>scheduleMutation.mutate()}>
        {scheduleMutation.isPending?'Resolving Week proposal…':'Preview complete Week Schedule'}
      </button>
      {scheduleMutation.error&&<p role="alert" className="error">{formatApiError(scheduleMutation.error)}</p>}
      {scheduleReview&&<section aria-label="Review complete Week Schedule">
        <h4>Full-week proposal</h4>
        <p>{scheduleReview.proposal.schedule.slots.length} process/match slots · {preflight.group_ids.length} match groups · {preflight.event_ids.length} events. SHA-256 <code>{scheduleReview.proposal.schedule_fingerprint}</code></p>
        <ol>{scheduleReview.proposal.schedule.slots.map(x=>
          <li key={x.ordinal}>#{x.ordinal}: {x.event_id??'shared Week'} · {x.group_ids.join(', ')} · Match Day {x.match_day_ordinal??'—'} / order {x.match_order??'—'}</li>
        )}</ol>
        {!scheduleCurrent&&<p role="alert" className="error">Proposal is stale; preview the current Week.</p>}
        <label><input type="checkbox" aria-label="Approve full Week Schedule"
          checked={scheduleConfirmed} onChange={e=>setScheduleConfirmed(e.target.checked)}/>
          Adopt every simultaneous tournament Slot in this exact proposal.</label>
        <button type="button" disabled={!scheduleConfirmed||!scheduleCurrent||adoptMutation.isPending}
          onClick={()=>adoptMutation.mutate(scheduleReview)}>
          {adoptMutation.isPending?'Saving Week Schedule…':'Commit reviewed Week Schedule'}
        </button>
      </section>}
      {adoptMutation.error&&<p role="alert" className="error">{formatApiError(adoptMutation.error)}</p>}
    </>}
    {schedule&&schedule.schedule&&<section aria-label="Persisted Week Schedule">
      <h4>Adopted Week Schedule</h4>
      <p>{schedule.schedule.slots.length} global slots; {uniqueScheduled} groups scheduled for this Event. Schedule fingerprint <code>{schedule.schedule_fingerprint}</code>.</p>
      <p>{rows.length} verified stored tournament match(es) in the available replay history.</p>
      {rows.length>0&&<table><thead><tr><th>Match</th><th>Winner</th><th>Loser</th><th>Rallies</th></tr></thead>
        <tbody>{rows.map(row=><tr key={row.groupId}><td>{row.matchId}</td><td>{row.winnerId}</td><td>{row.loserId}</td><td>{row.totalRallies}</td></tr>)}</tbody></table>}
      <p className="status">A recorded result is not proof of automatic next-round completion; inspect the current sporting Position and schedule before the next match.</p>
    </section>}
    {replaysQuery.error&&<p role="alert" className="error">Stored results unavailable: {formatApiError(replaysQuery.error)}</p>}
    <h4>Save sporting progress</h4>
    <p className="status">Saving includes all pending changes in this Run/Branch, not just the displayed tournament. Perform it after schedule adoption or matches as necessary.</p>
    {previewQuery.error&&<p role="alert" className="error">Simulation Save preview unavailable: {formatApiError(previewQuery.error)}</p>}
    <p>Saved Head: <code>{head||'Not available'}</code>. Unsaved simulation changes: {previewQuery.data?.has_unsaved_changes?'Yes':'No'}.</p>
    <button type="button" disabled={!canSave||checkpointMutation.isPending}
      onClick={()=>checkpointMutation.mutate()}>Review sporting Saved Revision</button>
    {saveReview&&<section aria-label="Confirm saved simulation revision">
      <p>Current Saved Head <code>{saveReview.head}</code> · Draft version {saveReview.draftVersion} · simulation fingerprint <code>{saveReview.preview.simulation_fingerprint}</code>.</p>
      {!saveCurrent&&<p role="alert" className="error">Sporting changes changed; reopen Save preview.</p>}
      <label><input type="checkbox" aria-label="Approve Run sporting Save"
        checked={saveConfirmed} onChange={e=>setSaveConfirmed(e.target.checked)}/>
        Save all outstanding authoritative sporting changes.</label>
      <button type="button" disabled={!saveConfirmed||!saveCurrent||saveMutation.isPending}
        onClick={()=>saveMutation.mutate(saveReview)}>
        {saveMutation.isPending?'Saving Run…':'Commit and verify Saved Revision'}
      </button>
    </section>}
    {saveMutation.error&&<p role="alert" className="error">Save/reload failed: {formatApiError(saveMutation.error)}. Inspect current Branch Head before retrying.</p>}
    {savedRevision&&<p role="status">Verified new Saved Revision: <code>{savedRevision}</code>.</p>}
    {notice&&<p role="status">{notice}</p>}
    <p><Link to={`/admin/runs/${encodeURIComponent(runId)}/simulate?branch=${encodeURIComponent(branchId)}`}>Open authoritative Position, subsequent rounds and recovery controls</Link></p>
  </SectionCard>
}
