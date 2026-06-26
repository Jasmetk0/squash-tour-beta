import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { type FormEvent, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'

import { applyCalendarTemplateToPlanningCalendar, compareCalendarTemplateDryRun, getSeasonRegistry, getSeasonTemplates, listCalendarTemplates, listPlanningSeasonCalendars } from '../api/client'
import { PageIntro, SectionCard } from '../components/RunScopedUi'
import type { CalendarTemplateCompareDryRunResponse, CalendarTemplateCompareTargetSource, CalendarTemplateEventRecord, PlanningCalendarApplyTemplateCommandResponse } from '../api/types'
import { type CalendarEventDraft, describeCalendarEventTiming, formatSeasonWeeks } from '../tour/calendarEventModel'
import { formatApiError } from '../utils/apiErrors'


const TARGET_PREVIEW_EVENTS: CalendarEventDraft[] = [
  {
    id: 'target-nemarque-open-2006-07',
    name: 'Némarque Open',
    categoryCode: 'DIAMOND',
    qualificationWeeks: [5],
    weeks: [6, 7],
    locked: true,
    status: 'canonical'
  },
  {
    id: 'target-world-championship-2006-07',
    name: 'World Championship',
    categoryCode: 'WORLD_CHAMPIONSHIP',
    qualificationWeeks: [48],
    weeks: [49, 50],
    locked: true,
    status: 'canonical'
  }
]

const SOURCE_PREVIEW_EVENTS: CalendarEventDraft[] = [
  {
    id: 'source-nemarque-open-sandbox',
    name: 'Némarque Open',
    categoryCode: 'DIAMOND',
    qualificationWeeks: [5],
    weeks: [6, 7],
    locked: true,
    status: 'template'
  },
  {
    id: 'source-ameriga-open-sandbox',
    name: 'Ameriga Open',
    categoryCode: 'DIAMOND',
    qualificationWeeks: [43],
    weeks: [44, 45],
    locked: true,
    status: 'template'
  },
  {
    id: 'source-world-championship-sandbox',
    name: 'World Championship',
    categoryCode: 'WORLD_CHAMPIONSHIP',
    qualificationWeeks: [48],
    weeks: [49, 50],
    locked: true,
    status: 'template'
  },
  {
    id: 'source-world-tour-finals-sandbox',
    name: 'World Tour Finals',
    categoryCode: 'WORLD_TOUR_FINALS',
    qualificationWeeks: [],
    weeks: [55],
    locked: true,
    status: 'template'
  }
]

const PLANNING_APPLY_CONFIRMATION = 'I understand this will apply reviewed template events to the planning calendar only.'

function eventComparisonKey(event: CalendarEventDraft): string {
  return `${event.name}|${event.categoryCode}|${event.weeks.join(',')}|${event.qualificationWeeks.join(',')}`
}

function getPreviewComparisonSummary(): Array<{ status: string, events: string[] }> {
  const targetKeys = new Map(TARGET_PREVIEW_EVENTS.map((event) => [eventComparisonKey(event), event]))
  const sourceKeys = new Map(SOURCE_PREVIEW_EVENTS.map((event) => [eventComparisonKey(event), event]))

  const same = SOURCE_PREVIEW_EVENTS.filter((event) => targetKeys.has(eventComparisonKey(event))).map((event) => event.name)
  const missingFromTarget = SOURCE_PREVIEW_EVENTS.filter((event) => !targetKeys.has(eventComparisonKey(event))).map((event) => event.name)
  const onlyInTarget = TARGET_PREVIEW_EVENTS.filter((event) => !sourceKeys.has(eventComparisonKey(event))).map((event) => event.name)
  const lockedTargetPreserved = TARGET_PREVIEW_EVENTS.filter((event) => event.locked).map((event) => event.name)

  return [
    { status: 'Same', events: same },
    { status: 'Missing from target', events: missingFromTarget },
    { status: 'Only in target', events: onlyInTarget },
    { status: 'Conflict', events: [] },
    { status: 'Locked target preserved', events: lockedTargetPreserved }
  ]
}


function toCalendarTemplateEventRecord(event: CalendarEventDraft): CalendarTemplateEventRecord {
  return {
    id: event.id,
    name: event.name,
    category_code: event.categoryCode,
    qualification_weeks: event.qualificationWeeks,
    weeks: event.weeks,
    locked: event.locked,
    source_template_id: null,
    event_fingerprint: null
  }
}

function formatOptionalWeeks(weeks?: number[] | null): string {
  return formatSeasonWeeks(weeks ?? [])
}

function PreviewEventList({ events }: { events: CalendarEventDraft[] }): JSX.Element {
  return (
    <ul className="dashboard-help-list">
      {events.map((event) => (
        <li key={event.id}>
          <strong>{event.name}</strong> — {event.categoryCode} — {describeCalendarEventTiming(event)} — {event.locked ? 'Locked' : 'Unlocked'}
        </li>
      ))}
    </ul>
  )
}

export function AdminTourSeasonsComparePage(): JSX.Element {
  const queryClient = useQueryClient()
  const registryQuery = useQuery({ queryKey: ['season-registry'], queryFn: getSeasonRegistry, retry: false })
  const templatesQuery = useQuery({ queryKey: ['season-templates'], queryFn: getSeasonTemplates, retry: false })
  const calendarTemplatesQuery = useQuery({ queryKey: ['calendar-templates'], queryFn: listCalendarTemplates, retry: false })
  const planningCalendarsQuery = useQuery({ queryKey: ['planning-season-calendars'], queryFn: listPlanningSeasonCalendars, retry: false })
  const [sourceTemplateId, setSourceTemplateId] = useState('')
  const [targetSeasonLabel, setTargetSeasonLabel] = useState('2006/07')
  const [targetSource, setTargetSource] = useState<CalendarTemplateCompareTargetSource>('payload')
  const [dryRunResponse, setDryRunResponse] = useState<CalendarTemplateCompareDryRunResponse | null>(null)
  const [requestedBy, setRequestedBy] = useState('')
  const [auditReason, setAuditReason] = useState('')
  const [explicitConfirmation, setExplicitConfirmation] = useState('')
  const [applyResponse, setApplyResponse] = useState<PlanningCalendarApplyTemplateCommandResponse | null>(null)

  const registry = registryQuery.data
  const templates = templatesQuery.data?.templates ?? []
  const templateSlotCount = templates.reduce((total, template) => total + template.slot_count, 0)
  const calendarTemplates = calendarTemplatesQuery.data?.templates ?? []
  const planningCalendars = planningCalendarsQuery.data?.calendars ?? []
  const targetEvents = TARGET_PREVIEW_EVENTS.map(toCalendarTemplateEventRecord)
  const compareMutation = useMutation({
    mutationFn: compareCalendarTemplateDryRun,
    onSuccess: (response) => {
      setDryRunResponse(response)
      setApplyResponse(null)
    }
  })
  const applyMutation = useMutation({
    mutationFn: () => applyCalendarTemplateToPlanningCalendar(targetSeasonLabel, {
      source_template_id: sourceTemplateId,
      policy: 'copy_missing_only',
      selected_source_event_ids: null,
      expected_planning_calendar_fingerprint: dryRunResponse?.target_calendar_fingerprint ?? '',
      source_template_fingerprint: dryRunResponse?.source_template_fingerprint ?? '',
      reviewed_diff_fingerprint: dryRunResponse?.diff_fingerprint ?? '',
      requested_by: requestedBy,
      audit_reason: auditReason,
      explicit_confirmation: explicitConfirmation
    }),
    onSuccess: (response) => {
      setApplyResponse(response)
      void queryClient.invalidateQueries({ queryKey: ['planning-season-calendars'] })
    }
  })

  useEffect(() => {
    if (!sourceTemplateId && calendarTemplates.length) {
      setSourceTemplateId(calendarTemplates[0].id)
    }
  }, [calendarTemplates, sourceTemplateId])

  useEffect(() => {
    if (targetSource === 'planning_calendar' && planningCalendars.length && !planningCalendars.some((calendar) => calendar.normalized_season_label === targetSeasonLabel || calendar.season_label === targetSeasonLabel)) {
      setTargetSeasonLabel(planningCalendars[0].normalized_season_label)
    }
  }, [planningCalendars, targetSeasonLabel, targetSource])

  const canShowApplyUi = targetSource === 'planning_calendar'
    && Boolean(sourceTemplateId)
    && Boolean(targetSeasonLabel)
    && Boolean(dryRunResponse)
    && dryRunResponse?.target_source === 'planning_calendar'
    && dryRunResponse.target_calendar_exists === true
    && Boolean(dryRunResponse.diff_fingerprint)
    && Boolean(dryRunResponse.source_template_fingerprint)
    && Boolean(dryRunResponse.target_calendar_fingerprint)

  const canApplyReviewedDiff = canShowApplyUi
    && requestedBy.trim().length > 0
    && auditReason.trim().length > 0
    && explicitConfirmation === PLANNING_APPLY_CONFIRMATION

  function handleCompareSubmit(event: FormEvent<HTMLFormElement>): void {
    event.preventDefault()
    setDryRunResponse(null)
    setApplyResponse(null)
    compareMutation.mutate(targetSource === 'planning_calendar' ? {
      target_season_label: targetSeasonLabel,
      source_template_id: sourceTemplateId,
      target_source: 'planning_calendar',
      policy: 'copy_missing_only'
    } : {
      target_season_label: targetSeasonLabel,
      source_template_id: sourceTemplateId,
      target_source: 'payload',
      target_events: targetEvents,
      policy: 'copy_missing_only'
    })
  }

  return (
    <section className="panel">
      <PageIntro
        title="Calendar Compare / Apply"
        subtitle="Dry-run compare by default, with guarded copy_missing_only apply for persisted planning calendars."
      />

      <SectionCard title="Calendar compare and apply safety notes">
        <ul className="dashboard-help-list">
          <li>Compare remains dry-run by default.</li>
          <li>Payload mode remains dry-run only.</li>
          <li>Only planning-calendar copy_missing_only apply is enabled after a reviewed persisted planning-calendar dry-run; replace/update workflows remain disabled.</li>
          <li>replace_unlocked_only is not enabled.</li>
          <li>replace_all is not enabled.</li>
          <li>No existing planning event is updated.</li>
          <li>No locked event is changed.</li>
          <li>No target-only event is deleted.</li>
          <li>No canonical season calendar is modified.</li>
          <li>No Viewer, rankings, race, history, run data, or simulation output changes.</li>
        </ul>
      </SectionCard>

      <SectionCard title="Summary">
        {registryQuery.isLoading || templatesQuery.isLoading ? <p className="status">Loading compare foundation…</p> : null}
        {registryQuery.error ? <p className="error">Failed to load season registry: {formatApiError(registryQuery.error)}</p> : null}
        {templatesQuery.error ? <p className="error">Failed to load season templates: {formatApiError(templatesQuery.error)}</p> : null}

        {registry || templatesQuery.data ? (
          <div className="dashboard-grid">
            <article className="metric-card"><span>Registry range</span><strong>{registry ? `${registry.start_season}–${registry.end_season}` : '—'}</strong></article>
            <article className="metric-card"><span>Registry season count</span><strong>{registry?.season_count ?? '—'}</strong></article>
            <article className="metric-card"><span>Registry week count</span><strong>{registry?.week_count ?? '—'}</strong></article>
            <article className="metric-card"><span>Season templates count</span><strong>{templates.length}</strong></article>
            <article className="metric-card"><span>Total template slots</span><strong>{templateSlotCount}</strong></article>
          </div>
        ) : null}
      </SectionCard>

      <SectionCard title="Comparison sources">
        <ul className="dashboard-help-list">
          <li>
            Season Template: {templates.length ? templates.map((template) => template.name).join(', ') : 'No templates available.'}
          </li>
          <li>Concrete Season: Selection workflow — planned.</li>
          <li>Another Season: Selection workflow — planned.</li>
          <li>Blank Calendar: Selection workflow — planned.</li>
        </ul>
      </SectionCard>

      <SectionCard title="Template slot preview">
        {templates.length ? (
          <table>
            <thead>
              <tr>
                <th>Template</th>
                <th>Slots</th>
                <th>Week Count</th>
                <th>Earliest Slot</th>
                <th>Latest Slot</th>
                <th>Qualification Slots</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {templates.map((template) => {
                const slotStarts = template.slots.map((slot) => slot.season_week_start)
                const slotEnds = template.slots.map((slot) => slot.season_week_end)
                const earliestSlot = slotStarts.length ? Math.min(...slotStarts) : null
                const latestSlot = slotEnds.length ? Math.max(...slotEnds) : null
                const qualificationSlots = template.slots.filter((slot) => slot.has_qualification).length

                return (
                  <tr key={template.template_id}>
                    <td>{template.name}</td>
                    <td>{template.slot_count}</td>
                    <td>{template.week_count}</td>
                    <td>{earliestSlot ? `SW${earliestSlot}` : '—'}</td>
                    <td>{latestSlot ? `SW${latestSlot}` : '—'}</td>
                    <td>{qualificationSlots}</td>
                    <td>{template.status}</td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        ) : (
          <p className="status">No season templates available for read-only preview.</p>
        )}
      </SectionCard>


      <SectionCard title="Two-pane compare/copy workspace preview">
        <p><strong>Preview only — not persisted, not applied, not simulation data.</strong></p>
        <p>This Admin-only foundation uses local example CalendarEventDraft rows with weeks and qualificationWeeks vocabulary. It does not call copy/apply APIs.</p>
        <div className="dashboard-grid">
          <article className="metric-card">
            <span>Target canonical season</span>
            <strong>2006/07</strong>
            <p>Left pane: target canonical season being edited in a future workflow.</p>
            <PreviewEventList events={TARGET_PREVIEW_EVENTS} />
          </article>
          <article className="metric-card">
            <span>Source calendar/template</span>
            <strong>Default World Tour Skeleton Sandbox</strong>
            <p>Right pane: source template or source season used for inspiration/copying in a future workflow.</p>
            <PreviewEventList events={SOURCE_PREVIEW_EVENTS} />
          </article>
        </div>
      </SectionCard>

      <SectionCard title="Comparison summary preview">
        <p>Preview only — this local deterministic comparison does not inspect persisted calendars or templates.</p>
        <ul className="dashboard-help-list">
          {getPreviewComparisonSummary().map((summary) => (
            <li key={summary.status}>
              <strong>{summary.status}:</strong> {summary.events.length ? summary.events.join(', ') : 'None in preview'}
            </li>
          ))}
        </ul>
      </SectionCard>

      <SectionCard title="Backend compare dry-run">
        <p><strong>Backend dry-run only.</strong></p>
        <ul className="dashboard-help-list">
          <li>Compare dry-run only until the reviewed planning-calendar diff is explicitly applied below.</li>
          <li>Apply uses copy_missing_only only.</li>
          <li>No existing planning event is updated.</li>
          <li>No locked event is changed.</li>
          <li>No target-only event is deleted.</li>
          <li>No canonical season calendar is modified.</li>
          <li>No Viewer, rankings, race, history, run data, or simulation output changes.</li>
          <li>Payload target mode uses local preview rows. Planning calendar target mode loads persisted planning calendars server-side.</li>
        </ul>
        {calendarTemplatesQuery.isLoading ? <p className="status">Loading persisted calendar templates…</p> : null}
        {calendarTemplatesQuery.error ? <p className="error">Failed to load persisted calendar templates: {formatApiError(calendarTemplatesQuery.error)}</p> : null}
        {!calendarTemplatesQuery.isLoading && !calendarTemplates.length ? (
          <p className="status">Create a persisted calendar template first. <Link to="/admin/tour-seasons/season-templates/new">Create new calendar template</Link></p>
        ) : null}
        {calendarTemplates.length ? (
          <form onSubmit={handleCompareSubmit} className="form-grid">
            <label>
              Source template
              <select value={sourceTemplateId} onChange={(event) => setSourceTemplateId(event.target.value)}>
                {calendarTemplates.map((template) => <option key={template.id} value={template.id}>{template.name}</option>)}
              </select>
            </label>
            <label>
              Target source
              <select value={targetSource} onChange={(event) => setTargetSource(event.target.value as CalendarTemplateCompareTargetSource)}>
                <option value="payload">Local payload preview rows</option>
                <option value="planning_calendar">Persisted planning calendar</option>
              </select>
            </label>
            {targetSource === 'planning_calendar' && planningCalendars.length ? (
              <label>
                Planning calendar
                <select value={targetSeasonLabel} onChange={(event) => setTargetSeasonLabel(event.target.value)}>
                  {planningCalendars.map((calendar) => (
                    <option key={calendar.normalized_season_label} value={calendar.normalized_season_label}>
                      {calendar.normalized_season_label} — {calendar.events.length} events — {calendar.status}
                    </option>
                  ))}
                </select>
              </label>
            ) : (
              <label>
                Target season label
                <input value={targetSeasonLabel} onChange={(event) => setTargetSeasonLabel(event.target.value)} />
              </label>
            )}
            <p className="status"><strong>Policy:</strong> copy_missing_only only.</p>
            {targetSource === 'payload' ? <p className="status">Payload target uses local preview target rows; target_fingerprint is derived from those rows.</p> : null}
            {targetSource === 'planning_calendar' ? <p className="status">Target is loaded server-side from persisted planning calendars. No planning calendar is mutated. target_fingerprint uses the persisted planning calendar fingerprint.</p> : null}
            {targetSource === 'planning_calendar' && planningCalendarsQuery.isLoading ? <p className="status">Loading persisted planning calendars…</p> : null}
            {targetSource === 'planning_calendar' && planningCalendarsQuery.error ? <p className="error">Failed to load persisted planning calendars: {formatApiError(planningCalendarsQuery.error)}</p> : null}
            {targetSource === 'planning_calendar' && !planningCalendarsQuery.isLoading && !planningCalendars.length ? <p className="status">No persisted planning calendars exist yet.</p> : null}
            <button type="submit" disabled={compareMutation.isPending || !sourceTemplateId || (targetSource === 'planning_calendar' && !planningCalendars.length)}>Run backend compare dry-run</button>
          </form>
        ) : null}
        {compareMutation.error ? <p className="error">Backend compare dry-run failed: {formatApiError(compareMutation.error)}{targetSource === 'planning_calendar' ? ' The selected planning calendar was not found or may not exist yet.' : ''}</p> : null}
        {dryRunResponse ? (
          <div>
            <div className="dashboard-grid">
              <article className="metric-card"><span>dry_run</span><strong>{String(dryRunResponse.dry_run)}</strong></article>
              <article className="metric-card"><span>mutation_performed</span><strong>{String(dryRunResponse.mutation_performed)}</strong></article>
              <article className="metric-card"><span>status</span><strong>{dryRunResponse.status}</strong></article>
              <article className="metric-card"><span>target_source</span><strong>{dryRunResponse.target_source}</strong></article>
              <article className="metric-card"><span>source_template_fingerprint</span><strong>{dryRunResponse.source_template_fingerprint ?? '—'}</strong></article>
              <article className="metric-card"><span>target_fingerprint</span><strong>{dryRunResponse.target_fingerprint}</strong></article>
              <article className="metric-card"><span>target_calendar_fingerprint</span><strong>{dryRunResponse.target_calendar_fingerprint ?? '—'}</strong></article>
              <article className="metric-card"><span>target_calendar_exists</span><strong>{String(dryRunResponse.target_calendar_exists ?? false)}</strong></article>
              <article className="metric-card"><span>diff_fingerprint</span><strong>{dryRunResponse.diff_fingerprint}</strong></article>
              <article className="metric-card"><span>safety.read_only</span><strong>{String(dryRunResponse.safety.read_only)}</strong></article>
              <article className="metric-card"><span>safety.apply_endpoint_enabled</span><strong>{String(dryRunResponse.safety.apply_endpoint_enabled)}</strong></article>
            </div>
            <p>{dryRunResponse.safety.message}</p>
            <p>{dryRunResponse.target_source === 'planning_calendar' ? 'Planning calendar mode: target_fingerprint uses the persisted planning calendar fingerprint.' : 'Payload mode: target_fingerprint is derived from local preview target rows.'}</p>
            <table>
              <thead><tr><th>same</th><th>missing_from_target</th><th>only_in_target</th><th>conflict</th><th>locked_target_preserved</th><th>selected source</th><th>source</th><th>target</th></tr></thead>
              <tbody><tr><td>{dryRunResponse.summary.same_count}</td><td>{dryRunResponse.summary.missing_from_target_count}</td><td>{dryRunResponse.summary.only_in_target_count}</td><td>{dryRunResponse.summary.conflict_count}</td><td>{dryRunResponse.summary.locked_target_preserved_count}</td><td>{dryRunResponse.summary.selected_source_event_count}</td><td>{dryRunResponse.summary.source_event_count}</td><td>{dryRunResponse.summary.target_event_count}</td></tr></tbody>
            </table>
            <table>
              <thead><tr><th>Status</th><th>Event</th><th>Category</th><th>Source event ID</th><th>Target event ID</th><th>Source weeks</th><th>Target weeks</th><th>Source qualification</th><th>Target qualification</th><th>Locked target</th><th>Reason</th></tr></thead>
              <tbody>{dryRunResponse.items.map((item, index) => <tr key={`${item.status}-${item.source_event_id ?? 'none'}-${item.target_event_id ?? 'none'}-${index}`}><td>{item.status}</td><td>{item.event_name}</td><td>{item.category_code}</td><td>{item.source_event_id ?? '—'}</td><td>{item.target_event_id ?? '—'}</td><td>{formatOptionalWeeks(item.source_weeks)}</td><td>{formatOptionalWeeks(item.target_weeks)}</td><td>{formatOptionalWeeks(item.source_qualification_weeks)}</td><td>{formatOptionalWeeks(item.target_qualification_weeks)}</td><td>{String(item.locked_target)}</td><td>{item.reason}</td></tr>)}</tbody>
            </table>
          </div>
        ) : null}
      </SectionCard>

      {canShowApplyUi ? (
        <SectionCard title="Apply reviewed diff to planning calendar">
          <p><strong>copy_missing_only only</strong></p>
          <ul className="dashboard-help-list">
            <li>This applies only missing source events.</li>
            <li>No existing planning event is updated.</li>
            <li>No locked event is changed.</li>
            <li>No target-only event is deleted.</li>
            <li>No canonical season calendar is modified.</li>
            <li>No simulation is invoked.</li>
            <li>No Viewer, rankings, race, history, run data, or simulation output changes.</li>
          </ul>
          <div className="dashboard-grid">
            <article className="metric-card"><span>source_template_id</span><strong>{sourceTemplateId}</strong></article>
            <article className="metric-card"><span>target_season_label</span><strong>{dryRunResponse.target_season_label}</strong></article>
            <article className="metric-card"><span>policy</span><strong>copy_missing_only</strong></article>
            <article className="metric-card"><span>source_template_fingerprint</span><strong>{dryRunResponse.source_template_fingerprint}</strong></article>
            <article className="metric-card"><span>target_calendar_fingerprint</span><strong>{dryRunResponse.target_calendar_fingerprint}</strong></article>
            <article className="metric-card"><span>reviewed diff fingerprint</span><strong>{dryRunResponse.diff_fingerprint}</strong></article>
            <article className="metric-card"><span>missing_from_target_count</span><strong>{dryRunResponse.summary.missing_from_target_count}</strong></article>
            <article className="metric-card"><span>same_count</span><strong>{dryRunResponse.summary.same_count}</strong></article>
            <article className="metric-card"><span>only_in_target_count</span><strong>{dryRunResponse.summary.only_in_target_count}</strong></article>
            <article className="metric-card"><span>conflict_count</span><strong>{dryRunResponse.summary.conflict_count}</strong></article>
            <article className="metric-card"><span>locked_target_preserved_count</span><strong>{dryRunResponse.summary.locked_target_preserved_count}</strong></article>
          </div>
          <form className="form-grid" onSubmit={(event) => { event.preventDefault(); applyMutation.mutate() }}>
            <label>requested_by<input value={requestedBy} onChange={(event) => setRequestedBy(event.target.value)} /></label>
            <label>audit_reason<textarea value={auditReason} onChange={(event) => setAuditReason(event.target.value)} /></label>
            <label>explicit_confirmation<input value={explicitConfirmation} onChange={(event) => setExplicitConfirmation(event.target.value)} /></label>
            <p className="status">Required exact confirmation: {PLANNING_APPLY_CONFIRMATION}</p>
            <button type="submit" disabled={!canApplyReviewedDiff || applyMutation.isPending}>Apply reviewed diff to planning calendar</button>
          </form>
          {applyMutation.error ? <div className="error"><p>Planning calendar apply failed: {formatApiError(applyMutation.error)}</p></div> : null}
          {applyResponse ? (applyResponse.mutation_performed ? (
            <div className="success">
              <p>{applyResponse.message}</p>
              <ul className="dashboard-help-list">
                <li>created_event_count: {applyResponse.created_event_count}</li>
                <li>audit_record_id: {applyResponse.audit_record_id ?? '—'}</li>
                <li>audit_record_fingerprint: {applyResponse.audit_record_fingerprint ?? '—'}</li>
                <li>audit_persisted: {String(applyResponse.audit_persisted)}</li>
                <li>audit_persistence_status: {applyResponse.audit_persistence_status}</li>
                <li>before_calendar_fingerprint: {applyResponse.before_calendar_fingerprint ?? '—'}</li>
                <li>after_calendar_fingerprint: {applyResponse.after_calendar_fingerprint ?? '—'}</li>
              </ul>
              <p>Planning calendar caches were invalidated. Re-run compare dry-run to review the updated diff.</p>
            </div>
          ) : (
            <div className="error">
              <p>{applyResponse.message}</p>
              <p>validation_errors: {applyResponse.validation_errors.length ? applyResponse.validation_errors.join('; ') : 'None'}</p>
              <p>validation_warnings: {applyResponse.validation_warnings.length ? applyResponse.validation_warnings.join('; ') : 'None'}</p>
            </div>
          )) : null}
        </SectionCard>
      ) : null}

      <SectionCard title="Future compare states (planned)">
        <p>Planned statuses: Same, Modified, Missing from current, Only in current, and Conflict.</p>
        <p>Planned actions: Apply to this season, Replace current, Keep current, Ignore, and Open editor.</p>
        <p>These actions are planned and not enabled.</p>
      </SectionCard>

      <SectionCard title="Navigation">
        <p><Link to="/admin/tour-seasons/season-templates">Open Season Templates</Link></p>
        <p><Link to="/admin/tour-seasons/season-templates/draft-sandbox">Open Draft Template Sandbox</Link></p>
        <p><Link to="/admin/tour-seasons/season-registry">Open Season Registry</Link></p>
        <p><Link to="/admin/seasons">Open Seasons</Link></p>
        <p><Link to="/admin/tour-seasons/validation">Open Calendar Validation</Link></p>
        <p><Link to="/admin/tour-seasons">Back to Tour &amp; Seasons</Link></p>
      </SectionCard>
    </section>
  )
}
