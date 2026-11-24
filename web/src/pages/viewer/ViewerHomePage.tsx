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
import { currentRankingViewerBranch } from './rankings/currentOfficialRanking'
import { verifiedHomeSources } from './viewerHomePublicSources'
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
    retry: false,
    refetchOnWindowFocus: true,
  })
  const branchId = currentRankingViewerBranch(contextQuery.data, normalizedActiveProductRunId)
  const sourceReady = Boolean(queryEnabled && branchId && !contextQuery.isPending &&
    !contextQuery.isFetching && !contextQuery.isError)

  // Bind all public GETs to the selected Run and authenticated Saved Branch.
  // Never render a cached or delayed prior-Branch response during a switch.
  const tournamentsQuery = useQuery({
    queryKey: ['viewer-home-tournament-history', normalizedActiveProductRunId, branchId],
    queryFn: () => getViewerTournamentHistory(normalizedActiveProductRunId),
    enabled: sourceReady, retry: false, refetchOnWindowFocus: false,
  })
  const rankingsQuery = useQuery({
    queryKey: ['viewer-home-ranking-history', normalizedActiveProductRunId, branchId],
    queryFn: () => listViewerOfficialRankingHistory(normalizedActiveProductRunId),
    enabled: sourceReady, retry: false, refetchOnWindowFocus: false,
  })
  const raceQuery = useQuery({
    queryKey: ['viewer-home-finals-race', normalizedActiveProductRunId, branchId],
    queryFn: () => getViewerFinalsRace(normalizedActiveProductRunId),
    enabled: sourceReady, retry: false, refetchOnWindowFocus: false,
  })
  const sourceQueries = [tournamentsQuery, rankingsQuery, raceQuery]
  const isActiveSummaryLoading = queryEnabled && (
    contextQuery.isPending || contextQuery.isFetching ||
    (sourceReady && sourceQueries.some(q => q.isPending || q.isFetching))
  )
  const isActiveSummaryUnavailable = queryEnabled && (
    contextQuery.isError || (sourceReady && sourceQueries.some(q => q.isError))
  )
  const isActiveSummaryContextInvalid = queryEnabled && !isActiveSummaryLoading &&
    !isActiveSummaryUnavailable && !branchId
  const verified = sourceReady && !isActiveSummaryLoading && !isActiveSummaryUnavailable
    ? verifiedHomeSources(
      tournamentsQuery.data, rankingsQuery.data, raceQuery.data,
      normalizedActiveProductRunId, branchId ?? '',
    ) : null
  const canRenderActiveRunData = Boolean(verified)
  const isActiveSummaryInvalid = sourceReady && !isActiveSummaryLoading &&
    !isActiveSummaryUnavailable && !verified

  // These legacy W61 projections are publications, not live predictions.
  const completedTournaments = verified?.publishedTournaments ?? []
  const latestCompletedTournament = verified?.latestPublishedTournament ?? null
  const latestRankingPublication = verified?.latestRankingPublication ?? null
  const latestRacePublication = verified?.latestRacePublication ?? null
  const unavailablePreview = hasProductRunId && !canRenderActiveRunData

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
              {isActiveSummaryContextInvalid || isActiveSummaryInvalid ? (
                <ViewerEmptyState>Saved Viewer Branch or public histories do not agree. The Home summary is withheld; open the detailed pages to check the source.</ViewerEmptyState>
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
                      { label: 'Viewer Branch', value: branchId ?? 'Not available yet' },
                      { label: 'Current season', value: contextQuery.data?.current_season ?? 'Not available yet' },
                      { label: 'Current week', value: contextQuery.data?.current_week ?? 'Not available yet' },
                      { label: 'Completed tournaments', value: verified?.publishedTournaments.length ?? 0 },
                      { label: 'Ranking publications', value: verified?.rankingPublicationCount ?? 0 },
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
            <ViewerEmptyState>{unavailablePreview ? 'Tournament preview unavailable until the Saved sources are verified.' : 'No completed canonical Tournament Result is published for this run yet.'}</ViewerEmptyState>
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
              {' · '}{verified?.rankingPublicationCount ?? 0} publications
            </p>
          ) : (
            <ViewerEmptyState>{unavailablePreview ? 'Ranking preview unavailable until the Saved sources are verified.' : 'No canonical Official Ranking publication is available for this run yet.'}</ViewerEmptyState>
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
            <ViewerEmptyState>{unavailablePreview ? 'Finals Race preview unavailable until the Saved sources are verified.' : 'No canonical World Tour Finals Race publication is available for this run yet.'}</ViewerEmptyState>
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
              {completedTournaments.length} completed tournaments · {verified?.rankingPublicationCount ?? 0} ranking publications · {verified?.racePublicationCount ?? 0} Finals Race publications.
            </p>
          ) : (
            <ViewerEmptyState>{unavailablePreview ? 'History preview unavailable until the Saved sources are verified.' : 'No canonical history summary is available for this run yet.'}</ViewerEmptyState>
          )}
          {hasProductRunId ? <Link className="viewer-active-run-link" to={viewerHistoryPath(normalizedActiveProductRunId)}>Open active run history</Link> : null}
        </ViewerSectionCard>
      </ViewerLandingGrid>
    </section>
  )
}
