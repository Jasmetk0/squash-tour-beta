import { useEffect, useMemo, useState, type FormEvent, type ReactNode } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link, useSearchParams } from 'react-router-dom'

import {
  getViewerCountries,
  getViewerPlayers,
  getViewerRunCalendar,
  getViewerTournamentHistory,
} from '../../../api/client'
import { ViewerActiveRunLinks, ViewerEmptyState, ViewerMetadataList } from '../../../components/viewer/ViewerLandingComponents'
import { ViewerShellPage } from '../../../components/viewer/ViewerShellPage'
import { useLanguage } from '../../../i18n/LanguageContext'
import { useActiveViewerProductRunId } from '../../../viewer/useActiveViewerProductRunId'
import { useViewerOfficialRunContext } from '../../../viewer/useViewerOfficialRunContext'
import type { ViewerCountries, ViewerPlayers } from '../../../api/types'
import { playerViewerBranch, verifiedViewerPlayers } from '../people/viewerPlayerDirectory'
import { joinedCountryRoster } from '../people/viewerCountryRosterJoin'
import { verifiedTournamentCatalog, type SavedTournamentEntry } from '../tour/viewerTournamentCatalog'
import { viewerRunsPath, viewerPlannedEventPath, viewerTournamentDetailPath } from '../../../viewer/viewerRoutes'
import { renderCountrySampleMetadata, renderPlayerSampleMetadata } from '../people'
import { normalizeViewerSearchQuery } from './viewerComparisonDisplay'

// Labels belong to Search; the existing public data and match/event metadata are unchanged.
const searchCopy = {
  title: ['Vyhledávání', 'Search'],
  emptyDescription: ['Vyhledávání ve Vieweru pouze pro čtení, založené na datech vybraného Product Runu.', 'Read-only Viewer Search using canonical Product Run data only.'],
  resultsDescription: ['Vyhledávání v uložených datech hráčů, zemí a turnajů vybraného Product Runu.', 'Read-only Viewer Search using canonical Saved-Revision player, country, and tournament data.'],
  emptyEyebrow: ['Vyhledávání ve Vieweru', 'Viewer search'],
  selectedRun: ['Vybraný Product Run', 'Selected Product Run'],
  loading: ['Načítám výsledky vyhledávání z uložených dat…', 'Loading canonical search results…'],
  sourceError: ['Některá uložená data pro vyhledávání jsou dočasně nedostupná.', 'Some canonical searchable metadata is temporarily unavailable.'],
  query: ['Dotaz', 'Query'],
  branch: ['Viewer Branch', 'Viewer Branch'],
  savedWeek: ['Uložený týden hráčů a zemí', 'Saved player and country week'],
  retry: ['Načíst znovu (GET)', 'Retry reads (GET)'],
  noResults: ['Nebyly nalezeny žádné odpovídající výsledky.', 'No matching Viewer results found.'],
  players: ['Hráči', 'Players'],
  noPlayers: ['Žádní odpovídající hráči.', 'No matching players.'],
  countries: ['Země', 'Countries'],
  noCountries: ['Žádné odpovídající země.', 'No matching countries.'],
  tournaments: ['Turnaje', 'Tournaments'],
  noTournaments: ['Žádné odpovídající turnaje.', 'No matching tournaments.'],
  links: ['Odkazy', 'Links'],
  browseRuns: ['Otevřít přehled Runů', 'Open run browser'],
  scope: ['Hledání v aktuálně dostupných uložených projekcích; nejde o historické hledání k libovolnému týdnu. Výsledky zápasů, mladí talenti a dřívější názvy sérií zde zatím nejsou pokryté.', 'Search covers the available Saved projections, not an arbitrary historical week. Match results, pre-Tour prospects and earlier series names are not yet covered.'],
  results: ['Výsledky', 'Results'],
  previous: ['Předchozí', 'Previous'],
  next: ['Další', 'Next'],
  page: ['Strana', 'Page'],
  first: ['První', 'First'],
  last: ['Poslední', 'Last'],
  jump: ['Přejít na stránku', 'Jump to page'],
  go: ['Přejít', 'Go'],
  pageError: ['Zadej číslo dostupné stránky.', 'Enter an available page number.'],
  eventId: ['ID turnaje', 'Event ID'],
  season: ['Sezona', 'Season'],
  week: ['Týden rozpisu', 'Scheduled week'],
  location: ['Místo', 'Location'],
  category: ['Kategorie', 'Category'],
  tour: ['Tour', 'Tour'],
  template: ['Šablona', 'Template'],
  publication: ['Publikovaný výsledek', 'Published result'],
  yes: ['Ano', 'Yes'],
  no: ['Ne', 'No'],
  openResult: ['Otevřít výsledek turnaje', 'Open tournament result'],
  routeNotice: ['Odkazy na výsledky používají kanonické cesty Product Runu.', 'Result links use canonical Product Run routes.'],
} as const

