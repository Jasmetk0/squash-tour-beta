import { useEffect, useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import {
  commitAdminPlayerHealthEdit,
  getAdminPlayerHealth,
  previewAdminPlayerHealthEdit,
  previewPlayerHealthSave,
  savePlayerHealthRevision
} from '../api/client'
import type {
  AdminHealthEditMode,
  AdminHealthEditPreview,
  AdminHealthEditRequest,
  PermanentHealthConsequence,
  PlayerHealthKind,
  PlayerHealthLifecycle,
  PlayerHealthRecord,
  PlayerHealthWeek
} from '../api/types'
import { SectionCard, SummaryPills } from '../components/RunScopedUi'
import { formatApiError } from '../utils/apiErrors'

type RecordDraft = {
  record_id: string
  kind: PlayerHealthKind
  condition_key: string
  lifecycle: PlayerHealthLifecycle
  severity: string
  domains: string
  started_before_run: boolean
  onset_season: string
  onset_week: string
  recovered_season: string
  recovered_week: string
  recurrence_of_record_id: string
  recovery_min: string
  recovery_max: string
  provenance: string
}

type ConsequenceDraft = {
  consequence_id: string
  source_record_id: string
  domains: string
  limitation_severity: string
  provenance: string
}

const lifecycleOptions: PlayerHealthLifecycle[] = ['At Risk', 'Active', 'Recovering', 'Recovered']
const kindOptions: PlayerHealthKind[] = ['Injury', 'Illness']

function weekLabel(week: PlayerHealthWeek): string {
  return `${2000 + week.season_index}/${String(2001 + week.season_index).slice(-2)} · Week ${week.week}`
}

function weekOrdinal(week: PlayerHealthWeek): number {
  return week.season_index * 61 + week.week - 1
}

function seasonInput(week: PlayerHealthWeek | null): string {
  return week ? String(week.season_index + 1) : ''
}

function weekInput(week: PlayerHealthWeek | null): string {
  return week ? String(week.week) : ''
}

function recordToDraft(record: PlayerHealthRecord): RecordDraft {
  return {
    record_id: record.record_id,
    kind: record.kind,
    condition_key: record.condition_key,
    lifecycle: record.lifecycle,
    severity: String(record.severity),
    domains: record.affected_domains.join(', '),
    started_before_run: record.started_before_run,
    onset_season: seasonInput(record.onset_week),
    onset_week: weekInput(record.onset_week),
    recovered_season: seasonInput(record.recovered_week),
    recovered_week: weekInput(record.recovered_week),
    recurrence_of_record_id: record.recurrence_of_record_id ?? '',
    recovery_min: record.recovery_window_min_weeks === null ? '' : String(record.recovery_window_min_weeks),
    recovery_max: record.recovery_window_max_weeks === null ? '' : String(record.recovery_window_max_weeks),
    provenance: record.provenance
  }
}

function consequenceToDraft(consequence: PermanentHealthConsequence): ConsequenceDraft {
  return {
    consequence_id: consequence.consequence_id,
    source_record_id: consequence.source_record_id,
    domains: consequence.affected_domains.join(', '),
    limitation_severity: String(consequence.limitation_severity),
    provenance: consequence.provenance
  }
}

function canonicalDomains(value: string): string[] {
  return [...new Set(value.split(',').map(item => item.trim()).filter(Boolean))].sort()
}

function parseWeek(season: string, week: string): PlayerHealthWeek | null {
  if (!season.trim() || !week.trim()) return null
  const seasonNumber = Number(season)
  const weekNumber = Number(week)
  if (!Number.isInteger(seasonNumber) || seasonNumber < 1 || seasonNumber > 50) return null
  if (!Number.isInteger(weekNumber) || weekNumber < 1 || weekNumber > 61) return null
  return { season_index: seasonNumber - 1, week: weekNumber }
}

function newRecord(mode: AdminHealthEditMode, currentWeek: PlayerHealthWeek): RecordDraft {
  const id = `health-${crypto.randomUUID()}`
  const preStart = mode === 'pre_start_input'
  return {
    record_id: id,
    kind: 'Injury',
    condition_key: '',
    lifecycle: 'Active',
    severity: '1',
    domains: '',
    started_before_run: preStart,
    onset_season: preStart ? '' : String(currentWeek.season_index + 1),
    onset_week: preStart ? '' : String(currentWeek.week),
    recovered_season: '',
    recovered_week: '',
    recurrence_of_record_id: '',
    recovery_min: '',
    recovery_max: '',
    provenance: ''
  }
}

function newConsequence(records: RecordDraft[]): ConsequenceDraft {
  return {
    consequence_id: `consequence-${crypto.randomUUID()}`,
    source_record_id: records.find(record => record.lifecycle === 'Recovered')?.record_id ?? '',
    domains: '',
    limitation_severity: '1',
    provenance: ''
  }
}

function draftIssue(
  records: RecordDraft[],
  consequences: ConsequenceDraft[],
  mode: AdminHealthEditMode,
  currentWeek: PlayerHealthWeek,
  operator: string,
  reason: string,
  reviewed: boolean
): string | null {
  const recordIds = records.map(record => record.record_id.trim())
  if (recordIds.some(id => !id)) return 'Every Health record needs a record ID.'
  if (new Set(recordIds).size !== recordIds.length) return 'Health record IDs must be unique.'
  for (const record of records) {
    if (!record.condition_key.trim()) return `Record ${record.record_id || 'unknown'} needs a condition key.`
    const severity = Number(record.severity)
    if (!Number.isInteger(severity) || severity < 0 || severity > 100) return `Record ${record.record_id} severity must be 0–100.`
    if (canonicalDomains(record.domains).length === 0) return `Record ${record.record_id} needs at least one affected domain.`
    if (!record.provenance.trim()) return `Record ${record.record_id} needs provenance.`
    if (mode === 'pre_start_input' && !record.started_before_run) return 'Pre-start input requires every record to be marked as started before the Run.'
    if (record.started_before_run) {
      if (record.onset_season || record.onset_week) return `Record ${record.record_id} started before the Run and cannot have an onset Week.`
    } else {
      const onset = parseWeek(record.onset_season, record.onset_week)
      if (!onset) return `Record ${record.record_id} needs a valid onset season/week.`
      if (weekOrdinal(onset) > weekOrdinal(currentWeek)) return `Record ${record.record_id} onset cannot be in the future.`
    }
    if (record.lifecycle === 'Recovered') {
      const recovered = parseWeek(record.recovered_season, record.recovered_week)
      if (!record.started_before_run && !recovered) return `Recovered record ${record.record_id} needs a recovered season/week.`
      if (recovered && weekOrdinal(recovered) > weekOrdinal(currentWeek)) return `Record ${record.record_id} recovery cannot be in the future.`
    } else if (record.recovered_season || record.recovered_week) {
      return `Only Recovered record ${record.record_id} may have a recovered Week.`
    }
    const hasMin = Boolean(record.recovery_min.trim())
    const hasMax = Boolean(record.recovery_max.trim())
    if (hasMin !== hasMax) return `Record ${record.record_id} recovery window needs both min and max.`
    if (hasMin && hasMax) {
      const min = Number(record.recovery_min)
      const max = Number(record.recovery_max)
      if (!Number.isInteger(min) || !Number.isInteger(max) || min < 0 || max < min) return `Record ${record.record_id} has an invalid recovery window.`
    }
    if (record.recurrence_of_record_id && record.recurrence_of_record_id === record.record_id) return `Record ${record.record_id} cannot recur from itself.`
  }

  const consequenceIds = consequences.map(item => item.consequence_id.trim())
  if (consequenceIds.some(id => !id)) return 'Every permanent consequence needs an ID.'
  if (new Set(consequenceIds).size !== consequenceIds.length) return 'Permanent consequence IDs must be unique.'
  for (const consequence of consequences) {
    const source = records.find(record => record.record_id === consequence.source_record_id)
    if (!source || source.lifecycle !== 'Recovered') return `Consequence ${consequence.consequence_id} must reference a Recovered Health record.`
    if (canonicalDomains(consequence.domains).length === 0) return `Consequence ${consequence.consequence_id} needs an affected domain.`
    const severity = Number(consequence.limitation_severity)
    if (!Number.isInteger(severity) || severity < 1 || severity > 100) return `Consequence ${consequence.consequence_id} severity must be 1–100.`
    if (!consequence.provenance.trim()) return `Consequence ${consequence.consequence_id} needs provenance.`
  }
  if (!operator.trim()) return 'Operator label is required.'
  if (!reason.trim()) return 'Audit reason is required.'
  if (!reviewed) return 'Explicit review confirmation is required.'
  return null
}

function buildRecord(record: RecordDraft): PlayerHealthRecord {
  const min = record.recovery_min.trim() ? Number(record.recovery_min) : null
  const max = record.recovery_max.trim() ? Number(record.recovery_max) : null
  return {
    record_id: record.record_id.trim(),
    kind: record.kind,
    condition_key: record.condition_key.trim(),
    lifecycle: record.lifecycle,
    severity: Number(record.severity),
    affected_domains: canonicalDomains(record.domains),
    onset_week: record.started_before_run ? null : parseWeek(record.onset_season, record.onset_week),
    recovered_week: record.lifecycle === 'Recovered' ? parseWeek(record.recovered_season, record.recovered_week) : null,
    started_before_run: record.started_before_run,
    recurrence_of_record_id: record.recurrence_of_record_id || null,
    recovery_window_min_weeks: min,
    recovery_window_max_weeks: max,
    provenance: record.provenance.trim()
  }
}

function buildConsequence(consequence: ConsequenceDraft): PermanentHealthConsequence {
  return {
    consequence_id: consequence.consequence_id.trim(),
    source_record_id: consequence.source_record_id,
    affected_domains: canonicalDomains(consequence.domains),
    limitation_severity: Number(consequence.limitation_severity),
    provenance: consequence.provenance.trim()
  }
}

export function PlayerHealthAdminPanel({
  runId,
  branchId,
  branchReadOnly,
  playerId
}: {
  runId: string
  branchId: string
  branchReadOnly: boolean
  playerId: string
}): JSX.Element {
  const queryClient = useQueryClient()
  const healthKey = ['admin-player-health', runId, branchId, playerId]
  const saveKey = ['admin-player-health-save', runId, branchId]
  const healthQuery = useQuery({
    queryKey: healthKey,
    queryFn: () => getAdminPlayerHealth(runId, branchId, playerId),
    retry: false
  })
  const savePreviewQuery = useQuery({
    queryKey: saveKey,
    queryFn: () => previewPlayerHealthSave(runId, branchId),
    enabled: healthQuery.isSuccess,
    retry: false
  })

  const current = healthQuery.data
  const [editing, setEditing] = useState(false)
  const [mode, setMode] = useState<AdminHealthEditMode>('current_state_correction')
  const [records, setRecords] = useState<RecordDraft[]>([])
  const [consequences, setConsequences] = useState<ConsequenceDraft[]>([])
  const [operator, setOperator] = useState('')
  const [reason, setReason] = useState('')
  const [reviewed, setReviewed] = useState(false)
  const [review, setReview] = useState<{ request: AdminHealthEditRequest; preview: AdminHealthEditPreview } | null>(null)
  const [status, setStatus] = useState<string | null>(null)

  useEffect(() => {
    if (!current) return
    setRecords(current.player.records.map(recordToDraft))
    setConsequences(current.player.permanent_consequences.map(consequenceToDraft))
    setMode(
      weekOrdinal(current.week) === 0 && current.player.records.every(record => record.started_before_run)
        ? 'pre_start_input'
        : 'current_state_correction'
    )
    setEditing(false)
    setReview(null)
    setReviewed(false)
  }, [current?.state_fingerprint, current?.branch_id, current?.player.player_id])

  const issue = useMemo(
    () => current && editing
      ? draftIssue(records, consequences, mode, current.week, operator, reason, reviewed)
      : null,
    [consequences, current, editing, mode, operator, reason, records, reviewed]
  )

  const previewMutation = useMutation({
    mutationFn: (request: AdminHealthEditRequest) => previewAdminPlayerHealthEdit(runId, branchId, playerId, request),
    retry: false,
    onSuccess: (preview, request) => {
      setReview({ request, preview })
      setStatus(null)
    }
  })
  const commitMutation = useMutation({
    mutationFn: () => {
      if (!review) throw new Error('Calculate a reviewed Health preview first.')
      return commitAdminPlayerHealthEdit(runId, branchId, playerId, review.request, review.preview.preview_fingerprint)
    },
    retry: false,
    onSuccess: async result => {
      setStatus(result.already_applied ? 'This exact Health edit was already committed.' : 'Health edit committed to the Working Draft. Save a Health Revision to make it recoverable.')
      setReview(null)
      setEditing(false)
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: healthKey }),
        queryClient.invalidateQueries({ queryKey: saveKey }),
        queryClient.invalidateQueries({ queryKey: ['admin-run-branches', runId] })
      ])
    }
  })
  const saveMutation = useMutation({
    mutationFn: () => {
      const preview = savePreviewQuery.data
      if (!preview?.can_save) throw new Error('No reviewed Health Working Draft is ready to save.')
      return savePlayerHealthRevision(runId, branchId, {
        expected_draft_version: preview.draft_version,
        expected_player_health_fingerprint: preview.health_component_fingerprint
      })
    },
    retry: false,
    onSuccess: async result => {
      setStatus(`Health Saved Revision ${result.saved_revision.revision_id} created.`)
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: healthKey }),
        queryClient.invalidateQueries({ queryKey: saveKey }),
        queryClient.invalidateQueries({ queryKey: ['admin-run-branches', runId] }),
        queryClient.invalidateQueries({ queryKey: ['saved-revision-history', runId, branchId] })
      ])
    }
  })

  const beginEdit = () => {
    if (!current) return
    setRecords(current.player.records.map(recordToDraft))
    setConsequences(current.player.permanent_consequences.map(consequenceToDraft))
    setOperator('')
    setReason('')
    setReviewed(false)
    setReview(null)
    setStatus(null)
    setEditing(true)
  }

  const calculatePreview = () => {
    if (!current || issue) return
    const request: AdminHealthEditRequest = {
      schema_version: 'admin_health_edit_request.v1',
      command_id: `admin-health-${crypto.randomUUID()}`,
      player_id: playerId,
      mode,
      expected_draft_version: current.draft_version,
      records: records.map(buildRecord).sort((a, b) => a.record_id.localeCompare(b.record_id)),
      permanent_consequences: consequences.map(buildConsequence).sort((a, b) => a.consequence_id.localeCompare(b.consequence_id)),
      audit_label: operator.trim(),
      audit_reason: reason.trim()
    }
    previewMutation.mutate(request)
  }

  const updateRecord = (index: number, patch: Partial<RecordDraft>) => {
    setRecords(old => old.map((record, position) => position === index ? { ...record, ...patch } : record))
  }
  const updateConsequence = (index: number, patch: Partial<ConsequenceDraft>) => {
    setConsequences(old => old.map((item, position) => position === index ? { ...item, ...patch } : item))
  }

  return (
    <SectionCard title="Canonical Player Health">
      {healthQuery.isPending ? <p role="status">Loading canonical Health state…</p> : null}
      {healthQuery.isError ? <p role="alert">Health state unavailable: {formatApiError(healthQuery.error)}</p> : null}
      {current ? (
        <>
          <SummaryPills
            items={[
              { label: 'Branch', value: branchId },
              { label: 'Week', value: weekLabel(current.week) },
              { label: 'Health records', value: current.player.records.length },
              { label: 'Permanent consequences', value: current.player.permanent_consequences.length },
              { label: 'Draft version', value: current.draft_version }
            ]}
          />
          <p className="status">State {current.state_fingerprint.slice(0, 12)} · component {current.health_component_fingerprint.slice(0, 12)}</p>
          {branchReadOnly ? <p role="alert">The Active Admin Branch is read-only. Health can be inspected but not edited.</p> : null}
          {!editing ? (
            <>
              {current.player.records.length === 0 ? <p>No Injury or Illness records are present at this Week.</p> : (
                <div className="table-scroll">
                  <table aria-label="Current Health records">
                    <thead><tr><th>ID</th><th>Type</th><th>Condition</th><th>Lifecycle</th><th>Severity</th><th>Domains</th><th>Origin</th></tr></thead>
                    <tbody>
                      {current.player.records.map(record => (
                        <tr key={record.record_id}>
                          <td>{record.record_id}</td>
                          <td>{record.kind}</td>
                          <td>{record.condition_key}</td>
                          <td>{record.lifecycle}</td>
                          <td>{record.severity}</td>
                          <td>{record.affected_domains.join(', ')}</td>
                          <td>{record.started_before_run ? 'Pre-start' : record.onset_week ? weekLabel(record.onset_week) : '—'}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
              {current.player.permanent_consequences.length > 0 ? (
                <div className="table-scroll">
                  <table aria-label="Permanent Health consequences">
                    <thead><tr><th>ID</th><th>Source</th><th>Severity</th><th>Domains</th></tr></thead>
                    <tbody>{current.player.permanent_consequences.map(item => (
                      <tr key={item.consequence_id}><td>{item.consequence_id}</td><td>{item.source_record_id}</td><td>{item.limitation_severity}</td><td>{item.affected_domains.join(', ')}</td></tr>
                    ))}</tbody>
                  </table>
                </div>
              ) : null}
              <button type="button" onClick={beginEdit} disabled={branchReadOnly}>Edit current Health</button>
            </>
          ) : (
            <section aria-label="Edit current Player Health">
              <h3>Reviewed Health edit</h3>
              <p>This replaces the selected player's complete Health profile at the current authoritative Week. Historical predecessor state is not rewritten.</p>
              {weekOrdinal(current.week) === 0 ? (
                <label>
                  Edit mode
                  <select value={mode} disabled={Boolean(review)} onChange={event => setMode(event.target.value as AdminHealthEditMode)}>
                    <option value="pre_start_input">Pre-start input</option>
                    <option value="current_state_correction">Current-state correction</option>
                  </select>
                </label>
              ) : <p>Mode: current-state correction</p>}
              <fieldset disabled={Boolean(review) || previewMutation.isPending || commitMutation.isPending}>
                <legend>Health records</legend>
                {records.length === 0 ? <p>No records. Add an Injury or Illness below.</p> : null}
                {records.map((record, index) => (
                  <fieldset key={record.record_id || index}>
                    <legend>Record {index + 1}</legend>
                    <label>Record ID <input value={record.record_id} maxLength={160} onChange={event => updateRecord(index, { record_id: event.target.value })} /></label>
                    <label>Type <select value={record.kind} onChange={event => updateRecord(index, { kind: event.target.value as PlayerHealthKind, recurrence_of_record_id: '' })}>{kindOptions.map(kind => <option key={kind}>{kind}</option>)}</select></label>
                    <label>Condition key <input value={record.condition_key} maxLength={160} onChange={event => updateRecord(index, { condition_key: event.target.value })} /></label>
                    <label>Lifecycle <select value={record.lifecycle} onChange={event => updateRecord(index, { lifecycle: event.target.value as PlayerHealthLifecycle, ...(event.target.value === 'Recovered' ? {} : { recovered_season: '', recovered_week: '' }) })}>{lifecycleOptions.map(value => <option key={value}>{value}</option>)}</select></label>
                    <label>Severity 0–100 <input type="number" min={0} max={100} step={1} value={record.severity} onChange={event => updateRecord(index, { severity: event.target.value })} /></label>
                    <label>Affected domains (comma separated) <input value={record.domains} onChange={event => updateRecord(index, { domains: event.target.value })} /></label>
                    <label className="checkbox-label"><input type="checkbox" checked={record.started_before_run} disabled={mode === 'pre_start_input'} onChange={event => updateRecord(index, { started_before_run: event.target.checked, onset_season: event.target.checked ? '' : String(current.week.season_index + 1), onset_week: event.target.checked ? '' : String(current.week.week) })} />Started before Run</label>
                    {!record.started_before_run ? (
                      <>
                        <label>Onset season (1–50) <input type="number" min={1} max={50} value={record.onset_season} onChange={event => updateRecord(index, { onset_season: event.target.value })} /></label>
                        <label>Onset week <input type="number" min={1} max={61} value={record.onset_week} onChange={event => updateRecord(index, { onset_week: event.target.value })} /></label>
                      </>
                    ) : null}
                    {record.lifecycle === 'Recovered' ? (
                      <>
                        <label>Recovered season (1–50) <input type="number" min={1} max={50} value={record.recovered_season} onChange={event => updateRecord(index, { recovered_season: event.target.value })} /></label>
                        <label>Recovered week <input type="number" min={1} max={61} value={record.recovered_week} onChange={event => updateRecord(index, { recovered_week: event.target.value })} /></label>
                      </>
                    ) : null}
                    <label>
                      Recurrence of
                      <select value={record.recurrence_of_record_id} onChange={event => updateRecord(index, { recurrence_of_record_id: event.target.value })}>
                        <option value="">None</option>
                        {records.filter(candidate => candidate.record_id !== record.record_id && candidate.kind === record.kind).map(candidate => <option key={candidate.record_id} value={candidate.record_id}>{candidate.record_id}</option>)}
                      </select>
                    </label>
                    <label>Recovery estimate min weeks <input type="number" min={0} max={520} value={record.recovery_min} onChange={event => updateRecord(index, { recovery_min: event.target.value })} /></label>
                    <label>Recovery estimate max weeks <input type="number" min={0} max={520} value={record.recovery_max} onChange={event => updateRecord(index, { recovery_max: event.target.value })} /></label>
                    <label>Provenance <textarea maxLength={1000} value={record.provenance} onChange={event => updateRecord(index, { provenance: event.target.value })} /></label>
                    <button type="button" onClick={() => setRecords(old => old.filter((_, position) => position !== index))}>Remove record {index + 1}</button>
                  </fieldset>
                ))}
                <button type="button" onClick={() => setRecords(old => [...old, newRecord(mode, current.week)])}>Add Health record</button>
              </fieldset>

              <fieldset disabled={Boolean(review) || previewMutation.isPending || commitMutation.isPending}>
                <legend>Permanent consequences</legend>
                {consequences.length === 0 ? <p>No permanent consequences.</p> : null}
                {consequences.map((item, index) => (
                  <fieldset key={item.consequence_id || index}>
                    <legend>Consequence {index + 1}</legend>
                    <label>Consequence ID <input maxLength={160} value={item.consequence_id} onChange={event => updateConsequence(index, { consequence_id: event.target.value })} /></label>
                    <label>Recovered source record <select value={item.source_record_id} onChange={event => updateConsequence(index, { source_record_id: event.target.value })}><option value="">Select source</option>{records.filter(record => record.lifecycle === 'Recovered').map(record => <option key={record.record_id} value={record.record_id}>{record.record_id}</option>)}</select></label>
                    <label>Affected domains (comma separated) <input value={item.domains} onChange={event => updateConsequence(index, { domains: event.target.value })} /></label>
                    <label>Limitation severity 1–100 <input type="number" min={1} max={100} value={item.limitation_severity} onChange={event => updateConsequence(index, { limitation_severity: event.target.value })} /></label>
                    <label>Provenance <textarea maxLength={1000} value={item.provenance} onChange={event => updateConsequence(index, { provenance: event.target.value })} /></label>
                    <button type="button" onClick={() => setConsequences(old => old.filter((_, position) => position !== index))}>Remove consequence {index + 1}</button>
                  </fieldset>
                ))}
                <button type="button" onClick={() => setConsequences(old => [...old, newConsequence(records)])}>Add permanent consequence</button>
              </fieldset>

              <fieldset disabled={Boolean(review) || previewMutation.isPending || commitMutation.isPending}>
                <legend>Audit and review</legend>
                <label>Operator label <input maxLength={200} value={operator} onChange={event => setOperator(event.target.value)} /></label>
                <label>Reason <textarea maxLength={2000} value={reason} onChange={event => setReason(event.target.value)} /></label>
                <label className="checkbox-label"><input type="checkbox" checked={reviewed} onChange={event => setReviewed(event.target.checked)} />I reviewed the complete current Health profile and this correction.</label>
                <button type="button" disabled={Boolean(issue)} onClick={calculatePreview}>Calculate Health preview</button>
                <button type="button" onClick={() => { setEditing(false); setReview(null) }}>Cancel edit</button>
                {issue ? <p className="status">{issue}</p> : null}
              </fieldset>

              {previewMutation.isPending ? <p role="status">Calculating Health preview…</p> : null}
              {previewMutation.isError ? <p role="alert">{formatApiError(previewMutation.error)}</p> : null}
              {review ? (
                <section aria-label="Health edit preview">
                  <h3>Review Health preview</h3>
                  <SummaryPills items={[
                    { label: 'Week', value: weekLabel(review.preview.week) },
                    { label: 'Records after', value: review.preview.after_state.players.find(player => player.player_id === playerId)?.records.length ?? 0 },
                    { label: 'Consequences after', value: review.preview.after_state.players.find(player => player.player_id === playerId)?.permanent_consequences.length ?? 0 },
                    { label: 'Before', value: review.preview.before_state_fingerprint.slice(0, 12) },
                    { label: 'After component', value: review.preview.after_component_fingerprint.slice(0, 12) }
                  ]} />
                  <p>Preview fingerprint: {review.preview.preview_fingerprint.slice(0, 16)}…</p>
                  <button type="button" disabled={commitMutation.isPending} onClick={() => commitMutation.mutate()}>{commitMutation.isError ? 'Retry exact Health commit' : 'Confirm reviewed Health edit'}</button>
                  <button type="button" disabled={commitMutation.isPending} onClick={() => { setReview(null); previewMutation.reset(); commitMutation.reset(); setReviewed(false) }}>Edit inputs and recalculate</button>
                  {commitMutation.isPending ? <p role="status">Committing Health edit…</p> : null}
                  {commitMutation.isError ? <p role="alert">{formatApiError(commitMutation.error)} The reviewed request is retained for an exact retry.</p> : null}
                </section>
              ) : null}
            </section>
          )}

          <section aria-label="Save Player Health revision">
            <h3>Save Health Revision</h3>
            {savePreviewQuery.isPending ? <p role="status">Checking Health Save state…</p> : null}
            {savePreviewQuery.isError ? <p role="alert">Health Save state unavailable: {formatApiError(savePreviewQuery.error)}</p> : null}
            {savePreviewQuery.data ? (
              <>
                <p>{savePreviewQuery.data.changed_since_saved_head ? 'Health differs from the current Saved Revision.' : 'Current Health is already captured by the Saved Revision.'}</p>
                <button type="button" disabled={branchReadOnly || !savePreviewQuery.data.can_save || saveMutation.isPending} onClick={() => saveMutation.mutate()}>Save Health Revision</button>
              </>
            ) : null}
            {saveMutation.isPending ? <p role="status">Saving Health Revision…</p> : null}
            {saveMutation.isError ? <p role="alert">{formatApiError(saveMutation.error)}</p> : null}
          </section>
          {status ? <p role="status">{status}</p> : null}
        </>
      ) : null}
    </SectionCard>
  )
}
