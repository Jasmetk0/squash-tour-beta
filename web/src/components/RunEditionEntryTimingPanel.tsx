import { useQuery, useQueryClient } from '@tanstack/react-query'
import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'

import {
  confirmRunEditionEntryTiming, getRunEditionEntryTiming, previewRunEditionEntryTiming,
  getRunContainer, listRunBranches, getBranchWorkingDraft, getRunPackageState,
  saveRunPackageWorkingDraft, listTournamentRankingPublicationOptions
} from '../api/client'
import type { RunCalendarMetadata } from '../api/runCalendarCreation'
import {
  entryTimingScope, isHash, weekInClock, sameTiming, sameWeek, sameClock, verifiedRunCalendar,
  type EditionEntryTiming, type EntryTimingConfirmPayload,
  type EntryTimingInspection, type EntryTimingPreview, type EntryTimingReceipt, type EntryWeek
} from '../api/runEditionEntryTiming'
import { useLanguage } from '../i18n/LanguageContext'
import { editionEntryTimingText } from '../i18n/editionEntryTimingText'
import { formatApiError } from '../utils/apiErrors'
import { SectionCard } from './RunScopedUi'

type WeekFields = { season: string; week: string }
type Inputs = {
  main: WeekFields
  mainDuration: string
  qualificationDuration: string
  commitmentEnabled: boolean
  commitment: WeekFields
  overrideEnabled: boolean
  override: WeekFields
  operator: string
  reason: string
}
const emptyWeek = (): WeekFields => ({ season: '', week: '' })
const emptyInputs = (): Inputs => ({
  main: emptyWeek(), mainDuration: '2', qualificationDuration: '1',
  commitmentEnabled: false, commitment: emptyWeek(),
  overrideEnabled: false, override: emptyWeek(), operator: '', reason: ''
})


const blockerText: Record<string, {cs: string; en: string}> = {
  entry_timing_missing: {cs: 'Chybí explicitní otevření Main; ze začátku turnaje nelze čas odvodit.', en: 'An explicit Main opening is missing; play week cannot supply a default.'},
  scope_not_writable: {cs: 'Run/Branch nebo uložená autorita nejsou zapisovatelné. Potvrzení je blokováno.', en: 'Run/Branch or saved authority is not writable; confirmation blocked.'},
  unsupported_execution: {cs: 'Kalendář lze plánovat, ale tento Run nemá povolené legacy ranking/sportovní provedení.', en: 'Planning is possible, but legacy ranking/sporting execution is unsupported for this Run.'},
  entry_timing_locked: {cs: 'Entry už bylo otevřeno; časování nelze změnit tímto příkazem.', en: 'Entry has opened; retiming is prohibited by this command.'},
  pre_start_ranking_required: {cs: 'Před Main Closing neexistuje předchozí Run týden. Vyber existující publikaci explicitně.', en: 'No prior Run week exists before Main Closing; choose an existing publication explicitly.'},
  ranking_publication_missing: {cs: 'Přesná povinná publikace neexistuje. Server nepoužije poslední dostupnou.', en: 'The exact required publication is missing; no latest-ranking fallback.'},
  ranking_binding_conflict: {cs: 'Edition už má jiný neměnný ranking. Konfiguraci nelze potvrdit.', en: 'A different immutable ranking is already bound. Configuration blocked.'},
  ranking_not_yet_current: {cs: 'Publikace je až za aktuálním týdnem Runu; ranking zatím nelze navázat.', en: 'Publication is after the current Run week, so ranking cannot yet be bound.'}
}