const SEARCH_PAGE_SIZE = 25

// Fold only search text; preserve the original IDs, names and season labels.
function folded(value: string | number | null | undefined): string {
  return String(value ?? '').normalize('NFD').replace(/\p{M}/gu, '').toLowerCase()
}
function matches(query: string, values: Array<string | number | null | undefined>): boolean {
  const terms = folded(query).trim().split(/\s+/).filter(Boolean)
  if (!terms.length) return false
  const fields = values.map(folded)
  return terms.every(term => fields.some(field => field.includes(term)))
}

function SearchTournamentRow({ entry, runId, t }: {
  entry: SavedTournamentEntry; runId: string; t: (key: keyof typeof searchCopy) => string;
}): JSX.Element {
  const { event, publication } = entry
  return <>
    <strong><Link to={viewerPlannedEventPath(runId, event.event_id)}>{event.event_name || event.event_id}</Link></strong>
    <ViewerMetadataList items={[
      { label: t('eventId'), value: event.event_id },
      { label: t('season'), value: String(event.season) },
      // The week-only route cannot identify a historical season.
      { label: t('week'), value: 'W' + event.season_week },
      { label: t('location'), value: [event.host_country, event.host_city].filter(Boolean).join(' · ') },
      { label: t('tour'), value: event.tour_level ?? '—' },
      { label: t('category'), value: event.category },
      { label: t('template'), value: event.template_id },
      { label: t('publication'), value: publication.result_published
        ? <Link to={viewerTournamentDetailPath(runId, event.event_id)}>{t('openResult')}</Link> : t('no') },
    ]} />
  </>
}

function SearchResultsSection<T>({ title, empty, items, itemKey, renderItem, t }: {
  title: string; empty: string; items: readonly T[]; itemKey: (item: T) => string;
  renderItem: (item: T) => ReactNode; t: (key: keyof typeof searchCopy) => string;
}): JSX.Element {
  const [page, setPage] = useState(1)
  const [jump, setJump] = useState('')
  const [invalidJump, setInvalidJump] = useState(false)
  const pages = Math.max(1, Math.ceil(items.length / SEARCH_PAGE_SIZE))
  const current = Math.min(page, pages)
  const offset = (current - 1) * SEARCH_PAGE_SIZE
  function navigate(next: number): void {
    setPage(next)
    setJump('')
    setInvalidJump(false)
  }
  function submitPage(event: FormEvent<HTMLFormElement>): void {
    event.preventDefault()
    const value = jump.trim()
    const next = Number(value)
    if (!/^[1-9]\d*$/.test(value) || !Number.isSafeInteger(next) || next > pages) {
      setInvalidJump(true)
      return
    }
    navigate(next)
  }
  return <section aria-label={title}>
    <h4>{title}</h4>
    {items.length ? <>
      <p role="status">{t('results')}: {offset + 1}–{Math.min(offset + SEARCH_PAGE_SIZE, items.length)} / {items.length}</p>
      <ul className="viewer-home-list">
        {items.slice(offset, offset + SEARCH_PAGE_SIZE).map(item =>
          <li key={itemKey(item)}>{renderItem(item)}</li>)}
      </ul>
      {pages > 1 ? <nav aria-label={title + ' – ' + t('page')}>
        <button type="button" disabled={current === 1} onClick={() => navigate(1)}>{t('first')}</button>
        <button type="button" disabled={current === 1} onClick={() => navigate(current - 1)}>{t('previous')}</button>
        <span>{t('page')} {current} / {pages}</span>
        <button type="button" disabled={current === pages} onClick={() => navigate(current + 1)}>{t('next')}</button>
        <button type="button" disabled={current === pages} onClick={() => navigate(pages)}>{t('last')}</button>
        <form aria-label={title + ' – ' + t('jump')} onSubmit={submitPage}>
          <label>{t('jump')} <input inputMode="numeric" value={jump} aria-invalid={invalidJump}
            onChange={event => { setJump(event.target.value); setInvalidJump(false) }} /></label>
          <button type="submit">{t('go')}</button>
          {invalidJump ? <p role="alert">{t('pageError')}</p> : null}
        </form>
      </nav> : null}
    </> : <p className="status">{empty}</p>}
  </section>
}

