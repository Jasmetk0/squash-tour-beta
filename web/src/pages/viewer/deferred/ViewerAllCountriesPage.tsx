import { useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'

import { getViewerCountries } from '../../../api/client'
import type { ViewerCountries } from '../../../api/types'
import { useLanguage } from '../../../i18n/LanguageContext'
import { useActiveViewerProductRunId } from '../../../viewer/useActiveViewerProductRunId'
import { useViewerOfficialRunContext } from '../../../viewer/useViewerOfficialRunContext'
import {
  viewerCountryProfilePath, viewerPlayerProfilePath, viewerRunsPath,
} from '../../../viewer/viewerRoutes'
import { playerViewerBranch } from '../people/viewerPlayerDirectory'
import {
  filterSavedCountries, verifiedSavedCountries, type SavedCountrySort,
} from '../people/viewerSavedCountries'

const PAGE_SIZE = 25
const copy = {
  title: ['Všechny země', 'All Countries'],
  subtitle: [
    'Úplný veřejný seznam zemí ze zvolené uložené Viewer Branch.',
    'Complete public list of countries in the selected Saved Viewer Branch.',
  ],
  scope: [
    'Údaje odpovídají uloženému stavu této Viewer Branch, nikoli historickému rekordu země ani žebříčku států. Neznámé OVR zůstává neznámé.',
    'Figures describe this Saved Viewer Branch, not a country all-time record or an official nation ranking. Unknown OVR remains unknown.',
  ],
  noRun: ['Nejprve vyber Product Run.', 'Select a Product Run first.'],
  runs: ['Seznam Runů', 'Run browser'],
  resolving: ['Ověřuji uloženou Viewer Branch…', 'Verifying Saved Viewer Branch…'],
  badContext: ['Viewer Branch neodpovídá vybranému Runu nebo není dostupná.', 'Viewer Branch does not match the selected Run or is unavailable.'],
  loading: ['Načítám veřejný seznam zemí…', 'Loading public country directory…'],
  unavailable: ['Veřejný seznam zemí není dostupný.', 'Public country directory is unavailable.'],
  mismatch: [
    'Seznam obsahuje neplatný údaj nebo neodpovídá ověřenému Runu a Viewer Branch.',
    'Directory contains invalid data or does not match the verified Run and Viewer Branch.',
  ],
  retry: ['Znovu načíst (GET)', 'Retry read (GET)'],
  run: ['Product Run', 'Product Run'],
  branch: ['Viewer Branch', 'Viewer Branch'],
  clock: ['Uložený čas', 'Saved clock'],
  count: ['Počet zemí', 'Country count'],
  search: ['Hledat zemi nebo hráče', 'Search country or player'],
  order: ['Řadit podle', 'Sort by'],
  code: ['Kód země', 'Country code'],
  playersSort: ['Počtu hráčů', 'Player count'],
  activeSort: ['Aktivních hráčů', 'Active players'],
  ovrSort: ['Průměrného veřejného OVR', 'Average public OVR'],
  clear: ['Vymazat filtry', 'Clear filters'],
  table: ['Ověřený uložený seznam zemí', 'Verified Saved country directory'],
  country: ['Země', 'Country'],
  players: ['Hráči', 'Players'],
  active: ['Aktivní', 'Active'],
  retired: ['Ukončená kariéra', 'Retired'],
  avgOvr: ['Průměrné veřejné OVR', 'Average public OVR'],
  topPlayer: ['Nejlepší veřejný hráč', 'Top public player'],
  topOvr: ['Veřejné OVR hráče', 'Player public OVR'],
  empty: ['V tomto Runu zatím nejsou uložené země.', 'No countries have been saved in this Run yet.'],
  none: ['Hledání neodpovídá žádné uložené zemi.', 'No Saved country matches the search.'],
  shown: ['Zobrazeno', 'Showing'],
  of: ['z', 'of'],
  page: ['Stránka', 'Page'],
  previous: ['Předchozí', 'Previous'],
  next: ['Další', 'Next'],
} as const
type Key = keyof typeof copy
type T = (name: Key) => string

function CountryDirectory({ source, runId, t }: {
  source: ViewerCountries; runId: string; t: T
}): JSX.Element {
  const [search, setSearch] = useState('')
  const [sort, setSort] = useState<SavedCountrySort>('country')
  const [page, setPage] = useState(1)
  const filtered = useMemo(
    () => filterSavedCountries(source.countries, search, sort), [source, search, sort],
  )
  const pages = Math.ceil(filtered.length / PAGE_SIZE)
  const currentPage = Math.min(page, pages || 1)
  const offset = (currentPage - 1) * PAGE_SIZE
  const visible = filtered.slice(offset, offset + PAGE_SIZE)
  const number = (value: number | null) => value === null ? '—' : String(value)

  return <article className="viewer-active-run-card">
    <dl className="metadata-list viewer-metadata-list">
      <div><dt>{t('run')}</dt><dd>{runId}</dd></div>
      <div><dt>{t('branch')}</dt><dd>{source.viewer_branch_id}</dd></div>
      <div><dt>{t('clock')}</dt><dd>{source.season_index} · W{source.week}</dd></div>
      <div><dt>{t('count')}</dt><dd>{source.country_count}</dd></div>
    </dl>
    {source.country_count === 0 ? <p className="empty-state">{t('empty')}</p> : <>
      <div className="viewer-filters">
        <label htmlFor="saved-country-search">{t('search')}</label>
        <input id="saved-country-search" type="search" value={search}
          onChange={e => { setSearch(e.target.value); setPage(1) }} />
        <label htmlFor="saved-country-sort">{t('order')}</label>
        <select id="saved-country-sort" value={sort}
          onChange={e => { setSort(e.target.value as SavedCountrySort); setPage(1) }}>
          <option value="country">{t('code')}</option>
          <option value="players">{t('playersSort')}</option>
          <option value="active">{t('activeSort')}</option>
          <option value="average_ovr">{t('ovrSort')}</option>
        </select>
        <button type="button" onClick={() => { setSearch(''); setSort('country'); setPage(1) }}>{t('clear')}</button>
      </div>
      {filtered.length === 0 ? <p className="empty-state">{t('none')}</p> : (
        <div className="table-wrap">
          <table aria-label={t('table')}>
            <thead><tr>
              <th scope="col">{t('country')}</th>
              <th scope="col">{t('players')}</th>
              <th scope="col">{t('active')}</th>
              <th scope="col">{t('retired')}</th>
              <th scope="col">{t('avgOvr')}</th>
              <th scope="col">{t('topPlayer')}</th>
              <th scope="col">{t('topOvr')}</th>
            </tr></thead>
            <tbody>{visible.map(country => <tr key={country.country_code}>
              <td><Link to={viewerCountryProfilePath(runId, country.country_code)}>
                {country.country_code}
              </Link></td>
              <td>{country.player_count}</td>
              <td>{country.active_player_count}</td>
              <td>{country.retired_player_count}</td>
              <td>{number(country.average_current_ovr)}</td>
              <td>{country.top_player_id === null ? '—'
                : <Link to={viewerPlayerProfilePath(runId, country.top_player_id)}>
                  {country.top_player_name}
                </Link>}</td>
              <td>{number(country.top_player_current_ovr)}</td>
            </tr>)}</tbody>
          </table>
        </div>
      )}
      <p role="status">{t('shown')} {filtered.length ? offset + 1 : 0}–
        {filtered.length ? offset + visible.length : 0} {t('of')} {filtered.length}</p>
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

export function ViewerAllCountriesPage(): JSX.Element {
  const runId = useActiveViewerProductRunId()?.trim() ?? ''
  const { language } = useLanguage()
  const t: T = key => copy[key][language === 'cs' ? 0 : 1]
  const context = useViewerOfficialRunContext(runId)
  const branchId = playerViewerBranch(context.data, runId)
  const validContext = Boolean(runId && branchId && !context.isPending && !context.isFetching && !context.isError)
  const query = useQuery({
    // Once #1851 is merged, reuse the same exact source-scoped country cache
    // as its guarded Country Hub, never the legacy Run-only cache key.
    queryKey: ['viewer-countries-hub-canonical', runId, branchId],
    queryFn: () => getViewerCountries(runId),
    enabled: validContext,
    retry: false,
    refetchOnWindowFocus: false,
  })

  return <section className="panel viewer-shell-page">
    <div className="page-intro">
      <h2>{t('title')}</h2>
      <p className="subtitle">{t('subtitle')}</p>
    </div>
    <p className="subtitle">{t('scope')}</p>
    {!runId ? <p className="empty-state">{t('noRun')} <Link to={viewerRunsPath()}>{t('runs')}</Link></p> :
      context.isPending || context.isFetching ? <p role="status">{t('resolving')}</p> :
      !validContext ? <div role="alert">
        <p>{t('badContext')}</p>
        <button type="button" onClick={() => void context.refetch()}>{t('retry')}</button>
      </div> :
      query.isPending || query.isFetching ? <p role="status">{t('loading')}</p> :
      query.isError ? <div role="alert">
        <p>{t('unavailable')}</p>
        <button type="button" onClick={() => void query.refetch()}>{t('retry')}</button>
      </div> : (() => {
        const countries = verifiedSavedCountries(query.data, runId, branchId ?? '')
        return countries
          ? <CountryDirectory key={JSON.stringify([runId, branchId])} source={countries} runId={runId} t={t} />
          : <div role="alert">
              <p>{t('mismatch')}</p>
              <button type="button" onClick={() => void query.refetch()}>{t('retry')}</button>
            </div>
      })()}
  </section>
}
