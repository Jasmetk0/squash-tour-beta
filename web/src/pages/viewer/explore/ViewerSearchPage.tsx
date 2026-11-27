import { useEffect, useMemo, useState, type FormEvent, type ReactNode } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useSearchParams } from 'react-router-dom'

import {
  getViewerCountries,
  getViewerPlayers,
  getViewerRunCalendar,
  getViewerTournamentHistory,
} from '../../../api/client'
import { ViewerActiveRunLinks, ViewerEmptyState } from '../../../components/viewer/ViewerLandingComponents'
import { ViewerShellPage } from '../../../components/viewer/ViewerShellPage'
import { useLanguage } from '../../../i18n/LanguageContext'
import { useActiveViewerProductRunId } from '../../../viewer/useActiveViewerProductRunId'
import { useViewerOfficialRunContext } from '../../../viewer/useViewerOfficialRunContext'
import type { ViewerCountries, ViewerPlayers } from '../../../api/types'
import { playerViewerBranch, verifiedViewerPlayers } from '../people/viewerPlayerDirectory'
import { verifiedTournamentCatalog } from '../tour/viewerTournamentCatalog'
import { viewerRunsPath } from '../../../viewer/viewerRoutes'
import { renderCountrySampleMetadata, renderPlayerSampleMetadata } from '../people'
import { normalizeViewerSearchQuery, searchTextMatches, type ViewerSearchTournamentResult } from './viewerComparisonDisplay'
import { renderSearchTournamentMetadata } from './viewerComparisonRender'

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
  routeNotice: ['Odkazy na výsledky používají kanonické cesty Product Runu.', 'Result links use canonical Product Run routes.'],
} as const

const SEARCH_PAGE_SIZE = 25

function SearchResultsSection<T>({ title, empty, items, itemKey, renderItem, t }: {
  title: string; empty: string; items: readonly T[]; itemKey: (item: T) => string;
  renderItem: (item: T) => ReactNode; t: (key: keyof typeof searchCopy) => string;
}): JSX.Element {
  const [page, setPage] = useState(1)
  const pages = Math.max(1, Math.ceil(items.length / SEARCH_PAGE_SIZE))
  const current = Math.min(page, pages)
  const offset = (current - 1) * SEARCH_PAGE_SIZE
  return <section aria-label={title}>
    <h4>{title}</h4>
    {items.length ? <>
      <p role="status">{t('results')}: {offset + 1}–{Math.min(offset + SEARCH_PAGE_SIZE, items.length)} / {items.length}</p>
      <ul className="viewer-home-list">
        {items.slice(offset, offset + SEARCH_PAGE_SIZE).map(item =>
          <li key={itemKey(item)}>{renderItem(item)}</li>)}
      </ul>
      {pages > 1 ? <nav aria-label={title + ' – ' + t('page')}>
        <button type="button" disabled={current === 1} onClick={() => setPage(current - 1)}>{t('previous')}</button>
        <span>{t('page')} {current} / {pages}</span>
        <button type="button" disabled={current === pages} onClick={() => setPage(current + 1)}>{t('next')}</button>
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
  const groups = new Map<string, { players: number; active: number; rated: number; sum: number; max: number }>()
  const players = new Map(roster.players.map(player => [player.player_id, player]))
  for (const player of roster.players) {
    const row = groups.get(player.country_code) ?? { players: 0, active: 0, rated: 0, sum: 0, max: 0 }
    row.players++
    if (player.status === 'active') row.active++
    if (player.current_ovr !== null) {
      row.rated++
      row.sum += player.current_ovr
      row.max = Math.max(row.max, player.current_ovr)
    }
    groups.set(player.country_code, row)
  }
  const fields = new Set(['country_code', 'player_count', 'active_player_count', 'retired_player_count',
    'average_current_ovr', 'top_player_id', 'top_player_name', 'top_player_current_ovr'])
  const seen = new Set<string>()
  for (const country of value.countries) {
    if (!country || typeof country !== 'object' || Object.keys(country).length !== fields.size ||
        Object.keys(country).some(key => !fields.has(key)) ||
        typeof country.country_code !== 'string' || !/^[A-Z]{3}$/.test(country.country_code) ||
        seen.has(country.country_code)) return null
    const group = groups.get(country.country_code)
    if (!group || country.player_count !== group.players || country.active_player_count !== group.active ||
        country.retired_player_count !== group.players - group.active) return null
    const top = country.top_player_id === null ? null : players.get(country.top_player_id)
    if (country.top_player_id === null) {
      if (group.rated !== 0 || country.top_player_name !== null || country.top_player_current_ovr !== null ||
          country.average_current_ovr !== null) return null
    } else if (!top || top.country_code !== country.country_code || top.name !== country.top_player_name ||
        top.current_ovr === null || top.current_ovr !== country.top_player_current_ovr ||
        typeof country.average_current_ovr !== 'number' || !Number.isFinite(country.average_current_ovr) ||
        country.average_current_ovr < 0 || country.average_current_ovr > top.current_ovr ||
        top.current_ovr !== group.max || group.rated === 0 ||
        Math.abs(country.average_current_ovr - group.sum / group.rated) > 0.00500001) return null
    seen.add(country.country_code)
  }
  return seen.size === groups.size ? value as ViewerCountries : null
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
  const tournaments = useMemo<Array<ViewerSearchTournamentResult & { eventName: string }>>(() => {
    if (!verified || !catalog) return []
    return catalog.entries
      .filter(({ event }) => searchTextMatches(urlQuery, [
        event.event_id, event.event_name, event.tour_level,
        event.category, event.template_id, event.season_week,
      ]))
      .map(({ event, publication }) => ({
        eventId: event.event_id,
        eventName: event.event_name,
        season: Number.parseInt(String(event.season).split('/')[0] ?? '', 10) || null,
        week: event.season_week,
        tour: event.tour_level,
        category: event.category,
        templateId: event.template_id,
        hasPlannedEvent: true,
        hasPersistedEvent: publication.result_published,
      }))
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
    searchTextMatches(urlQuery, [
      player.player_id,
      player.name,
      player.country_code,
      player.status,
      player.identity_source,
    ])
  )
  const countries = (verified ? countrySource?.countries ?? [] : []).filter((country) =>
    searchTextMatches(urlQuery, [
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
        {isLoading ? <p className="status">{t('loading')}</p> : null}
        {hasError ? <ViewerEmptyState>{t('sourceError')}</ViewerEmptyState> : null}
        <dl className="metadata-list">
          <div><dt>Product Run</dt><dd>{productRunId}</dd></div>
          <div><dt>{t('query')}</dt><dd>{urlQuery}</dd></div>
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
          itemKey={event => event.eventId}
          renderItem={event => <>
            <strong>{event.eventName || event.eventId}</strong>
            {renderSearchTournamentMetadata(productRunId, event)}
          </>} />
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
