import { useEffect, useMemo, useRef, useState, type FormEvent } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link, useParams, useSearchParams } from 'react-router-dom'
import { useViewerProductRunRouteContext } from '../viewer/ViewerProductRunRouteContext'
import { useLanguage } from '../i18n/LanguageContext'
import { joinedCountryRoster } from './viewer/people/viewerCountryRosterJoin'
import { verifiedViewerPlayers, filteredPlayerDirectory, parsePlayerDirectoryPage, PLAYER_DIRECTORY_PAGE_SIZE, type PlayerDirectoryFilters } from './viewer/people/viewerPlayerDirectory'

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

// Both Run surfaces share the public roster verifier used by the global hub.
function useRunPlayerRoster(requested: boolean) {
  const { productRunId: runId, officialBranchId: branchId, officialContext, isLoading, isStale, refetch } = useViewerProductRunRouteContext()
  const validContext = Boolean(runId && branchId && officialContext?.product_run_id === runId &&
    officialContext?.official_branch_id === branchId && !isLoading && !isStale)
  const query = useQuery({
    queryKey: ['viewer-run-players-canonical', runId, branchId],
    queryFn: () => getViewerPlayers(runId),
    enabled: validContext && requested,
    retry: false
  })
  const verified = useMemo(() => verifiedViewerPlayers(query.data, runId, branchId), [query.data, runId, branchId])
  const ready = validContext && requested && !query.isFetching && !query.isPending && !query.isError
  return { runId, branchId, validContext, isLoading, refetch, query, source: ready ? verified : null }
}

