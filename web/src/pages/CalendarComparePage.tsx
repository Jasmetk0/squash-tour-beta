import { useMutation, useQuery } from '@tanstack/react-query'
import { type FormEvent, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'

import { compareCalendarTemplateDryRun, getSeasonRegistry, getSeasonTemplates, listCalendarTemplates } from '../api/client'
import { PageIntro, SectionCard } from '../components/RunScopedUi'
import type { CalendarTemplateComparePolicy, CalendarTemplateCompareDryRunResponse, CalendarTemplateEventRecord } from '../api/types'
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

const FUTURE_COPY_APPLY_ACTIONS = [
  'Copy selected source events — planned',
  'Replace unlocked target events only — planned',
  'Preserve locked target events — planned',
  'Unlock target event before overwrite — planned',
  'Preview diff before apply — planned',
  'Confirm apply with audit log — planned'
]

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
  const registryQuery = useQuery({ queryKey: ['season-registry'], queryFn: getSeasonRegistry, retry: false })
  const templatesQuery = useQuery({ queryKey: ['season-templates'], queryFn: getSeasonTemplates, retry: false })
  const calendarTemplatesQuery = useQuery({ queryKey: ['calendar-templates'], queryFn: listCalendarTemplates, retry: false })
  const [sourceTemplateId, setSourceTemplateId] = useState('')
  const [targetSeasonLabel, setTargetSeasonLabel] = useState('2006/07')
  const [policy, setPolicy] = useState<CalendarTemplateComparePolicy>('replace_unlocked_only')
  const [dryRunResponse, setDryRunResponse] = useState<CalendarTemplateCompareDryRunResponse | null>(null)

  const registry = registryQuery.data
  const templates = templatesQuery.data?.templates ?? []
  const templateSlotCount = templates.reduce((total, template) => total + template.slot_count, 0)
  const calendarTemplates = calendarTemplatesQuery.data?.templates ?? []
  const targetEvents = TARGET_PREVIEW_EVENTS.map(toCalendarTemplateEventRecord)
  const compareMutation = useMutation({
    mutationFn: compareCalendarTemplateDryRun,
    onSuccess: (response) => setDryRunResponse(response)
  })

  useEffect(() => {
    if (!sourceTemplateId && calendarTemplates.length) {
      setSourceTemplateId(calendarTemplates[0].id)
    }
  }, [calendarTemplates, sourceTemplateId])

  function handleCompareSubmit(event: FormEvent<HTMLFormElement>): void {
    event.preventDefault()
    setDryRunResponse(null)
    compareMutation.mutate({
      target_season_label: targetSeasonLabel,
      source_template_id: sourceTemplateId,
      target_events: targetEvents,
      policy
    })
  }

  return (
    <section className="panel">
      <PageIntro
        title="Calendar Compare / Apply"
        subtitle="Read-only comparison foundation for templates, registry seasons, and future concrete season calendars."
      />

      <SectionCard title="Read-only foundation notes">
        <ul className="dashboard-help-list">
          <li>Comparison foundation only.</li>
          <li>Apply/Replace workflows are planned and not enabled.</li>
          <li>No concrete season calendars are created or modified on this page.</li>
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
          <li>No canonical season calendar is modified.</li>
          <li>No copy/apply endpoint is called.</li>
          <li>No Viewer, run, rankings, race, history, or simulation output changes.</li>
          <li>Target events are still local preview rows for this phase. The dry-run endpoint is real, but no canonical season calendar is read or mutated.</li>
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
              Target season label
              <input value={targetSeasonLabel} onChange={(event) => setTargetSeasonLabel(event.target.value)} />
            </label>
            <label>
              Policy
              <select value={policy} onChange={(event) => setPolicy(event.target.value as CalendarTemplateComparePolicy)}>
                <option value="replace_unlocked_only">replace_unlocked_only</option>
                <option value="copy_missing_only">copy_missing_only</option>
              </select>
            </label>
            <button type="submit" disabled={compareMutation.isPending || !sourceTemplateId}>Run backend compare dry-run</button>
          </form>
        ) : null}
        {compareMutation.error ? <p className="error">Backend compare dry-run failed: {formatApiError(compareMutation.error)}</p> : null}
        {dryRunResponse ? (
          <div>
            <div className="dashboard-grid">
              <article className="metric-card"><span>dry_run</span><strong>{String(dryRunResponse.dry_run)}</strong></article>
              <article className="metric-card"><span>mutation_performed</span><strong>{String(dryRunResponse.mutation_performed)}</strong></article>
              <article className="metric-card"><span>status</span><strong>{dryRunResponse.status}</strong></article>
              <article className="metric-card"><span>source_template_fingerprint</span><strong>{dryRunResponse.source_template_fingerprint ?? '—'}</strong></article>
              <article className="metric-card"><span>target_fingerprint</span><strong>{dryRunResponse.target_fingerprint}</strong></article>
              <article className="metric-card"><span>diff_fingerprint</span><strong>{dryRunResponse.diff_fingerprint}</strong></article>
              <article className="metric-card"><span>safety.read_only</span><strong>{String(dryRunResponse.safety.read_only)}</strong></article>
              <article className="metric-card"><span>safety.apply_endpoint_enabled</span><strong>{String(dryRunResponse.safety.apply_endpoint_enabled)}</strong></article>
            </div>
            <p>{dryRunResponse.safety.message}</p>
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

      <SectionCard title="Future copy/apply actions">
        <ul className="dashboard-help-list">
          {FUTURE_COPY_APPLY_ACTIONS.map((action) => <li key={action}>{action}</li>)}
        </ul>
      </SectionCard>

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
