import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { useParams } from 'react-router-dom'

import { forkRunBranch, getRunContainer, listBranchCheckpoints, listBranchStates, listRunBranches } from '../api/client'
import type { AdminForkRunBranchRequest, BranchCheckpoint, RunBranch } from '../api/types'
import { EmptyState, MetadataList, PageIntro, SectionCard } from '../components/RunScopedUi'
import { formatApiError } from '../utils/apiErrors'

const forkSafeKinds = new Set(['initial', 'current_state_capture'])
const fieldNames = ['target_branch_display_name', 'target_branch_id', 'target_legacy_simulation_run_id', 'target_branch_seed', 'command_id'] as const

type FormValues = Record<(typeof fieldNames)[number], string>
const emptyForm: FormValues = { target_branch_display_name: '', target_branch_id: '', target_legacy_simulation_run_id: '', target_branch_seed: '', command_id: '' }

export function AdminRunBranchesPage(): JSX.Element {
  const { runId = '' } = useParams()
  const queryClient = useQueryClient()
  const [sourceBranchId, setSourceBranchId] = useState('')
  const [form, setForm] = useState<FormValues>(emptyForm)
  const [confirmed, setConfirmed] = useState(false)
  const runQuery = useQuery({ queryKey: ['run-container', runId], queryFn: () => getRunContainer(runId), enabled: Boolean(runId) })
  const branchesQuery = useQuery({ queryKey: ['run-branches', runId], queryFn: () => listRunBranches(runId), enabled: Boolean(runId) })
  const statesQuery = useQuery({ queryKey: ['branch-states', runId], queryFn: () => listBranchStates({ run_id: runId }), enabled: Boolean(runId) })
  const checkpointsQuery = useQuery({ queryKey: ['branch-checkpoints', runId], queryFn: () => listBranchCheckpoints({ run_id: runId }), enabled: Boolean(runId) })
  const branches = branchesQuery.data?.run_branches ?? []
  const selectedId = sourceBranchId || branches[0]?.branch_id || ''
  const selected = branches.find((branch) => branch.branch_id === selectedId)
  const selectedState = statesQuery.data?.branch_states.find((state) => state.branch_id === selectedId)
  const effectiveHead = selected?.head_checkpoint_id && selectedState?.head_checkpoint_id === selected.head_checkpoint_id ? selected.head_checkpoint_id : null
  const headCheckpoint = checkpointsQuery.data?.branch_checkpoints.find((checkpoint) => checkpoint.checkpoint_id === effectiveHead)
  const sourceEligible = Boolean(selected && selected.status === 'active' && !selected.read_only && effectiveHead && headCheckpoint && forkSafeKinds.has(headCheckpoint.kind))
  const validForm = fieldNames.every((name) => form[name].trim()) && /^-?\d+$/.test(form.target_branch_seed.trim())
  const mutation = useMutation({
    mutationFn: (payload: AdminForkRunBranchRequest) => forkRunBranch(runId, payload),
    onSuccess: async () => {
      await Promise.all(['run-container', 'run-branches', 'branch-states', 'branch-checkpoints'].map((key) => queryClient.invalidateQueries({ queryKey: [key, runId] })))
    }
  })
  const canSubmit = sourceEligible && validForm && confirmed && !mutation.isPending
  const allCheckpoints = checkpointsQuery.data?.branch_checkpoints ?? []
  const loading = runQuery.isLoading || branchesQuery.isLoading || statesQuery.isLoading || checkpointsQuery.isLoading
  const error = runQuery.error || branchesQuery.error || statesQuery.error || checkpointsQuery.error

  function submit(event: React.FormEvent<HTMLFormElement>): void {
    event.preventDefault()
    if (!canSubmit || !selected || !effectiveHead) return
    mutation.mutate({
      source_branch_id: selected.branch_id, source_checkpoint_id: effectiveHead,
      target_branch_id: form.target_branch_id.trim(), target_branch_display_name: form.target_branch_display_name.trim(),
      target_legacy_simulation_run_id: form.target_legacy_simulation_run_id.trim(), target_branch_seed: Number.parseInt(form.target_branch_seed.trim(), 10), command_id: form.command_id.trim()
    })
  }

  return <main>
    <PageIntro title="Manage Branches" subtitle="Inspect Product Run Branches and create an independent atomic fork." meta={`Product Run: ${runId || 'unknown'}`} />
    {loading && <p className="status">Loading Branches...</p>}
    {error && <p className="error">Failed to load Branches: {formatApiError(error)}</p>}
    {!loading && !error && <>
      <SectionCard title="Product Run">
        <MetadataList items={[{ label: 'Display name', value: runQuery.data?.display_name ?? '—' }, { label: 'Status', value: runQuery.data?.status ?? '—' }, { label: 'Branches', value: branches.length }]} />
      </SectionCard>
      <SectionCard title="Branches">
        {branches.length === 0 ? <EmptyState message="No Branches are available for this Product Run." /> : <div className="item-list" aria-label="Product Run Branches">{branches.map((branch) => <BranchCard key={branch.branch_id} branch={branch} checkpoint={allCheckpoints.find((item) => item.checkpoint_id === branch.head_checkpoint_id)} state={statesQuery.data?.branch_states.find((item) => item.branch_id === branch.branch_id)} />)}</div>}
      </SectionCard>
      <SectionCard title="Create Branch fork">
        <form onSubmit={submit}>
          <label>Source Branch<select aria-label="Source Branch" value={selectedId} onChange={(event) => setSourceBranchId(event.target.value)}>{branches.map((branch) => <option key={branch.branch_id} value={branch.branch_id}>{branch.display_name} ({branch.branch_id})</option>)}</select></label>
          <p>Source checkpoint: <strong>{effectiveHead ?? 'No safe effective head'}</strong></p>
          {!sourceEligible && <p className="error">The selected source must be active, writable, have agreeing heads, and use an initial or current_state_capture head.</p>}
          {fieldNames.map((name) => <label key={name}>{name.replace(/_/g, ' ')}<input aria-label={name} value={form[name]} onChange={(event) => setForm({ ...form, [name]: event.target.value })} /></label>)}
          <label><input type="checkbox" checked={confirmed} onChange={(event) => setConfirmed(event.target.checked)} /> I understand this creates an independent Branch and does not change the official Branch.</label>
          <button type="submit" disabled={!canSubmit}>{mutation.isPending ? 'Creating fork...' : 'Create Branch fork'}</button>
        </form>
        {mutation.error && <p className="error">{formatApiError(mutation.error)}</p>}
        {mutation.data && <div className="status" aria-label="Fork result">Created target Branch: {mutation.data.target_branch_id}; target checkpoint: {mutation.data.target_checkpoint_id}; target legacy run: {mutation.data.target_legacy_simulation_run_id}; idempotent replay: {String(mutation.data.idempotent_replay)}; created_mapping: {String(mutation.data.created_mapping)}; official_branch_changed: {String(mutation.data.official_branch_changed)}</div>}
      </SectionCard>
      <SectionCard title="Selected Branch checkpoints">
        {!selected ? <EmptyState message="Select a Branch to inspect checkpoints." /> : <ul className="item-list" aria-label="Branch checkpoints">{allCheckpoints.filter((checkpoint) => checkpoint.branch_id === selected.branch_id).map((checkpoint) => <li key={checkpoint.checkpoint_id}><strong>{checkpoint.checkpoint_id}</strong> — {checkpoint.kind}, sequence {checkpoint.sequence}, season {checkpoint.season}, week {checkpoint.week ?? '—'}, event {checkpoint.event_id ?? '—'}; {checkpoint.checkpoint_id === effectiveHead ? ' effective head;' : ''} {checkpoint.checkpoint_id === effectiveHead && forkSafeKinds.has(checkpoint.kind) ? ' fork-safe' : ' not fork-safe'}</li>)}</ul>}
      </SectionCard>
    </>}
  </main>
}

