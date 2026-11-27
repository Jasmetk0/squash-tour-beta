import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'

import { getViewerRunCalendar } from '../../../api/client'
import { ViewerEmptyState } from '../../../components/viewer/ViewerLandingComponents'
import { ViewerShellPage } from '../../../components/viewer/ViewerShellPage'
import { useLanguage } from '../../../i18n/LanguageContext'
import { useViewerContext } from '../../../viewer/ViewerContext'
import { useActiveViewerProductRunId } from '../../../viewer/useActiveViewerProductRunId'
import { useViewerOfficialRunContext } from '../../../viewer/useViewerOfficialRunContext'
import { viewerPlannedEventPath, viewerRunsPath, viewerSeasonCalendarPath } from '../../../viewer/viewerRoutes'
import {
  savedCalendarEventCoversWeek, savedCalendarSeasonKey, savedCalendarViewerBranch, verifiedSavedSeasonCalendar,
} from './savedCalendarBrowsing'

const copy = {
  title: ['Vybraný týden', 'Current Week'],
  description: [
    'Rozpis vybraného týdne z nejnovějšího uloženého kalendáře Viewer Branch; nejde o historický stav ani živé výsledky.',
    'Selected-week schedule from the latest Saved Viewer Branch calendar; not historical as-of state or live results.',
  ],
  selectRun: ['Nejprve vyber Product Run.', 'Select a Product Run first.'],
  resolving: ['Ověřuji uloženou Viewer Branch…', 'Verifying the saved Viewer Branch…'],
  contextError: ['Viewer Branch neodpovídá vybranému Runu nebo ji nelze ověřit.', 'Viewer Branch does not match the selected Run or cannot be verified.'],
  retry: ['Načíst znovu (GET)', 'Retry read (GET)'],
  loading: ['Načítám uložený kalendář…', 'Loading Saved calendar…'],
  readError: ['Uložený kalendář není dostupný.', 'Saved calendar is unavailable.'],
  invalid: ['Kalendář patří jinému Runu/Viewer Branch nebo má neplatná veřejná data. Události se nezobrazují.', 'Calendar belongs to another Run/Viewer Branch or contains invalid public data. No events are shown.'],
  selected: ['Vybraný týden Vieweru', 'Selected Viewer week'],
  historicalLimit: ['Zdroj neobsahuje čas zveřejnění ani historické verze rozpisu. Stav turnajů k vybranému týdnu proto nezobrazujeme; odkazy vedou na aktuálně uložené údaje.', 'This source has no publication timestamp or historical schedule versions. Tournament status as of the selected week is therefore not shown; links open the currently Saved data.'],
  season: ['Sezona', 'Season'],
  run: ['Product Run', 'Product Run'],
  branch: ['Viewer Branch', 'Viewer Branch'],
  selectedSeason: ['Vybraná sezona', 'Selected season'],
  selectedWeek: ['Vybraný týden', 'Selected week'],
  empty: ['Pro tento vybraný týden nejsou v uloženém kalendáři žádné události.', 'No events are present in the Saved calendar for this selected week.'],
  events: ['Ověřené události vybraného týdne', 'Verified selected-week events'],
  schedule: ['Otevřít uložený kalendář Runu', 'Open Product Run schedule'],
  runs: ['Otevřít přehled Runů', 'Open run browser'],
} as const

export function ViewerCurrentWeekPage(): JSX.Element {
  const context = useViewerContext()
  const { language } = useLanguage()
  const t = (key: keyof typeof copy): string => copy[key][language === 'cs' ? 0 : 1]
  const runId = useActiveViewerProductRunId()?.trim() ?? ''
  const sourceContext = useViewerOfficialRunContext(runId)
  const branchId = savedCalendarViewerBranch(sourceContext.data, runId)
  const contextReady = Boolean(runId && branchId &&
    !sourceContext.isPending && !sourceContext.isFetching && !sourceContext.isError)

  // The Run + Saved Viewer Branch are both part of the query identity.
  // Never display a stale response while a new Branch is being resolved.
  const calendarQuery = useQuery({
    queryKey: ['viewer-current-week-calendar', runId, branchId],
    queryFn: () => getViewerRunCalendar(runId),
    enabled: contextReady,
    retry: false,
    refetchOnWindowFocus: false,
  })

  const selectedSeason = String(context.selectedSeason)
  const calendar = contextReady && !calendarQuery.isPending &&
    !calendarQuery.isFetching && !calendarQuery.isError
    ? verifiedSavedSeasonCalendar(calendarQuery.data, runId, branchId ?? '')
    : null
  const eventsForWeek = calendar?.events.filter(event =>
    savedCalendarSeasonKey(event.season) === selectedSeason &&
    savedCalendarEventCoversWeek(event, context.selectedWeek)
  ) ?? []

  return (
    <ViewerShellPage title={t('title')} description={t('description')}>
      {!runId ? <ViewerEmptyState>{t('selectRun')}</ViewerEmptyState> : (
        <article className="viewer-active-run-card" aria-label={t('events')}>
          <span className="eyebrow">{t('selected')}</span>
          <h3>{t('season')} {selectedSeason} · W{context.selectedWeek}</h3>
          <dl className="metadata-list">
            <div><dt>{t('run')}</dt><dd>{runId}</dd></div>
            <div><dt>{t('branch')}</dt><dd>{contextReady ? branchId : '—'}</dd></div>
            <div><dt>{t('selectedSeason')}</dt><dd>{selectedSeason}</dd></div>
            <div><dt>{t('selectedWeek')}</dt><dd>{context.selectedWeek}</dd></div>
          </dl>
          <p className="status">{t('historicalLimit')}</p>

          {sourceContext.isPending || sourceContext.isFetching ? (
            <p className="status" role="status">{t('resolving')}</p>
          ) : !contextReady ? (
            <div role="alert">
              <p>{t('contextError')}</p>
              <button type="button" onClick={() => void sourceContext.refetch()}>{t('retry')}</button>
            </div>
          ) : calendarQuery.isPending || calendarQuery.isFetching ? (
            <p className="status" role="status">{t('loading')}</p>
          ) : calendarQuery.isError ? (
            <div role="alert">
              <p>{t('readError')}</p>
              <button type="button" onClick={() => void calendarQuery.refetch()}>{t('retry')}</button>
            </div>
          ) : !calendar ? (
            <div role="alert">
              <p>{t('invalid')}</p>
              <button type="button" onClick={() => void calendarQuery.refetch()}>{t('retry')}</button>
            </div>
          ) : eventsForWeek.length === 0 ? (
            <ViewerEmptyState>{t('empty')}</ViewerEmptyState>
          ) : (
            <ul className="viewer-home-list" aria-label={t('events')}>
              {eventsForWeek.map(event => (
                <li key={event.event_id}>
                  <Link to={viewerPlannedEventPath(runId, event.event_id)}>
                    {event.event_name || event.event_id}
                  </Link> · {event.category} · {event.tour_level ?? '—'}
                </li>
              ))}
            </ul>
          )}
          <p className="viewer-active-run-actions">
            <Link className="viewer-active-run-link" to={viewerSeasonCalendarPath(runId)}>{t('schedule')}</Link>{' '}
            <Link className="viewer-active-run-link" to={viewerRunsPath()}>{t('runs')}</Link>
          </p>
        </article>
      )}
    </ViewerShellPage>
  )
}
