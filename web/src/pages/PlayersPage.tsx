import { useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useParams } from 'react-router-dom'

import { getRunPlayerDetail, listRunPlayers } from '../api/client'
import { CurrentContextStrip, PageIntro, SectionCard } from '../components/RunScopedUi'

const SOURCE_OPTIONS = ['', 'rollover_carried', 'planner_generated', 'manual_override']

export function PlayersPage(): JSX.Element {
  const { runId = '' } = useParams()
  const [search, setSearch] = useState('')
  const [countryCode, setCountryCode] = useState('')
  const [sourceType, setSourceType] = useState('')
  const [minAge, setMinAge] = useState('')
  const [maxAge, setMaxAge] = useState('')
  const [selectedPlayerId, setSelectedPlayerId] = useState<string | null>(null)

  const queryParams = useMemo(
    () => ({
      search: search.trim() || undefined,
      country_code: countryCode.trim().toUpperCase() || undefined,
      source_type: sourceType || undefined,
      min_age: minAge ? Number(minAge) : undefined,
      max_age: maxAge ? Number(maxAge) : undefined,
      limit: 200,
      offset: 0,
      sort: 'overall_desc'
    }),
    [search, countryCode, sourceType, minAge, maxAge]
  )

  const playersQuery = useQuery({
    queryKey: ['run-players', runId, queryParams],
    queryFn: () => listRunPlayers(runId, queryParams),
    enabled: Boolean(runId)
  })

  const detailQuery = useQuery({
    queryKey: ['run-player-detail', runId, selectedPlayerId],
    queryFn: () => getRunPlayerDetail(runId, selectedPlayerId ?? ''),
    enabled: Boolean(runId && selectedPlayerId)
  })

  return (
    <section className="panel">
      <PageIntro title="Run Players Explorer" subtitle="Read-only player pool explorer for the selected run." />
      <CurrentContextStrip
        items={[
          { label: 'Run', value: runId || 'unknown' },
          { label: 'Visible rows', value: playersQuery.data?.players.length ?? '—' },
          { label: 'Total filtered', value: playersQuery.data?.total ?? '—' }
        ]}
      />
      <SectionCard title="Filters">
        <div className="form-grid">
          <label>
            Search (name / ID)
            <input value={search} onChange={(event) => setSearch(event.target.value)} />
          </label>
          <label>
            Country code
            <input value={countryCode} onChange={(event) => setCountryCode(event.target.value)} maxLength={3} />
          </label>
          <label>
            Source type
            <select value={sourceType} onChange={(event) => setSourceType(event.target.value)}>
              {SOURCE_OPTIONS.map((value) => (
                <option key={value} value={value}>
                  {value || 'all'}
                </option>
              ))}
            </select>
          </label>
          <label>
            Min age
            <input type="number" value={minAge} onChange={(event) => setMinAge(event.target.value)} min={15} max={60} />
          </label>
          <label>
            Max age
            <input type="number" value={maxAge} onChange={(event) => setMaxAge(event.target.value)} min={15} max={60} />
          </label>
        </div>
      </SectionCard>
      <SectionCard title="Players">
        {playersQuery.isLoading ? <p className="status">Loading players…</p> : null}
        {playersQuery.error ? <p className="error">Failed to load players: {String(playersQuery.error)}</p> : null}
        {!playersQuery.isLoading && !playersQuery.error && playersQuery.data ? (
          <table>
            <thead>
              <tr>
                <th>Player ID</th>
                <th>Name</th>
                <th>Country</th>
                <th>Age</th>
                <th>Source</th>
                <th>Band</th>
                <th>Technique</th>
                <th>Movement</th>
                <th>Physical</th>
                <th>Mental</th>
              </tr>
            </thead>
            <tbody>
              {playersQuery.data.players.map((player) => (
                <tr key={player.player_id}>
                  <td>
                    <button type="button" onClick={() => setSelectedPlayerId(player.player_id)}>
                      {player.player_id}
                    </button>
                  </td>
                  <td>{player.name}</td>
                  <td>{player.country_code}</td>
                  <td>{player.age}</td>
                  <td>{player.source_type}</td>
                  <td>{player.quality_band ?? '—'}</td>
                  <td>{player.technique}</td>
                  <td>{player.movement}</td>
                  <td>{player.physical}</td>
                  <td>{player.mental}</td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : null}
      </SectionCard>
      <SectionCard title="Player detail">
        {!selectedPlayerId ? <p className="status">Select a player from the table to inspect detail.</p> : null}
        {selectedPlayerId && detailQuery.isLoading ? <p className="status">Loading player detail…</p> : null}
        {selectedPlayerId && detailQuery.error ? <p className="error">Failed to load detail: {String(detailQuery.error)}</p> : null}
        {selectedPlayerId && detailQuery.data ? (
          <>
            <p>
              <strong>{detailQuery.data.name}</strong> ({detailQuery.data.player_id}) • {detailQuery.data.country_code} • age{' '}
              {detailQuery.data.age}
            </p>
            <p>
              Source: {detailQuery.data.source_type} | Band: {detailQuery.data.quality_band ?? '—'} | Top band:{' '}
              {detailQuery.data.is_top_band ? 'yes' : 'no'} | Override: {detailQuery.data.override_id ?? '—'}
            </p>
            <p>
              Style: {detailQuery.data.play_style} / {detailQuery.data.archetype}
            </p>
            <pre className="json-block">{JSON.stringify(detailQuery.data, null, 2)}</pre>
          </>
        ) : null}
      </SectionCard>
    </section>
  )
}