function fieldsFromWeek(value: EntryWeek | null): WeekFields {
  return value ? { season: String(value.season_index), week: String(value.week) } : emptyWeek()
}
function inputsFromTiming(value: EditionEntryTiming): Inputs {
  return {
    ...emptyInputs(), main: fieldsFromWeek(value.main_open),
    mainDuration: String(value.main_duration_weeks),
    qualificationDuration: String(value.qualification_duration_weeks),
    commitmentEnabled: value.final_commitment !== null,
    commitment: fieldsFromWeek(value.final_commitment),
    overrideEnabled: value.ranking_publication_override !== null,
    override: fieldsFromWeek(value.ranking_publication_override)
  }
}
function makeTiming(form: Inputs, calendar: RunCalendarMetadata): EditionEntryTiming | null {
  const week = (value: WeekFields): EntryWeek | null => {
    if (!/^\d+$/.test(value.season) || !/^\d+$/.test(value.week)) return null
    const candidate: EntryWeek = { calendar, season_index: Number(value.season), week: Number(value.week) }
    return weekInClock(candidate, calendar) ? candidate : null
  }
  const main = week(form.main)
  const commitment = form.commitmentEnabled ? week(form.commitment) : null
  const publication = form.overrideEnabled ? week(form.override) : null
  const mainDuration = Number(form.mainDuration)
  const qualificationDuration = Number(form.qualificationDuration)
  if (!main || (form.commitmentEnabled && !commitment) || (form.overrideEnabled && !publication) ||
    !/^[1-9]\d*$/.test(form.mainDuration) || !/^[1-9]\d*$/.test(form.qualificationDuration) ||
    !Number.isSafeInteger(mainDuration) || !Number.isSafeInteger(qualificationDuration)) return null
  return {
    schema_version: 'edition_entry_timing.v1',
    main_open: main, main_duration_weeks: mainDuration,
    qualification_duration_weeks: qualificationDuration,
    final_commitment: commitment, ranking_publication_override: publication
  }
}

// A confirmation command ID must never fall back to predictable pseudo-randomness.
const nonce = () => 'admin-entry-timing-' + crypto.randomUUID()

