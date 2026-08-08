import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useEffect, useRef, useState } from 'react'
import { useParams } from 'react-router-dom'

import { getBranchCheckpoint, getBranchState, getRunContainer } from '../api/client'
import type { AdminBranchExecutionResponse, BranchState } from '../api/types'
import { useAdminBranch } from '../admin/AdminBranchContext'
import { adminBranchHeadQueryKey, adminBranchStateQueryKey } from '../admin/adminQueryKeys'
import { BranchSimulationAction, executeBranchSimulation, newCommandId, simulationActions, simulationEligibility, validExecutionResponse } from '../admin/branchSimulation'
import { CurrentContextStrip, MetadataList, PageIntro, SectionCard } from '../components/RunScopedUi'
import { formatApiError } from '../utils/apiErrors'

type Review = { action: BranchSimulationAction; runId: string; branchId: string; head: string; state: BranchState; checkpointKind: string }
type ExecutionSnapshot = Review & { auditReason: string; commandId: string; viewerBranchId: string | null }

export function RunSimulationPage(): JSX.Element {
  const { runId = '' } = useParams()
  const queryClient = useQueryClient()
  const { selectedBranchId, selectedBranch, viewerBranchId } = useAdminBranch()
  const [review, setReview] = useState<Review | null>(null)
  const [reason, setReason] = useState('')
  const [commandId, setCommandId] = useState(newCommandId)
  const [confirmed, setConfirmed] = useState(false)
  const [notice, setNotice] = useState<string | null>(null)
  const [result, setResult] = useState<AdminBranchExecutionResponse | null>(null)
  const currentContextRef = useRef({ runId, branchId: selectedBranchId })
  currentContextRef.current = { runId, branchId: selectedBranchId }

  const runQuery = useQuery({ queryKey: ['admin-run-container', runId], queryFn: () => getRunContainer(runId), enabled: Boolean(runId), retry: false })
  const stateQuery = useQuery({ queryKey: adminBranchStateQueryKey(runId, selectedBranchId), queryFn: () => getBranchState(selectedBranchId!), enabled: Boolean(runId && selectedBranchId), retry: false })
  const state = stateQuery.data?.run_id === runId && stateQuery.data.branch_id === selectedBranchId ? stateQuery.data : undefined
  const headId = selectedBranch?.head_checkpoint_id && state?.head_checkpoint_id === selectedBranch.head_checkpoint_id ? selectedBranch.head_checkpoint_id : null
  const checkpointQuery = useQuery({ queryKey: adminBranchHeadQueryKey(runId, selectedBranchId, headId), queryFn: () => getBranchCheckpoint(headId!), enabled: Boolean(headId), retry: false })
  const checkpoint = checkpointQuery.data?.checkpoint_id === headId && checkpointQuery.data.run_id === runId && checkpointQuery.data.branch_id === selectedBranchId ? checkpointQuery.data : undefined
  const eligibility = selectedBranch ? simulationEligibility(runQuery.data, selectedBranch, state, checkpoint ? [checkpoint] : []) : 'Select an Active Admin Branch in the header.'
  const currentHead = !eligibility ? headId : null

  useEffect(() => {
    setReview(null); setReason(''); setConfirmed(false); setNotice(null); setResult(null); setCommandId(newCommandId())
  }, [runId, selectedBranchId])

  async function refreshTarget(targetRunId: string, targetBranchId: string): Promise<void> {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: ['admin-run-branches', targetRunId] }),
      queryClient.invalidateQueries({ queryKey: adminBranchStateQueryKey(targetRunId, targetBranchId) }),
      queryClient.invalidateQueries({ queryKey: ['admin-branch-head', targetRunId, targetBranchId] }),
      queryClient.invalidateQueries({ queryKey: ['run-branches', targetRunId] }),
      queryClient.invalidateQueries({ queryKey: ['branch-states', targetRunId] }),
      queryClient.invalidateQueries({ queryKey: ['branch-checkpoints', targetRunId] }),
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
    if (!selectedBranchId || !state || !checkpoint || !currentHead) return
    setReview({ action, runId, branchId: selectedBranchId, head: currentHead, state, checkpointKind: checkpoint.kind })
    setConfirmed(false); setReason(''); setNotice(null); setResult(null); setCommandId(newCommandId())
  }
  const stale = Boolean(review && (review.runId !== runId || review.branchId !== selectedBranchId || review.head !== currentHead))
  const canSubmit = Boolean(review && !stale && !eligibility && reason.trim() && commandId.trim() && confirmed && !mutation.isPending)
  const mutationBelongsToCurrentContext = mutation.variables?.runId === runId && mutation.variables.branchId === selectedBranchId

  return <section className="panel">
    <PageIntro title="Simulation" subtitle="Advance the Active Admin Branch at its reviewed deterministic head." meta={`Run: ${runQuery.data?.display_name ?? runId}`} />
    <CurrentContextStrip items={[
      { label: 'Run', value: runId || '—' }, { label: 'Branch', value: selectedBranch ? `${selectedBranch.display_name} (${selectedBranch.branch_id})` : '—' },
      { label: 'Season', value: state?.current_season ?? '—' }, { label: 'Week', value: state?.current_week != null ? `W${state.current_week}` : '—' },
      { label: 'Event', value: state?.current_event_id ?? '—' }, { label: 'Head', value: currentHead ?? '—' },
    ]} />
    {(runQuery.isLoading || stateQuery.isLoading || checkpointQuery.isLoading) && <p className="status">Loading Active Admin Branch execution state…</p>}
    {(runQuery.error || stateQuery.error || checkpointQuery.error) && <p role="alert" className="error">Simulation context unavailable: {formatApiError(runQuery.error || stateQuery.error || checkpointQuery.error)}</p>}
    {eligibility && <p role="alert" className="error">Simulation blocked: {eligibility}</p>}
    <SectionCard title="Choose action"><div className="quick-actions">{(Object.keys(simulationActions) as BranchSimulationAction[]).map(action => <button key={action} type="button" disabled={Boolean(eligibility)} onClick={() => choose(action)}>{simulationActions[action].label}</button>)}</div></SectionCard>
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
