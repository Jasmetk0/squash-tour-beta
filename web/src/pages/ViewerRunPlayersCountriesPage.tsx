import { useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link, useParams, useSearchParams } from 'react-router-dom'
import { useViewerProductRunRouteContext } from '../viewer/ViewerProductRunRouteContext'

import {
  getViewerCountries,
  getViewerPlayers
} from '../api/client'
import { CurrentContextStrip, MetadataList, PageIntro, SectionCard } from '../components/RunScopedUi'
import {
  viewerCountriesPath,
  viewerCountryProfilePath,
  viewerPlayerProfilePath,
  viewerPlayersPath,
  viewerTournamentDetailPath,
  viewerWeekDetailPath
} from '../viewer/viewerRoutes'

const PLAYER_SOURCE_OPTIONS = ['', 'rollover_carried', 'planner_generated', 'manual_override']
const COUNTRY_SORT_OPTIONS = ['total_players_desc', 'avg_overall_desc', 'avg_age_asc', 'country_code_asc']

function displayMetric(value: number | null | undefined): string | number {
  return typeof value === 'number' ? value : '—'
}

function displayFixed(value: number | null | undefined): string {
  return typeof value === 'number' && Number.isFinite(value) ? value.toFixed(2) : '—'
}

function isPlainRecord(value: unknown): value is Record<string, unknown> {
  return Boolean(value) && typeof value === 'object' && !Array.isArray(value)
}

function scalarText(value: unknown): string | null {
  if (typeof value === 'string') return value
  if (typeof value === 'number' && Number.isFinite(value)) return String(value)
  if (typeof value === 'boolean') return value ? 'yes' : 'no'
  return null
}

function optionalNumber(value: unknown): number | null {
  return typeof value === 'number' && Number.isFinite(value) ? value : null
}


function safeEntries(value: unknown): unknown[] {
  if (!isPlainRecord(value) || !Array.isArray(value.entries)) return []
  return value.entries
}

type SafeCareerEntry = {
  run_id: string | null
  season: number | null
  age: number | null
  overall: number | null
  technique: number | null
  movement: number | null
  physical: number | null
  mental: number | null
  source_type: string | null
  quality_band: string | null
}

type SafePerformanceEntry = {
  run_id: string | null
  season: number | null
  ranking_position: number | null
  race_position: number | null
  tournaments_played: number | null
  titles: number | null
  wins: number | null
  losses: number | null
}

type SafeTournamentResultEntry = {
  run_id: string | null
  season: number | null
  week: number | null
  event_sequence: number | null
  event_id: string | null
  event_name: string | null
  event_category: string | null
  finish: string | null
  is_title: boolean | null
  wins: number | null
  losses: number | null
  ranking_points_awarded: number | null
}

function normalizeCareerEntries(value: unknown): SafeCareerEntry[] {
  return safeEntries(value).flatMap((entry) => {
    if (!isPlainRecord(entry)) return []
    return [{
      run_id: scalarText(entry.run_id),
      season: optionalNumber(entry.season),
      age: optionalNumber(entry.age),
      overall: optionalNumber(entry.overall),
      technique: optionalNumber(entry.technique),
      movement: optionalNumber(entry.movement),
      physical: optionalNumber(entry.physical),
      mental: optionalNumber(entry.mental),
      source_type: scalarText(entry.source_type),
      quality_band: scalarText(entry.quality_band)
    }]
  })
}

function normalizePerformanceEntries(value: unknown): SafePerformanceEntry[] {
  return safeEntries(value).flatMap((entry) => {
    if (!isPlainRecord(entry)) return []
    return [{
      run_id: scalarText(entry.run_id),
      season: optionalNumber(entry.season),
      ranking_position: optionalNumber(entry.ranking_position),
      race_position: optionalNumber(entry.race_position),
      tournaments_played: optionalNumber(entry.tournaments_played),
      titles: optionalNumber(entry.titles),
      wins: optionalNumber(entry.wins),
      losses: optionalNumber(entry.losses)
    }]
  })
}

