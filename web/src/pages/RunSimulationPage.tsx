import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useEffect, useRef, useState } from 'react'
import { useParams, useSearchParams } from 'react-router-dom'

import { getBranchCheckpoint, getBranchState, getRunContainer, getRunPackageState } from '../api/client'
import type { AdminBranchExecutionResponse, BranchState } from '../api/types'
import { useAdminBranch } from '../admin/AdminBranchContext'
import { useAdminTime } from '../admin/AdminTimeContext'
import { adminBranchCheckpointsQueryKey, adminBranchHeadQueryKey, adminBranchStateQueryKey } from '../admin/adminQueryKeys'
import { BranchSimulationAction, executeBranchSimulation, newCommandId, simulationActions, simulationEligibility, validExecutionResponse } from '../admin/branchSimulation'
import { CurrentContextStrip, MetadataList, PageIntro, SectionCard } from '../components/RunScopedUi'
import { formatApiError } from '../utils/apiErrors'
import { AuthoritativeSimulationPanel } from './AuthoritativeSimulationPanel'

type Review = { action: BranchSimulationAction; runId: string; branchId: string; head: string; state: BranchState; checkpointKind: string }
type ExecutionSnapshot = Review & { auditReason: string; commandId: string; viewerBranchId: string | null }

export function RunSimulationPage(): JSX.Element {
  const { runId = '' } = useParams()
  const [searchParams] = useSearchParams()
  const queryClient = useQueryClient()
  const { selectedBranchId, selectedBranch, viewerBranchId, branches, isLoading: branchesLoading, selectBranch } = useAdminBranch()
  const requestedBranchId = searchParams.get('branch')?.trim() ?? ''
  const requestedBranch = requestedBranchId ? branches.find(branch => branch.branch_id === requestedBranchId) ?? null : null
  const requestedBranchInvalid = Boolean(requestedBranchId && !branchesLoading && !requestedBranch)
  const requestedBranchPending = Boolean(requestedBranch && selectedBranchId !== requestedBranch.branch_id)
  const executionBranchId = requestedBranchId ? (requestedBranchPending || requestedBranchInvalid ? null : selectedBranchId) : selectedBranchId
  const executionBranch = executionBranchId ? selectedBranch : null
  const time = useAdminTime()
  const [review, setReview] = useState<Review | null>(null)
  const [reason, setReason] = useState('')
  const [commandId, setCommandId] = useState(newCommandId)
  const [confirmed, setConfirmed] = useState(false)
  const [notice, setNotice] = useState<string | null>(null)
  const [result, setResult] = useState<AdminBranchExecutionResponse | null>(null)
  const currentContextRef = useRef({ runId, branchId: executionBranchId })
  currentContextRef.current = { runId, branchId: executionBranchId }

  useEffect(() => {
    if (requestedBranch && selectedBranchId !== requestedBranch.branch_id) selectBranch(requestedBranch.branch_id)
  }, [requestedBranch, selectedBranchId, selectBranch])

  const runQuery = useQuery({ queryKey: ['admin-run-container', runId], queryFn: () => getRunContainer(runId), enabled: Boolean(runId), retry: false })
  const stateQuery = useQuery({ queryKey: adminBranchStateQueryKey(runId, executionBranchId), queryFn: () => getBranchState(executionBranchId!), enabled: Boolean(runId && executionBranchId), retry: false })
  const state = stateQuery.data?.run_id === runId && stateQuery.data.branch_id === executionBranchId ? stateQuery.data : undefined
  const headId = executionBranch?.head_checkpoint_id && state?.head_checkpoint_id === executionBranch.head_checkpoint_id ? executionBranch.head_checkpoint_id : null
  const checkpointQuery = useQuery({ queryKey: adminBranchHeadQueryKey(runId, executionBranchId, headId), queryFn: () => getBranchCheckpoint(headId!), enabled: Boolean(headId), retry: false })
  const packageQuery = useQuery({ queryKey: ['run-package-state', runId, executionBranchId], queryFn: () => getRunPackageState(runId, executionBranchId!), enabled: Boolean(runId && executionBranchId), retry: false })
  const packageOwnership = packageQuery.isSuccess ? (packageQuery.data.state === null ? 'historical' : 'package') : 'unknown'
  const checkpoint = checkpointQuery.data?.checkpoint_id === headId && checkpointQuery.data.run_id === runId && checkpointQuery.data.branch_id === executionBranchId ? checkpointQuery.data : undefined
  const eligibility = executionBranch ? simulationEligibility(runQuery.data, executionBranch, state, checkpoint ? [checkpoint] : []) : requestedBranchInvalid ? 'Requested Branch does not exist in this Product Run.' : requestedBranchPending ? 'Selecting requested Branch…' : 'Select an Active Admin Branch in the header.'
  const currentHead = !eligibility ? headId : null
  const canonicalEligibility = !executionBranch
    ? 'Select an Active Admin Branch in the header.'
    : executionBranch.run_id !== runId
      ? 'Branch belongs to another Product Run.'
      : runQuery.isLoading
        ? 'Product Run is still loading.'
        : !runQuery.data
          ? 'Product Run is unavailable.'
          : runQuery.data.status !== 'active'
            ? 'Product Run must be active.'
            : runQuery.data.read_only
              ? 'Product Run is read-only.'
              : executionBranch.status !== 'active'
                ? 'Branch must be active.'
                : executionBranch.read_only
                  ? 'Branch is read-only.'
                  : !executionBranch.saved_head_revision_id
                    ? 'Branch has no Saved Revision head.'
                    : null

  useEffect(() => {
    setReview(null); setReason(''); setConfirmed(false); setNotice(null); setResult(null); setCommandId(newCommandId())
  }, [runId, executionBranchId])

  useEffect(() => {
    if (review?.action !== 'world_tour_finals' && packageOwnership !== 'historical') {
      setReview(null); setConfirmed(false)
    }
  }, [packageOwnership, review?.action])

  async function refreshTarget(targetRunId: string, targetBranchId: string): Promise<void> {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: ['admin-run-branches', targetRunId] }),
      queryClient.invalidateQueries({ queryKey: adminBranchStateQueryKey(targetRunId, targetBranchId) }),
      queryClient.invalidateQueries({ queryKey: ['admin-branch-head', targetRunId, targetBranchId] }),
      queryClient.invalidateQueries({ queryKey: ['run-branches', targetRunId] }),
      queryClient.invalidateQueries({ queryKey: ['branch-states', targetRunId] }),
      queryClient.invalidateQueries({ queryKey: ['branch-checkpoints', targetRunId] }),
      queryClient.invalidateQueries({ queryKey: adminBranchCheckpointsQueryKey(targetRunId, targetBranchId) }),
    ])
  }

  const mutation = useMutation({
    mutationFn: (snapshot: ExecutionSnapshot) => executeBranchSimulation(snapshot.action, snapshot.runId, snapshot.branchId, {
      expected_head_checkpoint_id: snapshot.head, command_id: snapshot.commandId, audit_reason: snapshot.auditReason, explicit_confirmation: true,
    }),
    onSuccess: async (response, snapshot) => {
      const isCurrent = currentContextRef.current.runId === snapshot.runId && currentContextRef.current.branchId === snapshot.branchId
      if (!validExecutionResponse(response, snapshot.action, snapshot.runId, snapshot.branchId, snapshot.head)) {
        if (isCurrent) { setConfirmed(false); setCommandId(newCommandId()); setResult(null); setReview(null); setNotice('Response contract error. Refresh and review the Branch head again.') }
        await refreshTarget(snapshot.runId, snapshot.branchId); return
      }
      if (isCurrent) {
        setConfirmed(false); setCommandId(newCommandId()); setResult(response); setReview(null)
        setNotice(`${simulationActions[snapshot.action].label} advanced ${snapshot.branchId} from ${response.previous_head_checkpoint_id} to ${response.new_head_checkpoint_id}. The Viewer Branch pointer was not changed.`)
      }
      await refreshTarget(snapshot.runId, snapshot.branchId)
      await queryClient.invalidateQueries({ predicate: query => query.queryKey.includes(response.legacy_simulation_run_id) })
      if (snapshot.branchId === snapshot.viewerBranchId) await queryClient.invalidateQueries({ queryKey: ['viewer-official-run-context', snapshot.runId] })
    },
    onError: async (error, snapshot) => {
      if ((error as { status?: number }).status !== 409) return
      const isCurrent = currentContextRef.current.runId === snapshot.runId && currentContextRef.current.branchId === snapshot.branchId
      if (isCurrent) { setConfirmed(false); setReview(null); setCommandId(newCommandId()); setNotice('Branch execution state changed. The target was refreshed; review the new head before trying again.') }
      await refreshTarget(snapshot.runId, snapshot.branchId)
    }
  })

  function choose(action: BranchSimulationAction): void {
    if (action !== 'world_tour_finals' && packageOwnership !== 'historical') return
    if (!executionBranchId || !state || !checkpoint || !currentHead) return
    setReview({ action, runId, branchId: executionBranchId, head: currentHead, state, checkpointKind: checkpoint.kind })
    setConfirmed(false); setReason(''); setNotice(null); setResult(null); setCommandId(newCommandId())
  }
  const stale = Boolean(review && (review.runId !== runId || review.branchId !== executionBranchId || review.head !== currentHead))
  const canSubmit = Boolean(review && (review.action === 'world_tour_finals' || packageOwnership === 'historical') && !stale && !eligibility && reason.trim() && commandId.trim() && confirmed && !mutation.isPending)
  const mutationBelongsToCurrentContext = mutation.variables?.runId === runId && mutation.variables.branchId === executionBranchId

  return <section className="panel">
    <PageIntro title="Simulation" subtitle="Advance the Active Admin Branch at its reviewed deterministic head." meta={`Run: ${runQuery.data?.display_name ?? runId}`} />
    <CurrentContextStrip items={[
      { label: 'Run', value: runId || '—' }, { label: 'Branch', value: executionBranch ? `${executionBranch.display_name} (${executionBranch.branch_id})` : requestedBranchInvalid ? `Invalid requested Branch: ${requestedBranchId}` : requestedBranchPending ? `Selecting ${requestedBranchId}…` : '—' },
      { label: 'View context', value: time.mode === 'present' ? 'Present' : `Past · S${time.viewSeason ?? '—'} · ${time.viewWeek == null ? '—' : `W${time.viewWeek}`} · ${time.viewCheckpointId ?? 'unavailable'}` },
      { label: 'Execution target', value: 'Branch HEAD' },
      { label: 'Season', value: state?.current_season ?? '—' }, { label: 'Week', value: state?.current_week != null ? `W${state.current_week}` : '—' },
      { label: 'Event', value: state?.current_event_id ?? '—' }, { label: 'Head', value: currentHead ?? '—' },
    ]} />
    {(runQuery.isLoading || branchesLoading || requestedBranchPending || stateQuery.isLoading || checkpointQuery.isLoading) && <p className="status">Loading Active Admin Branch execution state…</p>}
    {requestedBranchInvalid ? <p className="error">Requested Branch {requestedBranchId} does not exist in this Product Run. Choose a valid Admin Branch before simulation.</p> : null}
    {(runQuery.error || stateQuery.error || checkpointQuery.error) && <p role="alert" className="error">Simulation context unavailable: {formatApiError(runQuery.error || stateQuery.error || checkpointQuery.error)}</p>}
    <AuthoritativeSimulationPanel
      runId={runId}
      branchId={executionBranchId ?? ''}
      savedRevisionId={executionBranch?.saved_head_revision_id ?? null}
      blockedReason={canonicalEligibility}
    />

    {eligibility && <p role="alert" className="error">Legacy compatibility simulation blocked: {eligibility}</p>}
    <SectionCard title="Legacy compatibility simulation actions">
      <p className="status">
        These controls still use the legacy branch simulation wrapper. Canonical Next Match, Next Slot, Next Match Day, Next Round, Next Tournament, Next Week, Next Season and Full Simulation now live in the authoritative panel above; legacy actions remain compatibility tools only.
      </p>
      {packageOwnership === 'package' && <p className="status">This Branch is Package-backed. Use the authoritative simulation panel above for Next Match, Next Round, Next Week, Next Tournament, and Full Season.</p>}
      {packageOwnership === 'unknown' && <p role="alert" className="error">Package ownership is being verified or is unavailable. Legacy non-Finals actions are blocked until this Branch is verified as historical.</p>}
      <div className="quick-actions">{(Object.keys(simulationActions) as BranchSimulationAction[]).filter(action => action === 'world_tour_finals' || packageOwnership !== 'package').map(action => <button key={action} type="button" disabled={Boolean(eligibility) || (action !== 'world_tour_finals' && packageOwnership !== 'historical')} onClick={() => choose(action)}>{simulationActions[action].label}</button>)}</div>
    </SectionCard>
    {review && <SectionCard title={`Review ${simulationActions[review.action].label}`}>
      <form onSubmit={event => { event.preventDefault(); if (canSubmit && review) mutation.mutate({ ...review, auditReason: reason.trim(), commandId: commandId.trim(), viewerBranchId }) }}>
        <MetadataList items={[{ label: 'Action', value: simulationActions[review.action].label }, { label: 'Run', value: review.runId }, { label: 'Branch', value: review.branchId }, { label: 'Reviewed head', value: review.head }, { label: 'Checkpoint kind', value: review.checkpointKind }, { label: 'Season', value: review.state.current_season ?? '—' }, { label: 'Week', value: review.state.current_week ?? '—' }, { label: 'Event', value: review.state.current_event_id ?? '—' }, { label: 'Event sequence', value: review.state.current_event_sequence ?? '—' }]} />
        <p>{simulationActions[review.action].explanation}</p><p>Only this Branch advances. The Viewer Branch pointer never changes.</p>
        {stale && <p role="alert" className="error">The Active Admin Branch or head changed. Choose the action again to review current state.</p>}
        <label>Simulation audit reason<textarea aria-label="Simulation audit reason" value={reason} onChange={event => setReason(event.target.value)} /></label>
        <p>Caller-generated Command ID: <code aria-label="Simulation command ID">{commandId}</code> <button type="button" onClick={() => { setCommandId(newCommandId()); setConfirmed(false) }}>Generate new command ID</button></p>
        <label><input aria-label="Confirm simulation" type="checkbox" checked={confirmed} onChange={event => setConfirmed(event.target.checked)} /> {simulationActions[review.action].confirmationLabel}</label>
        <button type="submit" disabled={!canSubmit}>{mutation.isPending ? 'Executing…' : simulationActions[review.action].confirmationLabel}</button>
      </form>
    </SectionCard>}
    {notice && <p className="status">{notice}</p>}{mutation.error && mutationBelongsToCurrentContext && (mutation.error as { status?: number }).status !== 409 && <p className="error">{formatApiError(mutation.error)}</p>}
    {result && <SectionCard title="Execution result"><MetadataList items={[{ label: 'Branch', value: result.branch_id }, { label: 'Previous head', value: result.previous_head_checkpoint_id }, { label: 'New head', value: result.new_head_checkpoint_id }, { label: 'Viewer Branch pointer changed', value: result.official_branch_changed ? 'Yes' : 'No' }]} /></SectionCard>}
  </section>
}
