import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'

import { getSeasonRegistry, getSeasonTemplates } from '../api/client'
import { PageIntro, SectionCard } from '../components/RunScopedUi'
import { type CalendarEventDraft, describeCalendarEventTiming } from '../tour/calendarEventModel'
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

  const registry = registryQuery.data
  const templates = templatesQuery.data?.templates ?? []
  const templateSlotCount = templates.reduce((total, template) => total + template.slot_count, 0)

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
