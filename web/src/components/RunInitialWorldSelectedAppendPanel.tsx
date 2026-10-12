/** Add a reviewed subset to an already SAVED, pre-ranking InitialWorld. */
import { useEffect, useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import {
  previewRunOwnedInitialWorld, previewSelectedInitialWorldAppend,
  commitSelectedInitialWorldAppend
} from '../api/client'
import type {
  RunInitialWorldAdoption, RunInitialWorldPreview, RunInitialWorldState,
  SelectedInitialWorldAppendRequest, SelectedInitialWorldAppendPreview
} from '../api/runInitialWorldSetup'
import { verifiedInitialWorldPreview } from '../api/runInitialWorldSetup'
import { formatApiError } from '../utils/apiErrors'
import { GeneratedPlayerReviewInspector } from './GeneratedPlayerReviewInspector'

type Source = {request: RunInitialWorldAdoption; preview: RunInitialWorldPreview}
type Candidate = {request: SelectedInitialWorldAppendRequest; preview: SelectedInitialWorldAppendPreview}

export function RunInitialWorldSelectedAppendPanel({
  runId, branchId, head, draftVersion, packageFingerprint, current,
  currentFingerprint, enabled
}: {
  runId: string
  branchId: string
  head: string
  draftVersion: number
  packageFingerprint: string
  current: RunInitialWorldState
  currentFingerprint: string
  enabled: boolean
}): JSX.Element {
  const queryClient = useQueryClient()
  const [seed, setSeed] = useState(20261012)
  const [count, setCount] = useState(128)
  const [auditReason, setAuditReason] = useState(
    'Add specifically reviewed generated players to the saved opening population.'
  )
  const [source, setSource] = useState<Source | null>(null)
  const [selectedIds, setSelectedIds] = useState<string[]>([])
  const [candidate, setCandidate] = useState<Candidate | null>(null)
  const [approved, setApproved] = useState(false)
  const [notice, setNotice] = useState('')
  const worldId = current.world_package_id
  const worldFingerprint = current.adoption_request_fingerprint
  const knownIds = new Set(current.players.map(p=>p.player_id))
  const conflicts = selectedIds.filter(id=>knownIds.has(id))
  const canGenerate = enabled && Boolean(worldId) &&
    Number.isSafeInteger(seed) && Number.isSafeInteger(count) && count>=1 && count<=1000 &&
    /^[a-f0-9]{64}$/.test(packageFingerprint)

  useEffect(() => {
    setSource(null);setSelectedIds([]);setCandidate(null);setApproved(false);setNotice('')
  }, [runId,branchId,head,draftVersion,packageFingerprint,worldFingerprint,
      seed,count,auditReason])

  const sourceAction=useMutation({
    mutationFn:async ():Promise<Source>=>{
      if(!canGenerate || !worldId) throw new Error('Saved Run, World and valid generation inputs are required.')
      const request:RunInitialWorldAdoption={
        command_id:'selected-append-source-'+crypto.randomUUID(),
        generation:{
          world_package_id:worldId,season:'2000/2001',
          seed,target_pool_size:count,naming_policy:'country_serial.v1'
        },
        audit_label:'Review source cohort for selected append',
        audit_reason:'Read-only new cohort. Select specific unique identities for append.',
        official_run:false,
        best_n:current.policies[0]?.best_n??15,
        automatic_retirement_age:46
      }
      const preview=await previewRunOwnedInitialWorld(runId,branchId,request)
      if(!verifiedInitialWorldPreview(preview,runId,branchId,request))
        throw new Error('New source cohort failed exact Run-owned preview validation.')
      return {request,preview}
    },
    onSuccess:next=>{
      setSource(next);setSelectedIds([]);setCandidate(null);setApproved(false)
      setNotice('Generated a read-only source. Select only IDs missing from the saved InitialWorld.')
    }
  })

  const preflightAction=useMutation({
    mutationFn:async ():Promise<Candidate>=>{
      if(!enabled || !source || !worldId || !selectedIds.length || conflicts.length ||
          !auditReason.trim() || auditReason.length>1000)
        throw new Error('Select non-colliding players from the exact verified source.')
      const request:SelectedInitialWorldAppendRequest={
        append:{
          command_id:'selected-append-'+crypto.randomUUID(),
          generation:source.request,
          selected_player_ids:[...new Set(selectedIds)].sort(),
          audit_label:'Add reviewed players',
          audit_reason:auditReason.trim()
        },
        expected_head:head,
        expected_draft_version:draftVersion,
        expected_package_fingerprint:packageFingerprint,
        expected_initial_world_fingerprint:currentFingerprint
      }
      const preview=await previewSelectedInitialWorldAppend(runId,branchId,request)
      if(!preview.preview_only || !/^[a-f0-9]{64}$/.test(preview.fingerprint) ||
        preview.state.run_id!==runId || preview.state.branch_id!==branchId ||
        preview.added_count!==request.append.selected_player_ids.length ||
        preview.state.players.length!==current.players.length+preview.added_count ||
        preview.state.selected_appends?.slice(-1)[0]?.command_id!==request.append.command_id)
        throw new Error('Selected append preview failed Run/Branch or cardinality verification.')
      const before=new Map(current.players.map(p=>[p.player_id,JSON.stringify(p)]))
      const after=new Map(preview.state.players.map(p=>[p.player_id,JSON.stringify(p)]))
      if(after.size!==preview.state.players.length || [...before].some(([id,p])=>after.get(id)!==p) ||
          request.append.selected_player_ids.some(id=>before.has(id)||!after.has(id)))
        throw new Error('Selected append mutated old players or returned an unknown selected ID.')
      return {request,preview}
    },
    onSuccess:next=>{setCandidate(next);setApproved(false);setNotice(
      'Server verified the selected subset. Explicit Commit and manual Saved Revision remain separate.'
    )}
  })
  const commitAction=useMutation({
    mutationFn:async ()=>{
      if(!enabled || !candidate || !approved)
        throw new Error('Approve only the exact server-verified selected append.')
      const installed=await commitSelectedInitialWorldAppend(
        runId,branchId,candidate.request,candidate.preview.fingerprint
      )
      if(installed.run_id!==runId || installed.branch_id!==branchId ||
        installed.players.length!==candidate.preview.state.players.length ||
        installed.selected_appends?.slice(-1)[0]?.command_id!==candidate.request.append.command_id)
        throw new Error('Commit response is inconsistent: inspect stored InitialWorld before saving.')
      return installed
    },
    onSuccess:async()=>{
      setSource(null);setCandidate(null);setSelectedIds([]);setApproved(false)
      setNotice('Selected players staged in InitialWorld. Use the separate Save InitialWorld revision below.')
      await Promise.all([
        queryClient.invalidateQueries({queryKey:['run-owned-initial-world',runId,branchId]}),
        queryClient.invalidateQueries({queryKey:['initial-world-save-preview',runId,branchId]})
      ])
    },
    onError:()=>{
      setCandidate(null);setApproved(false)
      void queryClient.invalidateQueries({queryKey:['run-owned-initial-world',runId,branchId]})
    }
  })
  // The parent provides the exact stored InitialWorld fingerprint from the
  // authoritative save-preflight endpoint, not from an unsaved UI projection.
  return <section className="section-subtle" aria-label="Add selected generated players">
    <h4>Add selected players to saved InitialWorld</h4>
    <p className="status">
      Existing players: {current.players.length}. This path requires an exactly saved,
      untouched Week-1 InitialWorld. It is closed once ranking/sporting activity starts.
      It never replaces existing player identities, runs Keep, or automatically Saves.
    </p>
    {!enabled && <p role="alert">
      First finish the pending Save, or resolve the current Run/Branch/World state.
    </p>}
    <div className="form-grid">
      <label>New source seed
        <input aria-label="Selected append source seed" type="number" value={seed}
          onChange={e=>setSeed(Number(e.target.value))} />
      </label>
      <label>New source cohort size (1–1000)
        <input aria-label="Selected append source size" type="number" min={1} max={1000}
          value={count} onChange={e=>setCount(Number(e.target.value))} />
      </label>
    </div>
    <label>Append audit reason
      <input aria-label="Selected append audit reason" maxLength={1000}
        value={auditReason} onChange={e=>setAuditReason(e.target.value)} />
    </label>
    <button type="button" disabled={!canGenerate || sourceAction.isPending ||
      commitAction.isPending} onClick={()=>sourceAction.mutate()}>
      Preview source players (read-only)
    </button>
    {sourceAction.error && <p role="alert">Source unavailable: {formatApiError(sourceAction.error)}</p>}
    {source && <div>
      <p role="status">Candidate source: {source.preview.state.players.length} players.
        Existing IDs in source: {source.preview.state.players.filter(p=>knownIds.has(p.player_id)).length}.
        Selection is separate from Keep and Adopt.
      </p>
      <GeneratedPlayerReviewInspector
        key={source.preview.fingerprint} players={source.preview.state.players}
        bulkSelectedIds={selectedIds}
        bulkSelectionDisabled={Boolean(candidate)||preflightAction.isPending||commitAction.isPending}
        onBulkSelectionChange={ids=>{setSelectedIds(ids);setCandidate(null);setApproved(false)}} />
      <p role="status">Selected: {selectedIds.length}. Conflicting IDs: {conflicts.length}.</p>
      {conflicts.length>0 && <p role="alert">
        These IDs already exist and cannot be added: {conflicts.slice(0,10).join(', ')}
        {conflicts.length>10?'…':''}
      </p>}
      <button type="button" disabled={!enabled || !selectedIds.length || conflicts.length>0 ||
        Boolean(candidate) || preflightAction.isPending || commitAction.isPending}
        onClick={()=>preflightAction.mutate()}>
        Verify selected addition on server (no write)
      </button>
    </div>}
    {preflightAction.error && <p role="alert">
      Selected append preview failed: {formatApiError(preflightAction.error)}
    </p>}
    {candidate && <section aria-label="Verified selected append">
      <p role="status">Verified exact new identities: {candidate.preview.added_count}.
        Total after append: {candidate.preview.state.players.length}. Fingerprint:
        <code>{candidate.preview.fingerprint.slice(0,16)}…</code>.
        No source or Saved Revision changed during Preview.
      </p>
      <label><input type="checkbox" aria-label="Approve selected InitialWorld append"
        checked={approved} onChange={e=>setApproved(e.target.checked)} />
        Commit these exact selected players to the current Working state.
      </label>
      <button type="button" disabled={!enabled || !approved || commitAction.isPending}
        onClick={()=>commitAction.mutate()}>
        {commitAction.isPending?'Committing selected players…':'Commit selected players (Save separately)'}
      </button>
      <button type="button" disabled={commitAction.isPending} onClick={()=>{
        setCandidate(null);setApproved(false)
      }}>Discard selected append approval</button>
    </section>}
    {commitAction.error && <p role="alert">
      Append conflict: {formatApiError(commitAction.error)}
    </p>}
    {notice && <p role="status">{notice}</p>}
  </section>
}
