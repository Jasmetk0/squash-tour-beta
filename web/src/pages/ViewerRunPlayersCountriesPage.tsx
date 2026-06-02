import { useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link, useParams, useSearchParams } from 'react-router-dom'

import {
  getRunNationDetail,
  getRunPlayerDetail,
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
                    <td>{player.country_code}</td>
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
                { label: 'Country', value: playerProfile.country_code },
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
              <Link to={`/viewer/runs/${runId}/countries/${playerProfile.country_code}`}>Country page</Link>
            </p>
          </SectionCard>

          <details>
            <summary>Show technical player data</summary>
            <pre className="json-block">{JSON.stringify(detailQuery.data, null, 2)}</pre>
          </details>
        </>
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
          <p className="status">This preview is not connected for this data shape yet.</p>
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
            <p className="status">No data is available for this run yet.</p>
          )
        ) : (
          <p className="status">This preview is not connected for this data shape yet.</p>
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
