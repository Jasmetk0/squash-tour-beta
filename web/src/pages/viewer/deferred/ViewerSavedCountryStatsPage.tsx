import { useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'

import { getViewerCountries } from '../../../api/client'
import type { ViewerCountries, ViewerCountry } from '../../../api/types'
import { useLanguage } from '../../../i18n/LanguageContext'
import { useActiveViewerProductRunId } from '../../../viewer/useActiveViewerProductRunId'
import { useViewerOfficialRunContext } from '../../../viewer/useViewerOfficialRunContext'
import { viewerCountryProfilePath, viewerPlayerProfilePath, viewerRunsPath } from '../../../viewer/viewerRoutes'
import { playerViewerBranch } from '../people/viewerPlayerDirectory'

const PAGE_SIZE = 25
const copy = {
  title: ['Statistiky uložených zemí', 'Saved Country Stats'],
  description: [
    'Veřejný stav hráčů podle země v ověřené uložené Viewer Branch.',
    'Public player counts by country in the verified Saved Viewer Branch.',
  ],
  scope: [
    'Počty a OVR odpovídají pouze uloženému týdnu. Nejde o oficiální Country Ranking, historické rekordy, výsledky zápasů ani statistiku libovolně vybraného týdne. Chybějící OVR se nedopočítává.',
    'Counts and OVR reflect only the Saved week. This is not an official Country Ranking, historical records, match results, or a statistic for an arbitrary selected week. Missing OVR is not calculated.',
  ],
  noRun: ['Nejprve vyber Product Run.', 'Select a Product Run first.'],
  runs: ['Seznam Runů', 'Run browser'],
  resolving: ['Ověřuji uloženou Viewer Branch…', 'Verifying Saved Viewer Branch…'],
  contextError: ['Nelze ověřit Viewer Branch tohoto Runu.', 'Cannot verify the Viewer Branch of this Run.'],
  loading: ['Načítám veřejné údaje o zemích…', 'Loading public country data…'],
  unavailable: ['Veřejné údaje o zemích nejsou dostupné.', 'Public country data is unavailable.'],
  mismatch: ['Zdroj zemí neodpovídá Runu nebo obsahuje neplatná data.', 'Country source mismatches the Run or contains invalid data.'],
  retry: ['Načíst znovu (GET)', 'Retry read (GET)'],
  run: ['Product Run', 'Product Run'],
  branch: ['Viewer Branch', 'Viewer Branch'],
  clock: ['Uložený čas', 'Saved clock'],
  countryCount: ['Zemí ve zdroji', 'Countries in source'],
  playerCount: ['Hráčů ve zdroji', 'Players in source'],
  activeCount: ['Aktivních hráčů', 'Active players'],
  retiredCount: ['Hráčů po kariéře', 'Retired players'],
  search: ['Hledat kód země nebo veřejného hráče', 'Search country code or public player'],
  subset: ['Zobrazit země', 'Show countries'],
  all: ['Všechny země', 'All countries'],
  hasActive: ['S aktivními hráči', 'With active players'],
  hasRetired: ['S hráči po kariéře', 'With retired players'],
  sort: ['Seřadit podle', 'Sort by'],
  sortCode: ['Kód země A–Z', 'Country code A–Z'],
  sortPlayers: ['Hráčů sestupně', 'Players descending'],
  sortActive: ['Aktivních sestupně', 'Active descending'],
  sortRetired: ['Po kariéře sestupně', 'Retired descending'],
  sortOvr: ['Veřejné průměrné OVR sestupně', 'Public average OVR descending'],
  reset: ['Vymazat filtry', 'Clear filters'],
  table: ['Veřejné statistiky zemí', 'Public country statistics'],
  country: ['Země', 'Country'],
  players: ['Hráči', 'Players'],
  active: ['Aktivní', 'Active'],
  retired: ['Po kariéře', 'Retired'],
  activeShare: ['Podíl aktivních', 'Active share'],
  average: ['Průměrné veřejné OVR', 'Average public OVR'],
  top: ['Nejlepší veřejný hráč', 'Top public player'],
  noCountries: ['Ve zdroji zatím nejsou žádné země.', 'No countries have been saved in this source yet.'],
  noMatch: ['Filtrům neodpovídá žádná země.', 'No country matches these filters.'],
  showing: ['Zobrazeno', 'Showing'],
  of: ['z', 'of'],
  page: ['Stránka', 'Page'],
  previous: ['Předchozí', 'Previous'],
  next: ['Další', 'Next'],
} as const
type Key = keyof typeof copy
type T = (key: Key) => string
type Cohort = 'all' | 'active' | 'retired'
type CountryStatsSort = 'code' | 'players' | 'active' | 'retired' | 'ovr'

const PUBLIC_COUNTRY_FIELDS = new Set([
  'country_code', 'player_count', 'active_player_count', 'retired_player_count',
  'average_current_ovr', 'top_player_id', 'top_player_name', 'top_player_current_ovr',
])
function whole(value: unknown, max = Number.MAX_SAFE_INTEGER): value is number {
  return typeof value === 'number' && Number.isSafeInteger(value) && value >= 0 && value <= max
}
function ovr(value: unknown): value is number | null {
  return value === null || (typeof value === 'number' && Number.isFinite(value) && value >= 0 && value <= 200)
}
function nonblank(value: unknown): value is string {
  return typeof value === 'string' && value.trim().length > 0
}

// Reusable source proof for this independent stats PR. Country Hub #1851 and
// All Countries #1855 have independently owned guards; Work can consolidate
// the shared contract at integration without coupling unmerged branches.
export function verifiedCountryStatsSource(
  source: unknown, runId: string, branchId: string,
): ViewerCountries | null {
  if (!nonblank(runId) || !nonblank(branchId) || !source || typeof source !== 'object') return null
  const value = source as Partial<ViewerCountries>
  if (
    value.schema_version !== 'viewer_countries.v1' ||
    value.product_run_id !== runId || value.viewer_branch_id !== branchId ||
    !whole(value.season_index) || !whole(value.week, 61) || value.week < 1 ||
    !whole(value.country_count) || !Array.isArray(value.countries) ||
    value.countries.length !== value.country_count
  ) return null
  const seen = new Set<string>()
  for (const item of value.countries) {
    if (!item || typeof item !== 'object') return null
    const country = item as Partial<ViewerCountry>
    if (
      typeof country.country_code !== 'string' ||
      !/^[A-Z]{3}$/.test(country.country_code) || seen.has(country.country_code) ||
      !whole(country.player_count) || !whole(country.active_player_count) ||
      !whole(country.retired_player_count) ||
      country.active_player_count + country.retired_player_count !== country.player_count ||
      !ovr(country.average_current_ovr) || !ovr(country.top_player_current_ovr) ||
      (country.top_player_id !== null && !nonblank(country.top_player_id)) ||
      (country.top_player_name !== null && !nonblank(country.top_player_name)) ||
      (country.top_player_id === null) !== (country.top_player_name === null) ||
      (country.player_count === 0 && country.top_player_id !== null) ||
      (country.top_player_id === null) !== (country.top_player_current_ovr === null) ||
      (country.top_player_id === null) !== (country.average_current_ovr === null) ||
      (country.top_player_current_ovr !== null && !Number.isInteger(country.top_player_current_ovr)) ||
      (typeof country.average_current_ovr === 'number' && typeof country.top_player_current_ovr === 'number' &&
        country.average_current_ovr > country.top_player_current_ovr) ||
      Object.keys(item).some(key => !PUBLIC_COUNTRY_FIELDS.has(key))
    ) return null
    seen.add(country.country_code)
  }
  return value as ViewerCountries
}

export function filteredCountryStats(
  source: ViewerCountries, search = '', cohort: Cohort = 'all', sort: CountryStatsSort = 'players',
): ViewerCountry[] {
  const q = search.trim().toLocaleLowerCase()
  const selected = source.countries.filter(country =>
    (cohort === 'all' || (cohort === 'active' ? country.active_player_count : country.retired_player_count) > 0) &&
    (!q || [country.country_code, country.top_player_name ?? '', country.top_player_id ?? '']
      .some(text => text.toLocaleLowerCase().includes(q)))
  )
  return [...selected].sort((a, b) => {
    const code = () => a.country_code.localeCompare(b.country_code, 'cs')
    if (sort === 'players') return b.player_count - a.player_count || code()
    if (sort === 'active') return b.active_player_count - a.active_player_count || code()
    if (sort === 'retired') return b.retired_player_count - a.retired_player_count || code()
    if (sort === 'ovr') {
      if (a.average_current_ovr === null && b.average_current_ovr !== null) return 1
      if (b.average_current_ovr === null && a.average_current_ovr !== null) return -1
      return (b.average_current_ovr ?? 0) - (a.average_current_ovr ?? 0) || code()
    }
    return code()
  })
}

function CountryStatsDirectory({ source, runId, t }: {
  source: ViewerCountries; runId: string; t: T
}): JSX.Element {
  const [search, setSearch] = useState('')
  const [cohort, setCohort] = useState<Cohort>('all')
  const [sort, setSort] = useState<CountryStatsSort>('players')
  const [page, setPage] = useState(1)
  const rows = useMemo(
    () => filteredCountryStats(source, search, cohort, sort),
    [source, search, cohort, sort],
  )
  const pages = Math.ceil(rows.length / PAGE_SIZE)
  const currentPage = Math.min(page, pages || 1)
  const offset = (currentPage - 1) * PAGE_SIZE
  const visible = rows.slice(offset, offset + PAGE_SIZE)
  // These are exactly source-provided player counts, not an inferred average OVR.
  const totals = useMemo(() => source.countries.reduce((sum, country) => ({
    players: sum.players + country.player_count,
    active: sum.active + country.active_player_count,
    retired: sum.retired + country.retired_player_count,
  }), { players: 0, active: 0, retired: 0 }), [source])
  function clear(): void {
    setSearch(''); setCohort('all'); setSort('players'); setPage(1)
  }
  return <article className="viewer-active-run-card">
    <dl className="metadata-list viewer-metadata-list">
      <div><dt>{t('run')}</dt><dd>{runId}</dd></div>
      <div><dt>{t('branch')}</dt><dd>{source.viewer_branch_id}</dd></div>
      <div><dt>{t('clock')}</dt><dd>{source.season_index} · W{source.week}</dd></div>
      <div><dt>{t('countryCount')}</dt><dd>{source.country_count}</dd></div>
      <div><dt>{t('playerCount')}</dt><dd>{totals.players}</dd></div>
      <div><dt>{t('activeCount')}</dt><dd>{totals.active}</dd></div>
      <div><dt>{t('retiredCount')}</dt><dd>{totals.retired}</dd></div>
    </dl>
    {source.country_count === 0 ? <p className="empty-state">{t('noCountries')}</p> : <>
      <div className="viewer-filters">
        <label htmlFor="country-stats-search">{t('search')}</label>
        <input id="country-stats-search" type="search" value={search}
          onChange={e => { setSearch(e.target.value); setPage(1) }} />
        <label htmlFor="country-stats-cohort">{t('subset')}</label>
        <select id="country-stats-cohort" value={cohort}
          onChange={e => { setCohort(e.target.value as Cohort); setPage(1) }}>
          <option value="all">{t('all')}</option>
          <option value="active">{t('hasActive')}</option>
          <option value="retired">{t('hasRetired')}</option>
        </select>
        <label htmlFor="country-stats-sort">{t('sort')}</label>
        <select id="country-stats-sort" value={sort}
          onChange={e => { setSort(e.target.value as CountryStatsSort); setPage(1) }}>
          <option value="players">{t('sortPlayers')}</option>
          <option value="active">{t('sortActive')}</option>
          <option value="retired">{t('sortRetired')}</option>
          <option value="ovr">{t('sortOvr')}</option>
          <option value="code">{t('sortCode')}</option>
        </select>
        <button type="button" onClick={clear}>{t('reset')}</button>
      </div>
      {rows.length === 0 ? <p className="empty-state">{t('noMatch')}</p> :
        <div className="table-wrap">
          <table aria-label={t('table')}>
            <thead><tr>
              <th scope="col">{t('country')}</th>
              <th scope="col">{t('players')}</th>
              <th scope="col">{t('active')}</th>
              <th scope="col">{t('retired')}</th>
              <th scope="col">{t('activeShare')}</th>
              <th scope="col">{t('average')}</th>
              <th scope="col">{t('top')}</th>
            </tr></thead>
            <tbody>{visible.map(country => <tr key={country.country_code}>
              <td><Link to={viewerCountryProfilePath(runId, country.country_code)}>
                {country.country_code}</Link></td>
              <td>{country.player_count}</td>
              <td>{country.active_player_count}</td>
              <td>{country.retired_player_count}</td>
              <td>{country.player_count > 0
                ? Math.round(country.active_player_count / country.player_count * 100) + '%'
                : '—'}</td>
              <td>{country.average_current_ovr ?? '—'}</td>
              <td>{country.top_player_id
                ? <Link to={viewerPlayerProfilePath(runId, country.top_player_id)}>{country.top_player_name}</Link>
                : '—'}</td>
            </tr>)}</tbody>
          </table>
        </div>
      }
      <p role="status">{t('showing')} {rows.length ? offset + 1 : 0}–
        {rows.length ? offset + visible.length : 0} {t('of')} {rows.length}</p>
      {pages > 1 ? <nav aria-label={t('page')}>
        <button type="button" disabled={currentPage === 1}
          onClick={() => setPage(n => Math.max(1, n - 1))}>{t('previous')}</button>
        <span>{t('page')} {currentPage} / {pages}</span>
        <button type="button" disabled={currentPage === pages}
          onClick={() => setPage(n => Math.min(pages, n + 1))}>{t('next')}</button>
      </nav> : null}
    </>}
  </article>
}

export function ViewerSavedCountryStatsPage(): JSX.Element {
  const runId = useActiveViewerProductRunId()?.trim() ?? ''
  const { language } = useLanguage()
  const t: T = key => copy[key][language === 'cs' ? 0 : 1]
  const context = useViewerOfficialRunContext(runId)
  const branchId = playerViewerBranch(context.data, runId)
  const validContext = Boolean(runId && branchId && !context.isPending && !context.isFetching && !context.isError)
  const query = useQuery({
    // Same canonical GET and source-scoped React Query identity as Country Hub
    // #1851 and All Countries #1855, without depending on their unmerged code.
    queryKey: ['viewer-countries-hub-canonical', runId, branchId],
    queryFn: () => getViewerCountries(runId),
    enabled: validContext,
    retry: false, refetchOnWindowFocus: false,
  })
  return <section className="panel viewer-shell-page">
    <div className="page-intro">
      <h2>{t('title')}</h2>
      <p className="subtitle">{t('description')}</p>
    </div>
    <p className="subtitle">{t('scope')}</p>
    {!runId ? <p className="empty-state">{t('noRun')} <Link to={viewerRunsPath()}>{t('runs')}</Link></p> :
      context.isPending || context.isFetching ? <p role="status">{t('resolving')}</p> :
      !validContext ? <div role="alert">
        <p>{t('contextError')}</p>
        <button type="button" onClick={() => void context.refetch()}>{t('retry')}</button>
      </div> :
      query.isPending || query.isFetching ? <p role="status">{t('loading')}</p> :
      query.isError ? <div role="alert">
        <p>{t('unavailable')}</p>
        <button type="button" onClick={() => void query.refetch()}>{t('retry')}</button>
      </div> : (() => {
        const source = verifiedCountryStatsSource(query.data, runId, branchId ?? '')
        return source ? <CountryStatsDirectory
          key={JSON.stringify([runId, branchId])} source={source} runId={runId} t={t} /> :
          <div role="alert">
            <p>{t('mismatch')}</p>
            <button type="button" onClick={() => void query.refetch()}>{t('retry')}</button>
          </div>
      })()}
  </section>
}
