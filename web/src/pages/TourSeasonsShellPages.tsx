import { type ReactNode } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'

import { getCategories, getSeasonTemplates, getTournaments } from '../api/client'
import { PageIntro, SectionCard } from '../components/RunScopedUi'
import { formatApiError } from '../utils/apiErrors'

function TourSeasonsShellPage({
  title,
  subtitle,
  children
}: {
  title: string
  subtitle: string
  children: ReactNode
}): JSX.Element {
  return (
    <section className="panel">
      <PageIntro title={title} subtitle={subtitle} />
      <SectionCard title="Planned model">{children}</SectionCard>
      <SectionCard title="Current tooling">
        <p>
          This page is a transitional shell. Continue operational editing in{' '}
          <Link to="/admin/tournament-templates">Tournament Templates</Link> and{' '}
          <Link to="/admin/seasons">Seasons</Link>.
        </p>
        <p>
          Return to the <Link to="/admin/tour-seasons">Tour &amp; Seasons hub</Link>.
        </p>
      </SectionCard>
    </section>
  )
}

export function AdminTourSeasonsCategoriesPage(): JSX.Element {
  const categoriesQuery = useQuery({ queryKey: ['categories'], queryFn: getCategories, retry: false })
  const payload = categoriesQuery.data

  return (
    <section className="panel">
      <PageIntro title="Categories" subtitle="Read-only category rules packages derived from current tournament template config." />
      <SectionCard title="Read-only foundation notes">
        <ul className="dashboard-help-list">
          <li>Read-only foundation.</li>
          <li>Full category editor/versioning is planned.</li>
          <li>Existing operational tooling remains in <Link to="/admin/tournament-templates">/admin/tournament-templates</Link>.</li>
          <li>Category values may be null when source templates contain mixed values.</li>
        </ul>
      </SectionCard>
      <SectionCard title="Summary">
        {categoriesQuery.isLoading ? <p className="status">Loading categories…</p> : null}
        {categoriesQuery.error ? <p className="error">Failed to load categories: {formatApiError(categoriesQuery.error)}</p> : null}
        {payload ? <ul className="dashboard-help-list"><li>Categories: {payload.categories.length}</li><li>Source path: {payload.source_path ?? '—'}</li><li>Status: {payload.status}</li></ul> : null}
      </SectionCard>
      {payload ? (
        <SectionCard title="Category rules packages">
          <table>
            <thead><tr><th>Category</th><th>Templates</th><th>Main Draw</th><th>Qualifying Draw</th><th>Footprint</th><th>Mandatory</th><th>Source Templates</th><th>Status</th></tr></thead>
            <tbody>
              {payload.categories.map((category) => (
                <tr key={category.category_id}>
                  <td>{category.name} ({category.category_id})</td><td>{category.template_count}</td><td>{category.main_draw_size ?? '—'}</td><td>{category.qualification_draw_size ?? '—'}</td><td>{category.schedule_footprint_weeks ?? '—'}</td><td>{category.mandatory === null ? '—' : category.mandatory ? 'Yes' : 'No'}</td><td>{category.source_template_ids.join(', ')}</td><td>{category.status}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {payload.categories.map((category) => category.notes.length ? <p key={`${category.category_id}-notes`}>{category.name} notes: {category.notes.join('; ')}</p> : null)}
          <p>Category editor — planned.</p>
        </SectionCard>
      ) : null}
      <SectionCard title="Navigation">
        <p><Link to="/admin/tournament-templates">Open Tournament Templates</Link></p>
        <p><Link to="/admin/tour-seasons/season-templates">Open Season Templates</Link></p>
        <p><Link to="/admin/tour-seasons">Back to Tour &amp; Seasons</Link></p>
      </SectionCard>
    </section>
  )
}

export function AdminTourSeasonsTournamentsPage(): JSX.Element {
  const tournamentsQuery = useQuery({ queryKey: ['tournaments'], queryFn: getTournaments, retry: false })
  const payload = tournamentsQuery.data

  const qualificationLabel = (value: boolean | null): string => {
    if (value === true) return 'Yes'
    if (value === false) return 'No'
    return 'Mixed'
  }

  return (
    <section className="panel">
      <PageIntro title="Tournaments" subtitle="Read-only tournament master records derived from current tournament template config." />
      <SectionCard title="Read-only foundation notes">
        <ul className="dashboard-help-list">
          <li>Read-only foundation.</li>
          <li>Full tournament master editor is planned.</li>
          <li>Tournament editions are planned separately.</li>
          <li>Existing operational tooling remains in <Link to="/admin/tournament-templates">/admin/tournament-templates</Link>.</li>
          <li>Values may be null when source templates contain mixed values.</li>
        </ul>
      </SectionCard>
      <SectionCard title="Summary">
        {tournamentsQuery.isLoading ? <p className="status">Loading tournaments…</p> : null}
        {tournamentsQuery.error ? <p className="error">Failed to load tournaments: {formatApiError(tournamentsQuery.error)}</p> : null}
        {payload ? <ul className="dashboard-help-list"><li>Tournaments: {payload.tournaments.length}</li><li>Source path: {payload.source_path ?? '—'}</li><li>Status: {payload.status}</li></ul> : null}
      </SectionCard>
      {payload ? <SectionCard title="Tournament master records"><table><thead><tr><th>Tournament</th><th>Categories</th><th>Tour Levels</th><th>Host</th><th>Region</th><th>Default Duration</th><th>Qualification</th><th>Source Templates</th><th>Status</th></tr></thead><tbody>{payload.tournaments.map((tournament) => (<tr key={tournament.tournament_id}><td>{tournament.name} ({tournament.tournament_id})</td><td>{tournament.categories.join(', ')}</td><td>{tournament.tour_levels.join(', ')}</td><td>{tournament.default_host_country ?? 'mixed'}</td><td>{tournament.default_region ?? 'mixed'}</td><td>{tournament.default_duration_weeks ?? '—'}</td><td>{tournament.has_qualification === null ? qualificationLabel(tournament.has_qualification) : qualificationLabel(tournament.has_qualification)}</td><td>{tournament.source_template_ids.join(', ')}</td><td>{tournament.status}</td></tr>))}</tbody></table>{payload.tournaments.map((tournament) => tournament.notes.length ? <p key={`${tournament.tournament_id}-notes`}>{tournament.name} notes: {tournament.notes.join('; ')}</p> : null)}<p>Tournament master editor — planned.</p><p>Tournament editions — planned.</p></SectionCard> : null}
      <SectionCard title="Navigation"><p><Link to="/admin/tournament-templates">Open Tournament Templates</Link></p><p><Link to="/admin/tour-seasons/categories">Open Categories</Link></p><p><Link to="/admin/tour-seasons/season-templates">Open Season Templates</Link></p><p><Link to="/admin/tour-seasons">Back to Tour &amp; Seasons</Link></p></SectionCard>
    </section>
  )
}

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
        <SectionCard key={template.template_id} title={template.name}>
          <ul className="dashboard-help-list">
            <li>Template ID: {template.template_id}</li><li>Slot count: {template.slot_count}</li><li>Week count: {template.week_count}</li><li>Status: {template.status}</li><li>Description: {template.description}</li><li>Apply to Season — planned</li>
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

export function AdminTourSeasonsComparePage(): JSX.Element {
  return (
    <TourSeasonsShellPage title="Calendar Compare / Apply" subtitle="Compare a current season with a template or another season.">
      <p>Planned statuses: Same, Modified, Missing from current, Only in current, and Conflict.</p>
      <p>Planned actions: Apply to this season, Replace current, Keep current, Ignore, and Open editor.</p>
      <p>
        Current operational calendar editing remains in <Link to="/admin/seasons">Seasons</Link>.
      </p>
    </TourSeasonsShellPage>
  )
}

export function AdminTourSeasonsValidationPage(): JSX.Element {
  return (
    <TourSeasonsShellPage title="Calendar Validation" subtitle="Validation hub for deterministic season schedule safety checks.">
      <ul className="dashboard-help-list">
        <li>W01–W61 range</li>
        <li>Multi-week blocks must be consecutive</li>
        <li>Qualifying must be before main draw</li>
        <li>Diamond: 1 qualifying week + 2 main draw weeks (if applicable)</li>
        <li>Mandatory events present</li>
        <li>Schedule conflicts</li>
        <li>Invalid or missing category or host</li>
      </ul>
      <p>
        For current workflows, use <Link to="/admin/seasons">Seasons</Link> and{' '}
        <Link to="/admin/diagnostics">Diagnostics</Link>.
      </p>
    </TourSeasonsShellPage>
  )
}
