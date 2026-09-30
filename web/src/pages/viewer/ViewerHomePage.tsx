import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'

import {
  getViewerFinalsRace,
  getViewerOfficialRunContext,
  getViewerTournamentHistory,
  listViewerOfficialRankingHistory
} from '../../api/client'
import { ViewerActiveRunLinks, ViewerEmptyState, ViewerLandingGrid, ViewerMetadataList, ViewerSectionCard } from '../../components/viewer/ViewerLandingComponents'
import { ViewerRunSelector } from '../../components/ViewerRunSelector'
import { useViewerContext } from '../../viewer/ViewerContext'
import { useActiveViewerRunId } from '../../viewer/useActiveViewerRunId'
import { useActiveViewerProductRunId } from '../../viewer/useActiveViewerProductRunId'
import {
  buildViewerHomeActiveRunLinks,
  buildViewerHomePrimaryHubLinks,
  buildViewerHomeReadOnlyNotes,
  getViewerHomeActiveRunLabel,
  normalizeViewerHomeActiveRunId
} from '../../viewer/viewerHomeDisplay'
import {
  viewerFinalsPath,
  viewerHistoryPath,
  viewerRacePath,
  viewerRankingsPath,
  viewerRunsPath,
  viewerSeasonCalendarPath,
  viewerTournamentsPath,
  viewerTournamentDetailPath
} from '../../viewer/viewerRoutes'

