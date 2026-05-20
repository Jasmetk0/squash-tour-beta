import { type ReactNode } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'

import { getSeasonTemplates } from '../api/client'
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
  return (
    <TourSeasonsShellPage title="Categories" subtitle="Category = rules package valid for a season range.">
      <p>Examples: Diamond 2000/01–2015/16 and Diamond 2016/17–2039/40.</p>
      <p>
        Planned category fields: category name, valid season range, tour level, prestige rank, mandatory flag, main draw size,
        qualification draw size, direct entries, qualifiers, wildcards, lucky losers, seeds count, points by round, prize money,
        match format, entry rules, qualification rules, and schedule footprint.
      </p>
      <p>
        Transitional: currently managed through <Link to="/admin/tournament-templates">Tournament Templates tooling</Link>.
      </p>
    </TourSeasonsShellPage>
  )
}

export function AdminTourSeasonsTournamentsPage(): JSX.Element {
  return (
    <TourSeasonsShellPage title="Tournaments" subtitle="Tournament = reusable master tournament brand.">
      <p>Examples: Némarque Open, Ameriga Open, Bogemia Gold, and World Championship.</p>
      <p>
        Concrete season edition example: Némarque Open 2030/31. Entries, draw, results, champion, and points awarded belong to
        the edition, not the master tournament.
      </p>
      <p>
        Planned split from category/template tooling. Use <Link to="/admin/tournament-templates">Tournament Templates</Link> for
        current operations.
      </p>
    </TourSeasonsShellPage>
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
