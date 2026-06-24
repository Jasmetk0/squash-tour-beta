import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'

import { getSeasonTemplates, listCalendarTemplates } from '../api/client'
import { describeCalendarEventTiming, type CalendarEventDraft } from '../tour/calendarEventModel'
import { PageIntro, SectionCard } from '../components/RunScopedUi'
import { formatApiError } from '../utils/apiErrors'


const exampleDraftTemplateEvents: CalendarEventDraft[] = [
  {
    id: 'example-nemarque-open',
    name: 'Némarque Open',
    categoryCode: 'DIAMOND',
    weeks: [6, 7],
    qualificationWeeks: [5],
    locked: true,
    status: 'template'
  },
  {
    id: 'example-ameriga-open',
    name: 'Ameriga Open',
    categoryCode: 'DIAMOND',
    weeks: [44, 45],
    qualificationWeeks: [43],
    locked: true,
    status: 'template'
  },
  {
    id: 'example-world-championship',
    name: 'World Championship',
    categoryCode: 'WORLD_CHAMPIONSHIP',
    weeks: [49, 50],
    qualificationWeeks: [48],
    locked: true,
    status: 'template'
  },
  {
    id: 'example-world-tour-finals',
    name: 'World Tour Finals',
    categoryCode: 'WORLD_TOUR_FINALS',
    weeks: [55],
    qualificationWeeks: [],
    locked: true,
    status: 'template'
  }
]

const plannedTemplateWorkflow = [
  'Create draft template — planned',
  'Add events using weeks and qualificationWeeks — planned',
  'Lock important events — planned',
  'Compare template against canonical season — planned',
  'Copy selected events into canonical season — planned',
  'Replace unlocked events only — planned'
]

