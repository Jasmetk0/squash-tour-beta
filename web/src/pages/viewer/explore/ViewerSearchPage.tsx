import { useEffect, useMemo, useState } from 'react'
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
import { useActiveViewerProductRunId } from '../../../viewer/useActiveViewerProductRunId'
import { viewerRunsPath } from '../../../viewer/viewerRoutes'
import { renderCountrySampleMetadata, renderPlayerSampleMetadata } from '../people'
import { normalizeViewerSearchQuery, searchTextMatches, type ViewerSearchTournamentResult } from './viewerComparisonDisplay'
import { renderSearchTournamentMetadata } from './viewerComparisonRender'

export function ViewerSearchPage(): JSX.Element {
  const productRunId = useActiveViewerProductRunId()
  const [searchParams] = useSearchParams()
  const urlQuery = normalizeViewerSearchQuery(searchParams)
  const [query, setQuery] = useState(urlQuery)
  const hasSearchQuery = urlQuery.length > 0

  useEffect(() => {
    setQuery(urlQuery)
  }, [urlQuery])

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
      <ViewerShellPage title="Search" description="Read-only Viewer Search using canonical Product Run data only.">
        <article className="viewer-active-run-card" aria-label="Search">
          <span className="eyebrow">Viewer search</span>
          <h3>Search{urlQuery ? `: ${urlQuery}` : ''}</h3>
          <label className="field-label" htmlFor="viewer-search-shell-input">Search</label>
          <input
            id="viewer-search-shell-input"
            aria-label="Read-only Viewer search shell"
            placeholder="Search players, countries, tournaments…"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
          />
          <ViewerEmptyState>No Product Run search context is available yet.</ViewerEmptyState>
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
    <ViewerShellPage title="Search" description="Read-only Viewer Search using canonical Saved-Revision player, country, and tournament data.">
      <article className="viewer-active-run-card" aria-label="Search">
        <span className="eyebrow">Selected Product Run</span>
        <h3>Search: {urlQuery}</h3>
        {isLoading ? <p className="status">Loading canonical search results…</p> : null}
        {hasError ? <ViewerEmptyState>Some canonical searchable metadata is temporarily unavailable.</ViewerEmptyState> : null}
        <dl className="metadata-list">
          <div><dt>Product Run</dt><dd>{productRunId}</dd></div>
          <div><dt>Query</dt><dd>{urlQuery}</dd></div>
        </dl>
        <label className="field-label" htmlFor="viewer-search-shell-input">Search</label>
        <input
          id="viewer-search-shell-input"
          aria-label="Read-only Viewer search shell"
          placeholder="Search players, countries, tournaments…"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
        />
        {!isLoading && !hasError && !hasResults ? <ViewerEmptyState>No matching Viewer results found.</ViewerEmptyState> : null}

        <section aria-label="Players">
          <h4>Players</h4>
          {players.length ? (
            <ul className="viewer-home-list">
              {players.map((player) => (
                <li key={player.player_id}>{renderPlayerSampleMetadata(player, productRunId)}</li>
              ))}
            </ul>
          ) : <p className="status">No matching players.</p>}
        </section>

        <section aria-label="Countries">
          <h4>Countries</h4>
          {countries.length ? (
            <ul className="viewer-home-list">
              {countries.map((country) => (
                <li key={country.country_code}>{renderCountrySampleMetadata(country, productRunId)}</li>
              ))}
            </ul>
          ) : <p className="status">No matching countries.</p>}
        </section>

        <section aria-label="Tournaments">
          <h4>Tournaments</h4>
          {tournaments.length ? (
            <ul className="viewer-home-list">
              {tournaments.map((event) => (
                <li key={event.eventId}>{renderSearchTournamentMetadata(productRunId, event)}</li>
              ))}
            </ul>
          ) : <p className="status">No matching tournaments.</p>}
        </section>

        <section aria-label="Links">
          <h4>Links</h4>
          <ViewerActiveRunLinks links={[{ label: 'Open run browser', to: viewerRunsPath() }]} />
          <p className="status">Result links use canonical Product Run routes.</p>
        </section>
      </article>
    </ViewerShellPage>
  )
}