function BranchCard({ branch, state, checkpoint }: { branch: RunBranch; state?: { head_checkpoint_id: string | null; current_season: number | null; current_week: number | null; current_event_id: string | null; current_event_sequence: number | null }; checkpoint?: BranchCheckpoint }): JSX.Element {
  const mode = branch.is_official ? 'Official Branch' : branch.status === 'active' && !branch.read_only ? 'Active writable Branch' : 'Read-only or inactive Branch'
  return <article className="panel nested-panel"><h4>{branch.display_name} {branch.is_official && <span className="status">Official</span>}</h4><p>{mode}</p><MetadataList items={[{ label: 'Branch ID', value: branch.branch_id }, { label: 'Status', value: branch.status }, { label: 'Read only', value: String(branch.read_only) }, { label: 'Branch seed', value: branch.branch_seed ?? '—' }, { label: 'Legacy simulation run', value: branch.legacy_simulation_run_id ?? '—' }, { label: 'Forked from Branch', value: branch.forked_from_branch_id ?? '—' }, { label: 'Forked from checkpoint', value: branch.forked_from_checkpoint_id ?? '—' }, { label: 'Head checkpoint', value: branch.head_checkpoint_id ?? '—' }, { label: 'Effective head', value: branch.head_checkpoint_id && branch.head_checkpoint_id === state?.head_checkpoint_id ? branch.head_checkpoint_id : 'Heads disagree or missing' }, { label: 'Current season', value: state?.current_season ?? '—' }, { label: 'Current week', value: state?.current_week ?? '—' }, { label: 'Current event ID', value: state?.current_event_id ?? '—' }, { label: 'Current event sequence', value: state?.current_event_sequence ?? '—' }, { label: 'Head kind', value: checkpoint?.kind ?? '—' }]} /></article>
}