export function ViewerHomePage(): JSX.Element {
  const context = useViewerContext()
  const activeRunId = useActiveViewerRunId()
  const activeProductRunId = useActiveViewerProductRunId()
  const normalizedActiveRunId = normalizeViewerHomeActiveRunId(activeRunId)
  const normalizedActiveProductRunId = activeProductRunId ?? ''
  const hasProductRunId = Boolean(normalizedActiveProductRunId)
  const activeRunLinks = buildViewerHomeActiveRunLinks(normalizedActiveProductRunId)
  const primaryHubLinks = buildViewerHomePrimaryHubLinks()
  const readOnlyNotes = buildViewerHomeReadOnlyNotes()
  const activeRunLabel = getViewerHomeActiveRunLabel(normalizedActiveRunId)
  const queryEnabled = Boolean(normalizedActiveRunId && normalizedActiveProductRunId)

  const contextQuery = useQuery({
    queryKey: ['viewer-home-official-context', normalizedActiveProductRunId],
    queryFn: () => getViewerOfficialRunContext(normalizedActiveProductRunId),
    enabled: queryEnabled,
    retry: false
  })
  const tournamentsQuery = useQuery({
    queryKey: ['viewer-home-tournament-history', normalizedActiveProductRunId],
    queryFn: () => getViewerTournamentHistory(normalizedActiveProductRunId),
    enabled: queryEnabled,
    retry: false
  })
  const rankingsQuery = useQuery({
    queryKey: ['viewer-home-ranking-history', normalizedActiveProductRunId],
    queryFn: () => listViewerOfficialRankingHistory(normalizedActiveProductRunId),
    enabled: queryEnabled,
    retry: false
  })
  const raceQuery = useQuery({
    queryKey: ['viewer-home-finals-race', normalizedActiveProductRunId],
    queryFn: () => getViewerFinalsRace(normalizedActiveProductRunId),
    enabled: queryEnabled,
    retry: false
  })

  const activeQueries = [contextQuery, tournamentsQuery, rankingsQuery, raceQuery]
  const isActiveSummaryLoading = queryEnabled && activeQueries.some((query) => query.isLoading)
  const isActiveSummaryUnavailable = queryEnabled && activeQueries.some((query) => query.isError)
  const canRenderActiveRunData = queryEnabled && !isActiveSummaryLoading && !isActiveSummaryUnavailable

  const completedTournaments = (tournamentsQuery.data?.tournaments ?? []).filter((event) => event.result_published)
  const latestCompletedTournament = completedTournaments.at(-1) ?? null
  const latestRankingPublication = rankingsQuery.data?.publications.at(-1) ?? null
  const latestRacePublication =
    raceQuery.data?.latest_target_season_index == null
      ? null
      : raceQuery.data.publications.find(
          (publication) => publication.target_season_index === raceQuery.data?.latest_target_season_index
        ) ?? null

  const finalsStatus = latestRacePublication?.selection_published
    ? latestRacePublication.finals_event_id
      ? 'Selection published'
      : 'Selection published; event pending'
    : latestRacePublication
      ? 'Race published; selection pending'
      : 'Not available yet'

  return (
    <section className="panel viewer-home viewer-home--msa">
      <div className="page-intro viewer-home__hero">
        <span className="eyebrow">MSA Homepage</span>
        <h2>MSA Squash — Season {context.selectedSeason} · W{context.selectedWeek}</h2>
        <p className="subtitle">
          A public, read-only entry hub backed by canonical Viewer Saved-Revision projections.
        </p>
      </div>

      <ViewerRunSelector compact />
      <p className="viewer-active-run-actions">
        <Link className="viewer-active-run-link" to={viewerRunsPath()}>Open run browser</Link>
      </p>

      <section className="viewer-active-run-panel" aria-label="Active Viewer run status">
        {normalizedActiveRunId ? (
          <>
            <div>
              <span className="eyebrow">Active Viewer run</span>
              <h3>{activeRunLabel}</h3>
              {!hasProductRunId ? (
                <ViewerEmptyState>Select a Product Run before loading canonical Viewer summaries.</ViewerEmptyState>
              ) : null}
              {isActiveSummaryLoading ? <p className="status">Loading canonical Viewer summary…</p> : null}
              {isActiveSummaryUnavailable ? (
                <ViewerEmptyState>Active run summary is temporarily unavailable. Try opening the run pages below for more detail.</ViewerEmptyState>
              ) : null}
              {canRenderActiveRunData ? (
                <>
                  <p className="status">
                    Using Product Run <strong>{normalizedActiveProductRunId}</strong> from the selected Viewer Branch Saved Revision.
                  </p>
                  <ViewerMetadataList
                    className="viewer-home-summary-list"
                    ariaLabel="Active run summary fields"
                    items={[
                      { label: 'Product Run', value: contextQuery.data?.product_run_display_name ?? normalizedActiveProductRunId },
                      { label: 'Viewer Branch', value: tournamentsQuery.data?.viewer_branch_id ?? rankingsQuery.data?.viewer_branch_id ?? raceQuery.data?.viewer_branch_id ?? 'Not available yet' },
                      { label: 'Current season', value: contextQuery.data?.current_season ?? 'Not available yet' },
                      { label: 'Current week', value: contextQuery.data?.current_week ?? 'Not available yet' },
                      { label: 'Completed tournaments', value: tournamentsQuery.data?.published_result_count ?? 0 },
                      { label: 'Ranking publications', value: rankingsQuery.data?.publication_count ?? 0 },
                      { label: 'Finals', value: finalsStatus }
                    ]}
                  />
                </>
              ) : null}
            </div>

            <ViewerActiveRunLinks
              layout="grid"
              links={hasProductRunId ? activeRunLinks : []}
            />
            {!hasProductRunId ? <p className="status">Select a Product Run before opening run-scoped pages.</p> : null}
          </>
        ) : (
          <ViewerEmptyState>No active Viewer run selected. Open the run browser to choose a run before using run-scoped shortcuts.</ViewerEmptyState>
        )}
      </section>

      <ViewerLandingGrid>
        <ViewerSectionCard kicker="Canonical tournament" title="Latest Completed Tournament" variant="hero">
          {canRenderActiveRunData && latestCompletedTournament ? (
            <>
              <p>
                <Link to={viewerTournamentDetailPath(normalizedActiveProductRunId, latestCompletedTournament.event_id)}>
                  {latestCompletedTournament.event_name || latestCompletedTournament.event_id}
                </Link>
                {' · '}{latestCompletedTournament.season} W{latestCompletedTournament.season_week}
              </p>
              <p className="status">
                Champion {latestCompletedTournament.champion_player_id ?? 'Unavailable'} · Finalist {latestCompletedTournament.finalist_player_id ?? 'Unavailable'}
              </p>
              <Link className="viewer-active-run-link" to={viewerTournamentsPath(normalizedActiveProductRunId)}>
                Open active run tournaments
              </Link>
            </>
          ) : (
            <ViewerEmptyState>No completed canonical Tournament Result is published for this run yet.</ViewerEmptyState>
          )}
        </ViewerSectionCard>

        <ViewerSectionCard kicker="Canonical schedule" title="Season Schedule">
          <p className="status">
            Schedule browsing stays on the canonical run-scoped calendar surface; Viewer Home does not reconstruct unpublished Working Draft plans.
          </p>
          {hasProductRunId ? (
            <Link className="viewer-active-run-link" to={viewerSeasonCalendarPath(normalizedActiveProductRunId)}>
              Open active run schedule
            </Link>
          ) : null}
        </ViewerSectionCard>

        <ViewerSectionCard kicker="Canonical rankings" title="Official Ranking Publications">
          {canRenderActiveRunData && latestRankingPublication ? (
            <p>
              Latest Official Ranking: Season {latestRankingPublication.season_index} W{latestRankingPublication.week}
              {' · '}ordinal {latestRankingPublication.week_ordinal}
              {' · '}{latestRankingPublication.row_count} players
              {' · '}{rankingsQuery.data?.publication_count ?? 0} publications
            </p>
          ) : (
            <ViewerEmptyState>No canonical Official Ranking publication is available for this run yet.</ViewerEmptyState>
          )}
          {hasProductRunId ? (
            <Link className="viewer-active-run-link" to={viewerRankingsPath(normalizedActiveProductRunId)}>
              Open active run rankings
            </Link>
          ) : null}
        </ViewerSectionCard>

        <ViewerSectionCard kicker="Canonical race" title="World Tour Finals Race">
          {canRenderActiveRunData && latestRacePublication ? (
            <p>
              Target season {latestRacePublication.target_season_index}
              {' · '}cutoff season {latestRacePublication.cutoff_season_index} W{latestRacePublication.cutoff_week}
              {' · '}{latestRacePublication.rows.length} players
              {' · '}{latestRacePublication.selection_published ? 'selection published' : 'selection pending'}
            </p>
          ) : (
            <ViewerEmptyState>No canonical World Tour Finals Race publication is available for this run yet.</ViewerEmptyState>
          )}
          {hasProductRunId ? (
            <>
              <Link className="viewer-active-run-link" to={viewerRacePath(normalizedActiveProductRunId)}>
                Open active run race
              </Link>
              {' · '}
              <Link className="viewer-active-run-link" to={viewerFinalsPath(normalizedActiveProductRunId)}>
                Open World Tour Finals
              </Link>
            </>
          ) : null}
        </ViewerSectionCard>

        <ViewerSectionCard kicker="Read-only matches" title="Featured Matches">
          <ViewerEmptyState>This preview is not connected to a canonical Home read model yet.</ViewerEmptyState>
          {hasProductRunId ? <Link className="viewer-active-run-link" to={viewerTournamentsPath(normalizedActiveProductRunId)}>Open active run tournaments</Link> : null}
        </ViewerSectionCard>

        <ViewerSectionCard kicker="Read-only analytics" title="Predictions &amp; Upset Watch">
          <ViewerEmptyState>This preview is not connected to a canonical Home read model yet.</ViewerEmptyState>
        </ViewerSectionCard>

        <ViewerSectionCard kicker="Viewer surfaces" title="Viewer hub links">
          <p className="status">Open read-only Viewer pages without changing simulation state.</p>
          <ul className="viewer-home-list" aria-label="Viewer Home top-level hub links">
            {primaryHubLinks.map((link) => (
              <li key={`${link.label}:${link.to}`}>
                <Link to={link.to}>{link.label}</Link>{link.description ? <> · {link.description}</> : null}
              </li>
            ))}
          </ul>
        </ViewerSectionCard>

        <ViewerSectionCard kicker="Read-only safety" title="What this hub does not infer">
          <ul className="viewer-home-list" aria-label="Viewer Home read-only notes">
            {readOnlyNotes.map((note) => <li key={note}>{note}</li>)}
          </ul>
        </ViewerSectionCard>

        <ViewerSectionCard kicker="Canonical history" title="History">
          {canRenderActiveRunData ? (
            <p>
              {completedTournaments.length} completed tournaments · {rankingsQuery.data?.publication_count ?? 0} ranking publications · {raceQuery.data?.publications.length ?? 0} Finals Race publications.
            </p>
          ) : (
            <ViewerEmptyState>No canonical history summary is available for this run yet.</ViewerEmptyState>
          )}
          {hasProductRunId ? <Link className="viewer-active-run-link" to={viewerHistoryPath(normalizedActiveProductRunId)}>Open active run history</Link> : null}
        </ViewerSectionCard>
      </ViewerLandingGrid>
    </section>
  )
}
