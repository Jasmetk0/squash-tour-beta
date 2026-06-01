import { useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link, useParams, useSearchParams } from 'react-router-dom'

import {
  getRunNationDetail,
  getRunPlayerCareerHistory,
  getRunPlayerCareerPerformance,
  getRunPlayerDetail,
  getRunPlayerTournamentResults,
  listRunNations,
  listRunPlayers
} from '../api/client'
import { CurrentContextStrip, MetadataList, PageIntro, SectionCard } from '../components/RunScopedUi'

const PLAYER_SOURCE_OPTIONS = ['', 'rollover_carried', 'planner_generated', 'manual_override']
const COUNTRY_SORT_OPTIONS = ['total_players_desc', 'avg_overall_desc', 'avg_age_asc', 'country_code_asc']

function displayMetric(value: number | null | undefined): string | number {
  return value ?? '—'
}

function displayFixed(value: number | null | undefined): string {
  return typeof value === 'number' ? value.toFixed(2) : '—'
}

export function ViewerRunPlayersPage(): JSX.Element {
  const { runId = '' } = useParams()
  const [searchParams] = useSearchParams()
  const [search, setSearch] = useState('')
  const [countryCode, setCountryCode] = useState(() => searchParams.get('country') ?? '')
  const [sourceType, setSourceType] = useState('')
  const [minAge, setMinAge] = useState('')
  const [maxAge, setMaxAge] = useState('')

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
    queryKey: ['viewer-run-players', runId, queryParams],
    queryFn: () => listRunPlayers(runId, queryParams),
    enabled: Boolean(runId)
  })

  return (
    <section className="panel">
      <PageIntro title="Players" subtitle="Read-only player pool for the selected run." />
      <CurrentContextStrip
        items={[
          { label: 'Active run ID', value: runId || 'unknown' },
          { label: 'Total player count', value: playersQuery.data?.total ?? '—' },
          { label: 'Visible players', value: playersQuery.data?.players.length ?? '—' }
        ]}
      />

      <SectionCard title="Player filters">
        <div className="form-grid">
          <label>
            Search
            <input value={search} onChange={(event) => setSearch(event.target.value)} />
          </label>
          <label>
            Country
            <input value={countryCode} onChange={(event) => setCountryCode(event.target.value)} maxLength={3} />
          </label>
          <label>
            Source type
            <select value={sourceType} onChange={(event) => setSourceType(event.target.value)}>
              {PLAYER_SOURCE_OPTIONS.map((value) => (
                <option key={value} value={value}>
                  {value || 'all'}
                </option>
              ))}
            </select>
          </label>
          <label>
            Age min
            <input type="number" value={minAge} onChange={(event) => setMinAge(event.target.value)} min={15} max={60} />
          </label>
          <label>
            Age max
            <input type="number" value={maxAge} onChange={(event) => setMaxAge(event.target.value)} min={15} max={60} />
          </label>
        </div>
      </SectionCard>

      <SectionCard title="Player pool">
        {playersQuery.isLoading ? <p className="status">Loading players…</p> : null}
        {playersQuery.error ? <p className="error">Failed to load players: {String(playersQuery.error)}</p> : null}
        {!playersQuery.isLoading && !playersQuery.error && playersQuery.data ? (
          playersQuery.data.players.length > 0 ? (
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
                  <th>Profile</th>
                </tr>
              </thead>
              <tbody>
                {playersQuery.data.players.map((player) => (
                  <tr key={player.player_id}>
                    <td>{player.player_id}</td>
                    <td>{player.name}</td>
                    <td>{player.country_code}</td>
                    <td>{player.age}</td>
                    <td>{player.source_type}</td>
                    <td>{player.quality_band ?? '—'}</td>
                    <td>{player.technique}</td>
                    <td>{player.movement}</td>
                    <td>{player.physical}</td>
                    <td>{player.mental}</td>
                    <td>
                      <Link to={`/viewer/runs/${runId}/players/${player.player_id}/career`}>Open player career/profile</Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <p className="status">No players matched the selected read-only filters.</p>
          )
        ) : null}
      </SectionCard>
    </section>
  )
}

export function ViewerRunPlayerCareerPage(): JSX.Element {
  const { runId = '', playerId = '' } = useParams()

  const detailQuery = useQuery({
    queryKey: ['viewer-run-player-detail', runId, playerId],
    queryFn: () => getRunPlayerDetail(runId, playerId),
    enabled: Boolean(runId && playerId)
  })
  const careerQuery = useQuery({
    queryKey: ['viewer-player-career-history', runId, playerId],
    queryFn: () => getRunPlayerCareerHistory(runId, playerId),
    enabled: Boolean(runId && playerId)
  })
  const performanceQuery = useQuery({
    queryKey: ['viewer-player-career-performance', runId, playerId],
    queryFn: () => getRunPlayerCareerPerformance(runId, playerId),
    enabled: Boolean(runId && playerId)
  })
  const tournamentResultsQuery = useQuery({
    queryKey: ['viewer-player-career-results', runId, playerId],
    queryFn: () => getRunPlayerTournamentResults(runId, playerId),
    enabled: Boolean(runId && playerId)
  })

  const latestCareerEntry = careerQuery.data?.entries.length ? careerQuery.data.entries[careerQuery.data.entries.length - 1] : null
  const name = detailQuery.data?.name ?? careerQuery.data?.player_name ?? performanceQuery.data?.player_name ?? tournamentResultsQuery.data?.player_name ?? null
  const countryCode = detailQuery.data?.country_code ?? careerQuery.data?.country_code ?? performanceQuery.data?.country_code ?? tournamentResultsQuery.data?.country_code ?? null

  return (
    <section className="panel">
      <PageIntro title="Player Profile" subtitle="Read-only player profile and career preview for the selected run." />
      <CurrentContextStrip
        items={[
          { label: 'Active run ID', value: runId || 'unknown' },
          { label: 'Player ID', value: playerId || 'unknown' },
          { label: 'Career entries', value: careerQuery.data?.entries.length ?? '—' }
        ]}
      />

      <SectionCard title="Profile summary">
        {detailQuery.isLoading || careerQuery.isLoading ? <p className="status">Loading player profile…</p> : null}
        {detailQuery.error && careerQuery.error ? <p className="error">Failed to load player profile: {String(detailQuery.error)}</p> : null}
        <MetadataList
          items={[
            { label: 'Name', value: name ?? '—' },
            { label: 'Player ID', value: playerId || 'unknown' },
            { label: 'Country', value: countryCode ?? '—' },
            { label: 'Age', value: detailQuery.data?.age ?? latestCareerEntry?.age ?? '—' },
            { label: 'Source', value: detailQuery.data?.source_type ?? latestCareerEntry?.source_type ?? '—' },
            { label: 'Band', value: detailQuery.data?.quality_band ?? latestCareerEntry?.quality_band ?? '—' }
          ]}
        />
        <p>
          <Link to={`/viewer/runs/${runId}/players`}>Back to players</Link>
          {countryCode ? <> · <Link to={`/viewer/runs/${runId}/countries/${countryCode}`}>Country page</Link></> : null}
        </p>
      </SectionCard>

      <SectionCard title="Attributes">
        {detailQuery.data || latestCareerEntry ? (
          <MetadataList
            items={[
              { label: 'Technique', value: detailQuery.data?.technique ?? latestCareerEntry?.technique ?? '—' },
              { label: 'Movement', value: detailQuery.data?.movement ?? latestCareerEntry?.movement ?? '—' },
              { label: 'Physical', value: detailQuery.data?.physical ?? latestCareerEntry?.physical ?? '—' },
              { label: 'Mental', value: detailQuery.data?.mental ?? latestCareerEntry?.mental ?? '—' }
            ]}
          />
        ) : (
          <p className="status">Player career preview is not connected for this data shape yet.</p>
        )}
      </SectionCard>

      <SectionCard title="Career timeline">
        {careerQuery.error ? <p className="error">Failed to load career history: {String(careerQuery.error)}</p> : null}
        {careerQuery.data ? (
          careerQuery.data.entries.length > 0 ? (
            <table>
              <thead>
                <tr>
                  <th>Season</th>
                  <th>Run</th>
                  <th>Age</th>
                  <th>Overall</th>
                  <th>Technique</th>
                  <th>Movement</th>
                  <th>Physical</th>
                  <th>Mental</th>
                  <th>Source</th>
                  <th>Band</th>
                </tr>
              </thead>
              <tbody>
                {careerQuery.data.entries.map((entry) => (
                  <tr key={`${entry.run_id}-${entry.season}`}>
                    <td>{entry.season}</td>
                    <td>{entry.run_id}</td>
                    <td>{entry.age}</td>
                    <td>{entry.overall}</td>
                    <td>{entry.technique}</td>
                    <td>{entry.movement}</td>
                    <td>{entry.physical}</td>
                    <td>{entry.mental}</td>
                    <td>{entry.source_type ?? '—'}</td>
                    <td>{entry.quality_band ?? '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <p className="status">Player career preview is not connected for this data shape yet.</p>
          )
        ) : null}
      </SectionCard>

      <SectionCard title="Tournament history">
        {performanceQuery.isLoading || tournamentResultsQuery.isLoading ? <p className="status">Loading tournament history…</p> : null}
        {performanceQuery.error ? <p className="error">Failed to load season performance: {String(performanceQuery.error)}</p> : null}
        {tournamentResultsQuery.error ? <p className="error">Failed to load tournament results: {String(tournamentResultsQuery.error)}</p> : null}
        {performanceQuery.data?.entries.length ? (
          <table>
            <thead>
              <tr>
                <th>Season</th>
                <th>Run</th>
                <th>Ranking</th>
                <th>Race</th>
                <th>Tournaments</th>
                <th>Titles</th>
                <th>Wins</th>
                <th>Losses</th>
              </tr>
            </thead>
            <tbody>
              {performanceQuery.data.entries.map((entry) => (
                <tr key={`performance-${entry.run_id}-${entry.season}`}>
                  <td>{entry.season}</td>
                  <td>{entry.run_id}</td>
                  <td>{displayMetric(entry.ranking_position)}</td>
                  <td>{displayMetric(entry.race_position)}</td>
                  <td>{entry.tournaments_played}</td>
                  <td>{entry.titles}</td>
                  <td>{entry.wins}</td>
                  <td>{entry.losses}</td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : null}
        {tournamentResultsQuery.data?.entries.length ? (
          <table>
            <thead>
              <tr>
                <th>Season</th>
                <th>Week</th>
                <th>Event</th>
                <th>Category</th>
                <th>Finish</th>
                <th>Wins</th>
                <th>Losses</th>
                <th>Points</th>
              </tr>
            </thead>
            <tbody>
              {tournamentResultsQuery.data.entries.map((entry) => (
                <tr key={`result-${entry.run_id}-${entry.event_id}-${entry.event_sequence}`}>
                  <td>{entry.season}</td>
                  <td>{displayMetric(entry.week)}</td>
                  <td>{entry.event_name ?? entry.event_id}</td>
                  <td>{entry.event_category ?? '—'}</td>
                  <td>{entry.finish ?? '—'}{entry.is_title ? ' 🏆' : ''}</td>
                  <td>{entry.wins}</td>
                  <td>{entry.losses}</td>
                  <td>{displayMetric(entry.ranking_points_awarded)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : null}
        {performanceQuery.data && tournamentResultsQuery.data && !performanceQuery.data.entries.length && !tournamentResultsQuery.data.entries.length ? (
          <p className="status">Player career preview is not connected for this data shape yet.</p>
        ) : null}
      </SectionCard>

      {detailQuery.data ? (
        <details>
          <summary>Show technical player data</summary>
          <pre className="json-block">{JSON.stringify(detailQuery.data, null, 2)}</pre>
        </details>
      ) : null}
    </section>
  )
}

export function ViewerRunCountriesPage(): JSX.Element {
  const { runId = '' } = useParams()
  const [search, setSearch] = useState('')
  const [sort, setSort] = useState('total_players_desc')

  const queryParams = useMemo(
    () => ({
      search: search.trim() || undefined,
      sort,
      limit: 300,
      offset: 0
    }),
    [search, sort]
  )

  const nationsQuery = useQuery({
    queryKey: ['viewer-run-countries', runId, queryParams],
    queryFn: () => listRunNations(runId, queryParams),
    enabled: Boolean(runId)
  })

  return (
    <section className="panel">
      <PageIntro title="Countries" subtitle="Read-only country strength overview for the selected run." />
      <CurrentContextStrip
        items={[
          { label: 'Active run ID', value: runId || 'unknown' },
          { label: 'Total country count', value: nationsQuery.data?.total ?? '—' },
          { label: 'Visible countries', value: nationsQuery.data?.nations.length ?? '—' }
        ]}
      />

      <SectionCard title="Country filters">
        <div className="form-grid">
          <label>
            Search country
            <input value={search} onChange={(event) => setSearch(event.target.value)} />
          </label>
          <label>
            Sort
            <select value={sort} onChange={(event) => setSort(event.target.value)}>
              {COUNTRY_SORT_OPTIONS.map((value) => (
                <option key={value} value={value}>
                  {value}
                </option>
              ))}
            </select>
          </label>
        </div>
      </SectionCard>

      <SectionCard title="Country overview">
        {nationsQuery.isLoading ? <p className="status">Loading countries…</p> : null}
        {nationsQuery.error ? <p className="error">Failed to load countries: {String(nationsQuery.error)}</p> : null}
        {!nationsQuery.isLoading && !nationsQuery.error && nationsQuery.data ? (
          nationsQuery.data.nations.length > 0 ? (
            <table>
              <thead>
                <tr>
                  <th>Country code</th>
                  <th>Country name</th>
                  <th>Total players</th>
                  <th>Average overall</th>
                  <th>Average age</th>
                  <th>Source counts</th>
                  <th>Top player</th>
                  <th>Profile</th>
                </tr>
              </thead>
              <tbody>
                {nationsQuery.data.nations.map((nation) => (
                  <tr key={nation.country_code}>
                    <td>{nation.country_code}</td>
                    <td>{nation.country_name ?? '—'}</td>
                    <td>{nation.total_players}</td>
                    <td>{displayFixed(nation.average_overall)}</td>
                    <td>{displayFixed(nation.average_age)}</td>
                    <td>
                      carryover {nation.rollover_carried_count} · intake {nation.planner_generated_count} · manual {nation.manual_override_count}
                    </td>
                    <td>
                      {nation.top_player_name ?? '—'} {nation.top_player_id ? `(${nation.top_player_id})` : ''}
                    </td>
                    <td>
                      <Link to={`/viewer/runs/${runId}/countries/${nation.country_code}`}>Open country profile</Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <p className="status">No countries matched the selected read-only filters.</p>
          )
        ) : null}
      </SectionCard>
    </section>
  )
}

export function ViewerRunCountryDetailPage(): JSX.Element {
  const { runId = '', countryCode = '' } = useParams()

  const detailQuery = useQuery({
    queryKey: ['viewer-run-country-detail', runId, countryCode],
    queryFn: () => getRunNationDetail(runId, countryCode),
    enabled: Boolean(runId && countryCode)
  })

  return (
    <section className="panel">
      <PageIntro title="Country Profile" subtitle="Read-only country profile for the selected run." />
      <CurrentContextStrip
        items={[
          { label: 'Active run ID', value: runId || 'unknown' },
          { label: 'Country code', value: countryCode || 'unknown' },
          { label: 'Player count', value: detailQuery.data?.total_players ?? '—' }
        ]}
      />

      <SectionCard title="Country summary">
        {detailQuery.isLoading ? <p className="status">Loading country profile…</p> : null}
        {detailQuery.error ? <p className="error">Failed to load country profile: {String(detailQuery.error)}</p> : null}
        {detailQuery.data ? (
          <>
            <MetadataList
              items={[
                { label: 'Country code', value: detailQuery.data.country_code },
                { label: 'Country name', value: detailQuery.data.country_name ?? '—' },
                { label: 'Player count', value: detailQuery.data.total_players },
                { label: 'Average overall', value: displayFixed(detailQuery.data.average_overall) },
                { label: 'Average age', value: displayFixed(detailQuery.data.average_age) },
                {
                  label: 'Source counts',
                  value: `carryover ${detailQuery.data.rollover_carried_count} · intake ${detailQuery.data.planner_generated_count} · manual ${detailQuery.data.manual_override_count}`
                }
              ]}
            />
            <p>
              <Link to={`/viewer/runs/${runId}/countries`}>Back to countries</Link> ·{' '}
              <Link to={`/viewer/runs/${runId}/players?country=${detailQuery.data.country_code}`}>Player list</Link>
            </p>
          </>
        ) : null}
        {!detailQuery.isLoading && !detailQuery.error && !detailQuery.data ? (
          <p className="status">Country profile preview is not connected for this data shape yet.</p>
        ) : null}
      </SectionCard>

      <SectionCard title="Top players">
        {detailQuery.data ? (
          detailQuery.data.top_players.length > 0 ? (
            <table>
              <thead>
                <tr>
                  <th>Player</th>
                  <th>Age</th>
                  <th>Overall</th>
                  <th>Source</th>
                  <th>Band</th>
                  <th>Profile</th>
                </tr>
              </thead>
              <tbody>
                {detailQuery.data.top_players.map((player) => (
                  <tr key={player.player_id}>
                    <td>{player.name} ({player.player_id})</td>
                    <td>{player.age}</td>
                    <td>{player.overall}</td>
                    <td>{player.source_type}</td>
                    <td>{player.quality_band ?? '—'}</td>
                    <td>
                      <Link to={`/viewer/runs/${runId}/players/${player.player_id}/career`}>Open player career/profile</Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <p className="status">No top-player preview is available for this country yet.</p>
          )
        ) : (
          <p className="status">Country profile preview is not connected for this data shape yet.</p>
        )}
      </SectionCard>

      {detailQuery.data ? (
        <details>
          <summary>Show technical country data</summary>
          <pre className="json-block">{JSON.stringify(detailQuery.data, null, 2)}</pre>
        </details>
      ) : null}
    </section>
  )
}
