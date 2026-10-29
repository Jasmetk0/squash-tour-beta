import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'

import {
  getViewerFinalsRace, getViewerTournamentHistory, listViewerOfficialRankingHistory
} from '../../../api/client'
import { useLanguage, type Language } from '../../../i18n/LanguageContext'
import { useActiveViewerProductRunId } from '../../../viewer/useActiveViewerProductRunId'
import { useViewerOfficialRunContext } from '../../../viewer/useViewerOfficialRunContext'
import {
  viewerFinalsPath, viewerHistoryPath, viewerPlannedEventPath, viewerRacePath,
  viewerRankingSnapshotPath, viewerRankingsPath, viewerRunsPath, viewerTournamentsPath
} from '../../../viewer/viewerRoutes'
import { rankingSeasonLabel, verifiedSavedHistory } from './viewerSavedHistorySummary'

const copy = {
  title: ['Historie', 'History'],
  subtitle: ['Ověřený přehled zveřejněných historických dat vybrané Viewer Branch.', 'Verified overview of published historical data from the selected Viewer Branch.'],
  scopeTitle: ['Publikovaná historie', 'Published history'],
  run: ['Product Run', 'Product Run'],
  branch: ['Viewer Branch', 'Viewer Branch'],
  tournamentTotal: ['Turnaje v kalendáři', 'Scheduled tournaments'],
  tournaments: ['Publikované výsledky turnajů', 'Published tournament results'],
  rankings: ['Publikované Official Rankingy', 'Published Official Rankings'],
  race: ['Sezónní publikace Finals Race', 'Seasonal Finals Race publications'],
  noRun: ['Není vybraný žádný Product Run.', 'No Product Run is selected.'],
  chooseRun: ['Vybrat Product Run', 'Choose Product Run'],
  resolving: ['Ověřuji uloženou Viewer Branch…', 'Resolving saved Viewer Branch…'],
  loading: ['Načítám uložené publikace…', 'Loading saved publications…'],
  contextError: ['Ověření Viewer Branch není dostupné.', 'Viewer Branch context is unavailable.'],
  invalidContext: ['Kontext neodpovídá vybranému Product Runu a Viewer Branch.', 'Context does not match the selected Product Run and Viewer Branch.'],
  readError: ['Jedna nebo více historických publikací není dostupných. Částečný souhrn se nezobrazuje.', 'One or more historical publications are unavailable. No partial summary is displayed.'],
  corrupt: ['Zdroje historie si neodpovídají nebo obsahují neplatnou publikaci. Částečný souhrn se nezobrazuje.', 'History sources disagree or contain an invalid publication. No partial summary is displayed.'],
  retry: ['Načíst znovu (pouze GET)', 'Retry read (GET only)'],
  empty: ['V této uložené větvi zatím nejsou publikované sportovní výsledky.', 'No sporting results have been published in this Saved Branch yet.'],
  recentTitle: ['Poslední publikované záznamy', 'Latest published records'],
  latestTournament: ['Poslední výsledek turnaje', 'Latest tournament result'],
  latestRanking: ['Poslední Official Ranking', 'Latest Official Ranking'],
  latestRace: ['Poslední Finals Race', 'Latest Finals Race'],
  none: ['Zatím nepublikováno', 'Not published yet'],
  season: ['Sezona', 'Season'],
  week: ['týden', 'week'],
  openHistory: ['Historie vybraného Runu', 'Full run history'],
  openTournaments: ['Turnaje', 'Tournaments'],
  openRankings: ['Historie rankingů', 'Ranking history'],
  openFinals: ['World Tour Finals', 'World Tour Finals']
} as const
type Copy = Record<keyof typeof copy, string>
function words(language: Language): Copy {
  const i = language === 'cs' ? 0 : 1
  return Object.fromEntries(Object.entries(copy).map(([key, values]) => [key, values[i]])) as Copy
}