export function AdminTourSeasonsSeasonTemplatesPage(): JSX.Element {
  const templatesQuery = useQuery({ queryKey: ['season-templates'], queryFn: getSeasonTemplates, retry: false })
  const calendarTemplatesQuery = useQuery({ queryKey: ['calendar-templates'], queryFn: listCalendarTemplates, retry: false })
  const payload = templatesQuery.data
  const calendarTemplatesPayload = calendarTemplatesQuery.data
  const calendarTemplates = calendarTemplatesPayload?.templates ?? []
  return (
    <section className="panel">
      <PageIntro title="Season Templates" subtitle="Reusable calendar plans that can later be copied into concrete seasons." />
      <SectionCard title="Read-only foundation notes">
        <ul className="dashboard-help-list">
          <li>Read-only foundation.</li>
          <li><Link to="/admin/tour-seasons/season-templates/draft-sandbox">Open Draft Template Sandbox</Link></li>
          <li>Editing/copy/apply workflows are planned.</li>
          <li>Current operational calendar tooling remains in <Link to="/admin/seasons">/admin/seasons</Link>.</li>
          <li>Season Registry is separate and available at <Link to="/admin/tour-seasons/season-registry">/admin/tour-seasons/season-registry</Link>.</li>
        </ul>
      </SectionCard>
      <SectionCard title="Admin-only calendar draft templates">
        <p>
          Calendar draft templates are Admin-only planning objects. They are not played, not visible in Viewer,
          and do not mutate canonical seasons until explicitly copied/applied later.
        </p>
        <p>
          Template events use weeks and qualificationWeeks. Qualification belongs to the main event. Locked events
          must be explicitly unlocked before move/delete/overwrite actions.
        </p>
        <h3>Future template workflow</h3>
        <ul className="dashboard-help-list">
          {plannedTemplateWorkflow.map((item) => <li key={item}>{item}</li>)}
        </ul>
        <h3>Default World Tour Skeleton</h3>
        <p>Examples only — future Admin template model, not persisted template data.</p>
        <ul className="dashboard-help-list">
          {exampleDraftTemplateEvents.map((event) => (
            <li key={event.id}>
              {event.name} — {event.categoryCode} — {describeCalendarEventTiming(event)} — {event.locked ? 'Locked' : 'Unlocked'}
            </li>
          ))}
        </ul>
      </SectionCard>
      <SectionCard title="Summary">
        {templatesQuery.isLoading ? <p className="status">Loading season templates…</p> : null}
        {templatesQuery.error ? <p className="error">Failed to load season templates: {formatApiError(templatesQuery.error)}</p> : null}
        {payload ? <ul className="dashboard-help-list"><li>Templates: {payload.templates.length}</li><li>Source path: {payload.source_path ?? '—'}</li><li>Status: {payload.status}</li></ul> : null}
      </SectionCard>
      <SectionCard title="Persisted Admin calendar templates">
        <p>
          Persisted Admin calendar templates are Admin-only planning/config objects stored by the backend. They are not played,
          not visible in Viewer, and do not mutate canonical seasons, runs, rankings, race, history, or simulation output.
        </p>
        <p>
          Phase A is read-only wiring only. Editing, archive, copy/apply to canonical seasons, and simulation integration are planned but not enabled.
        </p>
        {calendarTemplatesQuery.isLoading ? <p className="status">Loading persisted Admin calendar templates…</p> : null}
        {calendarTemplatesQuery.error ? <p className="error">Failed to load persisted Admin calendar templates: {formatApiError(calendarTemplatesQuery.error)}</p> : null}
        {calendarTemplatesPayload ? (
          <ul className="dashboard-help-list">
            <li>Persisted templates: {calendarTemplates.length}</li>
            <li>Source path: {calendarTemplatesPayload.source_path ?? '—'}</li>
            <li>Schema version: {calendarTemplatesPayload.schema_version}</li>
            <li>Status: {calendarTemplatesPayload.status}</li>
          </ul>
        ) : null}
        {calendarTemplatesPayload && calendarTemplates.length === 0 ? <p className="status">No persisted Admin calendar templates exist yet.</p> : null}
        {calendarTemplates.length ? (
          <table>
            <thead>
              <tr>
                <th>Name</th>
                <th>id</th>
                <th>Status</th>
                <th>Event count</th>
                <th>template_fingerprint</th>
                <th>Read-only detail</th>
              </tr>
            </thead>
            <tbody>
              {calendarTemplates.map((template) => (
                <tr key={template.id}>
                  <td>{template.name}</td>
                  <td>{template.id}</td>
                  <td>{template.status}</td>
                  <td>{template.events.length}</td>
                  <td>{template.template_fingerprint ?? '—'}</td>
                  <td><Link to={`/admin/tour-seasons/season-templates/calendar/${encodeURIComponent(template.id)}`}>Open persisted calendar template</Link></td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : null}
      </SectionCard>
      {payload?.templates.map((template) => (
        <SectionCard key={template.template_id} title={`${template.name} (${template.template_id})`}>
          <ul className="dashboard-help-list">
            <li>Template: <Link to={`/admin/tour-seasons/season-templates/${template.template_id}`}>{template.name} ({template.template_id})</Link></li><li>Template ID: {template.template_id}</li><li>Slot count: {template.slot_count}</li><li>Week count: {template.week_count}</li><li>Status: {template.status}</li><li>Description: {template.description}</li><li>Apply to Season — planned</li>
          </ul>
          <table><thead><tr><th>Week block</th><th>Tournament</th><th>Category</th><th>Host</th><th>Region</th><th>Qualification</th><th>Source</th></tr></thead><tbody>{template.slots.map((slot) => (
            <tr key={slot.slot_id}><td>SW{slot.season_week_start}–SW{slot.season_week_end}</td><td>{slot.tournament_name}</td><td>{slot.category}</td><td>{slot.host_country ?? '—'}</td><td>{slot.region ?? '—'}</td><td>{slot.has_qualification ? `Yes (QW${slot.qualifying_week_start ?? '—'})` : 'No'}</td><td>{slot.source_template_id ?? '—'}</td></tr>
          ))}</tbody></table>
        </SectionCard>
      ))}
      <SectionCard title="Navigation">
        <p><Link to="/admin/tour-seasons">Back to Tour &amp; Seasons</Link></p>
        <p><Link to="/admin/seasons">Open Seasons</Link></p>
        <p>
          <Link to="/admin/tour-seasons/season-registry">Open Season Registry</Link>
        </p>
        <p><Link to="/admin/tour-seasons/categories">Open Categories</Link></p>
        <p><Link to="/admin/tour-seasons/compare">Open Calendar Compare / Apply</Link></p>
        <p><Link to="/admin/tournament-templates">Open Tournament Templates current tooling</Link></p>
      </SectionCard>
    </section>
  )
}
