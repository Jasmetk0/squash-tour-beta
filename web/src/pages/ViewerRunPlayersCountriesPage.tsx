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

function countryProfilePath(runId: string, countryCode: string): string {
  return `/viewer/runs/${encodeURIComponent(runId)}/countries/${encodeURIComponent(countryCode)}`
}

function playerProfilePath(runId: string, playerId: string): string {
  return `/viewer/runs/${encodeURIComponent(runId)}/players/${encodeURIComponent(playerId)}/career`
}

function countryCodeCell(countryCode: string | null | undefined, runId: string): JSX.Element | string {
  if (!countryCode) return '—'
  if (!runId) return countryCode

  return <Link to={countryProfilePath(runId, countryCode)}>{countryCode}</Link>
}

function playerProfileCell(
  runId: string,
  playerId: string | null | undefined,
  playerName: string | null | undefined
): JSX.Element | string {
  if (!playerId) return playerName ?? '—'

  const label = playerName ? `${playerName} (${playerId})` : playerId
  return <Link to={playerProfilePath(runId, playerId)}>{label}</Link>
}

function tournamentDetailPath(runId: string, eventId: string): string {
  return `/viewer/runs/${encodeURIComponent(runId)}/tournaments/${encodeURIComponent(eventId)}`
}

function weekDetailPath(runId: string, week: number): string {
  return `/viewer/runs/${encodeURIComponent(runId)}/weeks/${week}`
}

function weekCell(runId: string, week: number | null | undefined): JSX.Element | string {
  if (typeof week !== 'number') return '—'

  return <Link to={weekDetailPath(runId, week)}>W{week}</Link>
}

function tournamentEventCell(
  runId: string,
  eventId: string | null | undefined,
  eventName: string | null | undefined
): JSX.Element | string {
  if (!eventId) return eventName ?? '—'

  return <Link to={tournamentDetailPath(runId, eventId)}>{eventName ?? eventId}</Link>
}

function hasPlayerProfileShape(value: unknown): value is {
  player_id: string
  name: string
  country_code: string
  age: number
  source_type?: string | null
  override_id?: string | null
  quality_band?: string | null
  is_top_band?: boolean | null
  origin_source_type?: string | null
  origin_season?: number | null
  origin_quality_band?: string | null
  technique?: number | null
  movement?: number | null
  physical?: number | null
  mental?: number | null
  overall?: number | null
} {
  if (!value || typeof value !== 'object') {
    return false
  }
  const candidate = value as Record<string, unknown>
  return (
    typeof candidate.player_id === 'string' &&
    typeof candidate.name === 'string' &&
    typeof candidate.country_code === 'string' &&
    typeof candidate.age === 'number'
  )
}


type CountryProfileShape = {
  run_id?: string
  country_code: string
  country_name?: string | null
  total_players: number
  average_overall?: number | null
  average_age?: number | null
  top_band_count?: number | null
  manual_override_count?: number | null
  planner_generated_count?: number | null
  rollover_carried_count?: number | null
  average_visible_stats?: {
    technique?: number | null
    movement?: number | null
    physical?: number | null
    mental?: number | null
  } | null
  source_mix?: Record<string, number> | null
  band_distribution?: Array<{ band: string; count: number }> | null
  origin_band_distribution?: Array<{ band: string; count: number }> | null
  top_players?: Array<{
    player_id?: string | null
    name?: string | null
    age?: number | null
    overall?: number | null
    source_type?: string | null
    quality_band?: string | null
    is_top_band?: boolean | null
  }> | null
}

function hasCountryProfileShape(value: unknown): value is CountryProfileShape {
  if (!value || typeof value !== 'object') {
    return false
  }
  const candidate = value as Record<string, unknown>
  return typeof candidate.country_code === 'string' && typeof candidate.total_players === 'number'
}

function displayCountMap(values: Record<string, number> | null | undefined): string {
  if (!values || !Object.keys(values).length) {
    return '—'
  }
  return Object.entries(values)
    .map(([label, count]) => `${label} ${count}`)
    .join(' · ')
}

