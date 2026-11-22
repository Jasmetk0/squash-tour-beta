import { useEffect, useMemo, useState, type FormEvent } from 'react'
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
  routeNotice: ['Odkazy na výsledky používají kanonické cesty Product Runu.', 'Result links use canonical Product Run routes.'],
} as const

export function ViewerSearchPage(): JSX.Element {
  const productRunId = useActiveViewerProductRunId()
  const [searchParams, setSearchParams] = useSearchParams()
  const { language } = useLanguage()
  const isCzech = language === 'cs'
  const t = (key: keyof typeof searchCopy): string => searchCopy[key][isCzech ? 0 : 1]
  const urlQuery = normalizeViewerSearchQuery(searchParams)
  const [query, setQuery] = useState(urlQuery)
  const hasSearchQuery = urlQuery.length > 0

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
    queryKey: ['viewer-search-canonical-players', productRunId],
    queryFn: () => getViewerPlayers(productRunId ?? ''),
    enabled: Boolean(productRunId && hasSearchQuery),
    retry: false
  })
  const countriesQuery = useQuery({
    queryKey: ['viewer-search-canonical-countries', productRunId],
    queryFn: () => getViewerCountries(productRunId ?? ''),
    enabled: Boolean(productRunId && hasSearchQuery),
    retry: false
  })
  const calendarQuery = useQuery({
    queryKey: ['viewer-search-canonical-calendar', productRunId],
    queryFn: () => getViewerRunCalendar(productRunId ?? ''),
    enabled: Boolean(productRunId && hasSearchQuery),
    retry: false
  })
  const historyQuery = useQuery({
    queryKey: ['viewer-search-canonical-tournament-history', productRunId],
    queryFn: () => getViewerTournamentHistory(productRunId ?? ''),
    enabled: Boolean(productRunId && hasSearchQuery),
    retry: false
  })

  const tournaments = useMemo<ViewerSearchTournamentResult[]>(() => {
    const resultIds = new Set(
      (historyQuery.data?.tournaments ?? [])
        .filter((event) => event.result_published)
        .map((event) => event.event_id)
    )
    return (calendarQuery.data?.seasons ?? [])
      .flatMap((season) => season.events)
      .filter((event) =>
        searchTextMatches(urlQuery, [
          event.event_id,
          event.event_name,
          event.tour_level,
          event.category,
          event.template_id,
          event.season_week,
        ])
      )
      .map((event) => ({
        eventId: event.event_id,
        season: Number.parseInt(String(event.season).split('/')[0] ?? '', 10) || null,
        week: event.season_week,
        tour: event.tour_level,
        category: event.category,
        templateId: event.template_id,
        hasPlannedEvent: true,
        hasPersistedEvent: resultIds.has(event.event_id),
      }))
  }, [calendarQuery.data?.seasons, historyQuery.data?.tournaments, urlQuery])

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

  const players = (playersQuery.data?.players ?? []).filter((player) =>
    searchTextMatches(urlQuery, [
      player.player_id,
      player.name,
      player.country_code,
      player.status,
      player.identity_source,
    ])
  )
  const countries = (countriesQuery.data?.countries ?? []).filter((country) =>
    searchTextMatches(urlQuery, [
      country.country_code,
      country.top_player_name,
      country.top_player_id,
    ])
  )
  const isLoading =
    playersQuery.isLoading ||
    countriesQuery.isLoading ||
    calendarQuery.isLoading ||
    historyQuery.isLoading
  const hasError =
    playersQuery.isError ||
    countriesQuery.isError ||
    calendarQuery.isError ||
    historyQuery.isError
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
        {!isLoading && !hasError && !hasResults ? <ViewerEmptyState>{t('noResults')}</ViewerEmptyState> : null}

        <section aria-label={t('players')}>
          <h4>{t('players')}</h4>
          {players.length ? (
            <ul className="viewer-home-list">
              {players.map((player) => (
                <li key={player.player_id}>{renderPlayerSampleMetadata(player, productRunId)}</li>
              ))}
            </ul>
          ) : <p className="status">{t('noPlayers')}</p>}
        </section>

        <section aria-label={t('countries')}>
          <h4>{t('countries')}</h4>
          {countries.length ? (
            <ul className="viewer-home-list">
              {countries.map((country) => (
                <li key={country.country_code}>{renderCountrySampleMetadata(country, productRunId)}</li>
              ))}
            </ul>
          ) : <p className="status">{t('noCountries')}</p>}
        </section>

        <section aria-label={t('tournaments')}>
          <h4>{t('tournaments')}</h4>
          {tournaments.length ? (
            <ul className="viewer-home-list">
              {tournaments.map((event) => (
                <li key={event.eventId}>{renderSearchTournamentMetadata(productRunId, event)}</li>
              ))}
            </ul>
          ) : <p className="status">{t('noTournaments')}</p>}
        </section>

        <section aria-label={t('links')}>
          <h4>{t('links')}</h4>
          <ViewerActiveRunLinks links={[{ label: t('browseRuns'), to: viewerRunsPath() }]} />
          <p className="status">{t('routeNotice')}</p>
        </section>
      </article>
    </ViewerShellPage>
  )
}
