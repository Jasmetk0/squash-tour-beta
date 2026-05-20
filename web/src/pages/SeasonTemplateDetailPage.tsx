import { useQuery } from '@tanstack/react-query'
import { Link, useParams } from 'react-router-dom'

import { getSeasonTemplates } from '../api/client'
import { DetailFieldGrid } from '../components/DetailUi'
import { PageIntro, SectionCard } from '../components/RunScopedUi'
import { formatApiError } from '../utils/apiErrors'

export function AdminTourSeasonsSeasonTemplateDetailPage(): JSX.Element {
  const { templateId = '' } = useParams()
  const templatesQuery = useQuery({ queryKey: ['season-templates'], queryFn: getSeasonTemplates, retry: false })
  const payload = templatesQuery.data
  const template = payload?.templates.find((item) => item.template_id === templateId)

  const slots = template?.slots ?? []
  const earliestWeek = slots.length ? Math.min(...slots.map((slot) => slot.season_week_start)) : null
  const latestWeek = slots.length ? Math.max(...slots.map((slot) => slot.season_week_end)) : null
  const qualificationSlotCount = slots.filter((slot) => slot.has_qualification).length

  return (
    <section className="panel">
      <PageIntro title="Season Template" subtitle="Read-only reusable calendar plan derived from current tournament template config." />

      {templatesQuery.isLoading ? <p className="status">Loading season template…</p> : null}
      {templatesQuery.error ? <p className="error">Failed to load season template: {formatApiError(templatesQuery.error)}</p> : null}
      {!templatesQuery.isLoading && !templatesQuery.error && !template ? <p className="status">Season template not found.</p> : null}

      {template ? (
        <>
          <SectionCard title="Header summary">
            <DetailFieldGrid fields={[
              { label: 'Name', value: template.name },
              { label: 'Template ID', value: template.template_id },
              { label: 'Status', value: template.status },
              { label: 'Source', value: template.source }
            ]} />
          </SectionCard>

          <SectionCard title="Identity">
            <DetailFieldGrid fields={[
              { label: 'template_id', value: template.template_id },
              { label: 'name', value: template.name },
              { label: 'description', value: template.description },
              { label: 'season_count_supported', value: template.season_count_supported ?? '—' },
              { label: 'week_count', value: template.week_count },
              { label: 'slot_count', value: template.slot_count },
              { label: 'status', value: template.status }
            ]} />
          </SectionCard>

          <SectionCard title="Source">
            <ul className="dashboard-help-list">
              <li>source: {template.source}</li>
              <li>source_path: {payload?.source_path ?? '—'}</li>
              <li>Read-only foundation note: This template detail is currently view-only and derived from tournament template config.</li>
            </ul>
          </SectionCard>

          <SectionCard title="Slot overview">
            <ul className="dashboard-help-list">
              <li>total slots: {slots.length}</li>
              <li>week_count: {template.week_count}</li>
              <li>earliest season_week_start: {earliestWeek ?? '—'}</li>
              <li>latest season_week_end: {latestWeek ?? '—'}</li>
              <li>slots with qualification: {qualificationSlotCount}</li>
            </ul>
          </SectionCard>

          <SectionCard title="Slots">
            <table>
              <thead>
                <tr>
                  <th>Slot</th><th>Week block</th><th>Tournament</th><th>Category</th><th>Host</th><th>Region</th><th>Qualification</th><th>Main draw week</th><th>Source template</th><th>Notes</th>
                </tr>
              </thead>
              <tbody>
                {slots.map((slot) => (
                  <tr key={slot.slot_id}>
                    <td>{slot.slot_id}</td>
                    <td>SW{slot.season_week_start}–SW{slot.season_week_end}</td>
                    <td>{slot.tournament_name}</td>
                    <td>{slot.category}</td>
                    <td>{slot.host_country ?? '—'}</td>
                    <td>{slot.region ?? '—'}</td>
                    <td>{slot.has_qualification ? `Yes (QW${slot.qualifying_week_start ?? '—'})` : 'No'}</td>
                    <td>{slot.main_draw_week_start ?? '—'}</td>
                    <td>{slot.source_template_id ?? '—'}</td>
                    <td>{slot.notes ?? '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </SectionCard>

          <SectionCard title="Planned future model">
            <ul className="dashboard-help-list">
              <li>Season template editor — planned.</li>
              <li>Copy/apply to concrete season — planned.</li>
              <li>Compare/apply workflows — planned.</li>
              <li>Concrete seasons will later snapshot/copy template slots into editable season calendars.</li>
            </ul>
          </SectionCard>
        </>
      ) : null}

      <SectionCard title="Navigation">
        <p><Link to="/admin/tour-seasons/season-templates">Back to Season Templates</Link></p>
        <p><Link to="/admin/tour-seasons/season-registry">Open Season Registry</Link></p>
        <p><Link to="/admin/tour-seasons/tournaments">Open Tournaments</Link></p>
        <p><Link to="/admin/tour-seasons/categories">Open Categories</Link></p>
        <p><Link to="/admin/seasons">Open Seasons</Link></p>
      </SectionCard>
    </section>
  )
}
