import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'

import { getViewerFinalsRace, getViewerRunCalendar, getViewerTournamentHistory } from '../../../api/client'
import { ViewerEmptyState } from '../../../components/viewer/ViewerLandingComponents'
import { ViewerShellPage } from '../../../components/viewer/ViewerShellPage'
import { useLanguage } from '../../../i18n/LanguageContext'
import { useActiveViewerProductRunId } from '../../../viewer/useActiveViewerProductRunId'
import { useViewerOfficialRunContext } from '../../../viewer/useViewerOfficialRunContext'
import { ViewerSignedSeasonComparison } from './ViewerSignedSeasonComparison'
import { raceSeasonsNewestFirst, validViewerRaceHistory } from '../rankings/finalsRaceBrowsing'
import { savedCalendarViewerBranch } from './savedCalendarBrowsing'
import { verifiedTournamentCatalog, type SavedTournamentEntry } from './viewerTournamentCatalog'
import {
  viewerFinalsPath,
  viewerPlannedEventPath,
  viewerRunsPath,
  viewerSeasonCalendarPath,
  viewerTournamentDetailPath,
  viewerTournamentsPath,
} from '../../../viewer/viewerRoutes'

const copy = {
  title: ['Přehled Tour a sezon', 'Season Hub'],
  description: ['Přehled pouze ověřených veřejných dat uložené Viewer Branch. Není to aktuální pracovní koncept Adminu.', 'Summary of verified public data from one Saved Viewer Branch, not the Admin Working Draft.'],
  selectRun: ['Nejprve vyber Product Run.', 'Select a Product Run first.'],
  contextLoading: ['Ověřuji uloženou Viewer Branch…', 'Verifying saved Viewer Branch…'],
  contextError: ['Vybraný Run nemá ověřenou Viewer Branch.', 'The selected Run has no verified Viewer Branch.'],
  loading: ['Načítám uložený kalendář, výsledky a Finals Race…', 'Loading Saved calendar, results and Finals Race…'],
  readError: ['Alespoň jeden uložený veřejný zdroj není dostupný. Souhrn se nezobrazuje.', 'At least one Saved public source is unavailable. No summary is shown.'],
  invalid: ['Uložené zdroje neodpovídají stejné Viewer Branch nebo obsahují neplatná data. Souhrn se nezobrazuje.', 'Saved sources do not agree on one Viewer Branch or contain invalid data. No summary is shown.'],
  retry: ['Načíst znovu (GET)', 'Retry reads (GET)'],
  eyebrow: ['Ověřený Product Run', 'Verified Product Run'],
  summary: ['Přehled uložené Tour', 'Saved Tour summary'],
  run: ['Product Run', 'Product Run'],
  branch: ['Viewer Branch', 'Viewer Branch'],
  seasons: ['Počet uložených sezon', 'Saved season count'],
  events: ['Události v kalendáři', 'Calendar events'],
  results: ['Publikované výsledky turnajů', 'Published tournament results'],
  unpublished: ['První událost bez publikovaného výsledku', 'First event without a published result'],
  latest: ['Poslední publikovaný výsledek', 'Latest published result'],
  finals: ['Poslední publikace Finals Race', 'Latest Finals Race publication'],
  noFinals: ['Zatím nepublikováno', 'Not published yet'],
  noEvents: ['V uložené Tour nejsou žádné turnaje.', 'No tournaments exist in this Saved Tour.'],
  sourceScope: ['Událost bez publikovaného výsledku nemusí být příští skutečně hraný turnaj. Kalendář není živé skóre.', 'An event without a published result is not necessarily the next event played. The calendar is not a live score feed.'],
  tournaments: ['Otevřít turnaje Runu', 'Open Product Run tournaments'],
  schedule: ['Otevřít kalendář Runu', 'Open Product Run schedule'],
  finalsLink: ['Otevřít Finals Runu', 'Open Product Run finals'],
  runs: ['Otevřít přehled Runů', 'Open run browser'],
} as const

function seasonOrder(a: SavedTournamentEntry, b: SavedTournamentEntry): number {
  return String(a.event.season).localeCompare(String(b.event.season), undefined, { numeric: true }) ||
    a.event.season_week - b.event.season_week ||
    a.event.event_id.localeCompare(b.event.event_id)
}