function displayDistribution(values: Array<{ band: string; count: number }> | null | undefined): string {
  if (!values?.length) {
    return '—'
  }
  return values.map((entry) => `${entry.band} ${entry.count}`).join(' · ')
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
      <PageIntro title="Players" subtitle="Read-only player profiles for the selected run." />
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

      <SectionCard title="Player profiles">
        {playersQuery.isLoading ? <p className="status">Loading players…</p> : null}
        {playersQuery.error ? <p className="error">Failed to load players: {String(playersQuery.error)}</p> : null}
        {!playersQuery.isLoading && !playersQuery.error && playersQuery.data ? (
          playersQuery.data.players.length > 0 ? (
            <table>
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Country</th>
                  <th>Age</th>
                  <th>Quality band</th>
                  <th>Power Rating</th>
                  <th>Player Profile</th>
                </tr>
              </thead>
              <tbody>
                {playersQuery.data.players.map((player) => (
                  <tr key={player.player_id}>
                    <td>{player.name}</td>
                    <td>{countryCodeCell(player.country_code, runId)}</td>
                    <td>{player.age}</td>
                    <td>{player.quality_band ?? '—'}</td>
                    <td>{displayMetric(player.overall)}</td>
                    <td>
                      <Link to={`/viewer/runs/${runId}/players/${player.player_id}/career`}>Open Player Profile</Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <p className="status">No data is available for this run yet.</p>
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

  const playerProfile = hasPlayerProfileShape(detailQuery.data) ? detailQuery.data : null
  const showDeferredPreview = !detailQuery.isLoading && !detailQuery.error && !playerProfile

  return (
    <section className="panel">
      <PageIntro title="Player Profile" subtitle="Read-only player profile for the selected run." />
      <CurrentContextStrip
        items={[
          { label: 'Active run ID', value: runId || 'unknown' },
          { label: 'Player ID', value: playerId || 'unknown' },
          { label: 'Profile status', value: playerProfile ? 'connected' : 'preview pending' }
        ]}
      />

      {detailQuery.isLoading ? <p className="status">Loading player profile…</p> : null}
      {detailQuery.error ? <p className="error">Failed to load player profile: {String(detailQuery.error)}</p> : null}
      {showDeferredPreview ? <p className="status">This preview is not connected for this data shape yet.</p> : null}

      {playerProfile ? (
        <>
          <SectionCard title="Identity">
            <MetadataList
              items={[
                { label: 'Name', value: playerProfile.name },
                { label: 'Player ID', value: playerProfile.player_id },
                { label: 'Country', value: countryCodeCell(playerProfile.country_code, runId) },
                { label: 'Age', value: playerProfile.age }
              ]}
            />
          </SectionCard>

          <SectionCard title="Attributes / Power Rating">
            <MetadataList
              items={[
                { label: 'Technique', value: displayMetric(playerProfile.technique) },
                { label: 'Movement', value: displayMetric(playerProfile.movement) },
                { label: 'Physical', value: displayMetric(playerProfile.physical) },
                { label: 'Mental', value: displayMetric(playerProfile.mental) },
                { label: 'Power Rating', value: displayMetric(playerProfile.overall) }
              ]}
            />
          </SectionCard>

          <SectionCard title="Origin / source">
            <MetadataList
              items={[
                { label: 'Source type', value: playerProfile.source_type ?? '—' },
                { label: 'Manual provenance ID', value: playerProfile.override_id ?? '—' },
                { label: 'Quality band', value: playerProfile.quality_band ?? '—' },
                { label: 'Top band', value: typeof playerProfile.is_top_band === 'boolean' ? (playerProfile.is_top_band ? 'yes' : 'no') : '—' },
                { label: 'Origin source type', value: playerProfile.origin_source_type ?? '—' },
                { label: 'Origin season', value: displayMetric(playerProfile.origin_season) },
                { label: 'Origin quality band', value: playerProfile.origin_quality_band ?? '—' }
              ]}
            />
          </SectionCard>

          <SectionCard title="Links">
            <p>
              <Link to={`/viewer/runs/${runId}/players`}>Back to players</Link> ·{' '}
              <Link to={countryProfilePath(runId, playerProfile.country_code)}>Country page</Link>
            </p>
          </SectionCard>
        </>
      ) : null}

      <SectionCard title="Season Timeline">
        {careerQuery.isLoading ? <p className="status">Loading season timeline…</p> : null}
        {careerQuery.error ? <p className="error">Failed to load career history: {String(careerQuery.error)}</p> : null}
        {careerQuery.data ? (
          careerQuery.data.entries.length > 0 ? (
            <table>
              <thead>
                <tr>
                  <th>Season</th>
                  <th>Run</th>
                  <th>Age</th>
                  <th>Power Rating</th>
                  <th>Technique</th>
                  <th>Movement</th>
                  <th>Physical</th>
                  <th>Mental</th>
                  <th>Source</th>
                  <th>Quality band</th>
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
            <p className="status">This preview is not connected for this data shape yet.</p>
          )
        ) : null}
      </SectionCard>

      <SectionCard title="Tournament History">
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
                  <td>{weekCell(runId, entry.week)}</td>
                  <td>{tournamentEventCell(runId, entry.event_id, entry.event_name)}</td>
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
          <p className="status">This preview is not connected for this data shape yet.</p>
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
                  <th>Country</th>
                  <th>Players</th>
                  <th>Average Power Rating</th>
                  <th>Average age</th>
                  <th>Top player</th>
                  <th>Source mix</th>
                  <th>Country Profile</th>
                </tr>
              </thead>
              <tbody>
                {nationsQuery.data.nations.map((nation) => (
                  <tr key={nation.country_code}>
                    <td>{nation.country_name ?? nation.country_code} ({nation.country_code})</td>
                    <td>{nation.total_players}</td>
                    <td>{displayFixed(nation.average_overall)}</td>
                    <td>{displayFixed(nation.average_age)}</td>
                    <td>
                      {playerProfileCell(runId, nation.top_player_id, nation.top_player_name)}
                    </td>
                    <td>
                      carryover {nation.rollover_carried_count} · intake {nation.planner_generated_count} · manual {nation.manual_override_count}
                    </td>
                    <td>
                      <Link to={countryProfilePath(runId, nation.country_code)}>Open country profile</Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <p className="status">No data is available for this run yet.</p>
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

  const countryProfile = hasCountryProfileShape(detailQuery.data) ? detailQuery.data : null
  const showDeferredPreview = !detailQuery.isLoading && !detailQuery.error && !countryProfile

  return (
    <section className="panel">
      <PageIntro title="Country Profile" subtitle="Read-only country profile for the selected run." />
      <CurrentContextStrip
        items={[
          { label: 'Active run ID', value: runId || 'unknown' },
          { label: 'Country code', value: countryCode || 'unknown' },
          { label: 'Profile status', value: countryProfile ? 'connected' : 'preview pending' }
        ]}
      />

      {detailQuery.isLoading ? <p className="status">Loading country profile…</p> : null}
      {detailQuery.error ? <p className="error">Failed to load country profile: {String(detailQuery.error)}</p> : null}
      {showDeferredPreview ? <p className="status">This preview is not connected for this data shape yet.</p> : null}

      {countryProfile ? (
        <>
          <SectionCard title="Overview">
            <MetadataList
              items={[
                { label: 'Country code', value: countryProfile.country_code },
                { label: 'Country name', value: countryProfile.country_name ?? '—' },
                { label: 'Total players', value: countryProfile.total_players },
                { label: 'Average Power Rating', value: displayFixed(countryProfile.average_overall) },
                { label: 'Average age', value: displayFixed(countryProfile.average_age) }
              ]}
            />
          </SectionCard>

          <SectionCard title="Player base">
            <MetadataList
              items={[
                { label: 'Top band count', value: displayMetric(countryProfile.top_band_count) },
                { label: 'Manual override count', value: displayMetric(countryProfile.manual_override_count) },
                { label: 'Planner generated count', value: displayMetric(countryProfile.planner_generated_count) },
                { label: 'Rollover carried count', value: displayMetric(countryProfile.rollover_carried_count) }
              ]}
            />
          </SectionCard>

          <SectionCard title="Source mix">
            <p>{displayCountMap(countryProfile.source_mix)}</p>
          </SectionCard>

          <SectionCard title="Talent bands">
            <MetadataList
              items={[
                { label: 'Current band distribution', value: displayDistribution(countryProfile.band_distribution) },
                { label: 'Origin band distribution', value: displayDistribution(countryProfile.origin_band_distribution) },
                { label: 'Average technique', value: displayFixed(countryProfile.average_visible_stats?.technique) },
                { label: 'Average movement', value: displayFixed(countryProfile.average_visible_stats?.movement) },
                { label: 'Average physical', value: displayFixed(countryProfile.average_visible_stats?.physical) },
                { label: 'Average mental', value: displayFixed(countryProfile.average_visible_stats?.mental) }
              ]}
            />
          </SectionCard>

          <SectionCard title="Top players">
            {countryProfile.top_players?.length ? (
              <table>
                <thead>
                  <tr>
                    <th>Player</th>
                    <th>Age</th>
                    <th>Power Rating</th>
                    <th>Source</th>
                    <th>Band</th>
                  </tr>
                </thead>
                <tbody>
                  {countryProfile.top_players.map((player, index) => (
                    <tr key={player.player_id ?? `${player.name ?? 'unknown'}-${index}`}>
                      <td>{playerProfileCell(runId, player.player_id, player.name)}</td>
                      <td>{displayMetric(player.age)}</td>
                      <td>{displayMetric(player.overall)}</td>
                      <td>{player.source_type ?? '—'}</td>
                      <td>{player.quality_band ?? '—'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <p className="status">No data is available for this run yet.</p>
            )}
          </SectionCard>

          <SectionCard title="Links">
            <p>
              <Link to={`/viewer/runs/${runId}/countries`}>Back to countries</Link> ·{' '}
              <Link to={`/viewer/runs/${runId}/players?country=${countryProfile.country_code}`}>Player list</Link>
            </p>
          </SectionCard>
        </>
      ) : null}

      {countryProfile ? (
        <details>
          <summary>Show technical country data</summary>
          <pre className="json-block">{JSON.stringify(detailQuery.data, null, 2)}</pre>
        </details>
      ) : null}
    </section>
  )
}
