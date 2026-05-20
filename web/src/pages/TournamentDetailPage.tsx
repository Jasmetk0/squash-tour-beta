import { useQuery } from '@tanstack/react-query'
import { Link, useParams } from 'react-router-dom'

import { getTournaments } from '../api/client'
import { DetailFieldGrid, DetailList } from '../components/DetailUi'
import { PageIntro, SectionCard } from '../components/RunScopedUi'
import { formatApiError } from '../utils/apiErrors'

function qualificationLabel(value: boolean | null): string {
  if (value === true) return 'Yes'
  if (value === false) return 'No'
  return 'Mixed'
}

function formatList(values: string[]): string {
  return values.length > 0 ? values.join(', ') : '—'
}

export function AdminTourSeasonsTournamentDetailPage(): JSX.Element {
  const { tournamentId = '' } = useParams()
  const tournamentsQuery = useQuery({ queryKey: ['tournaments'], queryFn: getTournaments, retry: false })
  const payload = tournamentsQuery.data
  const tournament = payload?.tournaments.find((item) => item.tournament_id === tournamentId)

  return (
    <section className="panel">
      <PageIntro
        title="Tournament Master"
        subtitle="Read-only tournament brand profile derived from current tournament template config."
      />

      {tournamentsQuery.isLoading ? <p className="status">Loading tournament master…</p> : null}
      {tournamentsQuery.error ? <p className="error">Failed to load tournament master: {formatApiError(tournamentsQuery.error)}</p> : null}
      {payload && !tournament ? <p className="status">Tournament master not found.</p> : null}

      {tournament ? (
        <>
          <SectionCard title="Header summary">
            <DetailFieldGrid fields={[
              { label: 'Name', value: tournament.name },
              { label: 'Tournament ID', value: tournament.tournament_id },
              { label: 'Status', value: tournament.status },
              { label: 'Source', value: tournament.source }
            ]} />
          </SectionCard>

          <SectionCard title="Identity">
            <DetailFieldGrid fields={[
              { label: 'name', value: tournament.name },
              { label: 'tournament_id', value: tournament.tournament_id },
              { label: 'template_count', value: tournament.template_count },
              { label: 'source_template_ids', value: formatList(tournament.source_template_ids) },
              { label: 'status', value: tournament.status }
            ]} />
          </SectionCard>

          <SectionCard title="Classification">
            <ul className="dashboard-help-list">
              <li>categories: {formatList(tournament.categories)}</li>
              <li>tour levels: {formatList(tournament.tour_levels)}</li>
              <li>default category: {tournament.default_category ?? 'mixed'}</li>
              <li>default duration weeks: {tournament.default_duration_weeks ?? 'mixed'}</li>
            </ul>
          </SectionCard>

          <SectionCard title="Geography">
            <ul className="dashboard-help-list">
              <li>host countries: {formatList(tournament.host_countries)}</li>
              <li>regions: {formatList(tournament.regions)}</li>
              <li>default host country: {tournament.default_host_country ?? 'mixed'}</li>
              <li>default region: {tournament.default_region ?? 'mixed'}</li>
            </ul>
          </SectionCard>

          <SectionCard title="Qualification">
            <p>has qualification: {qualificationLabel(tournament.has_qualification)}</p>
          </SectionCard>

          <SectionCard title="Notes">
            <DetailList items={tournament.notes} emptyLabel="No notes." />
          </SectionCard>

          <SectionCard title="Planned future model">
            <ul className="dashboard-help-list">
              <li>Tournament master editor — planned.</li>
              <li>Tournament editions — planned.</li>
              <li>Concrete edition example: {tournament.name} 2030/31.</li>
              <li>Entries, draw, results, champion, points awarded belong to editions, not the master record.</li>
            </ul>
          </SectionCard>
        </>
      ) : null}

      <SectionCard title="Navigation">
        <p><Link to="/admin/tour-seasons/tournaments">Back to Tournaments</Link></p>
        <p><Link to="/admin/tournament-templates">Open Tournament Templates</Link></p>
        <p><Link to="/admin/tour-seasons/categories">Open Categories</Link></p>
        <p><Link to="/admin/tour-seasons/season-templates">Open Season Templates</Link></p>
      </SectionCard>
    </section>
  )
}