function HistoryForBranch({ runId, branchId, t }: { runId: string; branchId: string; t: Copy }): JSX.Element {
  const tournamentsQuery = useQuery({
    queryKey: ['viewer-top-history-tournaments', runId, branchId],
    queryFn: () => getViewerTournamentHistory(runId),
    retry: false,
    refetchOnWindowFocus: false
  })
  const rankingsQuery = useQuery({
    queryKey: ['viewer-top-history-rankings', runId, branchId],
    queryFn: () => listViewerOfficialRankingHistory(runId),
    retry: false,
    refetchOnWindowFocus: false
  })
  const raceQuery = useQuery({
    queryKey: ['viewer-top-history-finals-race', runId, branchId],
    queryFn: () => getViewerFinalsRace(runId),
    retry: false,
    refetchOnWindowFocus: false
  })
  function retryReaders(): void {
    void Promise.all([tournamentsQuery.refetch(), rankingsQuery.refetch(), raceQuery.refetch()])
  }
  if (tournamentsQuery.isPending || rankingsQuery.isPending || raceQuery.isPending) {
    return <p className="status" role="status">{t.loading}</p>
  }
  if (tournamentsQuery.isError || rankingsQuery.isError || raceQuery.isError) {
    return <div role="alert"><p className="error">{t.readError}</p><button type="button" onClick={retryReaders}>{t.retry}</button></div>
  }
  const summary = verifiedSavedHistory(
    tournamentsQuery.data, rankingsQuery.data, raceQuery.data, runId, branchId
  )
  if (!summary) return <div role="alert"><p className="error">{t.corrupt}</p><button type="button" onClick={retryReaders}>{t.retry}</button></div>

  const hasPublications = summary.publishedTournamentCount + summary.rankingCount + summary.raceCount > 0
  return (
    <>
      <dl aria-label={t.scopeTitle} className="metadata-list viewer-metadata-list">
        <div><dt>{t.run}</dt><dd>{runId}</dd></div>
        <div><dt>{t.branch}</dt><dd>{branchId}</dd></div>
        <div><dt>{t.tournamentTotal}</dt><dd>{summary.tournamentCount}</dd></div>
        <div><dt>{t.tournaments}</dt><dd>{summary.publishedTournamentCount}</dd></div>
        <div><dt>{t.rankings}</dt><dd>{summary.rankingCount}</dd></div>
        <div><dt>{t.race}</dt><dd>{summary.raceCount}</dd></div>
      </dl>
      {!hasPublications ? <p className="empty-state">{t.empty}</p> : (
        <section aria-label={t.recentTitle}>
          <h4>{t.recentTitle}</h4>
          <dl className="metadata-list">
            <div>
              <dt>{t.latestTournament}</dt>
              <dd>{summary.lastTournament ?
                <Link to={viewerPlannedEventPath(runId, summary.lastTournament.event_id)}>
                  {summary.lastTournament.event_name || summary.lastTournament.event_id} · {summary.lastTournament.season} · W{summary.lastTournament.season_week}
                </Link> : t.none}</dd>
            </div>
            <div>
              <dt>{t.latestRanking}</dt>
              <dd>{summary.lastRanking ?
                <Link to={viewerRankingSnapshotPath(runId, summary.lastRanking.week_ordinal)}>
                  {rankingSeasonLabel(summary.lastRanking.season_index)} · W{summary.lastRanking.week} · {summary.lastRanking.policy_id}
                </Link> : t.none}</dd>
            </div>
            <div>
              <dt>{t.latestRace}</dt>
              <dd>{summary.latestRaceSeason !== null ?
                <Link to={viewerRacePath(runId)}>{rankingSeasonLabel(summary.latestRaceSeason)}</Link> : t.none}</dd>
            </div>
          </dl>
        </section>
      )}
      <nav aria-label={t.scopeTitle} className="viewer-active-run-actions">
        <Link className="viewer-active-run-link" to={viewerHistoryPath(runId)}>{t.openHistory}</Link>{' '}
        <Link className="viewer-active-run-link" to={viewerTournamentsPath(runId)}>{t.openTournaments}</Link>{' '}
        <Link className="viewer-active-run-link" to={viewerRankingsPath(runId)}>{t.openRankings}</Link>{' '}
        <Link className="viewer-active-run-link" to={viewerFinalsPath(runId)}>{t.openFinals}</Link>
      </nav>
    </>
  )
}

export function ViewerHistoryPage(): JSX.Element {
  const runId = useActiveViewerProductRunId()?.trim() ?? ''
  const { language } = useLanguage()
  const t = words(language)
  const context = useViewerOfficialRunContext(runId)
  const data = context.data
  const branchId = data?.product_run_id === runId &&
    typeof data?.official_branch_id === 'string' && data.official_branch_id.trim()
    ? data.official_branch_id : null

  return (
    <section className="panel viewer-shell-page">
      <div className="page-intro">
        <h2>{t.title}</h2>
        <p className="subtitle">{t.subtitle}</p>
      </div>
      <article className="viewer-active-run-card" aria-label={t.scopeTitle}>
        <h3>{t.scopeTitle}</h3>
        {!runId ? <p className="empty-state">{t.noRun} <Link to={viewerRunsPath()}>{t.chooseRun}</Link></p> :
          context.isPending || context.isFetching ? <p className="status" role="status">{t.resolving}</p> :
          context.isError ? <div role="alert"><p className="error">{t.contextError}</p><button type="button" onClick={() => void context.refetch()}>{t.retry}</button></div> :
          !branchId ? <div role="alert"><p className="error">{t.invalidContext}</p><button type="button" onClick={() => void context.refetch()}>{t.retry}</button></div> :
          <HistoryForBranch key={JSON.stringify([runId, branchId])} runId={runId} branchId={branchId} t={t} />}
      </article>
    </section>
  )
}
