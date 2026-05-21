import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'

import { getSeasonRegistry, getSeasonTemplates, getTourSeasonsValidation } from '../api/client'
import { DetailList } from '../components/DetailUi'
import { PageIntro, SectionCard } from '../components/RunScopedUi'
import { formatApiError } from '../utils/apiErrors'

export function AdminSeasonBuilderPage(): JSX.Element {
  const registryQuery = useQuery({ queryKey: ['season-registry'], queryFn: getSeasonRegistry, retry: false })
  const templatesQuery = useQuery({ queryKey: ['season-templates'], queryFn: getSeasonTemplates, retry: false })
  const validationQuery = useQuery({ queryKey: ['tour-seasons-validation'], queryFn: getTourSeasonsValidation, retry: false })

  const registry = registryQuery.data
  const templates = templatesQuery.data?.templates ?? []
  const seasonExamples = registry?.seasons.slice(0, 5) ?? []
  const hasTemplates = templates.length > 0
  const slotsWithinRange = templates.every((template) => template.slots.every((slot) => slot.season_week_start >= 1 && slot.season_week_end <= 61))
  const allTemplatesWeek61 = templates.every((template) => template.week_count === 61)

  return (
    <section className="panel">
      <PageIntro title="Season Builder" subtitle="Read-only preflight foundation for future season creation workflows." />

      <SectionCard title="Read-only foundation notes">
        <ul className="dashboard-help-list">
          <li>This page does not build or modify calendars.</li>
          <li>Build from template is planned.</li>
          <li>Copy from another season is planned.</li>
          <li>Blank calendar creation is planned.</li>
          <li>Compare/apply workflow is planned.</li>
          <li>Actual build actions will require explicit audited backend commands in a later phase.</li>
        </ul>
      </SectionCard>

      <SectionCard title="Target season candidates">
        {registryQuery.isLoading ? <p className="status">Loading season registry…</p> : null}
        {registryQuery.error ? <p className="error">Failed to load season registry: {formatApiError(registryQuery.error)}</p> : null}
        {registry ? (
          <>
            <div className="dashboard-grid">
              <article className="metric-card"><span>First season</span><strong>{registry.start_season}</strong></article>
              <article className="metric-card"><span>Last season</span><strong>{registry.end_season}</strong></article>
              <article className="metric-card"><span>Season count</span><strong>{registry.season_count}</strong></article>
              <article className="metric-card"><span>Week count</span><strong>{registry.week_count}</strong></article>
            </div>
            <p>Example season targets:</p>
            <DetailList
              items={seasonExamples.map((season) => (
                <Link key={season.label} to={`/admin/seasons/detail/${encodeURIComponent(season.label)}`}>{season.label}</Link>
              ))}
              emptyLabel="No season examples available."
            />
          </>
        ) : null}
      </SectionCard>

      <SectionCard title="Available season templates">
        {templatesQuery.isLoading ? <p className="status">Loading season templates…</p> : null}
        {templatesQuery.error ? <p className="error">Failed to load season templates: {formatApiError(templatesQuery.error)}</p> : null}
        {templatesQuery.data ? (
          <>
            <ul className="dashboard-help-list">
              <li>Template count: {templates.length}</li>
              <li>Source path: {templatesQuery.data.source_path ?? '—'}</li>
            </ul>
            {templates.map((template) => (
              <article key={template.template_id} className="metric-card">
                <p><strong>{template.name}</strong></p>
                <p>Template ID: {template.template_id}</p>
                <p>Slot count: {template.slot_count}</p>
                <p>Week count: {template.week_count}</p>
                <p>Status: {template.status}</p>
                <p><Link to={`/admin/tour-seasons/season-templates/${template.template_id}`}>Open template detail</Link></p>
              </article>
            ))}
          </>
        ) : null}
      </SectionCard>

      <SectionCard title="Planned source types">
        <ul className="dashboard-help-list">
          <li>Blank calendar</li>
          <li>Season template</li>
          <li>Another concrete season</li>
          <li>Existing tournament copied into season</li>
          <li>Custom tournament slot</li>
        </ul>
      </SectionCard>

      <SectionCard title="Read-only preflight checklist">
        <p>Read-only preflight preview. Not an authoritative build gate.</p>
        <ul className="dashboard-help-list">
          <li><strong>Severity: {registry ? 'OK' : 'Warning'}</strong> — Registry loaded</li>
          <li><strong>Severity: {hasTemplates ? 'OK' : 'Warning'}</strong> — At least one season template available</li>
          <li><strong>Severity: {hasTemplates && allTemplatesWeek61 ? 'OK' : 'Info'}</strong> — Template week_count is 61</li>
          <li><strong>Severity: {hasTemplates && slotsWithinRange ? 'OK' : 'Info'}</strong> — Template slots are within SW1–SW61</li>
          <li><strong>Severity: {validationQuery.data ? 'Info' : validationQuery.error ? 'Warning' : 'Info'}</strong> — Backend validation foundation available</li>
        </ul>
      </SectionCard>

      <SectionCard title="Navigation">
        <p><Link to="/admin/seasons">Back to Seasons</Link></p>
        <p><Link to="/admin/tour-seasons/season-registry">Open Season Registry</Link></p>
        <p><Link to="/admin/tour-seasons/season-templates">Open Season Templates</Link></p>
        <p><Link to="/admin/tour-seasons/compare">Open Calendar Compare / Apply</Link></p>
        <p><Link to="/admin/tour-seasons/validation">Open Calendar Validation</Link></p>
      </SectionCard>
    </section>
  )
}
