import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'

import { getSeasonRegistry } from '../api/client'
import { PageIntro, SectionCard } from '../components/RunScopedUi'
import { formatApiError } from '../utils/apiErrors'

const WEEKS_PER_SEASON = 61
const WEEKS_PER_YEAR = 61
const SEASON_WEEK_1_YEAR_WEEK = 37

function seasonWeekToYearWeek(seasonWeek: number): number {
  return ((SEASON_WEEK_1_YEAR_WEEK - 1 + (seasonWeek - 1)) % WEEKS_PER_YEAR) + 1
}

export function AdminTourSeasonsSeasonRegistryPage(): JSX.Element {
  const registryQuery = useQuery({ queryKey: ['season-registry'], queryFn: getSeasonRegistry, retry: false })
  const registry = registryQuery.data

  return (
    <section className="panel">
      <PageIntro
        title="Season Registry"
        subtitle="Read-only deterministic registry for the fixed 2000/01–2049/50 MSA season model."
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

      <SectionCard title="Canonical calendar foundation">
        <p>Canonical seasons are the real 50-season MSA timeline from 2000/01 through 2049/50. Admin-only calendar templates will be created separately and can later be copied into these seasons. Template changes will not automatically mutate canonical seasons.</p>
        <p>Calendar events will use weeks and qualificationWeeks. Qualification belongs to the main event. Locked events must be explicitly unlocked before move/delete/overwrite actions.</p>
        <ul className="dashboard-help-list">
          <li>Registry is read-only.</li>
          <li>Every canonical season has exactly {WEEKS_PER_SEASON} Season Weeks.</li>
          <li>Season Week 1 = Year Week {SEASON_WEEK_1_YEAR_WEEK}.</li>
          <li>This is the simplified engine model.</li>
          <li>Compact label YYYY/YY is canonical for registry.</li>
          <li>Legacy YYYY/YYYY labels are still accepted at selected API boundaries during migration.</li>
          <li>Admin calendar editor: planned.</li>
        </ul>
      </SectionCard>

      <SectionCard title="Mapping examples">
        {registry ? (
          <ul className="dashboard-help-list">
            <li>SW1 → YW{seasonWeekToYearWeek(1)}</li>
            <li>SW25 → YW{seasonWeekToYearWeek(25)}</li>
            <li>SW26 → YW{seasonWeekToYearWeek(26)}</li>
            <li>SW61 → YW{seasonWeekToYearWeek(61)}</li>
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
        <p className="status">Season links open the read-only Concrete Season detail profile. Direct season editing workflow is planned.</p>
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
                  <th>Registry status</th>
                  <th>Calendar status</th>
                  <th>Calendar planning</th>
                  <th>Future actions</th>
                </tr>
              </thead>
              <tbody>
                {registry.seasons.map((entry) => (
                  <tr key={entry.label}>
                    <td><Link to={`/admin/seasons/detail/${encodeURIComponent(entry.label)}`}>{entry.label}</Link></td>
                    <td>{entry.season_index}</td>
                    <td>{entry.season_start_year}</td>
                    <td>{entry.week_count}</td>
                    <td>SW{entry.season_week_start}–SW{entry.season_week_end}</td>
                    <td>YW{entry.year_week_start}</td>
                    <td>YW{entry.year_week_end}</td>
                    <td>{entry.status}</td>
                    <td>Calendar status: existing read model unavailable / not loaded</td>
                    <td>Canonical season · {WEEKS_PER_SEASON} Season Weeks · Admin calendar editor: planned</td>
                    <td>
                      <span>Open calendar — planned</span>{' · '}
                      <span>Copy from template — planned</span>{' · '}
                      <span>Save as template — planned</span>{' · '}
                      <span>Compare/copy workspace — planned</span>
                    </td>
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
