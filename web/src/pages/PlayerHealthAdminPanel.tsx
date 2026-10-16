import { useEffect, useMemo, useRef, useState } from 'react'
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
  PlayerHealthProfile,
  PlayerHealthKind,
  PlayerHealthLifecycle,
  PlayerHealthRecord,
  PlayerHealthWeek
} from '../api/types'
import { SectionCard, SummaryPills } from '../components/RunScopedUi'
import { formatApiError } from '../utils/apiErrors'
import { healthClock, healthOrdinal as weekOrdinal, healthWeekLabel as weekLabel, parseHealthWeek, sameHealthWeek, validateHealthView, validateHealthReview } from '../api/healthCalendar'
import { validateInitialHealthSave } from '../api/calendarInitialHealth'
import { acknowledgeSavedRunForm } from '../components/RunNavigationSafeguard'
import { healthIssue, healthText } from '../i18n/healthText'

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
      const onset = parseHealthWeek(record.onset_season, record.onset_week, currentWeek)
      if (!onset) return `Record ${record.record_id} needs a valid onset season/week.`
      if (weekOrdinal(onset) > weekOrdinal(currentWeek)) return `Record ${record.record_id} onset cannot be in the future.`
    }
    if (record.lifecycle === 'Recovered') {
      const recovered = parseHealthWeek(record.recovered_season, record.recovered_week, currentWeek)
      if ((record.recovered_season || record.recovered_week) && !recovered) return `Record ${record.record_id} needs a valid recovered season/week.`
      if (record.severity !== '0') return `Recovered record ${record.record_id} must have zero acute severity.`
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
      if (!Number.isInteger(min) || !Number.isInteger(max) || min < 0 || max < min || max > 520) return `Record ${record.record_id} has an invalid recovery window.`
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

function buildRecord(record: RecordDraft, currentWeek: PlayerHealthWeek): PlayerHealthRecord {
  const min = record.recovery_min.trim() ? Number(record.recovery_min) : null
  const max = record.recovery_max.trim() ? Number(record.recovery_max) : null
  return {
    record_id: record.record_id.trim(),
    kind: record.kind,
    condition_key: record.condition_key.trim(),
    lifecycle: record.lifecycle,
    severity: Number(record.severity),
    affected_domains: canonicalDomains(record.domains),
    onset_week: record.started_before_run ? null : parseHealthWeek(record.onset_season, record.onset_week, currentWeek),
    recovered_week: record.lifecycle === 'Recovered' ? parseHealthWeek(record.recovered_season, record.recovered_week, currentWeek) : null,
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

function HealthProfileReview({profile,locale}:{profile:PlayerHealthProfile;locale:'cs'|'en'}):JSX.Element {
  const t=(en:string)=>healthText(en,locale)
  return <div>
    {!profile.records.length&&<p>{t('No records. Add an Injury or Illness below.')}</p>}
    {profile.records.map(r=><article key={r.record_id}>
      <h5>{r.record_id}: {r.condition_key}</h5>
      <p>{t(r.kind)} · {t(r.lifecycle)} · {t('Severity')}: {r.severity} · {t('Domains')}: {r.affected_domains.join(', ')}</p>
      <p>{t('Origin')}: {r.started_before_run?t('Pre-start'):r.onset_week?weekLabel(r.onset_week,locale):'—'}
        {' · '}{t('Recovered week')}: {r.recovered_week?weekLabel(r.recovered_week,locale):'—'}</p>
      <p>{t('Recurrence of')}: {r.recurrence_of_record_id??'—'} · {t('Recovery estimate min weeks')}: {r.recovery_window_min_weeks??'—'}
        {' · '}{t('Recovery estimate max weeks')}: {r.recovery_window_max_weeks??'—'}</p>
      <p>{t('Provenance')}: {r.provenance}</p>
    </article>)}
    {profile.permanent_consequences.map(c=><article key={c.consequence_id}>
      <h5>{t('Consequence')}: {c.consequence_id}</h5>
      <p>{t('Source')}: {c.source_record_id} · {t('Severity')}: {c.limitation_severity} · {t('Domains')}: {c.affected_domains.join(', ')}</p>
      <p>{t('Provenance')}: {c.provenance}</p>
    </article>)}
  </div>
}

export function PlayerHealthAdminPanel({
  runId,
  branchId,
  branchReadOnly,
  playerId,
  savedHead,
  locale = 'en'
}: {
  runId: string
  branchId: string
  branchReadOnly: boolean
  playerId: string
  savedHead?: string
  locale?: 'cs' | 'en'
}): JSX.Element {
  const queryClient = useQueryClient()
  const t = (en: string) => healthText(en, locale)
  const healthKey = ['admin-player-health', runId, branchId, playerId, savedHead]
  const saveKey = ['admin-player-health-save', runId, branchId]
  const healthQuery = useQuery({
    queryKey: healthKey,
    queryFn: async () => validateHealthView(await getAdminPlayerHealth(runId, branchId, playerId), runId, branchId, playerId, savedHead),
    retry: false
  })
  const savePreviewQuery = useQuery({
    queryKey: saveKey,
    queryFn: () => previewPlayerHealthSave(runId, branchId),
    enabled: healthQuery.isSuccess,
    retry: false
  })

  const current = healthQuery.isError ? undefined : healthQuery.data
  const saveProof = savePreviewQuery.data
  const saveReady = Boolean(current && saveProof && !healthQuery.isFetching && !savePreviewQuery.isFetching
    && !healthQuery.isError && !savePreviewQuery.isError && !branchReadOnly && saveProof.can_save
    && saveProof.run_id===runId && saveProof.branch_id===branchId
    && saveProof.draft_version===current.draft_version
    && saveProof.health_component_fingerprint===current.health_component_fingerprint)
  const [editing, setEditing] = useState(false)
  const [mode, setMode] = useState<AdminHealthEditMode>('current_state_correction')
  const [records, setRecords] = useState<RecordDraft[]>([])
  const [consequences, setConsequences] = useState<ConsequenceDraft[]>([])
  const [operator, setOperator] = useState('')
  const [reason, setReason] = useState('')
  const [reviewed, setReviewed] = useState(false)
  const [review, setReview] = useState<{ request: AdminHealthEditRequest; preview: AdminHealthEditPreview; epoch: number } | null>(null)
  const [confirmApproved, setConfirmApproved] = useState(false)
  const [saveApproved, setSaveApproved] = useState(false)
  const [status, setStatus] = useState<string | null>(null)

  const source = JSON.stringify([runId, branchId, playerId, savedHead, branchReadOnly,
    current?.saved_head_revision_id, current?.state_fingerprint, current?.draft_version, healthQuery.isError, savePreviewQuery.isError,
    savePreviewQuery.data?.draft_version, savePreviewQuery.data?.health_component_fingerprint,
    mode, records, consequences, operator, reason])
  const guard = useRef({source, epoch: 0})
  if (guard.current.source !== source) guard.current = {source, epoch: guard.current.epoch + 1}
  useEffect(() => {setReview(null);setReviewed(false);setConfirmApproved(false);setSaveApproved(false)}, [source])

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
  }, [runId, branchId, playerId, savedHead, current?.state_fingerprint, current?.saved_head_revision_id, current?.draft_version])

  const issue = useMemo(
    () => current && editing
      ? draftIssue(records, consequences, mode, current.week, operator, reason, reviewed)
      : null,
    [consequences, current, editing, mode, operator, reason, records, reviewed]
  )

  const refresh = async (run = runId, branch = branchId) => {
    await Promise.all(['admin-player-health','admin-player-health-save','admin-run-branches',
      'run-branches','saved-player-profile','saved-revision-history','calendar-initial-health','package-working-draft']
      .map(key=>queryClient.invalidateQueries({queryKey:[key,run]})))
    void branch
  }
  const previewMutation = useMutation({
    mutationFn: async ({request,epoch}: {request:AdminHealthEditRequest;epoch:number}) => {
      if(!current)throw Error('Health source changed; reload this Run.')
      const preview = validateHealthReview(await previewAdminPlayerHealthEdit(runId,branchId,playerId,request), request, current)
      return {request,preview,epoch}
    }, retry:false,
    onSuccess: value => {
      if(value.epoch===guard.current.epoch){setReview(value);setConfirmApproved(false);setStatus(null)}
    }
  })
  const commitMutation = useMutation({
    mutationFn: async (frozen: NonNullable<typeof review>) => {
      if(!confirmApproved||frozen.epoch!==guard.current.epoch||branchReadOnly)throw Error('Health source changed; reload this Run.')
      const result=await commitAdminPlayerHealthEdit(frozen.preview.run_id,frozen.preview.branch_id,frozen.request.player_id,frozen.request,frozen.preview.preview_fingerprint)
      if(result.run_id!==runId||result.branch_id!==branchId||result.player_id!==playerId
        ||result.command_id!==frozen.request.command_id||!sameHealthWeek(result.week,frozen.preview.week)
        ||result.health_component_fingerprint!==frozen.preview.after_component_fingerprint)throw Error('Confirmed health differs from review.')
      return result
    }, retry:false,
    onSuccess: async (result,frozen) => {
      if(frozen.epoch===guard.current.epoch){
        setStatus(t(result.already_applied?'This exact Health edit was already committed.':'Health edit committed to the Working Draft. Save a Health Revision to make it recoverable.'))
        setReview(null);setEditing(false);setConfirmApproved(false)
      }
      await refresh(frozen.preview.run_id,frozen.preview.branch_id)
    },
    onError: async (_error,frozen) => {setConfirmApproved(false);await refresh(frozen.preview.run_id,frozen.preview.branch_id)}
  })
  const saveMutation = useMutation({
    mutationFn: async (epoch:number) => {
      const proof=savePreviewQuery.data
      if(epoch!==guard.current.epoch||healthQuery.isError||savePreviewQuery.isError||!saveApproved||!proof?.can_save||branchReadOnly||proof.run_id!==runId||proof.branch_id!==branchId
        ||proof.draft_version!==current?.draft_version||proof.health_component_fingerprint!==current?.health_component_fingerprint)throw Error('Health Save proof changed.')
      const result=await savePlayerHealthRevision(runId,branchId,{
        expected_draft_version:proof.draft_version,expected_player_health_fingerprint:proof.health_component_fingerprint})
      validateInitialHealthSave(result,runId,branchId,proof.health_component_fingerprint)
      return {result,run:runId,branch:branchId,epoch}
    },retry:false,
    onSuccess:async ({result,run,branch,epoch})=>{
      acknowledgeSavedRunForm(run,branch)
      if(epoch===guard.current.epoch){setSaveApproved(false);setStatus(t('Health Saved Revision created.')+' '+result.saved_revision.revision_id)}
      await refresh(run,branch)
    },onError:async()=>{setSaveApproved(false);await refresh()}
  })

  useEffect(()=>{setStatus(null)},[runId,branchId,playerId,savedHead])

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
      ...(current.schema_version==='admin_health_current_view.v2' ? {schema_version:'admin_health_edit_request.v2' as const,expected_saved_head:current.saved_head_revision_id!,expected_state_fingerprint:current.state_fingerprint} : {schema_version:'admin_health_edit_request.v1' as const}),
      command_id: `admin-health-${crypto.randomUUID()}`,
      player_id: playerId,
      mode,
      expected_draft_version: current.draft_version,
      records: records.map(record=>buildRecord(record,current.week)).sort((a, b) => a.record_id.localeCompare(b.record_id)),
      permanent_consequences: consequences.map(buildConsequence).sort((a, b) => a.consequence_id.localeCompare(b.consequence_id)),
      audit_label: operator.trim(),
      audit_reason: reason.trim()
    }
    setConfirmApproved(false)
    previewMutation.mutate({request,epoch:guard.current.epoch})
  }

  const updateRecord = (index: number, patch: Partial<RecordDraft>) => {
    setRecords(old => old.map((record, position) => position === index ? { ...record, ...patch } : record))
  }
  const updateConsequence = (index: number, patch: Partial<ConsequenceDraft>) => {
    setConsequences(old => old.map((item, position) => position === index ? { ...item, ...patch } : item))
  }

  return (
    <SectionCard title={t("Canonical Player Health")}>
      {healthQuery.isPending ? <p role="status">{t("Loading canonical Health state\u2026")}</p> : null}
      {healthQuery.isError ? <p role="alert">{t("Health state unavailable:")} {formatApiError(healthQuery.error)}</p> : null}
      {current ? (
        <>
          <SummaryPills
            items={[
              { label: t('Branch'), value: branchId },
              { label: t('Week'), value: weekLabel(current.week,locale) },
              { label: t('Health records'), value: current.player.records.length },
              { label: t('Permanent consequences'), value: current.player.permanent_consequences.length },
              { label: t('Draft version'), value: current.draft_version }
            ]}
          />
          <p className="status">{t("State")} {current.state_fingerprint.slice(0, 12)} · component {current.health_component_fingerprint.slice(0, 12)}</p>
          {branchReadOnly ? <p role="alert">{t("The Active Admin Branch is read-only. Health can be inspected but not edited.")}</p> : null}
          {!editing ? (
            <>
              {current.player.records.length === 0 ? <p>{t("No Injury or Illness records are present at this Week.")}</p> : (
                <div className="table-scroll">
                  <table aria-label={t("Current Health records")}>
                    <thead><tr><th>{t("ID")}</th><th>{t("Type")}</th><th>{t("Condition")}</th><th>{t("Lifecycle")}</th><th>{t("Severity")}</th><th>{t("Domains")}</th><th>{t("Origin")}</th></tr></thead>
                    <tbody>
                      {current.player.records.map(record => (
                        <tr key={record.record_id}>
                          <td>{record.record_id}</td>
                          <td>{record.kind}</td>
                          <td>{record.condition_key}</td>
                          <td>{record.lifecycle}</td>
                          <td>{record.severity}</td>
                          <td>{record.affected_domains.join(', ')}</td>
                          <td>{record.started_before_run ? t('Pre-start') : record.onset_week ? weekLabel(record.onset_week,locale) : '—'}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
              {current.player.permanent_consequences.length > 0 ? (
                <div className="table-scroll">
                  <table aria-label={t("Permanent Health consequences")}>
                    <thead><tr><th>{t("ID")}</th><th>{t("Source")}</th><th>{t("Severity")}</th><th>{t("Domains")}</th></tr></thead>
                    <tbody>{current.player.permanent_consequences.map(item => (
                      <tr key={item.consequence_id}><td>{item.consequence_id}</td><td>{item.source_record_id}</td><td>{item.limitation_severity}</td><td>{item.affected_domains.join(', ')}</td></tr>
                    ))}</tbody>
                  </table>
                </div>
              ) : null}
              <button type="button" onClick={beginEdit} disabled={branchReadOnly}>{t("Edit current Health")}</button>
            </>
          ) : (
            <section aria-label={t("Edit current Player Health")}>
              <p>{current.week.calendar ? `${t("Run calendar")}: W${current.week.calendar.weeks_per_year}, ${t("offset")} ${current.week.calendar.season_start_year_week}, ${healthClock(current.week).season_count} ${t("seasons")}` : t("Historical FAX calendar")}</p>
              <h3>{t("Reviewed Health edit")}</h3>
              <p>{t("This replaces the selected player's complete Health profile at the current authoritative Week. Historical predecessor state is not rewritten.")}</p>
              {weekOrdinal(current.week) === 0 ? (
                <label>
                  {t("Edit mode")}
                  <select aria-label={t("Edit mode")} value={mode} disabled={Boolean(review) || previewMutation.isPending || commitMutation.isPending} onChange={event => setMode(event.target.value as AdminHealthEditMode)}>
                    <option value="pre_start_input">{t("Pre-start input")}</option>
                    <option value="current_state_correction">{t("Current-state correction")}</option>
                  </select>
                </label>
              ) : <p>{t("Mode: current-state correction")}</p>}
              <fieldset disabled={Boolean(review) || previewMutation.isPending || commitMutation.isPending}>
                <legend>{t("Health records")}</legend>
                {records.length === 0 ? <p>{t("No records. Add an Injury or Illness below.")}</p> : null}
                {records.map((record, index) => (
                  <fieldset key={record.record_id || index}>
                    <legend>{t("Record")} {index + 1}</legend>
                    <label>{t("Record ID")} <input value={record.record_id} maxLength={160} onChange={event => updateRecord(index, { record_id: event.target.value })} /></label>
                    <label>{t("Type")} <select aria-label={t("Type")} value={record.kind} onChange={event => updateRecord(index, { kind: event.target.value as PlayerHealthKind, recurrence_of_record_id: '' })}>{kindOptions.map(kind => <option key={kind} value={kind}>{t(kind)}</option>)}</select></label>
                    <label>{t("Condition key")} <input value={record.condition_key} maxLength={160} onChange={event => updateRecord(index, { condition_key: event.target.value })} /></label>
                    <label>{t("Lifecycle")} <select aria-label={t("Lifecycle")} value={record.lifecycle} onChange={event => updateRecord(index, { lifecycle: event.target.value as PlayerHealthLifecycle, ...(event.target.value === 'Recovered' ? {} : { recovered_season: '', recovered_week: '' }) })}>{lifecycleOptions.map(value => <option key={value} value={value}>{t(value)}</option>)}</select></label>
                    <label>{t("Severity 0\u2013100")} <input type="number" min={0} max={100} step={1} value={record.severity} onChange={event => updateRecord(index, { severity: event.target.value })} /></label>
                    <label>{t("Affected domains (comma separated)")} <input value={record.domains} onChange={event => updateRecord(index, { domains: event.target.value })} /></label>
                    <label className="checkbox-label"><input type="checkbox" checked={record.started_before_run} disabled={mode === 'pre_start_input'} onChange={event => updateRecord(index, { started_before_run: event.target.checked, onset_season: event.target.checked ? '' : String(current.week.season_index + 1), onset_week: event.target.checked ? '' : String(current.week.week) })} />{t("Started before Run")}</label>
                    {!record.started_before_run ? (
                      <>
                        <label>{t("Onset season")} <input type="number" min={1} max={healthClock(current.week).season_count} value={record.onset_season} onChange={event => updateRecord(index, { onset_season: event.target.value })} /></label>
                        <label>{t("Onset week")} <input type="number" min={1} max={healthClock(current.week).weeks_per_year} value={record.onset_week} onChange={event => updateRecord(index, { onset_week: event.target.value })} /></label>
                      </>
                    ) : null}
                    {record.lifecycle === 'Recovered' ? (
                      <>
                        <label>{t("Recovered season")} <input type="number" min={1} max={healthClock(current.week).season_count} value={record.recovered_season} onChange={event => updateRecord(index, { recovered_season: event.target.value })} /></label>
                        <label>{t("Recovered week")} <input type="number" min={1} max={healthClock(current.week).weeks_per_year} value={record.recovered_week} onChange={event => updateRecord(index, { recovered_week: event.target.value })} /></label>
                      </>
                    ) : null}
                    <label>
                      {t("Recurrence of")}
                      <select aria-label={t("Recurrence of")} value={record.recurrence_of_record_id} onChange={event => updateRecord(index, { recurrence_of_record_id: event.target.value })}>
                        <option value="">{t("None")}</option>
                        {records.filter(candidate => candidate.record_id !== record.record_id && candidate.kind === record.kind).map(candidate => <option key={candidate.record_id} value={candidate.record_id}>{candidate.record_id}</option>)}
                      </select>
                    </label>
                    <label>{t("Recovery estimate min weeks")} <input type="number" min={0} max={520} value={record.recovery_min} onChange={event => updateRecord(index, { recovery_min: event.target.value })} /></label>
                    <label>{t("Recovery estimate max weeks")} <input type="number" min={0} max={520} value={record.recovery_max} onChange={event => updateRecord(index, { recovery_max: event.target.value })} /></label>
                    <label>{t("Provenance")} <textarea maxLength={1000} value={record.provenance} onChange={event => updateRecord(index, { provenance: event.target.value })} /></label>
                    <button type="button" onClick={() => setRecords(old => old.filter((_, position) => position !== index))}>{t("Remove record")} {index + 1}</button>
                  </fieldset>
                ))}
                <button type="button" onClick={() => setRecords(old => [...old, newRecord(mode, current.week)])}>{t("Add Health record")}</button>
              </fieldset>

              <fieldset disabled={Boolean(review) || previewMutation.isPending || commitMutation.isPending}>
                <legend>{t("Permanent consequences")}</legend>
                {consequences.length === 0 ? <p>{t("No permanent consequences.")}</p> : null}
                {consequences.map((item, index) => (
                  <fieldset key={item.consequence_id || index}>
                    <legend>{t("Consequence")} {index + 1}</legend>
                    <label>{t("Consequence ID")} <input maxLength={160} value={item.consequence_id} onChange={event => updateConsequence(index, { consequence_id: event.target.value })} /></label>
                    <label>{t("Recovered source record")} <select aria-label={t("Recovered source record")} value={item.source_record_id} onChange={event => updateConsequence(index, { source_record_id: event.target.value })}><option value="">{t("Select source")}</option>{records.filter(record => record.lifecycle === 'Recovered').map(record => <option key={record.record_id} value={record.record_id}>{record.record_id}</option>)}</select></label>
                    <label>{t("Affected domains (comma separated)")} <input value={item.domains} onChange={event => updateConsequence(index, { domains: event.target.value })} /></label>
                    <label>{t("Limitation severity 1\u2013100")} <input type="number" min={1} max={100} value={item.limitation_severity} onChange={event => updateConsequence(index, { limitation_severity: event.target.value })} /></label>
                    <label>{t("Provenance")} <textarea maxLength={1000} value={item.provenance} onChange={event => updateConsequence(index, { provenance: event.target.value })} /></label>
                    <button type="button" onClick={() => setConsequences(old => old.filter((_, position) => position !== index))}>{t("Remove consequence")} {index + 1}</button>
                  </fieldset>
                ))}
                <button type="button" onClick={() => setConsequences(old => [...old, newConsequence(records)])}>{t("Add permanent consequence")}</button>
              </fieldset>

              <fieldset disabled={Boolean(review) || previewMutation.isPending || commitMutation.isPending}>
                <legend>{t("Audit and review")}</legend>
                <label>{t("Operator label")} <input maxLength={200} value={operator} onChange={event => setOperator(event.target.value)} /></label>
                <label>{t("Reason")} <textarea maxLength={2000} value={reason} onChange={event => setReason(event.target.value)} /></label>
                <label className="checkbox-label"><input type="checkbox" checked={reviewed} onChange={event => setReviewed(event.target.checked)} />{t("I reviewed the complete current Health profile and this correction.")}</label>
                <button type="button" disabled={Boolean(issue)} onClick={calculatePreview}>{t("Calculate Health preview")}</button>
                <button type="button" onClick={() => { setEditing(false); setReview(null) }}>{t("Cancel edit")}</button>
                {issue ? <p className="status">{healthIssue(issue,locale)}</p> : null}
              </fieldset>

              {previewMutation.isPending ? <p role="status">{t("Calculating Health preview\u2026")}</p> : null}
              {previewMutation.isError ? <p role="alert">{formatApiError(previewMutation.error)}</p> : null}
              {review ? (
                <section aria-label={t("Health edit preview")}>
                  <h3>{t("Review Health preview")}</h3>
                  <SummaryPills items={[
                    { label: t('Week'), value: weekLabel(review.preview.week,locale) },
                    { label: t('Records after'), value: review.preview.after_state.players.find(player => player.player_id === playerId)?.records.length ?? 0 },
                    { label: t('Consequences after'), value: review.preview.after_state.players.find(player => player.player_id === playerId)?.permanent_consequences.length ?? 0 },
                    { label: t('Before'), value: review.preview.before_state_fingerprint.slice(0, 12) },
                    { label: t('After component'), value: review.preview.after_component_fingerprint.slice(0, 12) }
                  ]} />
                  <h4>{t('Complete change for this player')}</h4>
                  <p>{t('Before')}</p><HealthProfileReview profile={current.player} locale={locale}/>
                  <p>{t('After')}</p><HealthProfileReview profile={review.preview.after_state.players.find(p=>p.player_id===playerId)!} locale={locale}/>
                  <label className="checkbox-label"><input type="checkbox" aria-label={t('Confirm Health changes')} disabled={branchReadOnly || healthQuery.isFetching || savePreviewQuery.isFetching || commitMutation.isPending || review.epoch!==guard.current.epoch} checked={confirmApproved} onChange={e=>setConfirmApproved(e.target.checked)}/>{t('I approve these reviewed Health changes.')}</label>
                  <p>{t("Preview fingerprint:")} {review.preview.preview_fingerprint.slice(0, 16)}…</p>
                  <button type="button" disabled={!confirmApproved || branchReadOnly || healthQuery.isError || savePreviewQuery.isError || healthQuery.isFetching || savePreviewQuery.isFetching || commitMutation.isPending || review.epoch!==guard.current.epoch} onClick={() => commitMutation.mutate(review)}>{commitMutation.isError ? t('Retry exact Health commit') : t('Confirm reviewed Health edit')}</button>
                  <button type="button" disabled={commitMutation.isPending} onClick={() => { setReview(null); previewMutation.reset(); commitMutation.reset(); setReviewed(false);setConfirmApproved(false) }}>{t("Edit inputs and recalculate")}</button>
                  {commitMutation.isPending ? <p role="status">{t("Committing Health edit\u2026")}</p> : null}
                  {commitMutation.isError ? <p role="alert">{formatApiError(commitMutation.error)} {t('No automatic write retry. Reload and inspect, or explicitly approve the exact retry.')}</p> : null}
                </section>
              ) : null}
            </section>
          )}

          <section aria-label={t("Save Player Health revision")}>
            <h3>{t("Save Health Revision")}</h3>
            {savePreviewQuery.isPending ? <p role="status">{t("Checking Health Save state\u2026")}</p> : null}
            {savePreviewQuery.isError ? <p role="alert">{t("Health Save state unavailable:")} {formatApiError(savePreviewQuery.error)}</p> : null}
            {savePreviewQuery.data ? (
              <>
                <p>{savePreviewQuery.data.changed_since_saved_head ? t('Health differs from the current Saved Revision.') : t('Current Health is already captured by the Saved Revision.')}</p>
                <label className="checkbox-label"><input type="checkbox" aria-label={t('Confirm Health Save')} disabled={!saveReady || saveMutation.isPending} checked={saveApproved} onChange={e=>setSaveApproved(e.target.checked)}/>{t('Save this Health draft in a new revision.')}</label>
                <button type="button" disabled={!saveApproved || !saveReady || saveMutation.isPending} onClick={() => saveMutation.mutate(guard.current.epoch)}>{t("Save Health Revision")}</button>
              </>
            ) : null}
            {saveMutation.isPending ? <p role="status">{t("Saving Health Revision\u2026")}</p> : null}
            {saveMutation.isError ? <p role="alert">{formatApiError(saveMutation.error)}</p> : null}
          </section>
          {status ? <p role="status">{status}</p> : null}
        </>
      ) : null}
    </SectionCard>
  )
}
