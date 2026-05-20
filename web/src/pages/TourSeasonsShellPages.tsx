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
  return (
    <TourSeasonsShellPage title="Season Templates" subtitle="Reusable calendar plans that can be copied into concrete seasons.">
      <p>
        Season creation is planned to support: blank calendar, season template, another season, tournament copied from anywhere,
        or blank custom tournament.
      </p>
      <p>
        Current operational calendar tooling remains in <Link to="/admin/seasons">Seasons</Link>.
      </p>
      <SectionCard title="Season Registry">
        <p>Season Registry has moved to its own read-only page.</p>
        <p>
          Open <Link to="/admin/tour-seasons/season-registry">Season Registry</Link> for the fixed 2000/01–2039/40 mapping,
          summary metrics, and full registry table.
        </p>
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


function seasonWeekToYearWeek(seasonWeek: number, seasonWeek1YearWeek: number): number {
  return ((seasonWeek1YearWeek - 1 + (seasonWeek - 1)) % 61) + 1
}

export function AdminTourSeasonsSeasonRegistryPage(): JSX.Element {
  const registryQuery = useQuery({ queryKey: ['season-registry'], queryFn: getSeasonRegistry, retry: false })
  const registry = registryQuery.data

  return (
    <section className="panel">
      <PageIntro
        title="Season Registry"
        subtitle="Read-only deterministic registry for the fixed 2000/01–2039/40 MSA season model."
      />

      <SectionCard title="Registry summary">
        {registryQuery.isLoading ? <p className="status">Loading season registry…</p> : null}
        {registryQuery.error ? <p className="error">Failed to load season registry: {formatApiError(registryQuery.error)}</p> : null}
        {registry ? (
          <div className="dashboard-grid">
            <article className="metric-card"><span>Start season</span><strong>{registry.start_season}</strong></article>
            <article className="metric-card"><span>End season</span><strong>{registry.end_season}</strong></article>
            <article className="metric-card"><span>Season count</span><strong>{registry.season_count}</strong></article>
            <article className="metric-card"><span>Weeks per season</span><strong>{registry.week_count}</strong></article>
            <article className="metric-card"><span>Season Week 1 maps to Year Week</span><strong>{registry.season_week_1_year_week}</strong></article>
          </div>
        ) : null}
      </SectionCard>

      <SectionCard title="Model notes">
        <ul className="dashboard-help-list">
          <li>Registry is read-only.</li>
          <li>Every season has exactly 61 weeks.</li>
          <li>Season Week 1 = Year Week 37.</li>
          <li>This is the simplified engine model.</li>
          <li>Compact label YYYY/YY is canonical for registry.</li>
          <li>Legacy YYYY/YYYY labels are still accepted at selected API boundaries during migration.</li>
        </ul>
      </SectionCard>

      <SectionCard title="Mapping examples">
        {registry ? (
          <ul className="dashboard-help-list">
            <li>SW1 → YW{seasonWeekToYearWeek(1, registry.season_week_1_year_week)}</li>
            <li>SW25 → YW{seasonWeekToYearWeek(25, registry.season_week_1_year_week)}</li>
            <li>SW26 → YW{seasonWeekToYearWeek(26, registry.season_week_1_year_week)}</li>
            <li>SW61 → YW{seasonWeekToYearWeek(61, registry.season_week_1_year_week)}</li>
          </ul>
        ) : (
          <ul className="dashboard-help-list">
            <li>SW1 → YW37</li>
            <li>SW25 → YW61</li>
            <li>SW26 → YW1</li>
            <li>SW61 → YW36</li>
          </ul>
        )}
      </SectionCard>

      <SectionCard title="Registry table">
        {registry ? (
          registry.seasons.length ? (
            <table>
              <thead>
                <tr>
                  <th>Season</th>
                  <th>Index</th>
                  <th>Start Year</th>
                  <th>Weeks</th>
                  <th>Season Week Range</th>
                  <th>Year Week Start</th>
                  <th>Year Week End</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {registry.seasons.map((entry) => (
                  <tr key={entry.label}>
                    <td>{entry.label}</td>
                    <td>{entry.season_index}</td>
                    <td>{entry.season_start_year}</td>
                    <td>{entry.week_count}</td>
                    <td>SW{entry.season_week_start}–SW{entry.season_week_end}</td>
                    <td>YW{entry.year_week_start}</td>
                    <td>YW{entry.year_week_end}</td>
                    <td>{entry.status}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <p className="status">No season registry entries available.</p>
          )
        ) : null}
      </SectionCard>

      <SectionCard title="Navigation">
        <p>
          <Link to="/admin/tour-seasons">Back to Tour &amp; Seasons</Link>
        </p>
        <p>
          <Link to="/admin/seasons">Open Seasons</Link>
        </p>
        <p>
          <Link to="/admin/tour-seasons/season-templates">Open Season Templates</Link>
        </p>
      </SectionCard>
    </section>
  )
}