// Countries are a projection of the same public roster. Validate the exact
// source and public-only shape before rendering metadata (including fallback fields).
function verifiedSearchCountries(raw: unknown, roster: ViewerPlayers): ViewerCountries | null {
  if (!raw || typeof raw !== 'object') return null
  const value = raw as Partial<ViewerCountries>
  if (value.schema_version !== 'viewer_countries.v1' ||
      value.product_run_id !== roster.product_run_id || value.viewer_branch_id !== roster.viewer_branch_id ||
      value.season_index !== roster.season_index || value.week !== roster.week ||
      !Array.isArray(value.countries) || value.country_count !== value.countries.length) return null
  const rootFields = ['schema_version', 'product_run_id', 'viewer_branch_id', 'season_index', 'week', 'country_count', 'countries']
  const rowFields = ['country_code', 'player_count', 'active_player_count', 'retired_player_count',
    'average_current_ovr', 'top_player_id', 'top_player_name', 'top_player_current_ovr']
  const exact = (record: unknown, fields: string[]): boolean =>
    !!record && typeof record === 'object' && !Array.isArray(record) &&
    Object.keys(record).length === fields.length &&
    fields.every(key => Object.prototype.hasOwnProperty.call(record, key))
  if (!exact(raw, rootFields) || !value.countries.every(row => exact(row, rowFields))) return null
  // Use the existing roster consistency rules, including deterministic top
  // player ties and two-decimal mean precision. No extra GET is needed.
  return joinedCountryRoster(raw, roster) ? value as ViewerCountries : null
}