function normalizeTournamentResultEntries(value: unknown): SafeTournamentResultEntry[] {
  return safeEntries(value).flatMap((entry) => {
    if (!isPlainRecord(entry)) return []
    return [{
      run_id: scalarText(entry.run_id),
      season: optionalNumber(entry.season),
      week: optionalNumber(entry.week),
      event_sequence: optionalNumber(entry.event_sequence),
      event_id: scalarText(entry.event_id),
      event_name: scalarText(entry.event_name),
      event_category: scalarText(entry.event_category),
      finish: scalarText(entry.finish),
      is_title: typeof entry.is_title === 'boolean' ? entry.is_title : null,
      wins: optionalNumber(entry.wins),
      losses: optionalNumber(entry.losses),
      ranking_points_awarded: optionalNumber(entry.ranking_points_awarded)
    }]
  })
}

type SafeTopPlayer = {
  player_id: string | null
  name: string | null
  age: number | null
  overall: number | null
  source_type: string | null
  quality_band: string | null
}

function normalizeTopPlayers(value: unknown): SafeTopPlayer[] {
  if (!Array.isArray(value)) return []
  return value.flatMap((player) => {
    if (!isPlainRecord(player)) return []
    const playerId = scalarText(player.player_id)
    const name = scalarText(player.name)
    if (!playerId && !name) return []
    return [{
      player_id: playerId,
      name,
      age: optionalNumber(player.age),
      overall: optionalNumber(player.overall),
      source_type: scalarText(player.source_type),
      quality_band: scalarText(player.quality_band)
    }]
  })
}

function normalizeCountMap(value: unknown): Record<string, number> | null {
  if (!isPlainRecord(value)) return null
  const safeEntries = Object.entries(value).filter((entry): entry is [string, number] => typeof entry[1] === 'number' && Number.isFinite(entry[1]))
  return safeEntries.length ? Object.fromEntries(safeEntries) : null
}

function normalizeDistribution(value: unknown): Array<{ band: string; count: number }> | null {
  if (!Array.isArray(value)) return null
  const safeEntries = value.flatMap((entry) => {
    if (!isPlainRecord(entry)) return []
    const band = scalarText(entry.band)
    const count = optionalNumber(entry.count)
    return band && count !== null ? [{ band, count }] : []
  })
  return safeEntries.length ? safeEntries : null
}

type SafePlayerListEntry = {
  player_id: string
  name: string
  country_code: string | null
  age: number | null
  quality_band: string | null
  overall: number | null
}

type SafeNationListEntry = {
  country_code: string
  country_name: string | null
  total_players: number | null
  average_overall: number | null
  average_age: number | null
  rollover_carried_count: number | null
  planner_generated_count: number | null
  manual_override_count: number | null
  top_player_id: string | null
  top_player_name: string | null
}

function normalizePlayerListEntries(value: unknown): SafePlayerListEntry[] {
  if (!Array.isArray(value)) return []

  return value.flatMap((entry) => {
    if (!isPlainRecord(entry)) return []
    const playerId = scalarText(entry.player_id)
    const name = scalarText(entry.name)
    if (!playerId || !name) return []

    return [
      {
        player_id: playerId,
        name,
        country_code: scalarText(entry.country_code),
        age: optionalNumber(entry.age),
        quality_band: scalarText(entry.quality_band),
        overall: optionalNumber(entry.overall)
      }
    ]
  })
}

function normalizeNationListEntries(value: unknown): SafeNationListEntry[] {
  if (!Array.isArray(value)) return []

  return value.flatMap((entry) => {
    if (!isPlainRecord(entry)) return []
    const countryCode = scalarText(entry.country_code)
    if (!countryCode) return []

    return [
      {
        country_code: countryCode,
        country_name: scalarText(entry.country_name),
        total_players: optionalNumber(entry.total_players),
        average_overall: optionalNumber(entry.average_overall),
        average_age: optionalNumber(entry.average_age),
        rollover_carried_count: optionalNumber(entry.rollover_carried_count),
        planner_generated_count: optionalNumber(entry.planner_generated_count),
        manual_override_count: optionalNumber(entry.manual_override_count),
        top_player_id: scalarText(entry.top_player_id),
        top_player_name: scalarText(entry.top_player_name)
      }
    ]
  })
}

function countryCodeCell(countryCode: string | null | undefined, runId: string): JSX.Element | string {
  const safeCountryCode = scalarText(countryCode)
  if (!safeCountryCode) return '—'
  if (!runId) return safeCountryCode

  return <Link to={viewerCountryProfilePath(runId, safeCountryCode)}>{safeCountryCode}</Link>
}

