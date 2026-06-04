import { useEffect, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useSearchParams } from 'react-router-dom'

import { getRun, listEvents, listRunNations, listRunPlayers } from '../../../api/client'
import { ViewerActiveRunLinks, ViewerEmptyState } from '../../../components/viewer/ViewerLandingComponents'
import { ViewerShellPage } from '../../../components/viewer/ViewerShellPage'
import { viewerRunsPath } from '../../../viewer/viewerRoutes'
import { useActiveViewerRunId } from '../../../viewer/useActiveViewerRunId'
import { renderCountrySampleMetadata, renderPlayerSampleMetadata } from '../people'
import { buildSearchTournamentResults, normalizeViewerSearchQuery, searchTextMatches } from './viewerComparisonDisplay'
import { renderSearchTournamentMetadata } from './viewerComparisonRender'

export function ViewerSearchPage(): JSX.Element {
  const activeRunId = useActiveViewerRunId()
  const [searchParams] = useSearchParams()
  const urlQuery = normalizeViewerSearchQuery(searchParams)
  const [query, setQuery] = useState(urlQuery)
  const hasSearchQuery = urlQuery.length > 0

  useEffect(() => {
    setQuery(urlQuery)
  }, [urlQuery])

  const playersQuery = useQuery({
    queryKey: ['viewer-search-run-players', activeRunId],
    queryFn: () => listRunPlayers(activeRunId ?? '', { limit: 50, offset: 0 }),
    enabled: Boolean(activeRunId && hasSearchQuery),
    retry: false
  })
  const nationsQuery = useQuery({
    queryKey: ['viewer-search-run-nations', activeRunId],
    queryFn: () => listRunNations(activeRunId ?? '', { limit: 50, offset: 0 }),
    enabled: Boolean(activeRunId && hasSearchQuery),
    retry: false
  })
  const runQuery = useQuery({
    queryKey: ['viewer-search-run-calendar', activeRunId],
    queryFn: () => getRun(activeRunId ?? ''),
    enabled: Boolean(activeRunId && hasSearchQuery),
    retry: false
  })
  const eventsQuery = useQuery({
    queryKey: ['viewer-search-run-events', activeRunId],
    queryFn: () => listEvents(activeRunId ?? ''),
    enabled: Boolean(activeRunId && hasSearchQuery),
    retry: false
  })

  if (!activeRunId || !hasSearchQuery) {
    return (
      <ViewerShellPage title="Search" description="Read-only Viewer Search using active-run data only.">
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
          <ViewerEmptyState>No data is available for this run yet.</ViewerEmptyState>
        </article>
      </ViewerShellPage>
    )
  }

  const players = (playersQuery.data?.players ?? []).filter((player) => searchTextMatches(urlQuery, [player.player_id, player.name, player.country_code, player.quality_band]))
  const nations = (nationsQuery.data?.nations ?? []).filter((nation) => searchTextMatches(urlQuery, [nation.country_code, nation.country_name, nation.top_player_name, nation.top_player_id]))
  const tournaments = buildSearchTournamentResults(runQuery.data?.season_state.ordered_events ?? [], eventsQuery.data?.events ?? [], urlQuery)
  const isLoading = playersQuery.isLoading || nationsQuery.isLoading || runQuery.isLoading || eventsQuery.isLoading
  const hasError = playersQuery.isError || nationsQuery.isError || runQuery.isError || eventsQuery.isError
  const hasResults = players.length > 0 || nations.length > 0 || tournaments.length > 0

  return (
    <ViewerShellPage title="Search" description="Read-only Viewer Search using active-run player, country, and tournament data only.">
      <article className="viewer-active-run-card" aria-label="Search">
        <span className="eyebrow">Active Viewer run</span>
        <h3>Search: {urlQuery}</h3>
        {isLoading ? <p className="status">Loading active run search results…</p> : null}
        {hasError ? <ViewerEmptyState>Some active run searchable metadata is temporarily unavailable.</ViewerEmptyState> : null}
        <dl className="metadata-list">
          <div><dt>Active run ID</dt><dd>{activeRunId}</dd></div>
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
                <li key={player.player_id}>{renderPlayerSampleMetadata(player, activeRunId)}</li>
              ))}
            </ul>
          ) : <p className="status">No matching players.</p>}
        </section>

        <section aria-label="Countries">
          <h4>Countries</h4>
          {nations.length ? (
            <ul className="viewer-home-list">
              {nations.map((nation) => (
                <li key={nation.country_code}>{renderCountrySampleMetadata(nation, activeRunId)}</li>
              ))}
            </ul>
          ) : <p className="status">No matching countries.</p>}
        </section>

        <section aria-label="Tournaments">
          <h4>Tournaments</h4>
          {tournaments.length ? (
            <ul className="viewer-home-list">
              {tournaments.map((event) => (
                <li key={event.eventId}>{renderSearchTournamentMetadata(activeRunId, event)}</li>
              ))}
            </ul>
          ) : <p className="status">No matching tournaments.</p>}
        </section>

        <section aria-label="Links">
          <h4>Links</h4>
          <ViewerActiveRunLinks links={[{ label: 'Open run browser', to: viewerRunsPath() }]} />
          <p className="status">Result links are shown only when player, country, event, or week IDs are available.</p>
        </section>
      </article>
    </ViewerShellPage>
  )
}