export function ViewerSearchPage(): JSX.Element {
  const productRunId = useActiveViewerProductRunId()
  const [searchParams, setSearchParams] = useSearchParams()
  const { language } = useLanguage()
  const isCzech = language === 'cs'
  const t = (key: keyof typeof searchCopy): string => searchCopy[key][isCzech ? 0 : 1]
  const urlQuery = normalizeViewerSearchQuery(searchParams)
  const [query, setQuery] = useState(urlQuery)
  const hasSearchQuery = urlQuery.length > 0
  const context = useViewerOfficialRunContext(hasSearchQuery ? productRunId : null)
  const branchId = playerViewerBranch(context.data, productRunId ?? '')
  const ready = Boolean(productRunId && hasSearchQuery && branchId && !context.isPending && !context.isFetching && !context.isError)

  useEffect(() => {
    setQuery(urlQuery)
  }, [urlQuery, productRunId])

  function submitSearch(event: FormEvent<HTMLFormElement>): void {
    event.preventDefault()
    const next = new URLSearchParams(searchParams)
    const submittedQuery = query.trim()
    next.delete('query')
    next.delete('search')
    if (submittedQuery) next.set('q', submittedQuery)
    else next.delete('q')
    setQuery(submittedQuery)
    if (next.toString() !== searchParams.toString()) setSearchParams(next)
  }

  const searchForm = (
    <form onSubmit={submitSearch} role="search" aria-label={isCzech ? 'Vyhledávání ve Vieweru' : 'Viewer search'}>
      <label className="field-label" htmlFor="viewer-search-shell-input">{isCzech ? 'Hledat' : 'Search'}</label>
      <input
        id="viewer-search-shell-input"
        type="search"
        placeholder={isCzech ? 'Hráči, země, turnaje…' : 'Players, countries, tournaments…'}
        value={query}
        onChange={(event) => setQuery(event.target.value)}
      />
      <button type="submit">{isCzech ? 'Vyhledat' : 'Search'}</button>
    </form>
  )

  const playersQuery = useQuery({
    queryKey: ['viewer-search-canonical-players', productRunId, branchId],
    queryFn: () => getViewerPlayers(productRunId ?? ''),
    enabled: ready,
    retry: false
  })
  const countriesQuery = useQuery({
    queryKey: ['viewer-search-canonical-countries', productRunId, branchId],
    queryFn: () => getViewerCountries(productRunId ?? ''),
    enabled: ready,
    retry: false
  })
  const calendarQuery = useQuery({
    queryKey: ['viewer-search-canonical-calendar', productRunId, branchId],
    queryFn: () => getViewerRunCalendar(productRunId ?? ''),
    enabled: ready,
    retry: false
  })
  const historyQuery = useQuery({
    queryKey: ['viewer-search-canonical-tournament-history', productRunId, branchId],
    queryFn: () => getViewerTournamentHistory(productRunId ?? ''),
    enabled: ready,
    retry: false
  })

  const isLoading = context.isPending || context.isFetching ||
    (ready && [playersQuery, countriesQuery, calendarQuery, historyQuery].some(query => query.isPending || query.isFetching))
  const sourceError = context.isError || !branchId ||
    [playersQuery, countriesQuery, calendarQuery, historyQuery].some(query => query.isError)
  const roster = ready && !isLoading && !sourceError
    ? verifiedViewerPlayers(playersQuery.data, productRunId ?? '', branchId ?? '') : null
  const countrySource = roster ? verifiedSearchCountries(countriesQuery.data, roster) : null
  const catalog = ready && !isLoading && !sourceError
    ? verifiedTournamentCatalog(calendarQuery.data, historyQuery.data, productRunId ?? '', branchId ?? '') : null
  const verified = Boolean(roster && countrySource && catalog)
  const hasError = !isLoading && !verified
  function retrySearch(): void {
    if (!ready) {
      void context.refetch()
      return
    }
    void Promise.all([playersQuery.refetch(), countriesQuery.refetch(), calendarQuery.refetch(), historyQuery.refetch()])
  }
  const tournaments = useMemo(() => {
    if (!verified || !catalog) return []
    return catalog.entries.filter(({ event }) => matches(urlQuery, [
      event.event_id, event.event_name, event.tour_level,
      event.category, event.template_id, event.season_week, 'W' + event.season_week,
      event.season, event.host_country, event.host_city, event.region,
    ]))
  }, [catalog, verified, urlQuery])

  if (!productRunId || !hasSearchQuery) {
    return (
      <ViewerShellPage title={t('title')} description={t('emptyDescription')}>
        <article className="viewer-active-run-card" aria-label={t('title')}>
          <span className="eyebrow">{t('emptyEyebrow')}</span>
          <h3>{t('title')}{urlQuery ? `: ${urlQuery}` : ''}</h3>
          {searchForm}
          <ViewerEmptyState>{!productRunId
            ? (isCzech ? 'Nejprve vyber Run pro vyhledávání.' : 'Select a Run to search.')
            : (isCzech ? 'Zadej a odešli hledaný text.' : 'Enter and submit a search term.')}</ViewerEmptyState>
        </article>
      </ViewerShellPage>
    )
  }

  const players = (verified ? roster?.players ?? [] : []).filter((player) =>
    matches(urlQuery, [
      player.player_id,
      player.name,
      player.country_code,
      player.status,
      player.identity_source,
    ])
  )
  const countries = (verified ? countrySource?.countries ?? [] : []).filter((country) =>
    matches(urlQuery, [
      country.country_code,
      country.top_player_name,
      country.top_player_id,
    ])
  )
  const hasResults = players.length > 0 || countries.length > 0 || tournaments.length > 0

  return (
    <ViewerShellPage title={t('title')} description={t('resultsDescription')}>
      <article className="viewer-active-run-card" aria-label={t('title')}>
        <span className="eyebrow">{t('selectedRun')}</span>
        <h3>{t('title')}: {urlQuery}</h3>
        {isLoading ? <p className="status" role="status">{t('loading')}</p> : null}
        {hasError ? <div role="alert"><p>{t('sourceError')}</p>
          <button type="button" onClick={retrySearch}>{t('retry')}</button></div> : null}
        <dl className="metadata-list">
          <div><dt>Product Run</dt><dd>{productRunId}</dd></div>
          <div><dt>{t('query')}</dt><dd>{urlQuery}</dd></div>
          <div><dt>{t('branch')}</dt><dd>{verified ? branchId : '—'}</dd></div>
          <div><dt>{t('savedWeek')}</dt><dd>{verified && roster ? 'S' + roster.season_index + ' W' + roster.week : '—'}</dd></div>
        </dl>
        {searchForm}
        <p className="status">{t('scope')}</p>
        {!isLoading && !hasError && !hasResults ? <ViewerEmptyState>{t('noResults')}</ViewerEmptyState> : null}

        {verified ? <>
        <SearchResultsSection key={JSON.stringify([productRunId, branchId, urlQuery, 'players'])}
          title={t('players')} empty={t('noPlayers')} items={players} t={t}
          itemKey={player => player.player_id}
          renderItem={player => renderPlayerSampleMetadata({
            player_id: player.player_id, name: player.name, country_code: player.country_code,
            age: player.age, current_ovr: player.current_ovr, status: player.status,
            identity_source: player.identity_source,
          }, productRunId)} />
        <SearchResultsSection key={JSON.stringify([productRunId, branchId, urlQuery, 'countries'])}
          title={t('countries')} empty={t('noCountries')} items={countries} t={t}
          itemKey={country => country.country_code}
          renderItem={country => renderCountrySampleMetadata(country, productRunId)} />
        <SearchResultsSection key={JSON.stringify([productRunId, branchId, urlQuery, 'tournaments'])}
          title={t('tournaments')} empty={t('noTournaments')} items={tournaments} t={t}
          itemKey={entry => entry.event.event_id}
          renderItem={entry => <SearchTournamentRow entry={entry} runId={productRunId} t={t} />} />
        </> : null}
        <section aria-label={t('links')}>
          <h4>{t('links')}</h4>
          <ViewerActiveRunLinks links={[{ label: t('browseRuns'), to: viewerRunsPath() }]} />
          <p className="status">{t('routeNotice')}</p>
        </section>
      </article>
    </ViewerShellPage>
  )
}
