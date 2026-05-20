import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'

import { getTournaments } from '../api/client'
import { PageIntro, SectionCard } from '../components/RunScopedUi'
import { formatApiError } from '../utils/apiErrors'

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
      {payload ? <SectionCard title="Tournament master records"><table><thead><tr><th>Tournament</th><th>Categories</th><th>Tour Levels</th><th>Host</th><th>Region</th><th>Default Duration</th><th>Qualification</th><th>Source Templates</th><th>Status</th></tr></thead><tbody>{payload.tournaments.map((tournament) => (<tr key={tournament.tournament_id}><td><Link to={`/admin/tour-seasons/tournaments/${tournament.tournament_id}`}>{tournament.name} ({tournament.tournament_id})</Link></td><td>{tournament.categories.join(', ')}</td><td>{tournament.tour_levels.join(', ')}</td><td>{tournament.default_host_country ?? 'mixed'}</td><td>{tournament.default_region ?? 'mixed'}</td><td>{tournament.default_duration_weeks ?? '—'}</td><td>{tournament.has_qualification === null ? qualificationLabel(tournament.has_qualification) : qualificationLabel(tournament.has_qualification)}</td><td>{tournament.source_template_ids.join(', ')}</td><td>{tournament.status}</td></tr>))}</tbody></table>{payload.tournaments.map((tournament) => tournament.notes.length ? <p key={`${tournament.tournament_id}-notes`}>{tournament.name} notes: {tournament.notes.join('; ')}</p> : null)}<p>Tournament master editor — planned.</p><p>Tournament editions — planned.</p></SectionCard> : null}
      <SectionCard title="Navigation"><p><Link to="/admin/tournament-templates">Open Tournament Templates</Link></p><p><Link to="/admin/tour-seasons/categories">Open Categories</Link></p><p><Link to="/admin/tour-seasons/season-templates">Open Season Templates</Link></p><p><Link to="/admin/tour-seasons">Back to Tour &amp; Seasons</Link></p></SectionCard>
    </section>
  )
}
