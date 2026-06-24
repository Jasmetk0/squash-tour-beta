import { useQuery } from '@tanstack/react-query'
import { Link, useParams } from 'react-router-dom'

import { getCalendarTemplate } from '../api/client'
import { DetailFieldGrid } from '../components/DetailUi'
import { PageIntro, SectionCard } from '../components/RunScopedUi'
import { formatSeasonWeeks } from '../tour/calendarEventModel'
import { formatApiError, isApiNotFound } from '../utils/apiErrors'

export function AdminCalendarTemplateDetailPage(): JSX.Element {
  const { templateId = '' } = useParams()
  const templateQuery = useQuery({
    queryKey: ['calendar-template', templateId],
    queryFn: () => getCalendarTemplate(templateId),
    enabled: Boolean(templateId),
    retry: false
  })

  const template = templateQuery.data?.template ?? null
  const notFound = templateQuery.error && isApiNotFound(templateQuery.error)

  return (
    <section className="panel">
      <PageIntro
        title="Persisted Admin calendar template"
        subtitle="Read-only persisted Admin calendar template. Editing, archive, copy/apply to canonical seasons, and simulation integration are planned but not enabled."
      />

      <SectionCard title="Phase A safety boundary">
        <p>
          Persisted Admin calendar templates are Admin-only planning/config objects stored by the backend. They are not played,
          not visible in Viewer, and do not mutate canonical seasons, runs, rankings, race, history, or simulation output.
        </p>
      </SectionCard>

      {templateQuery.isLoading ? <p className="status">Loading persisted Admin calendar template…</p> : null}
      {templateQuery.error && !notFound ? <p className="error">Failed to load persisted Admin calendar template: {formatApiError(templateQuery.error)}</p> : null}
      {!templateQuery.isLoading && !templateQuery.error && !template ? <p className="status">Persisted Admin calendar template not found.</p> : null}
      {notFound ? <p className="status">Persisted Admin calendar template not found.</p> : null}

      {template ? (
        <>
          <SectionCard title="Template metadata">
            <DetailFieldGrid fields={[
              { label: 'Name', value: template.name },
              { label: 'id', value: template.id },
              { label: 'description', value: template.description || '—' },
              { label: 'status', value: template.status },
              { label: 'created_at', value: template.created_at ?? '—' },
              { label: 'updated_at', value: template.updated_at ?? '—' },
              { label: 'template_fingerprint', value: template.template_fingerprint ?? '—' },
              { label: 'source_path', value: templateQuery.data?.source_path ?? '—' },
              { label: 'schema_version', value: templateQuery.data?.schema_version ?? '—' },
              { label: 'response_status', value: templateQuery.data?.status ?? '—' },
              { label: 'event_count', value: template.events.length }
            ]} />
          </SectionCard>

          <SectionCard title="Events">
            {template.events.length ? (
              <table>
                <thead>
                  <tr>
                    <th>Name</th>
                    <th>id</th>
                    <th>category_code</th>
                    <th>weeks</th>
                    <th>qualification_weeks</th>
                    <th>Lock</th>
                    <th>country_code</th>
                    <th>City</th>
                    <th>Venue</th>
                    <th>Notes</th>
                    <th>event_fingerprint</th>
                  </tr>
                </thead>
                <tbody>
                  {template.events.map((event) => (
                    <tr key={event.id}>
                      <td>{event.name}</td>
                      <td>{event.id}</td>
                      <td>{event.category_code}</td>
                      <td>{formatSeasonWeeks(event.weeks)}</td>
                      <td>{formatSeasonWeeks(event.qualification_weeks)}</td>
                      <td>{event.locked ? 'Locked' : 'Unlocked'}</td>
                      <td>{event.country_code ?? '—'}</td>
                      <td>{event.city ?? '—'}</td>
                      <td>{event.venue ?? '—'}</td>
                      <td>{event.notes ?? '—'}</td>
                      <td>{event.event_fingerprint ?? '—'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <p className="status">This persisted Admin calendar template has no events.</p>
            )}
          </SectionCard>
        </>
      ) : null}

      <SectionCard title="Navigation">
        <p><Link to="/admin/tour-seasons/season-templates">Back to Season Templates</Link></p>
        <p><Link to="/admin/tour-seasons/season-templates/draft-sandbox">Open Draft Template Sandbox</Link></p>
        <p><Link to="/admin/tour-seasons/compare">Open Calendar Compare / Apply</Link></p>
        <p><Link to="/admin/tour-seasons/season-registry">Open Season Registry</Link></p>
      </SectionCard>
    </section>
  )
}