const runPlayerKeys = ['vpQ', 'vpCountry', 'country', 'vpOrigin', 'vpStatus', 'vpSort', 'vpMinAge', 'vpMaxAge', 'vpPage']
export function ViewerRunPlayersPage(): JSX.Element {
  const { runId, branchId, validContext, isLoading, refetch, query, source } = useRunPlayerRoster(true)
  const { language } = useLanguage()
  const l = (en: string, cs: string) => language === 'cs' ? cs : en
  const [params, setParams] = useSearchParams()
  const identity = validContext ? JSON.stringify([runId, branchId]) : null
  const previous = useRef<string | null>(null)
  const changed = Boolean(identity && previous.current && identity !== previous.current)
  const active = changed ? new URLSearchParams() : params
  const [jump, setJump] = useState('')
  const [badJump, setBadJump] = useState(false)
  const search = active.get('vpQ') ?? ''
  const country = active.get('vpCountry') ?? active.get('country') ?? 'all'
  const origin = active.get('vpOrigin') ?? 'all'
  const status = active.get('vpStatus') ?? 'all'
  const sort = active.get('vpSort') ?? 'public_ovr'
  const minAge = active.get('vpMinAge') ?? ''
  const maxAge = active.get('vpMaxAge') ?? ''
  const rawPage = active.get('vpPage') ?? '1'
  useEffect(() => {
    if (!identity) return
    if (changed) {
      const next = new URLSearchParams(params)
      runPlayerKeys.forEach(key => next.delete(key))
      if (next.toString() !== params.toString()) setParams(next, { replace: true })
    }
    previous.current = identity
  }, [identity, changed, params, setParams])
  useEffect(() => { setJump(''); setBadJump(false) }, [identity, search, country, origin, status, sort, minAge, maxAge, rawPage])
  const validAge = (value: string) => value === '' || /^(0|[1-9][0-9]*)$/.test(value) && Number(value) <= 120
  const invalidSelection = runPlayerKeys.some(key => active.getAll(key).length > 1) ||
    (active.has('country') && active.has('vpCountry')) ||
    (country !== 'all' && !/^[A-Z]{3}$/.test(country)) ||
    !['all', 'initial_world', 'run_prospect'].includes(origin) ||
    !['all', 'active', 'retired'].includes(status) || !['name', 'public_ovr', 'age'].includes(sort) ||
    !validAge(minAge) || !validAge(maxAge) ||
    (minAge !== '' && maxAge !== '' && Number(minAge) > Number(maxAge))
  const filtered = useMemo(() => {
    if (!source || invalidSelection) return []
    return filteredPlayerDirectory(source, { search, country, origin, status, sort } as PlayerDirectoryFilters).filter(player =>
      (minAge === '' || player.age >= Number(minAge)) && (maxAge === '' || player.age <= Number(maxAge)))
  }, [source, invalidSelection, search, country, origin, status, sort, minAge, maxAge])
  const pages = Math.max(1, Math.ceil(filtered.length / PLAYER_DIRECTORY_PAGE_SIZE))
  const page = /^[1-9][0-9]*$/.test(rawPage) ? parsePlayerDirectoryPage(rawPage, pages) : null
  const invalid = invalidSelection || page === null
  const offset = invalid ? 0 : ((page ?? 1) - 1) * PLAYER_DIRECTORY_PAGE_SIZE
  const rows = invalid ? [] : filtered.slice(offset, offset + PLAYER_DIRECTORY_PAGE_SIZE)
  const countries = useMemo(() => source ? [...new Set(source.players.map(player => player.country_code))].sort() : [], [source])
  function change(key: string, value: string, fallback: string, replace = false) {
    setParams(previous => {
      const next = new URLSearchParams(previous)
      if (changed) runPlayerKeys.forEach(k => next.delete(k))
      next.delete('vpPage')
      if (key === 'vpCountry') next.delete('country')
      if (value === fallback) next.delete(key)
      else next.set(key, value)
      return next
    }, { replace })
  }
  function clear() {
    setParams(previous => {
      const next = new URLSearchParams(previous)
      runPlayerKeys.forEach(key => next.delete(key))
      return next
    })
  }
  function go(n: number) {
    setParams(previous => {
      const next = new URLSearchParams(previous)
      if (n === 1) next.delete('vpPage')
      else next.set('vpPage', String(n))
      return next
    })
  }
  function submitJump(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const n = parsePlayerDirectoryPage(jump, pages)
    if (n === null) setBadJump(true)
    else { setJump(''); setBadJump(false); go(n) }
  }
  return <section className="panel">
    <PageIntro title={l('Players', 'Hráči')} subtitle={l('Canonical Saved-Revision player profiles for the selected Product Run.', 'Veřejné profily hráčů uložené revize vybraného Product Runu.')} />
    <CurrentContextStrip items={[
      { label: 'Product Run', value: runId || '—' }, { label: 'Viewer Branch', value: validContext ? branchId : '—' },
      { label: l('Public week', 'Uložený týden'), value: source ? 'S' + source.season_index + ' W' + source.week : '—' },
      { label: l('Total player count', 'Celkem hráčů'), value: source?.player_count ?? '—' },
      { label: l('Visible players', 'Hráči odpovídající filtrům'), value: source && !invalid ? filtered.length : '—' },
    ]} />
    {isLoading ? <p role="status">{l('Loading canonical players…', 'Načítám uložené hráče…')}</p> :
      !validContext ? <div role="alert"><p>{l('Viewer Branch context is not verified.', 'Kontext Viewer Branch není ověřený.')}</p><button type="button" onClick={refetch}>{l('Retry read (GET)', 'Načíst znovu (GET)')}</button></div> :
      query.isPending || query.isFetching ? <p role="status">{l('Loading canonical players…', 'Načítám uložené hráče…')}</p> :
      query.isError ? <div role="alert"><p>{l('Failed to load canonical players:', 'Hráče nelze načíst:')} {String(query.error)}</p><button type="button" onClick={() => void query.refetch()}>{l('Retry read (GET)', 'Načíst znovu (GET)')}</button></div> :
      !source ? <div role="alert"><p>{l('Saved player list is invalid or belongs to another source.', 'Seznam hráčů je neplatný nebo patří jinému zdroji.')}</p><button type="button" onClick={() => void query.refetch()}>{l('Retry read (GET)', 'Načíst znovu (GET)')}</button></div> : <>
      <SectionCard title={l('Player filters', 'Filtry hráčů')}><div className="form-grid">
        <label>{l('Search', 'Hledat')}<input type="search" value={search} onChange={e => change('vpQ', e.target.value, '', true)} /></label>
        <label>{l('Country', 'Země')}<select value={country} onChange={e => change('vpCountry', e.target.value, 'all')}>
          {country !== 'all' && !countries.includes(country) ? <option value={country}>{country}</option> : null}
          <option value="all">{l('all', 'vše')}</option>{countries.map(code => <option key={code} value={code}>{code}</option>)}
        </select></label>
        <label>{l('Identity source', 'Původ hráče')}<select value={origin} onChange={e => change('vpOrigin', e.target.value, 'all')}>
          {!['all', 'initial_world', 'run_prospect'].includes(origin) ? <option value={origin}>{origin}</option> : null}
          <option value="all">{l('all', 'vše')}</option><option value="initial_world">{l('initial world', 'počáteční svět')}</option><option value="run_prospect">{l('run prospect', 'nový talent Runu')}</option>
        </select></label>
        <label>{l('Status', 'Kariéra')}<select value={status} onChange={e => change('vpStatus', e.target.value, 'all')}>
          {!['all', 'active', 'retired'].includes(status) ? <option value={status}>{status}</option> : null}
          <option value="all">{l('all', 'vše')}</option><option value="active">{l('active', 'aktivní')}</option><option value="retired">{l('retired', 'po kariéře')}</option>
        </select></label>
        <label>{l('Sort', 'Řazení')}<select value={sort} onChange={e => change('vpSort', e.target.value, 'public_ovr')}>
          {!['name', 'public_ovr', 'age'].includes(sort) ? <option value={sort}>{sort}</option> : null}
          <option value="public_ovr">{l('Public OVR', 'Veřejné OVR')}</option><option value="name">{l('Name A–Z', 'Jméno A–Z')}</option><option value="age">{l('Age descending', 'Věk sestupně')}</option>
        </select></label>
        <label>{l('Age min', 'Věk od')}<input inputMode="numeric" value={minAge} onChange={e => change('vpMinAge', e.target.value, '', true)} /></label>
        <label>{l('Age max', 'Věk do')}<input inputMode="numeric" value={maxAge} onChange={e => change('vpMaxAge', e.target.value, '', true)} /></label>
        <button type="button" onClick={clear}>{l('Clear filters', 'Vymazat filtry')}</button>
      </div></SectionCard>
      <SectionCard title={l('Player profiles', 'Profily hráčů')}>
        {invalid ? <p role="alert">{l('The URL contains invalid filters or page. Correct or clear the selection.', 'Odkaz obsahuje neplatné filtry nebo stránku. Uprav nebo vymaž výběr.')}</p> :
          rows.length === 0 ? <p>{l('No canonical players match these filters.', 'Žádní hráči neodpovídají filtrům.')}</p> :
          <div className="table-wrap"><table aria-label={l('Saved Run player directory', 'Uložený seznam hráčů Runu')}>
            <thead><tr>{[l('Name', 'Jméno'), l('Country', 'Země'), l('Age', 'Věk'), l('Status', 'Kariéra'), l('Power Rating', 'Veřejné OVR'), l('Source', 'Původ'), l('Player Profile', 'Profil hráče')].map(label => <th scope="col" key={label}>{label}</th>)}</tr></thead>
            <tbody>{rows.map(player => <tr key={player.player_id}>
              <td>{player.name}</td><td>{countryCodeCell(player.country_code, runId)}</td><td>{player.age}</td>
              <td>{player.status === 'active' ? l('active', 'aktivní') : l('retired', 'po kariéře')}</td>
              <td>{displayMetric(player.current_ovr)}</td><td>{player.identity_source === 'initial_world' ? l('initial world', 'počáteční svět') : l('run prospect', 'nový talent Runu')}</td>
              <td><Link to={{ pathname: viewerPlayerProfilePath(runId, player.player_id), search: active.toString() }}>{l('Open Player Profile', 'Otevřít profil hráče')}</Link></td>
            </tr>)}</tbody>
          </table></div>}
        {!invalid ? <p role="status">{l('Showing', 'Zobrazeno')} {rows.length ? offset + 1 : 0}–{offset + rows.length} {l('of', 'z')} {filtered.length}</p> : null}
        {!invalid && pages > 1 && page !== null ? <nav aria-label={l('Page', 'Stránka')}>
          <button type="button" disabled={page === 1} onClick={() => go(1)}>{l('First', 'První')}</button>
          <button type="button" disabled={page === 1} onClick={() => go(page - 1)}>{l('Previous', 'Předchozí')}</button>
          <span>{l('Page', 'Stránka')} {page} / {pages}</span>
          <button type="button" disabled={page === pages} onClick={() => go(page + 1)}>{l('Next', 'Další')}</button>
          <button type="button" disabled={page === pages} onClick={() => go(pages)}>{l('Last', 'Poslední')}</button>
          <form onSubmit={submitJump}>
            <label>{l('Jump to page', 'Přejít na stránku')}<input inputMode="numeric" value={jump} aria-invalid={badJump} aria-describedby={badJump ? 'run-player-page-error' : undefined} onChange={e => { setJump(e.target.value); setBadJump(false) }} /></label>
            <button type="submit">{l('Go', 'Přejít')}</button>
            {badJump ? <span role="alert" id="run-player-page-error">{l('Enter a valid existing page number.', 'Zadej platné existující číslo stránky.')}</span> : null}
          </form>
        </nav> : null}
      </SectionCard>
    </>}
  </section>
}

