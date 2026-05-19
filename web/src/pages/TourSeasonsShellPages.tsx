import { type ReactNode } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'

import { getSeasonRegistry } from '../api/client'
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
  const registryQuery = useQuery({ queryKey: ['season-registry'], queryFn: getSeasonRegistry, retry: false })
  const registry = registryQuery.data
  return (
    <TourSeasonsShellPage title="Season Templates" subtitle="Reusable calendar plans that can be copied into concrete seasons.">
      <p>
        Season creation is planned to support: blank calendar, season template, another season, tournament copied from anywhere,
        or blank custom tournament.
      </p>
      <p>
        Current operational calendar tooling remains in <Link to="/admin/seasons">Seasons</Link>.
      </p>
      <SectionCard title="Season Registry (Read-only foundation)">
        {registryQuery.isLoading ? <p className="status">Loading season registry...</p> : null}
        {registryQuery.error ? <p className="error">Failed to load season registry: {formatApiError(registryQuery.error)}</p> : null}
        {registry ? (
          <>
            <p>
              Season range {registry.start_season}–{registry.end_season} · {registry.season_count} seasons · {registry.week_count} weeks per season · SW1 = YW{registry.season_week_1_year_week}
            </p>
            <table>
              <thead>
                <tr>
                  <th>Season</th><th>Index</th><th>Weeks</th><th>SW1 Year Week</th><th>Status</th>
                </tr>
              </thead>
              <tbody>
                {registry.seasons.map((entry) => (
                  <tr key={entry.label}>
                    <td>{entry.label}</td><td>{entry.season_index}</td><td>{entry.week_count}</td><td>{entry.year_week_start}</td><td>{entry.status}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </>
        ) : null}
      </SectionCard>
    </TourSeasonsShellPage>
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