function playerProfileCell(
  runId: string,
  playerId: string | null | undefined,
  playerName: string | null | undefined
): JSX.Element | string {
  const safePlayerId = scalarText(playerId)
  const safePlayerName = scalarText(playerName)
  if (!safePlayerId) return safePlayerName ?? '—'

  const label = safePlayerName ? `${safePlayerName} (${safePlayerId})` : safePlayerId
  return <Link to={viewerPlayerProfilePath(runId, safePlayerId)}>{label}</Link>
}

function weekCell(runId: string, week: number | null | undefined): JSX.Element | string {
  if (typeof week !== 'number') return '—'

  return <Link to={viewerWeekDetailPath(runId, week)}>W{week}</Link>
}

function tournamentEventCell(
  runId: string,
  eventId: string | null | undefined,
  eventName: string | null | undefined
): JSX.Element | string {
  const safeEventId = scalarText(eventId)
  const safeEventName = scalarText(eventName)
  if (!safeEventId) return safeEventName ?? '—'

  return <Link to={viewerTournamentDetailPath(runId, safeEventId)}>{safeEventName ?? safeEventId}</Link>
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
  const { productRunId: runId } = useViewerProductRunRouteContext()
  const [searchParams] = useSearchParams()
  const [search, setSearch] = useState('')
  const [countryCode, setCountryCode] = useState(() => searchParams.get('country') ?? '')
  const [sourceType, setSourceType] = useState('')
  const [minAge, setMinAge] = useState('')
  const [maxAge, setMaxAge] = useState('')

  const playersQuery = useQuery({
    queryKey: ['viewer-run-players-canonical', runId],
    queryFn: () => getViewerPlayers(runId),
    enabled: Boolean(runId),
    retry: false
  })

  const players = useMemo(() => {
    const normalizedSearch = search.trim().toLowerCase()
    const normalizedCountry = countryCode.trim().toUpperCase()
    const min = minAge ? Number(minAge) : null
    const max = maxAge ? Number(maxAge) : null
    return (playersQuery.data?.players ?? [])
      .filter((player) => !normalizedSearch || [player.player_id, player.name, player.country_code].some((value) => value.toLowerCase().includes(normalizedSearch)))
      .filter((player) => !normalizedCountry || player.country_code === normalizedCountry)
      .filter((player) => !sourceType || player.identity_source === sourceType)
      .filter((player) => min === null || player.age >= min)
      .filter((player) => max === null || player.age <= max)
      .sort((a, b) => (b.current_ovr ?? -1) - (a.current_ovr ?? -1) || a.player_id.localeCompare(b.player_id))
  }, [playersQuery.data?.players, search, countryCode, sourceType, minAge, maxAge])

  return (
    <section className="panel">
      <PageIntro title="Players" subtitle="Canonical Saved-Revision player profiles for the selected Product Run." />
      <CurrentContextStrip
        items={[
          { label: 'Product Run', value: runId || 'unknown' },
          { label: 'Viewer Branch', value: playersQuery.data?.viewer_branch_id ?? '—' },
          { label: 'Public week', value: playersQuery.data ? `S${playersQuery.data.season_index} W${playersQuery.data.week}` : '—' },
          { label: 'Total player count', value: playersQuery.data?.player_count ?? '—' },
          { label: 'Visible players', value: players.length }
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
            Identity source
            <select value={sourceType} onChange={(event) => setSourceType(event.target.value)}>
              <option value="">all</option>
              <option value="initial_world">initial world</option>
              <option value="run_prospect">run prospect</option>
            </select>
          </label>
          <label>
            Age min
            <input type="number" value={minAge} onChange={(event) => setMinAge(event.target.value)} min={15} max={120} />
          </label>
          <label>
            Age max
            <input type="number" value={maxAge} onChange={(event) => setMaxAge(event.target.value)} min={15} max={120} />
          </label>
        </div>
      </SectionCard>

      <SectionCard title="Player profiles">
        {playersQuery.isLoading ? <p className="status">Loading canonical players…</p> : null}
        {playersQuery.error ? <p className="error">Failed to load canonical players: {String(playersQuery.error)}</p> : null}
        {!playersQuery.isLoading && !playersQuery.error && playersQuery.data ? (
          players.length > 0 ? (
            <table>
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Country</th>
                  <th>Age</th>
                  <th>Status</th>
                  <th>Power Rating</th>
                  <th>Potential</th>
                  <th>Source</th>
                  <th>Player Profile</th>
                </tr>
              </thead>
              <tbody>
                {players.map((player) => (
                  <tr key={player.player_id}>
                    <td>{player.name}</td>
                    <td>{countryCodeCell(player.country_code, runId)}</td>
                    <td>{player.age}</td>
                    <td>{player.status}</td>
                    <td>{displayMetric(player.current_ovr)}</td>
                    <td>{displayMetric(player.potential_ovr)}</td>
                    <td>{player.identity_source.replace(/_/g, ' ')}</td>
                    <td>
                      <Link to={viewerPlayerProfilePath(runId, player.player_id)}>Open Player Profile</Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <p className="status">No canonical players match these filters.</p>
          )
        ) : null}
      </SectionCard>
    </section>
  )
}

export function ViewerRunPlayerCareerPage(): JSX.Element {
  const { playerId = '' } = useParams()
  const { productRunId: runId } = useViewerProductRunRouteContext()

  const playersQuery = useQuery({
    queryKey: ['viewer-run-player-profile-canonical', runId],
    queryFn: () => getViewerPlayers(runId),
    enabled: Boolean(runId && playerId),
    retry: false
  })

  const playerProfile = playersQuery.data?.players.find((player) => player.player_id === playerId) ?? null

  return (
    <section className="panel">
      <PageIntro
        title="Player Profile"
        subtitle="Canonical Saved-Revision current player profile. Historical career views remain deferred until a dedicated canonical history authority exists."
      />
      <CurrentContextStrip
        items={[
          { label: 'Product Run', value: runId || 'unknown' },
          { label: 'Viewer Branch', value: playersQuery.data?.viewer_branch_id ?? '—' },
          { label: 'Public week', value: playersQuery.data ? `S${playersQuery.data.season_index} W${playersQuery.data.week}` : '—' },
          { label: 'Player ID', value: playerId || 'unknown' },
          { label: 'Profile status', value: playerProfile ? 'canonical current profile' : 'unavailable' }
        ]}
      />

      {playersQuery.isLoading ? <p className="status">Loading canonical player profile…</p> : null}
      {playersQuery.error ? <p className="error">Failed to load canonical player profile: {String(playersQuery.error)}</p> : null}
      {!playersQuery.isLoading && !playersQuery.error && !playerProfile ? (
        <p className="status">No canonical player with this ID exists in the selected Saved Revision.</p>
      ) : null}

      {playerProfile ? (
        <>
          <SectionCard title="Identity">
            <MetadataList
              items={[
                { label: 'Name', value: playerProfile.name },
                { label: 'Player ID', value: playerProfile.player_id },
                { label: 'Country', value: countryCodeCell(playerProfile.country_code, runId) },
                { label: 'Age', value: playerProfile.age },
                { label: 'Status', value: playerProfile.status }
              ]}
            />
          </SectionCard>

          <SectionCard title="Current sporting state">
            <MetadataList
              items={[
                { label: 'Power Rating', value: displayMetric(playerProfile.current_ovr) },
                { label: 'Potential Power Rating', value: displayMetric(playerProfile.potential_ovr) },
                { label: 'Current form', value: displayMetric(playerProfile.current_form) },
                { label: 'Match sharpness', value: displayMetric(playerProfile.match_sharpness) },
                { label: 'Long-term fatigue', value: displayMetric(playerProfile.long_term_fatigue) }
              ]}
            />
          </SectionCard>

          <SectionCard title="Tour / identity source">
            <MetadataList
              items={[
                { label: 'Identity source', value: playerProfile.identity_source.replace(/_/g, ' ') },
                {
                  label: 'Tour entry',
                  value:
                    playerProfile.tour_entry_season_index !== null && playerProfile.tour_entry_week !== null
                      ? `S${playerProfile.tour_entry_season_index} W${playerProfile.tour_entry_week}`
                      : '—'
                }
              ]}
            />
          </SectionCard>

          <SectionCard title="Links">
            <p>
              <Link to={viewerPlayersPath(runId)}>Back to players</Link> ·{' '}
              <Link to={viewerCountryProfilePath(runId, playerProfile.country_code)}>Country page</Link>
            </p>
          </SectionCard>
        </>
      ) : null}

      <SectionCard title="Season Timeline">
        <p className="status">
          Deferred: canonical per-player season history is not published yet. Current profile data above comes only from the selected Saved Revision.
        </p>
      </SectionCard>

      <SectionCard title="Tournament History">
        <p className="status">
          Deferred: canonical per-player tournament/performance history is not published yet. No legacy SimulationRun history is shown here.
        </p>
      </SectionCard>
    </section>
  )
}

export function ViewerRunCountriesPage(): JSX.Element {
  const { productRunId: runId } = useViewerProductRunRouteContext()
  const [search, setSearch] = useState('')
  const [sort, setSort] = useState('player_count_desc')

  const countriesQuery = useQuery({
    queryKey: ['viewer-run-countries-canonical', runId],
    queryFn: () => getViewerCountries(runId),
    enabled: Boolean(runId),
    retry: false
  })

  const countries = useMemo(() => {
    const normalizedSearch = search.trim().toUpperCase()
    const values = (countriesQuery.data?.countries ?? []).filter(
      (country) => !normalizedSearch || country.country_code.includes(normalizedSearch)
    )
    return [...values].sort((a, b) => {
      if (sort === 'average_ovr_desc') return (b.average_current_ovr ?? -1) - (a.average_current_ovr ?? -1) || a.country_code.localeCompare(b.country_code)
      if (sort === 'country_code_asc') return a.country_code.localeCompare(b.country_code)
      return b.player_count - a.player_count || a.country_code.localeCompare(b.country_code)
    })
  }, [countriesQuery.data?.countries, search, sort])

  return (
    <section className="panel">
      <PageIntro title="Countries" subtitle="Canonical Saved-Revision country strength overview for the selected Product Run." />
      <CurrentContextStrip
        items={[
          { label: 'Product Run', value: runId || 'unknown' },
          { label: 'Viewer Branch', value: countriesQuery.data?.viewer_branch_id ?? '—' },
          { label: 'Public week', value: countriesQuery.data ? `S${countriesQuery.data.season_index} W${countriesQuery.data.week}` : '—' },
          { label: 'Total country count', value: countriesQuery.data?.country_count ?? '—' },
          { label: 'Visible countries', value: countries.length }
        ]}
      />

      <SectionCard title="Country filters">
        <div className="form-grid">
          <label>
            Search country code
            <input value={search} onChange={(event) => setSearch(event.target.value)} maxLength={3} />
          </label>
          <label>
            Sort
            <select value={sort} onChange={(event) => setSort(event.target.value)}>
              <option value="player_count_desc">player count desc</option>
              <option value="average_ovr_desc">average Power Rating desc</option>
              <option value="country_code_asc">country code asc</option>
            </select>
          </label>
        </div>
      </SectionCard>

      <SectionCard title="Country overview">
        {countriesQuery.isLoading ? <p className="status">Loading canonical countries…</p> : null}
        {countriesQuery.error ? <p className="error">Failed to load canonical countries: {String(countriesQuery.error)}</p> : null}
        {!countriesQuery.isLoading && !countriesQuery.error && countriesQuery.data ? (
          countries.length > 0 ? (
            <table>
              <thead>
                <tr>
                  <th>Country</th>
                  <th>Players</th>
                  <th>Active</th>
                  <th>Retired</th>
                  <th>Average Power Rating</th>
                  <th>Top player</th>
                  <th>Country Profile</th>
                </tr>
              </thead>
              <tbody>
                {countries.map((country) => (
                  <tr key={country.country_code}>
                    <td>{country.country_code}</td>
                    <td>{country.player_count}</td>
                    <td>{country.active_player_count}</td>
                    <td>{country.retired_player_count}</td>
                    <td>{displayFixed(country.average_current_ovr)}</td>
                    <td>{playerProfileCell(runId, country.top_player_id, country.top_player_name)}</td>
                    <td><Link to={viewerCountryProfilePath(runId, country.country_code)}>Open country profile</Link></td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <p className="status">No canonical countries match these filters.</p>
          )
        ) : null}
      </SectionCard>
    </section>
  )
}

export function ViewerRunCountryDetailPage(): JSX.Element {
  const { countryCode = '' } = useParams()
  const { productRunId: runId } = useViewerProductRunRouteContext()

  const countriesQuery = useQuery({
    queryKey: ['viewer-run-country-profile-canonical', runId],
    queryFn: () => getViewerCountries(runId),
    enabled: Boolean(runId && countryCode),
    retry: false
  })
  const playersQuery = useQuery({
    queryKey: ['viewer-run-country-profile-players-canonical', runId],
    queryFn: () => getViewerPlayers(runId),
    enabled: Boolean(runId && countryCode),
    retry: false
  })

  const normalizedCode = countryCode.toUpperCase()
  const countryProfile =
    countriesQuery.data?.countries.find((country) => country.country_code === normalizedCode) ?? null
  const countryPlayers = (playersQuery.data?.players ?? [])
    .filter((player) => player.country_code === normalizedCode)
    .sort((a, b) => (b.current_ovr ?? -1) - (a.current_ovr ?? -1) || a.player_id.localeCompare(b.player_id))

  const isLoading = countriesQuery.isLoading || playersQuery.isLoading
  const hasError = countriesQuery.isError || playersQuery.isError

  return (
    <section className="panel">
      <PageIntro
        title="Country Profile"
        subtitle="Canonical Saved-Revision current country profile. Historical talent/source breakdowns remain deferred until a dedicated canonical history authority exists."
      />
      <CurrentContextStrip
        items={[
          { label: 'Product Run', value: runId || 'unknown' },
          { label: 'Viewer Branch', value: countriesQuery.data?.viewer_branch_id ?? playersQuery.data?.viewer_branch_id ?? '—' },
          {
            label: 'Public week',
            value: countriesQuery.data
              ? `S${countriesQuery.data.season_index} W${countriesQuery.data.week}`
              : playersQuery.data
                ? `S${playersQuery.data.season_index} W${playersQuery.data.week}`
                : '—'
          },
          { label: 'Country code', value: normalizedCode || 'unknown' },
          { label: 'Profile status', value: countryProfile ? 'canonical current profile' : 'unavailable' }
        ]}
      />

      {isLoading ? <p className="status">Loading canonical country profile…</p> : null}
      {hasError ? (
        <p className="error">
          Failed to load canonical country profile: {String(countriesQuery.error ?? playersQuery.error)}
        </p>
      ) : null}
      {!isLoading && !hasError && !countryProfile ? (
        <p className="status">No canonical country with this code exists in the selected Saved Revision.</p>
      ) : null}

      {countryProfile ? (
        <>
          <SectionCard title="Overview">
            <MetadataList
              items={[
                { label: 'Country code', value: countryProfile.country_code },
                { label: 'Total players', value: countryProfile.player_count },
                { label: 'Active players', value: countryProfile.active_player_count },
                { label: 'Retired players', value: countryProfile.retired_player_count },
                { label: 'Average Power Rating', value: displayFixed(countryProfile.average_current_ovr) }
              ]}
            />
          </SectionCard>

          <SectionCard title="Top player">
            <MetadataList
              items={[
                {
                  label: 'Player',
                  value: playerProfileCell(runId, countryProfile.top_player_id, countryProfile.top_player_name)
                },
                { label: 'Power Rating', value: displayMetric(countryProfile.top_player_current_ovr) }
              ]}
            />
          </SectionCard>

          <SectionCard title="Current players">
            {countryPlayers.length ? (
              <table>
                <thead>
                  <tr>
                    <th>Player</th>
                    <th>Age</th>
                    <th>Status</th>
                    <th>Power Rating</th>
                    <th>Potential</th>
                  </tr>
                </thead>
                <tbody>
                  {countryPlayers.map((player) => (
                    <tr key={player.player_id}>
                      <td>{playerProfileCell(runId, player.player_id, player.name)}</td>
                      <td>{player.age}</td>
                      <td>{player.status}</td>
                      <td>{displayMetric(player.current_ovr)}</td>
                      <td>{displayMetric(player.potential_ovr)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <p className="status">No canonical players are published for this country in the selected Saved Revision.</p>
            )}
          </SectionCard>

          <SectionCard title="Links">
            <p>
              <Link to={viewerCountriesPath(runId)}>Back to countries</Link> ·{' '}
              <Link to={`${viewerPlayersPath(runId)}?country=${encodeURIComponent(countryProfile.country_code)}`}>Player list</Link>
            </p>
          </SectionCard>
        </>
      ) : null}

      <SectionCard title="Historical country analytics">
        <p className="status">
          Deferred: canonical historical source mix, talent-band evolution and historical country aggregates are not published yet.
        </p>
      </SectionCard>
    </section>
  )
}

