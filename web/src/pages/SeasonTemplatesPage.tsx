import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'

import { getSeasonTemplates } from '../api/client'
import { PageIntro, SectionCard } from '../components/RunScopedUi'
import { formatApiError } from '../utils/apiErrors'

export function AdminTourSeasonsSeasonTemplatesPage(): JSX.Element {
  const templatesQuery = useQuery({ queryKey: ['season-templates'], queryFn: getSeasonTemplates, retry: false })
  const payload = templatesQuery.data
  return (
    <section className="panel">
      <PageIntro title="Season Templates" subtitle="Reusable calendar plans that can later be copied into concrete seasons." />
      <SectionCard title="Read-only foundation notes">
        <ul className="dashboard-help-list">
          <li>Read-only foundation.</li>
          <li>Editing/copy/apply workflows are planned.</li>
          <li>Current operational calendar tooling remains in <Link to="/admin/seasons">/admin/seasons</Link>.</li>
          <li>Season Registry is separate and available at <Link to="/admin/tour-seasons/season-registry">/admin/tour-seasons/season-registry</Link>.</li>
        </ul>
      </SectionCard>
      <SectionCard title="Summary">
        {templatesQuery.isLoading ? <p className="status">Loading season templates…</p> : null}
        {templatesQuery.error ? <p className="error">Failed to load season templates: {formatApiError(templatesQuery.error)}</p> : null}
        {payload ? <ul className="dashboard-help-list"><li>Templates: {payload.templates.length}</li><li>Source path: {payload.source_path ?? '—'}</li><li>Status: {payload.status}</li></ul> : null}
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
        <p><Link to="/admin/seasons">Open Seasons</Link></p>
        <p>
          <Link to="/admin/tour-seasons/season-registry">Open Season Registry</Link>
        </p>
        <p><Link to="/admin/tournament-templates">Open Tournament Templates current tooling</Link></p>
      </SectionCard>
    </section>
  )
}