export function RunEditionEntryTimingPanel({ runId, branchId, packageId, eventId, calendar, enabled }: {
  runId: string; branchId: string; packageId: string; eventId: string
  calendar: RunCalendarMetadata; enabled: boolean
}): JSX.Element {
  const { language } = useLanguage()
  const t = editionEntryTimingText(language)
  const queryClient = useQueryClient()
  const scope = JSON.stringify([runId, branchId, packageId, eventId, calendar])
  const currentScope = useRef(scope)
  currentScope.current = scope
  const busy = useRef(false)
  const initialised = useRef('')
  const [form, setForm] = useState<Inputs>(emptyInputs)
  const [preview, setPreview] = useState<EntryTimingPreview | null>(null)
  const [retryPayload, setRetryPayload] = useState<EntryTimingConfirmPayload | null>(null)
  const [receipt, setReceipt] = useState<EntryTimingReceipt | null>(null)
  const [saveApproved, setSaveApproved] = useState(false)
  const [saving, setSaving] = useState(false)
  const [saveError, setSaveError] = useState('')
  const [savedRevision, setSavedRevision] = useState('')
  const [error, setError] = useState('')
  const [loadingPreview, setLoadingPreview] = useState(false)
  const [loadingConfirm, setLoadingConfirm] = useState(false)
  const [refreshed, setRefreshed] = useState<EntryTimingInspection | null>(null)
  const readable = Boolean(runId && branchId && packageId && eventId && calendar)
  const query = useQuery({
    queryKey: ['edition-entry-timing', runId, branchId, packageId, eventId, calendar],
    queryFn: () => getRunEditionEntryTiming(runId, branchId, packageId, eventId),
    enabled: readable, retry: false
  })
  const inspection = refreshed && entryTimingScope(refreshed, runId, branchId, packageId, eventId)
    ? refreshed : query.data && entryTimingScope(query.data, runId, branchId, packageId, eventId)
      ? query.data : null
  // Only request authentic Run/Branch-specific publications while the operator
  // explicitly edits the override; the list never binds a ranking by itself.
  const rankingOptionsQuery = useQuery({
    queryKey: ['tournament-ranking-publications', runId, branchId, eventId],
    queryFn: () => listTournamentRankingPublicationOptions(runId, branchId, eventId),
    enabled: Boolean(readable && enabled && inspection && form.overrideEnabled && !receipt && !retryPayload),
    retry: false
  })
  const validPublications = rankingOptionsQuery.data?.publications.filter(item =>
    item && isHash(item.snapshot_fingerprint) &&
    weekInClock({calendar, season_index: item.ranking_week?.season_index, week: item.ranking_week?.week}, calendar)
  ) ?? []

  useEffect(() => {
    initialised.current = ''
    setForm(emptyInputs())
    setPreview(null)
    setRetryPayload(null)
    setReceipt(null)
    setRefreshed(null)
    setSaveApproved(false)
    setSaving(false)
    setSaveError('')
    setSavedRevision('')
    setError('')
    busy.current = false
    setLoadingPreview(false)
    setLoadingConfirm(false)
  }, [scope])
  useEffect(() => {
    if (inspection && initialised.current !== scope) {
      initialised.current = scope
      if (inspection.timing) setForm(old => ({ ...inputsFromTiming(inspection.timing!), operator: old.operator, reason: old.reason }))
    }
  }, [inspection, scope])

  const update = (patch: Partial<Inputs>, changesTiming = true) => {
    // An uncertain confirm must preserve both its original ID and immutable payload.
    if (busy.current || loadingPreview || loadingConfirm || receipt || retryPayload || saving) return
    setForm(old => ({ ...old, ...patch }))
    if (changesTiming) setPreview(null)
    setError('')
  }
  const baseline = inspection?.timing ? inputsFromTiming(inspection.timing) : emptyInputs()
  const localChanged = Boolean(inspection && (
    form.main.season !== baseline.main.season || form.main.week !== baseline.main.week ||
    form.mainDuration !== baseline.mainDuration ||
    form.qualificationDuration !== baseline.qualificationDuration ||
    form.commitmentEnabled !== baseline.commitmentEnabled ||
    (form.commitmentEnabled && (form.commitment.season !== baseline.commitment.season ||
      form.commitment.week !== baseline.commitment.week)) ||
    form.overrideEnabled !== baseline.overrideEnabled ||
    (form.overrideEnabled && (form.override.season !== baseline.override.season ||
      form.override.week !== baseline.override.week))
  ))
  const timing = makeTiming(form, calendar)
  // An unsuccessful refetch is not proof that an older cached inspection is current.
  const previewCurrent = Boolean(preview && timing && enabled && !query.isError && !query.isFetching &&
    entryTimingScope(preview, runId, branchId, packageId, eventId) &&
    sameTiming(preview.timing, timing) && isHash(preview.preview_fingerprint))
  const canConfirm = previewCurrent && preview?.can_confirm_configuration === true &&
    form.operator.trim().length > 0 && form.operator.length <= 160 &&
    form.reason.trim().length > 0 && form.reason.length <= 1000 &&
    !loadingConfirm && !loadingPreview && !busy.current
  const editingBlocked = !enabled || Boolean(receipt) || Boolean(retryPayload) ||
    saving || loadingConfirm || loadingPreview || busy.current
  const durationValid = (raw: string) => /^[1-9]\d*$/.test(raw) && Number.isSafeInteger(Number(raw))
  // Matches the established Run calendar projection, not a universal YYYY/YY label.
  const seasonLabelFor = (index: number) => {
    const year = calendar.start_year + index
    return calendar.season_start_year_week === 1 ? String(year) : year + '/' + (year + 1)
  }

  async function calculatePreview(): Promise<void> {
    if (!enabled || !timing || receipt || saving || busy.current || query.isError || query.isFetching) return
    busy.current = true
    setLoadingPreview(true)
    setError('')
    setPreview(null)
    setRetryPayload(null)
    const origin = scope
    try {
      const result = await previewRunEditionEntryTiming(runId, branchId, packageId, eventId, timing)
      if (currentScope.current !== origin) return
      if (!weekInClock(result.timing.main_open, calendar) || !sameTiming(result.timing, timing))
        throw new Error('Preview calendar or exact configuration did not match.')
      setPreview(result)
    } catch (cause) {
      if (currentScope.current === origin) setError(t.previewError + ': ' + formatApiError(cause))
    } finally {
      if (currentScope.current === origin) { busy.current = false; setLoadingPreview(false) }
    }
  }

  async function submitConfirm(): Promise<void> {
    if (!canConfirm && !retryPayload) return
    if (busy.current || !previewCurrent || !timing || !enabled) return
    const payload: EntryTimingConfirmPayload = retryPayload ?? {
      timing, command_id: nonce(),
      expected_preview_fingerprint: preview!.preview_fingerprint,
      operator_label: form.operator.trim(), audit_reason: form.reason.trim()
    }
    if (!sameTiming(payload.timing, timing) || payload.expected_preview_fingerprint !== preview!.preview_fingerprint ||
      payload.operator_label !== form.operator.trim() || payload.audit_reason !== form.reason.trim()) return
    setRetryPayload(payload) // Hold the EXACT request even if the response is lost.
    busy.current = true
    setLoadingConfirm(true)
    setError('')
    const origin = scope
    try {
      const result = await confirmRunEditionEntryTiming(runId, branchId, packageId, eventId, payload)
      if (currentScope.current !== origin) return
      setReceipt(result)
      setSaveApproved(false)
      setSaveError('')
      setRetryPayload(null)
      setPreview(null)
      setRefreshed(null)
      // A successful confirm receipt is definitive: later read failures must
      // never be mislabelled as an uncertain write or solicit a second command.
      try {
        await Promise.all([
          queryClient.invalidateQueries({ queryKey: ['edition-entry-timing', runId, branchId, packageId, eventId] }),
          queryClient.invalidateQueries({ queryKey: ['run-package-state', runId, branchId] }),
          queryClient.invalidateQueries({ queryKey: ['package-working-draft', runId, branchId] }),
          queryClient.invalidateQueries({ queryKey: ['run-calendar', runId, branchId, packageId] })
        ])
        if (currentScope.current !== origin) return
        const latest = await getRunEditionEntryTiming(runId, branchId, packageId, eventId)
        if (currentScope.current === origin) setRefreshed(latest)
      } catch (refreshCause) {
        if (currentScope.current === origin) setError(t.refreshError + ': ' + formatApiError(refreshCause))
      }
    } catch (cause) {
      if (currentScope.current === origin) setError(t.confirmError + ' ' + formatApiError(cause))
    } finally {
      if (currentScope.current === origin) { busy.current = false; setLoadingConfirm(false) }
    }
  }

  async function saveReviewedDraft(): Promise<void> {
    const staged = receipt
    if (!staged || !saveApproved || busy.current || saving ||
      !entryTimingScope(staged.preview, runId, branchId, packageId, eventId)) return
    busy.current = true
    setSaving(true)
    setSaveError('')
    const origin = scope
    try {
      // Fresh authoritative reads: the Manage page's source-copy Save button only
      // handles its own source-copy receipt, so this is a separate reviewed Save.
      const [run, branches, draft, state] = await Promise.all([
        getRunContainer(runId), listRunBranches(runId),
        getBranchWorkingDraft(runId, branchId), getRunPackageState(runId, branchId)
      ])
      if (currentScope.current !== origin) return
      const branch = branches.run_branches.find(row =>
        row.run_id === runId && row.branch_id === branchId)
      const checkedClock = verifiedRunCalendar(run)
      if (!checkedClock || !sameClock(checkedClock, calendar) ||
        run.run_id !== runId || run.storage_kind !== 'custom_local' || run.read_only ||
        !branch || branch.status !== 'active' || branch.read_only ||
        branch.saved_head_revision_id !== staged.preview.saved_head_revision_id ||
        draft.run_id !== runId || draft.branch_id !== branchId ||
        draft.status !== 'dirty' ||
        draft.base_saved_revision_id !== branch.saved_head_revision_id ||
        draft.draft_version !== staged.draft_version ||
        state.state?.run_id !== runId || state.state.branch_id !== branchId ||
        state.fingerprint !== staged.state_fingerprint) {
        throw new Error('Saved head, Working Draft or Package changed since Entry confirmation.')
      }
      const result = await saveRunPackageWorkingDraft(runId, branchId, staged.draft_version)
      if (currentScope.current !== origin) return
      if (result.run_id !== runId || result.branch_id !== branchId ||
        result.working_draft.run_id !== runId || result.working_draft.branch_id !== branchId ||
        result.working_draft.status !== 'clean' ||
        result.working_draft.base_saved_revision_id !== result.saved_revision.revision_id ||
        !result.saved_revision.revision_id) {
        throw new Error('Saved Revision receipt identity or Draft state is invalid.')
      }
      setSavedRevision(result.saved_revision.revision_id)
      setReceipt(null)
      setSaveApproved(false)
      setRefreshed(null)
      // Save's authoritative receipt is final. A failed cache refresh cannot turn
      // a persisted Saved Revision into an apparent failed Save.
      try {
        await Promise.all([
          queryClient.invalidateQueries({ queryKey: ['admin-run-branches', runId] }),
        queryClient.invalidateQueries({ queryKey: ['run-branches', runId] }),
        queryClient.invalidateQueries({ queryKey: ['package-working-draft', runId, branchId] }),
        queryClient.invalidateQueries({ queryKey: ['run-package-state', runId, branchId] }),
        queryClient.invalidateQueries({ queryKey: ['run-calendar', runId, branchId, packageId] }),
          queryClient.invalidateQueries({ queryKey: ['edition-entry-timing', runId, branchId, packageId, eventId] })
        ])
      } catch (refreshCause) {
        if (currentScope.current === origin) setSaveError(t.saveRefreshError + ': ' + formatApiError(refreshCause))
      }
    } catch (cause) {
      if (currentScope.current === origin) setSaveError(t.saveError + ': ' + formatApiError(cause))
    } finally {
      if (currentScope.current === origin) { busy.current = false; setSaving(false) }
    }
  }

  const position = (p: EntryWeek | null) =>
    p ? (String(p.calendar.start_year + p.season_index) + ' / S' + p.season_index +
      ' W' + p.week) : '—'
  const formatTiming = (value: EditionEntryTiming | null) =>
    value ? position(value.main_open) + ' · Main ' + value.main_duration_weeks +
      'w · Q ' + value.qualification_duration_weeks + 'w · Final ' +
      position(value.final_commitment) + ' · Ranking override ' +
      position(value.ranking_publication_override) : t.absent
  const previewStatus = previewCurrent ? preview : null
  const effectiveStatus = previewStatus ?? (inspection?.timing ? inspection : null)
  const blockers = previewStatus?.blockers ?? inspection?.blockers ?? []
  // Compare frozen server fields only, never invent Main/Q windows in the client.
  const fieldChanges = previewStatus?.before ? [
    { label: t.diffMain, changed: !sameWeek(previewStatus.before.main_open, previewStatus.timing.main_open),
      before: position(previewStatus.before.main_open), after: position(previewStatus.timing.main_open) },
    { label: t.diffMainLength, changed: previewStatus.before.main_duration_weeks !== previewStatus.timing.main_duration_weeks,
      before: String(previewStatus.before.main_duration_weeks), after: String(previewStatus.timing.main_duration_weeks) },
    { label: t.diffQLength, changed: previewStatus.before.qualification_duration_weeks !== previewStatus.timing.qualification_duration_weeks,
      before: String(previewStatus.before.qualification_duration_weeks), after: String(previewStatus.timing.qualification_duration_weeks) },
    { label: t.diffCommitment, changed: !sameWeek(previewStatus.before.final_commitment, previewStatus.timing.final_commitment),
      before: position(previewStatus.before.final_commitment), after: position(previewStatus.timing.final_commitment) },
    { label: t.diffRanking, changed: !sameWeek(previewStatus.before.ranking_publication_override, previewStatus.timing.ranking_publication_override),
      before: position(previewStatus.before.ranking_publication_override), after: position(previewStatus.timing.ranking_publication_override) }
  ] : []
  const inputId = (field: string) => 'entry-timing-' + field
  const weekFields = (value: WeekFields, name: 'main' | 'commitment' | 'override', seasonLabel: string, weekLabel: string) => {
    const seasonInvalid = !/^\d+$/.test(value.season) ||
      Number(value.season) >= calendar.season_count
    const weekInvalid = !/^\d+$/.test(value.week) || Number(value.week) < 1 ||
      Number(value.week) > calendar.weeks_per_year
    return <div className="grid" key={name}>
      <label htmlFor={inputId(name + '-season')}>{seasonLabel}
        <select id={inputId(name + '-season')} value={value.season} disabled={editingBlocked}
          aria-invalid={seasonInvalid} aria-describedby={seasonInvalid ? inputId(name + '-season-error') : undefined}
          onChange={event => update({ [name]: { ...value, season: event.target.value } })}>
          <option value="">—</option>
          {Array.from({ length: calendar.season_count }, (_, index) => (
            <option key={index} value={index}>{seasonLabelFor(index)} (S{index})</option>
          ))}
        </select>
      </label>
      {seasonInvalid && <span id={inputId(name + '-season-error')} className="error">{t.seasonRange} 0–{calendar.season_count - 1}.</span>}
      <label htmlFor={inputId(name + '-week')}>{weekLabel}
        <input id={inputId(name + '-week')} type="number" min={1} max={calendar.weeks_per_year}
          step={1} value={value.week} disabled={editingBlocked} aria-invalid={weekInvalid}
          aria-describedby={weekInvalid ? inputId(name + '-week-error') : undefined}
          onChange={event => update({ [name]: { ...value, week: event.target.value } })} />
      </label>
      {weekInvalid && <span id={inputId(name + '-week-error')} className="error">{t.weekRange} 1–{calendar.weeks_per_year}.</span>}
    </div>
  }

  return <SectionCard title={t.heading}>
    <div id="run-edition-entry-timing" className="grid" aria-label={t.heading}>
      <p className="status">{t.intro}</p>
      <p role="status">{t.progress}: {savedRevision ? t.progressSaved :
        receipt ? t.progressDraft : previewStatus ? t.progressPreview :
        localChanged ? t.progressEdited : t.progressLocal}</p>
      <details>
        <summary>{t.contextDetails}</summary>
        <dl className="kv-grid">
          <dt>Run</dt><dd style={{overflowWrap: 'anywhere'}}>{runId}</dd>
          <dt>Branch</dt><dd style={{overflowWrap: 'anywhere'}}>{branchId}</dd>
          <dt>Edition</dt><dd style={{overflowWrap: 'anywhere'}}>{eventId}</dd>
          <dt>Calendar Package</dt><dd style={{overflowWrap: 'anywhere'}}>{packageId}</dd>
        </dl>
      </details>
      <p>{t.clock}: {calendar.weeks_per_year} W · {calendar.start_year} · {calendar.season_count} seasons · offset {calendar.season_start_year_week}</p>
      <p className="status">{t.indexNote}</p>
      {query.isLoading && !inspection && <p role="status">{t.loading}</p>}
      {query.error && <p role="alert" className="error">{t.failed}: {formatApiError(query.error)}</p>}
      <button type="button" disabled={query.isFetching || busy.current}
        onClick={() => {
          setRefreshed(null)
          // A fresh inspection invalidates an ordinary review. Retain only an
          // uncertain exact-command retry so the operator cannot lose its ID.
          if (!retryPayload) setPreview(null)
          setError('')
          void query.refetch()
        }}>{t.retryRead}</button>
      {!inspection && !query.isLoading && !query.error && <p role="status">{t.loading}</p>}
      {inspection && <p role="status">{inspection.timing ? t.existing : t.noPlan}</p>}
      {!enabled && !receipt && <p role="alert" className="error">{t.nonWritable}</p>}
      {!enabled && receipt && <p role="status">{t.awaitingSave}</p>}

      <fieldset disabled={editingBlocked || !inspection}>
        <legend>{inspection?.timing ? t.existing : t.newPlan}</legend>
        <p className="status">{t.mainHint}</p>
        {weekFields(form.main, 'main', t.mainSeason, t.mainWeek)}
        <div className="grid">
          <label htmlFor={inputId('main-duration')}>{t.mainDuration}
            <input id={inputId('main-duration')} type="number" min={1} step={1} value={form.mainDuration}
              aria-invalid={!durationValid(form.mainDuration)}
              aria-describedby={!durationValid(form.mainDuration) ? inputId('main-duration-error') : undefined}
              onChange={event => update({ mainDuration: event.target.value })} />
          </label>
          {!durationValid(form.mainDuration) && <span id={inputId('main-duration-error')} className="error">{t.durationError}</span>}
          <label htmlFor={inputId('q-duration')}>{t.qualificationDuration}
            <input id={inputId('q-duration')} type="number" min={1} step={1} value={form.qualificationDuration}
              aria-invalid={!durationValid(form.qualificationDuration)}
              aria-describedby={!durationValid(form.qualificationDuration) ? inputId('q-duration-error') : undefined}
              onChange={event => update({ qualificationDuration: event.target.value })} />
          </label>
          {!durationValid(form.qualificationDuration) && <span id={inputId('q-duration-error')} className="error">{t.durationError}</span>}
        </div>
        <p className="status">{t.durationHint}</p>
        <button type="button" disabled={form.mainDuration === '2' && form.qualificationDuration === '1'}
          onClick={() => update({ mainDuration: '2', qualificationDuration: '1' })}>{t.restoreDurations}</button>
        <details open>
          <summary>{t.advancedSettings}</summary>
          <p className="status">{t.advancedHint}</p>
        <label><input type="checkbox" checked={form.commitmentEnabled}
          onChange={event => update({ commitmentEnabled: event.target.checked })} /> {t.commitmentSwitch}</label>
        {form.commitmentEnabled && weekFields(form.commitment, 'commitment', t.commitmentSeason, t.commitmentWeek)}
        <label><input type="checkbox" checked={form.overrideEnabled}
          onChange={event => update({ overrideEnabled: event.target.checked })} /> {t.overrideSwitch}</label>
        {form.overrideEnabled && <div className="grid">
          <label htmlFor={inputId('publication-picker')}>{t.publicationsPicker}
            <select id={inputId('publication-picker')} disabled={editingBlocked || rankingOptionsQuery.isFetching}
              value={validPublications.some(row =>
                String(row.ranking_week.season_index) === form.override.season &&
                String(row.ranking_week.week) === form.override.week)
                ? form.override.season + ':' + form.override.week : ''}
              onChange={event => {
                const selected = validPublications.find(row =>
                  row.ranking_week.season_index + ':' + row.ranking_week.week === event.target.value)
                if (selected) update({override: {
                  season: String(selected.ranking_week.season_index),
                  week: String(selected.ranking_week.week)
                }})
              }}>
              <option value="">{t.publicationsPlaceholder}</option>
              {validPublications.map(row => <option
                key={row.ranking_week.season_index + ':' + row.ranking_week.week}
                value={row.ranking_week.season_index + ':' + row.ranking_week.week}>
                {seasonLabelFor(row.ranking_week.season_index)} · W{row.ranking_week.week}
                {' · '}{row.ranked_row_count} {t.rankingRows}
              </option>)}
            </select>
          </label>
          {rankingOptionsQuery.isPending && <p role="status">{t.publicationsLoading}</p>}
          {rankingOptionsQuery.isError && <p role="alert" className="error">
            {t.publicationsError}: {formatApiError(rankingOptionsQuery.error)}
          </p>}
          {rankingOptionsQuery.isSuccess && validPublications.length === 0 &&
            <p role="status">{t.publicationsEmpty}</p>}
          <p className="status">{t.publicationsHint}</p>
          {weekFields(form.override, 'override', t.overrideSeason, t.overrideWeek)}
        </div>}
        {!form.overrideEnabled && <p className="status">{t.defaultRanking}</p>}
        </details>
        <label htmlFor={inputId('operator')}>{t.operator}
          <input id={inputId('operator')} maxLength={160} value={form.operator} autoComplete="off"
            onChange={event => update({ operator: event.target.value }, false)} />
        </label>
        <label htmlFor={inputId('reason')}>{t.reason}
          <textarea id={inputId('reason')} maxLength={1000} value={form.reason}
            onChange={event => update({ reason: event.target.value }, false)} />
        </label>
      </fieldset>
      {inspection && !timing && <p role="status" className="error">{t.required}</p>}
      <button type="button" disabled={!enabled || !inspection || !localChanged || editingBlocked ||
        query.isError || query.isFetching}
        onClick={() => {
          setForm(old => ({ ...baseline, operator: old.operator, reason: old.reason }))
          setPreview(null)
          setError('')
        }}>{t.restoreLocal}</button>
      {form.operator.length > 160 && <p role="alert" className="error">{t.operatorError}</p>}
      {form.reason.length > 1000 && <p role="alert" className="error">{t.reasonError}</p>}
      <button type="button" disabled={!enabled || !inspection || !timing || receipt !== null || saving ||
        query.isError || query.isFetching || loadingPreview || loadingConfirm || busy.current}
        onClick={() => void calculatePreview()}>{loadingPreview ? t.previewing : t.previewButton}</button>
      {error && <p role="alert" className="error">{error}</p>}

      {effectiveStatus && <div className="grid" aria-live="polite">
        <h4>{previewStatus ? t.review : t.existing}</h4>
        {previewStatus && <div>
          <h5>{t.diffHeading}</h5>
          {previewStatus.before === null ? <p>{t.diffNewPlan}</p> :
            fieldChanges.some(item => item.changed)
              ? <ul>{fieldChanges.filter(item => item.changed).map(item =>
                <li key={item.label}><strong>{item.label}</strong>: {item.before} → {item.after}</li>
              )}</ul> : <p>{t.diffNoChanges}</p>}
          {previewStatus.before && fieldChanges.some(item => !item.changed) && <details>
            <summary>{t.diffUnchanged}</summary>
            <ul>{fieldChanges.filter(item => !item.changed).map(item =>
              <li key={item.label}>{item.label}: {item.after}</li>
            )}</ul>
          </details>}
        </div>}
        <dl className="kv-grid">
          <dt>{t.before}</dt><dd>{formatTiming(effectiveStatus.before)}</dd>
          <dt>{t.after}</dt><dd>{formatTiming(effectiveStatus.timing)}</dd>
          <dt>{t.mainWindow}</dt><dd>{position(effectiveStatus.resolved.main_open)} – {position(effectiveStatus.resolved.main_close)}</dd>
          <dt>{t.qualificationWindow}</dt><dd>{position(effectiveStatus.resolved.qualification_open)} – {position(effectiveStatus.resolved.qualification_close)}</dd>
          <dt>{t.commitment}</dt><dd>{position(effectiveStatus.resolved.final_commitment)}</dd>
          <dt>{t.dataWeek}</dt><dd>{position(effectiveStatus.resolved.default_ranking_completed_week)}</dd>
          <dt>{t.publishedWeek}</dt><dd>{position(effectiveStatus.resolved.ranking_publication_week)}</dd>
          <dt>{t.rankingSource}</dt><dd>{effectiveStatus.resolved.ranking_source === 'explicit_publication_override' ? t.sourceOverride : t.sourceDefault}</dd>
          <dt>{t.rankingFingerprint}</dt><dd>{effectiveStatus.ranking_snapshot_fingerprint ?? t.absent}</dd>
          <dt>{t.rankingBinding}</dt><dd>{t[effectiveStatus.ranking_binding_status]}</dd>
          <dt>{t.status}</dt><dd>{t[effectiveStatus.preflight_status]}</dd>
          <dt>{t.configState}</dt><dd>{t.working_draft}</dd>
          <dt>{t.currentWeek}</dt><dd>{position(effectiveStatus.current_week)}</dd>
        </dl>
        {effectiveStatus.ranking_will_be_bound && <p role="status">{t.rankingWillBind}</p>}
        {effectiveStatus.ranking_snapshot_fingerprint === null && <p role="status">{t.noRanking}</p>}
        {effectiveStatus.timing_and_ranking_ready && <p role="status">{t.timingReady}</p>}
        {effectiveStatus.preflight_status === 'unsupported_execution' &&
          <p role="status">{t.executionDenied}</p>}
      </div>}
      <p role="status" className="status">{t.eligibility}</p>
      {inspection && <div aria-live="polite">
        <h4>{t.blockers}</h4>
        {effectiveStatus && <p role="status">{
          effectiveStatus.can_confirm_configuration ? t.preparationPermitted : t.preparationBlocked
        }</p>}
        {blockers.length ? <ul>{blockers.map((blocker, index) =>
          <li key={blocker.code + '-' + index}><strong>{blocker.code}</strong>: {
            blockerText[blocker.code]?.[language] ?? blocker.detail
          }</li>)}</ul> : <p>{t.noBlockers}</p>}
      </div>}

      {previewStatus && <div className="grid">
        {!previewStatus.can_confirm_configuration && <p role="alert">{t.blockedConfirm}</p>}
        {retryPayload && <p role="alert">{t.retryHint} {t.retryCommandId}: {retryPayload.command_id}</p>}
        {!form.operator.trim() && <p role="status">{t.operatorError}</p>}
        {!form.reason.trim() && <p role="status">{t.reasonError}</p>}
        <button type="button" disabled={!canConfirm}
          onClick={() => void submitConfirm()}>
          {loadingConfirm ? t.confirming : retryPayload ? t.retryConfirm : t.confirmButton}
        </button>
      </div>}
      {receipt && <div className="grid" aria-live="polite">
        <p role="status">{t.confirmed}</p>
        <details><summary>{t.technicalDetails}</summary>
          <p style={{overflowWrap: 'anywhere'}}>{t.retryCommandId}: {receipt.command_id}</p>
          <p style={{overflowWrap: 'anywhere'}}>Preview: {receipt.preview.preview_fingerprint}</p>
        </details>
        <p>{t.working_draft} (v{receipt.draft_version})</p>
        <p className="status">{t.saveGuard}</p>
        <label><input type="checkbox" checked={saveApproved} disabled={saving || busy.current}
          onChange={event => setSaveApproved(event.target.checked)} /> {t.saveConsent}</label>
        <button type="button" disabled={!saveApproved || saving || busy.current}
          onClick={() => void saveReviewedDraft()}>{saving ? t.saving : t.saveButton}</button>
        <Link to={'/admin/runs/' + encodeURIComponent(runId) + '/manage?branch=' + encodeURIComponent(branchId)}>
          {t.savedLink}
        </Link>
      </div>}
      {saveError && <p role="alert" className="error">{saveError}</p>}
      {savedRevision && <div role="status">
        <p>{t.saved}</p>
        <p style={{overflowWrap: 'anywhere'}}>{t.savedRevisionId}: {savedRevision}</p>
        <Link to={'/admin/runs/' + encodeURIComponent(runId) + '/manage?branch=' + encodeURIComponent(branchId)}>
          {t.savedLink}
        </Link>
      </div>
    </div>
  </SectionCard>
}
