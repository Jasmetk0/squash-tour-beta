import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'

import { getSeasonRegistry, getSeasonTemplates } from '../api/client'
import { PageIntro, SectionCard } from '../components/RunScopedUi'
import { formatApiError } from '../utils/apiErrors'

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

      <SectionCard title="Future compare states (planned)">
        <p>Planned statuses: Same, Modified, Missing from current, Only in current, and Conflict.</p>
        <p>Planned actions: Apply to this season, Replace current, Keep current, Ignore, and Open editor.</p>
        <p>These actions are planned and not enabled.</p>
      </SectionCard>

      <SectionCard title="Navigation">
        <p><Link to="/admin/tour-seasons/season-templates">Open Season Templates</Link></p>
        <p><Link to="/admin/tour-seasons/season-registry">Open Season Registry</Link></p>
        <p><Link to="/admin/seasons">Open Seasons</Link></p>
        <p><Link to="/admin/tour-seasons/validation">Open Calendar Validation</Link></p>
        <p><Link to="/admin/tour-seasons">Back to Tour &amp; Seasons</Link></p>
      </SectionCard>
    </section>
  )
}
