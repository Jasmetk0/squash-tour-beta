import { useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'

import { getViewerRunCalendar } from '../../../api/client'
import { useLanguage } from '../../../i18n/LanguageContext'
import { useActiveViewerProductRunId } from '../../../viewer/useActiveViewerProductRunId'
import { useViewerOfficialRunContext } from '../../../viewer/useViewerOfficialRunContext'
import { viewerCountryProfilePath, viewerPlannedEventPath, viewerRunsPath } from '../../../viewer/viewerRoutes'
import {
  savedCalendarSeasonsNewestFirst, savedCalendarViewerBranch,
  savedCalendarSeasonKey, verifiedSavedSeasonCalendar, type SavedSeasonCalendar,
  type SavedCalendarStatus,
} from '../tour/savedCalendarBrowsing'

const PAGE_SIZE = 25
const copy = {
  title: ['Pořadatelské země', 'Hosting Nations'],
  description: [
    'Pořadatelské země a turnaje ze skutečného veřejného uloženého kalendáře.',
    'Hosting countries and tournaments from the real public Saved calendar.',
  ],
  scope: [
    'Počítají se všechny záznamy turnajů aktuální Viewer Branch podle filtru stavu, včetně zrušených při výběru všech stavů. Pořádání není důkaz odehrání zápasu ani historický národní rekord.',
    'All calendar event records in the current Saved Viewer Branch matching the status filter are counted, including cancellations when all statuses are selected. Hosting is not proof of a completed match or a historical national record.',
  ],
  noRun: ['Není vybraný Product Run.', 'No Product Run is selected.'],
  selectRun: ['Vybrat Run', 'Select Run'],
  contextLoading: ['Ověřuji uloženou Viewer Branch…', 'Verifying Saved Viewer Branch…'],
  badContext: ['Nelze ověřit Viewer Branch vybraného Runu.', 'Cannot verify the selected Run’s Viewer Branch.'],
  loading: ['Načítám uložený kalendář…', 'Loading Saved calendar…'],
  unavailable: ['Veřejný kalendář není dostupný.', 'Public calendar is unavailable.'],
  mismatch: ['Kalendář neodpovídá ověřenému Runu a Viewer Branch nebo má neplatnou strukturu.', 'Calendar does not match the verified Run and Viewer Branch or has invalid structure.'],
  retry: ['Znovu načíst (GET)', 'Retry read (GET)'],
  run: ['Product Run', 'Product Run'],
  branch: ['Viewer Branch', 'Viewer Branch'],
  events: ['Uložené turnaje', 'Saved tournaments'],
  nations: ['Pořadatelské země', 'Hosting countries'],
  season: ['Sezona', 'Season'],
  allSeasons: ['Všechny sezony', 'All seasons'],
  status: ['Stav turnaje', 'Event status'],
  allStatuses: ['Všechny stavy', 'All statuses'],
  completedStatus: ['Dokončeno', 'Completed'],
  plannedStatus: ['Plánováno', 'Planned'],
  scheduledStatus: ['Naplánováno', 'Scheduled'],
  activeStatus: ['Aktivní', 'Active'],
  cancelledStatus: ['Zrušeno', 'Cancelled'],
  search: ['Hledat kód země', 'Search country code'],
  reset: ['Vymazat filtry', 'Clear filters'],
  table: ['Počty uložených turnajů podle pořadatelské země', 'Saved event counts by hosting country'],
  country: ['Země (kód)', 'Country (code)'],
  count: ['Turnaje odpovídající filtrům', 'Events matching filters'],
  completed: ['Dokončené', 'Completed'],
  seasons: ['Sezony', 'Seasons'],
  recent: ['Nejpozdější turnaj podle rozpisu', 'Latest event by schedule'],
  none: ['Uložený kalendář zatím neobsahuje turnaje.', 'Saved calendar has no events yet.'],
  noMatch: ['Zvoleným filtrům neodpovídají žádné pořadatelské země.', 'No hosting nations match the filters.'],
  shown: ['Zobrazeno', 'Showing'],
  of: ['z', 'of'],
  page: ['Stránka', 'Page'],
  previous: ['Předchozí', 'Previous'],
  next: ['Další', 'Next'],
} as const
type Key = keyof typeof copy
type T = (key: Key) => string

export type HostingNationRow = {
  countryCode: string
  events: number
  completed: number
  seasons: number
  latestEventId: string
  latestEventName: string
  latestSeason: string
  latestWeek: number
}

// Source must first pass verifiedSavedSeasonCalendar. Distinguishes events
// in a public calendar from actually completed sporting results.
export function aggregateSavedHostingNations(
  calendar: SavedSeasonCalendar,
  season = 'all',
  status: SavedCalendarStatus = 'all',
  search = '',
): HostingNationRow[] {
  const order = new Map(savedCalendarSeasonsNewestFirst(calendar).map((s, index) => [s, index]))
  const text = search.trim().toLocaleLowerCase()
  const rows = new Map<string, HostingNationRow & { seenSeasons: Set<string> }>()
  for (const event of calendar.events) {
    const code = event.host_country
    const eventSeason = savedCalendarSeasonKey(event.season) ?? ''
    if ((season !== 'all' && eventSeason !== season) ||
        (status !== 'all' && event.status !== status) ||
        (text && !code.toLocaleLowerCase().includes(text))) continue
    const previous = rows.get(code)
    if (!previous) {
      rows.set(code, {
        countryCode: code, events: 1, completed: event.status === 'completed' ? 1 : 0,
        seasons: 1, seenSeasons: new Set([eventSeason]),
        latestEventId: event.event_id, latestEventName: event.event_name || event.event_id,
        latestSeason: eventSeason, latestWeek: event.season_week,
      })
      continue
    }
    previous.events++
    if (event.status === 'completed') previous.completed++
    previous.seenSeasons.add(eventSeason)
    previous.seasons = previous.seenSeasons.size
    const newRank = order.get(eventSeason) ?? Number.MAX_SAFE_INTEGER
    const oldRank = order.get(previous.latestSeason) ?? Number.MAX_SAFE_INTEGER
    if (newRank < oldRank ||
      (newRank === oldRank && (event.season_week > previous.latestWeek ||
        (event.season_week === previous.latestWeek && event.event_id < previous.latestEventId)))) {
      previous.latestEventId = event.event_id
      previous.latestEventName = event.event_name || event.event_id
      previous.latestSeason = eventSeason
      previous.latestWeek = event.season_week
    }
  }

  return [...rows.values()]
    .map(({ seenSeasons: _seenSeasons, ...row }) => row)
    .sort((a, b) => b.events - a.events || a.countryCode.localeCompare(b.countryCode, 'cs'))
}

function HostingDirectory({ calendar, runId, branchId, t }: {
  calendar: SavedSeasonCalendar; runId: string; branchId: string; t: T
}): JSX.Element {
  const [season, setSeason] = useState('all')
  const [status, setStatus] = useState<SavedCalendarStatus>('all')
  const [search, setSearch] = useState('')
  const [page, setPage] = useState(1)
  const seasons = useMemo(() => savedCalendarSeasonsNewestFirst(calendar), [calendar])
  const rows = useMemo(() =>
    aggregateSavedHostingNations(calendar, season, status, search),
    [calendar, season, status, search]
  )
  const pages = Math.ceil(rows.length / PAGE_SIZE)
  const currentPage = Math.min(page, pages || 1)
  const offset = (currentPage - 1) * PAGE_SIZE
  const visible = rows.slice(offset, offset + PAGE_SIZE)
  function reset(): void {
    setSeason('all'); setStatus('all'); setSearch(''); setPage(1)
  }
  return (
    <article className="viewer-active-run-card">
      <dl className="metadata-list viewer-metadata-list">
        <div><dt>{t('run')}</dt><dd>{runId}</dd></div>
        <div><dt>{t('branch')}</dt><dd>{branchId}</dd></div>
        <div><dt>{t('events')}</dt><dd>{calendar.eventCount}</dd></div>
        <div><dt>{t('nations')}</dt><dd>{new Set(calendar.events.map(event => event.host_country)).size}</dd></div>
      </dl>
      {calendar.eventCount === 0 ? <p className="empty-state">{t('none')}</p> : <>
        <div className="viewer-filters">
          <label htmlFor="hosting-season">{t('season')}</label>
          <select id="hosting-season" value={season} onChange={e => { setSeason(e.target.value); setPage(1) }}>
            <option value="all">{t('allSeasons')}</option>
            {seasons.map(value => <option key={value} value={value}>{value}</option>)}
          </select>
          <label htmlFor="hosting-status">{t('status')}</label>
          <select id="hosting-status" value={status} onChange={e => {
            setStatus(e.target.value as SavedCalendarStatus); setPage(1)
          }}>
            <option value="all">{t('allStatuses')}</option>
            <option value="completed">{t('completedStatus')}</option>
            <option value="planned">{t('plannedStatus')}</option>
            <option value="scheduled">{t('scheduledStatus')}</option>
            <option value="active">{t('activeStatus')}</option>
            <option value="cancelled">{t('cancelledStatus')}</option>
          </select>
          <label htmlFor="hosting-search">{t('search')}</label>
          <input id="hosting-search" type="search" value={search}
            onChange={e => { setSearch(e.target.value); setPage(1) }} />
          <button type="button" onClick={reset}>{t('reset')}</button>
        </div>
        {rows.length === 0 ? <p className="empty-state">{t('noMatch')}</p> : (
          <div className="table-wrap">
            <table aria-label={t('table')}>
              <thead><tr>
                <th scope="col">{t('country')}</th>
                <th scope="col">{t('count')}</th>
                <th scope="col">{t('completed')}</th>
                <th scope="col">{t('seasons')}</th>
                <th scope="col">{t('recent')}</th>
              </tr></thead>
              <tbody>{visible.map(row => <tr key={row.countryCode}>
                <td><Link to={viewerCountryProfilePath(runId, row.countryCode)}>{row.countryCode}</Link></td>
                <td>{row.events}</td>
                <td>{row.completed}</td>
                <td>{row.seasons}</td>
                <td>{row.latestSeason} · W{row.latestWeek} · {' '}
                  <Link to={viewerPlannedEventPath(runId, row.latestEventId)}>{row.latestEventName}</Link></td>
              </tr>)}</tbody>
            </table>
          </div>
        )}
        <p role="status">{t('shown')} {rows.length ? offset + 1 : 0}–
          {rows.length ? offset + visible.length : 0} {t('of')} {rows.length}</p>
        {pages > 1 ? <nav aria-label={t('page')}>
          <button type="button" disabled={currentPage === 1} onClick={() => setPage(currentPage - 1)}>{t('previous')}</button>
          <span>{t('page')} {currentPage} / {pages}</span>
          <button type="button" disabled={currentPage === pages} onClick={() => setPage(currentPage + 1)}>{t('next')}</button>
        </nav> : null}
      </>}
    </article>
  )
}

export function ViewerHostingNationsPage(): JSX.Element {
  const runId = useActiveViewerProductRunId()?.trim() ?? ''
  const { language } = useLanguage()
  const t: T = key => copy[key][language === 'cs' ? 0 : 1]
  const context = useViewerOfficialRunContext(runId)
  const branchId = savedCalendarViewerBranch(context.data, runId)
  const validContext = Boolean(runId && branchId && !context.isPending && !context.isFetching && !context.isError)
  const calendarQuery = useQuery({
    queryKey: ['viewer-hosting-nations-saved-calendar', runId, branchId],
    queryFn: () => getViewerRunCalendar(runId),
    enabled: validContext,
    retry: false, refetchOnWindowFocus: false,
  })

  return (
    <section className="panel viewer-shell-page">
      <div className="page-intro">
        <h2>{t('title')}</h2>
        <p className="subtitle">{t('description')}</p>
      </div>
      <p className="subtitle">{t('scope')}</p>
      {!runId ? <p className="empty-state">{t('noRun')} <Link to={viewerRunsPath()}>{t('selectRun')}</Link></p> :
        context.isPending || context.isFetching ? <p role="status">{t('contextLoading')}</p> :
        !validContext ? <div role="alert">
          <p>{t('badContext')}</p>
          <button type="button" onClick={() => void context.refetch()}>{t('retry')}</button>
        </div> :
        calendarQuery.isPending || calendarQuery.isFetching ? <p role="status">{t('loading')}</p> :
        calendarQuery.isError ? <div role="alert">
          <p>{t('unavailable')}</p>
          <button type="button" onClick={() => void calendarQuery.refetch()}>{t('retry')}</button>
        </div> : (() => {
          const calendar = verifiedSavedSeasonCalendar(calendarQuery.data, runId, branchId ?? '')
          return calendar ? <HostingDirectory key={JSON.stringify([runId, branchId])}
            calendar={calendar} runId={runId} branchId={branchId ?? ''} t={t} /> :
            <div role="alert">
              <p>{t('mismatch')}</p>
              <button type="button" onClick={() => void calendarQuery.refetch()}>{t('retry')}</button>
            </div>
        })()}
    </section>
  )
}