export function ViewerRunPlayerCareerPage(): JSX.Element {
  const { playerId = '' } = useParams()
  const { runId, branchId, validContext, isLoading, refetch, query: playersQuery, source } = useRunPlayerRoster(Boolean(playerId))
  const { language } = useLanguage()
  const l = (en: string, cs: string) => language === 'cs' ? cs : en
  const [params] = useSearchParams()
  const playerProfile = source?.players.find(player => player.player_id === playerId) ?? null

  return (
    <section className="panel">
      <PageIntro
        title={l('Player Profile', 'Profil hráče')}
        subtitle={l('Canonical Saved-Revision current player profile. Historical career views remain deferred until a dedicated canonical history authority exists.', 'Aktuální veřejný profil z uložené revize. Úplná historie kariéry zatím nemá kanonický veřejný zdroj.')}
      />
      <CurrentContextStrip
        items={[
          { label: 'Product Run', value: runId || 'unknown' },
          { label: 'Viewer Branch', value: validContext ? branchId : '—' },
          { label: l('Public week', 'Uložený týden'), value: source ? `S${source.season_index} W${source.week}` : '—' },
          { label: l('Player ID', 'ID hráče'), value: playerId || 'unknown' },
          { label: l('Profile status', 'Stav profilu'), value: playerProfile ? l('canonical current profile', 'aktuální uložený profil') : l('unavailable', 'nedostupný') }
        ]}
      />

      {isLoading ? <p role="status">{l('Loading canonical player profile…', 'Načítám uložený profil…')}</p> :
        !validContext ? <div role="alert"><p>{l('Viewer Branch context is not verified.', 'Kontext Viewer Branch není ověřený.')}</p><button type="button" onClick={refetch}>{l('Retry read (GET)', 'Načíst znovu (GET)')}</button></div> :
        !playerId ? <p role="alert">{l('No player ID was provided.', 'Chybí ID hráče.')}</p> :
        playersQuery.isPending || playersQuery.isFetching ? <p role="status">{l('Loading canonical player profile…', 'Načítám uložený profil…')}</p> :
        playersQuery.isError ? <div role="alert"><p>{l('Failed to load canonical player profile:', 'Profil hráče nelze načíst:')} {String(playersQuery.error)}</p><button type="button" onClick={() => void playersQuery.refetch()}>{l('Retry read (GET)', 'Načíst znovu (GET)')}</button></div> :
        !source ? <div role="alert"><p>{l('Saved player list is invalid or belongs to another source.', 'Seznam hráčů je neplatný nebo patří jinému zdroji.')}</p><button type="button" onClick={() => void playersQuery.refetch()}>{l('Retry read (GET)', 'Načíst znovu (GET)')}</button></div> :
        !playerProfile ? <p className="status">{l('No canonical player with this ID exists in the selected Saved Revision.', 'V uložené revizi není hráč s tímto ID.')}</p> : null}

      {playerProfile ? (
        <>
          <SectionCard title={l('Identity', 'Identita')}>
            <MetadataList
              items={[
                { label: l('Name', 'Jméno'), value: playerProfile.name },
                { label: l('Player ID', 'ID hráče'), value: playerProfile.player_id },
                { label: l('Country', 'Země'), value: countryCodeCell(playerProfile.country_code, runId) },
                { label: l('Age', 'Věk'), value: playerProfile.age },
                { label: l('Status', 'Kariéra'), value: playerProfile.status === 'active' ? l('active', 'aktivní') : l('retired', 'po kariéře') }
              ]}
            />
          </SectionCard>

          <SectionCard title={l('Current sporting state', 'Aktuální sportovní stav')}>
            <MetadataList
              items={[
                { label: l('Power Rating', 'Veřejné OVR'), value: displayMetric(playerProfile.current_ovr) }
              ]}
            />
          </SectionCard>

          <SectionCard title={l('Tour / identity source', 'Tour / původ hráče')}>
            <MetadataList
              items={[
                { label: l('Identity source', 'Původ hráče'), value: playerProfile.identity_source === 'initial_world' ? l('initial world', 'počáteční svět') : l('run prospect', 'nový talent Runu') },
                {
                  label: l('Tour entry', 'Vstup na Tour'),
                  value:
                    playerProfile.tour_entry_season_index !== null && playerProfile.tour_entry_week !== null
                      ? `S${playerProfile.tour_entry_season_index} W${playerProfile.tour_entry_week}`
                      : '—'
                }
              ]}
            />
          </SectionCard>

          <SectionCard title={l('Links', 'Odkazy')}>
            <p>
              <Link to={{ pathname: viewerPlayersPath(runId), search: params.toString() }}>{l('Back to players', 'Zpět na hráče')}</Link> ·{' '}
              <Link to={viewerCountryProfilePath(runId, playerProfile.country_code)}>{l('Country page', 'Profil země')}</Link>
            </p>
          </SectionCard>
        </>
      ) : null}

      <SectionCard title={l('Season Timeline', 'Historie sezon')}>
        <p className="status">
          {l('Deferred: canonical per-player season history is not published yet. Current profile data above comes only from the selected Saved Revision.', 'Individuální historie sezon zatím není veřejně dostupná. Profil pochází pouze z vybrané uložené revize.')}
        </p>
      </SectionCard>

      <SectionCard title={l('Tournament History', 'Historie turnajů')}>
        <p className="status">
          {l('Deferred: canonical per-player tournament/performance history is not published yet. No legacy SimulationRun history is shown here.', 'Individuální historie turnajů a výkonů zatím není veřejně dostupná. Historie starého SimulationRunu se zde nezobrazuje.')}
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
  const normalizedCode = countryCode.toUpperCase()
  const validCode = /^[A-Z]{3}$/.test(normalizedCode)
  const { runId, branchId, validContext, isLoading: contextLoading, refetch, query: playersQuery, source } = useRunPlayerRoster(validCode)
  const { language } = useLanguage()
  const l = (en: string, cs: string) => language === 'cs' ? cs : en
  const [params, setParams] = useSearchParams()
  const countriesQuery = useQuery({
    queryKey: ['viewer-run-country-profile-canonical', runId, branchId],
    queryFn: () => getViewerCountries(runId),
    enabled: validContext && validCode,
    retry: false
  })
  const isLoading = contextLoading || (validContext && validCode &&
    (countriesQuery.isPending || countriesQuery.isFetching || playersQuery.isPending || playersQuery.isFetching))
  const hasError = countriesQuery.isError || playersQuery.isError
  const joined = useMemo(() => source && !countriesQuery.isFetching && !countriesQuery.isError ?
    joinedCountryRoster(countriesQuery.data, source) : null,
    [source, countriesQuery.data, countriesQuery.isFetching, countriesQuery.isError])
  const countryEntry = joined?.get(normalizedCode)
  const countryProfile = countryEntry?.country ?? null
  const countryPlayers = useMemo(() => [...(countryEntry?.players ?? [])].sort(
    (a, b) => (b.current_ovr ?? -1) - (a.current_ovr ?? -1) || a.player_id.localeCompare(b.player_id)), [countryEntry])
  const rawPage = params.get('vcPlayerPage') ?? '1'
  const pages = Math.max(1, Math.ceil(countryPlayers.length / PLAYER_DIRECTORY_PAGE_SIZE))
  const page = params.getAll('vcPlayerPage').length <= 1 && /^[1-9][0-9]*$/.test(rawPage) ?
    parsePlayerDirectoryPage(rawPage, pages) : null
  const offset = ((page ?? 1) - 1) * PLAYER_DIRECTORY_PAGE_SIZE
  const visible = page === null ? [] : countryPlayers.slice(offset, offset + PLAYER_DIRECTORY_PAGE_SIZE)
  function go(n: number) {
    setParams(previous => {
      const next = new URLSearchParams(previous)
      if (n === 1) next.delete('vcPlayerPage')
      else next.set('vcPlayerPage', String(n))
      return next
    })
  }
  function retry() {
    void countriesQuery.refetch()
    void playersQuery.refetch()
  }

  return (
    <section className="panel">
      <PageIntro
        title={l('Country Profile', 'Profil země')}
        subtitle={l('Canonical Saved-Revision current country profile. Historical talent/source breakdowns remain deferred until a dedicated canonical history authority exists.', 'Aktuální veřejný profil země z uložené revize. Historické údaje zatím nemají kanonický veřejný zdroj.')}
      />
      <CurrentContextStrip
        items={[
          { label: 'Product Run', value: runId || 'unknown' },
          { label: 'Viewer Branch', value: validContext ? branchId : '—' },
          {
            label: l('Public week', 'Uložený týden'),
            value: joined && source ? `S${source.season_index} W${source.week}` : '—'
          },
          { label: l('Country code', 'Kód země'), value: normalizedCode || 'unknown' },
          { label: l('Profile status', 'Stav profilu'), value: countryProfile ? l('canonical current profile', 'aktuální uložený profil') : l('unavailable', 'nedostupný') }
        ]}
      />

      {isLoading ? <p role="status">{l('Loading canonical country profile…', 'Načítám uložený profil země…')}</p> :
        !validContext ? <div role="alert"><p>{l('Viewer Branch context is not verified.', 'Kontext Viewer Branch není ověřený.')}</p><button type="button" onClick={refetch}>{l('Retry read (GET)', 'Načíst znovu (GET)')}</button></div> :
        !validCode ? <p role="alert">{l('Invalid country code.', 'Neplatný kód země.')}</p> :
        hasError ? <div role="alert"><p>{l('Failed to load canonical country profile:', 'Profil země nelze načíst:')} {String(countriesQuery.error ?? playersQuery.error)}</p><button type="button" onClick={retry}>{l('Retry read (GET)', 'Načíst znovu (GET)')}</button></div> :
        !joined ? <div role="alert"><p>{l('Saved country and player sources do not match.', 'Uložené zdroje zemí a hráčů se neshodují.')}</p><button type="button" onClick={retry}>{l('Retry read (GET)', 'Načíst znovu (GET)')}</button></div> :
        !countryProfile ? <p className="status">{l('No canonical country with this code exists in the selected Saved Revision.', 'V uložené revizi není země s tímto kódem.')}</p> : null}

      {countryProfile ? (
        <>
          <SectionCard title={l('Overview', 'Přehled')}>
            <MetadataList
              items={[
                { label: l('Country code', 'Kód země'), value: countryProfile.country_code },
                { label: l('Total players', 'Celkem hráčů'), value: countryProfile.player_count },
                { label: l('Active players', 'Aktivní hráči'), value: countryProfile.active_player_count },
                { label: l('Retired players', 'Hráči po kariéře'), value: countryProfile.retired_player_count },
                { label: l('Average Power Rating', 'Průměrné veřejné OVR'), value: displayFixed(countryProfile.average_current_ovr) }
              ]}
            />
          </SectionCard>

          <SectionCard title={l('Top player', 'Nejlepší hráč')}>
            <MetadataList
              items={[
                {
                  label: l('Player', 'Hráč'),
                  value: playerProfileCell(runId, countryProfile.top_player_id, countryProfile.top_player_name)
                },
                { label: l('Power Rating', 'Veřejné OVR'), value: displayMetric(countryProfile.top_player_current_ovr) }
              ]}
            />
          </SectionCard>

          <SectionCard title={l('Current players', 'Aktuální hráči')}>
            {page === null ? <div role="alert"><p>{l('Invalid player page.', 'Neplatná stránka hráčů.')}</p><button type="button" onClick={() => go(1)}>{l('First page', 'První stránka')}</button></div> : countryPlayers.length ? (
              <table>
                <thead>
                  <tr>
                    <th scope="col">{l('Player', 'Hráč')}</th>
                    <th scope="col">{l('Age', 'Věk')}</th>
                    <th scope="col">{l('Status', 'Kariéra')}</th>
                    <th scope="col">{l('Power Rating', 'Veřejné OVR')}</th>
                  </tr>
                </thead>
                <tbody>
                  {visible.map((player) => (
                    <tr key={player.player_id}>
                      <td>{playerProfileCell(runId, player.player_id, player.name)}</td>
                      <td>{player.age}</td>
                      <td>{player.status === 'active' ? l('active', 'aktivní') : l('retired', 'po kariéře')}</td>
                      <td>{displayMetric(player.current_ovr)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <p className="status">No canonical players are published for this country in the selected Saved Revision.</p>
            )}
            {page !== null && pages > 1 ? <nav aria-label={l('Player page', 'Stránka hráčů')}>
              <button type="button" disabled={page === 1} onClick={() => go(1)}>{l('First', 'První')}</button>
              <button type="button" disabled={page === 1} onClick={() => go(page - 1)}>{l('Previous', 'Předchozí')}</button>
              <span>{l('Page', 'Stránka')} {page} / {pages}</span>
              <button type="button" disabled={page === pages} onClick={() => go(page + 1)}>{l('Next', 'Další')}</button>
              <button type="button" disabled={page === pages} onClick={() => go(pages)}>{l('Last', 'Poslední')}</button>
            </nav> : null}
          </SectionCard>

          <SectionCard title={l('Links', 'Odkazy')}>
            <p>
              <Link to={viewerCountriesPath(runId)}>{l('Back to countries', 'Zpět na země')}</Link> ·{' '}
              <Link to={`${viewerPlayersPath(runId)}?country=${encodeURIComponent(countryProfile.country_code)}`}>{l('Player list', 'Seznam hráčů')}</Link>
            </p>
          </SectionCard>
        </>
      ) : null}

      <SectionCard title={l('Historical country analytics', 'Historická analytika země')}>
        <p className="status">
          {l('Deferred: canonical historical source mix, talent-band evolution and historical country aggregates are not published yet.', 'Historické složení zdrojů, vývoj talentů a historické souhrny zemí zatím nejsou veřejně dostupné.')}
        </p>
      </SectionCard>
    </section>
  )
}