export function ViewerSeasonHubPage(): JSX.Element {
  const runId = useActiveViewerProductRunId()?.trim() ?? ''
  const { language } = useLanguage()
  const t = (key: keyof typeof copy): string => copy[key][language === 'cs' ? 0 : 1]
  const context = useViewerOfficialRunContext(runId)
  const branchId = savedCalendarViewerBranch(context.data, runId)
  const ready = Boolean(runId && branchId && !context.isPending &&
    !context.isFetching && !context.isError)

  // All three Saved readers are bound to one verified Run and Viewer Branch.
  // Old-Branch cached responses can never be displayed under a new source.
  const calendarQuery = useQuery({
    queryKey: ['viewer-season-hub-calendar', runId, branchId],
    queryFn: () => getViewerRunCalendar(runId),
    enabled: ready, retry: false, refetchOnWindowFocus: false,
  })
  const historyQuery = useQuery({
    queryKey: ['viewer-season-hub-history', runId, branchId],
    queryFn: () => getViewerTournamentHistory(runId),
    enabled: ready, retry: false, refetchOnWindowFocus: false,
  })
  const finalsQuery = useQuery({
    queryKey: ['viewer-season-hub-finals-race', runId, branchId],
    queryFn: () => getViewerFinalsRace(runId),
    enabled: ready, retry: false, refetchOnWindowFocus: false,
  })
  const loading = calendarQuery.isPending || calendarQuery.isFetching ||
    historyQuery.isPending || historyQuery.isFetching ||
    finalsQuery.isPending || finalsQuery.isFetching
  const failed = calendarQuery.isError || historyQuery.isError || finalsQuery.isError
  const catalog = ready && !loading && !failed
    ? verifiedTournamentCatalog(calendarQuery.data, historyQuery.data, runId, branchId ?? '')
    : null
  const finalsHistory = ready && !loading && !failed &&
    validViewerRaceHistory(finalsQuery.data, runId, branchId ?? '')
    ? finalsQuery.data : null
  const verified = Boolean(catalog && finalsHistory)
  const ascending = catalog ? [...catalog.entries].sort(seasonOrder) : []
  const firstUnpublished = ascending.find(item => !item.publication.result_published) ?? null
  const latestPublished = [...ascending].reverse().find(item => item.publication.result_published) ?? null
  const latestFinals = finalsHistory ? raceSeasonsNewestFirst(finalsHistory)[0] ?? null : null

  function retrySources(): void {
    void Promise.all([calendarQuery.refetch(), historyQuery.refetch(), finalsQuery.refetch()])
  }

  return (
    <ViewerShellPage title={t('title')} description={t('description')}>
      {!runId ? <ViewerEmptyState>{t('selectRun')}</ViewerEmptyState> : (
        <article className="viewer-active-run-card" aria-label={t('summary')}>
          {context.isPending || context.isFetching ? (
            <p className="status" role="status">{t('contextLoading')}</p>
          ) : !ready ? (
            <div role="alert"><p>{t('contextError')}</p>
              <button type="button" onClick={() => void context.refetch()}>{t('retry')}</button>
            </div>
          ) : loading ? (
            <p className="status" role="status">{t('loading')}</p>
          ) : failed ? (
            <div role="alert"><p>{t('readError')}</p>
              <button type="button" onClick={retrySources}>{t('retry')}</button>
            </div>
          ) : !verified || !catalog ? (
            <div role="alert"><p>{t('invalid')}</p>
              <button type="button" onClick={retrySources}>{t('retry')}</button>
            </div>
          ) : (
            <>
              <span className="eyebrow">{t('eyebrow')}</span>
              <h3>{t('summary')}</h3>
              <dl className="metadata-list">
                <div><dt>{t('run')}</dt><dd>{runId}</dd></div>
                <div><dt>{t('branch')}</dt><dd>{branchId}</dd></div>
                <div><dt>{t('seasons')}</dt><dd>{catalog.seasons.length}</dd></div>
                <div><dt>{t('events')}</dt><dd>{catalog.eventCount}</dd></div>
                <div><dt>{t('results')}</dt><dd>{catalog.publishedCount}</dd></div>
                <div><dt>{t('unpublished')}</dt><dd>{firstUnpublished
                  ? <Link to={viewerPlannedEventPath(runId, firstUnpublished.event.event_id)}>
                      {firstUnpublished.event.event_name || firstUnpublished.event.event_id}
                    </Link> : '—'}</dd></div>
                <div><dt>{t('latest')}</dt><dd>{latestPublished
                  ? <Link to={viewerTournamentDetailPath(runId, latestPublished.event.event_id)}>
                      {latestPublished.event.event_name || latestPublished.event.event_id}
                    </Link> : '—'}</dd></div>
                <div><dt>{t('finals')}</dt><dd>{latestFinals
                  ? `S${latestFinals.target_season_index} · cutoff S${latestFinals.cutoff_season_index} W${latestFinals.cutoff_week}`
                  : t('noFinals')}</dd></div>
              </dl>
              {catalog.eventCount === 0 ? <ViewerEmptyState>{t('noEvents')}</ViewerEmptyState> : null}
              <p className="status">{t('sourceScope')}</p>
              {firstUnpublished ? <p className="status">
                {String(firstUnpublished.event.season)} · W{firstUnpublished.event.season_week}
                {' · '}{firstUnpublished.event.category} · {firstUnpublished.event.tour_level ?? '—'}
              </p> : null}
              <p className="viewer-active-run-actions">
                <Link className="viewer-active-run-link" to={viewerTournamentsPath(runId)}>{t('tournaments')}</Link>{' '}
                <Link className="viewer-active-run-link" to={viewerSeasonCalendarPath(runId)}>{t('schedule')}</Link>{' '}
                <Link className="viewer-active-run-link" to={viewerFinalsPath(runId)}>{t('finalsLink')}</Link>{' '}
                <Link className="viewer-active-run-link" to={viewerRunsPath()}>{t('runs')}</Link>
              </p>
            </>
          )}
        </article>
      )}
      {ready && verified ? <ViewerSignedSeasonComparison key={JSON.stringify([runId, branchId])} runId={runId} /> : null}
    </ViewerShellPage>
  )
}
