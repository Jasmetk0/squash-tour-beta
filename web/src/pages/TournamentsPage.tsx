import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { Link } from 'react-router-dom'

import { getTournaments } from '../api/client'
import { PageIntro, SectionCard } from '../components/RunScopedUi'
import { formatApiError } from '../utils/apiErrors'

export function AdminTourSeasonsTournamentsPage(): JSX.Element {
  const tournamentsQuery = useQuery({ queryKey: ['tournaments'], queryFn: getTournaments, retry: false })
  const payload = tournamentsQuery.data
  const [search, setSearch] = useState('')
  const [tourLevel, setTourLevel] = useState('')
  const [category, setCategory] = useState('')
  const [sortBy, setSortBy] = useState<'source' | 'name'>('source')
  const tournaments = payload?.tournaments ?? []
  const tourLevels = Array.from(new Set(tournaments.flatMap(t => t.tour_levels))).sort()
  const categories = Array.from(new Set(tournaments.flatMap(t => t.categories))).sort()
  const needle = search.trim().toLocaleLowerCase()
  const visibleTournaments = tournaments.filter(t =>
    (!needle || `${t.name} ${t.tournament_id}`.toLocaleLowerCase().includes(needle)) &&
    (!tourLevel || t.tour_levels.includes(tourLevel)) &&
    (!category || t.categories.includes(category))
  )
  if (sortBy === 'name') {
    visibleTournaments.sort((a, b) => a.name.localeCompare(b.name) || a.tournament_id.localeCompare(b.tournament_id))
  }
  const clearFilters = () => { setSearch(''); setTourLevel(''); setCategory(''); setSortBy('source') }

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
      {payload ? <SectionCard title="Tournament master records">
        <div className="form-grid">
          <label>Search tournament name or ID
            <input type="search" value={search} onChange={event => setSearch(event.target.value)} />
          </label>
          <label>Filter tournament tour level
            <select value={tourLevel} onChange={event => setTourLevel(event.target.value)}>
              <option value="">All tour levels</option>
              {tourLevels.map(level => <option key={level} value={level}>{level}</option>)}
            </select>
          </label>
          <label>Filter tournament category
            <select value={category} onChange={event => setCategory(event.target.value)}>
              <option value="">All categories</option>
              {categories.map(value => <option key={value} value={value}>{value}</option>)}
            </select>
          </label>
          <label>Sort tournament records
            <select value={sortBy} onChange={event => setSortBy(event.target.value as typeof sortBy)}>
              <option value="source">Registry order</option>
              <option value="name">Name (A–Z)</option>
            </select>
          </label>
        </div>
        <button type="button" disabled={!search && !tourLevel && !category && sortBy === 'source'}
          onClick={clearFilters}>Clear tournament filters</button>
        <p role="status">Showing {visibleTournaments.length} of {tournaments.length} tournament records</p>
        {tournaments.length === 0 ? <p className="status">No tournament master records available.</p>
          : visibleTournaments.length === 0 ? <p className="status">No tournament records match the current filters.</p>
          : <div className="table-responsive"><table aria-label="Tournament master records table">
            <thead><tr><th>Tournament</th><th>Categories</th><th>Tour Levels</th><th>Host</th><th>Region</th><th>Default Duration</th><th>Qualification</th><th>Source Templates</th><th>Status</th></tr></thead>
            <tbody>{visibleTournaments.map(tournament => (
              <tr key={tournament.tournament_id}>
                <td><Link to={`/admin/tour-seasons/tournaments/${encodeURIComponent(tournament.tournament_id)}`}>{tournament.name} ({tournament.tournament_id})</Link></td>
                <td>{tournament.categories.join(', ')}</td>
                <td>{tournament.tour_levels.join(', ')}</td>
                <td>{tournament.default_host_country ?? 'mixed'}</td>
                <td>{tournament.default_region ?? 'mixed'}</td>
                <td>{tournament.default_duration_weeks ?? '—'}</td>
                <td>{qualificationLabel(tournament.has_qualification)}</td>
                <td>{tournament.source_template_ids.join(', ')}</td>
                <td>{tournament.status}</td>
              </tr>
            ))}</tbody>
          </table></div>}
        {visibleTournaments.map(tournament => tournament.notes.length
          ? <p key={`${tournament.tournament_id}-notes`}>{tournament.name} notes: {tournament.notes.join('; ')}</p>
          : null)}
        <p>Tournament master editor — planned.</p>
        <p>Tournament editions — planned.</p>
      </SectionCard> : null}
      <SectionCard title="Navigation"><p><Link to="/admin/tournament-templates">Open Tournament Templates</Link></p><p><Link to="/admin/tour-seasons/categories">Open Categories</Link></p><p><Link to="/admin/tour-seasons/season-templates">Open Season Templates</Link></p><p><Link to="/admin/tour-seasons">Back to Tour &amp; Seasons</Link></p></SectionCard>
    </section>
  )
}
