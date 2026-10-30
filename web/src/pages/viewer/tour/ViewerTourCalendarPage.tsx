import { useState, type FormEvent } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'

import { getViewerRunCalendar } from '../../../api/client'
import { ViewerShellPage } from '../../../components/viewer/ViewerShellPage'
import { useLanguage, type Language } from '../../../i18n/LanguageContext'
import { useActiveViewerProductRunId } from '../../../viewer/useActiveViewerProductRunId'
import { useViewerOfficialRunContext } from '../../../viewer/useViewerOfficialRunContext'
import {
  viewerPlannedEventPath, viewerRunsPath, viewerSeasonCalendarPath
} from '../../../viewer/viewerRoutes'
import {
  filterSavedCalendarEvents, parseSavedCalendarPage, savedCalendarSeasonsNewestFirst,
  savedCalendarViewerBranch, savedCalendarWeeks, SAVED_CALENDAR_PAGE_SIZE,
  verifiedSavedSeasonCalendar, type SavedCalendarStatus
} from './savedCalendarBrowsing'

const labels = {
  title: ['Sezonní kalendář', 'Season Calendar'],
  description: ['Prohlížení skutečně uložených sezon, týdnů a turnajů z vybrané Viewer Branch.', 'Browse actual saved seasons, weeks and tournaments from the selected Viewer Branch.'],
  summary: ['Uložený kalendář', 'Saved Calendar summary'],
  selectRun: ['Není vybrán žádný Product Run.', 'No Product Run is selected yet.'],
  runs: ['Vybrat Product Run', 'Select Product Run'],
  resolving: ['Ověřuji aktuální Viewer Branch…', 'Resolving current Viewer Branch…'],
  contextError: ['Viewer Branch se nepodařilo ověřit.', 'Viewer Branch could not be verified.'],
  contextMismatch: ['Viewer Branch neodpovídá aktuálně vybranému Product Runu.', 'Viewer Branch does not match the selected Product Run.'],
  retry: ['Načíst znovu (pouze GET)', 'Retry read (GET only)'],
  loading: ['Načítám uložený kalendář…', 'Loading saved calendar…'],
  error: ['Uložený kalendář není dostupný.', 'Saved Calendar metadata is temporarily unavailable.'],
  invalid: ['Uložený kalendář je neplatný nebo patří jinému Runu/Viewer Branch. Data se nezobrazují.', 'Saved calendar is invalid or belongs to another Run/Viewer Branch. No data is displayed.'],
  run: ['Product Run', 'Product Run'],
  branch: ['Viewer Branch', 'Viewer Branch'],
  seasons: ['Uložené sezony', 'Saved seasons'],
  events: ['Uložené turnaje', 'Saved events'],
  empty: ['Tento kalendář zatím neobsahuje žádné turnaje.', 'This saved calendar has no tournaments yet.'],
  season: ['Sezona', 'Season'],
  allSeasons: ['Všechny sezony', 'All seasons'],
  week: ['Týden', 'Week'],
  allWeeks: ['Všechny týdny', 'All weeks'],
  status: ['Stav v kalendáři', 'Calendar status'],
  allStatuses: ['Všechny stavy', 'All statuses'],
  search: ['Hledat název, ID nebo místo', 'Search name, ID or location'],
  clear: ['Vymazat filtry', 'Clear filters'],
  list: ['Uložené turnaje kalendáře', 'Saved calendar tournaments'],
  event: ['Turnaj', 'Tournament'],
  location: ['Země / město', 'Country / city'],
  tour: ['Tour', 'Tour'],
  category: ['Kategorie', 'Category'],
  yearWeek: ['Kalendářní týden', 'Calendar week'],
  noMatch: ['Žádný turnaj neodpovídá zvoleným filtrům.', 'No saved tournaments match the selected filters.'],
  first: ['První', 'First'],
  prev: ['Předchozí', 'Previous'],
  next: ['Další', 'Next'],
  last: ['Poslední', 'Last'],
  page: ['Stránka', 'Page'],
  shown: ['Zobrazeno', 'Showing'],
  of: ['z', 'of'],
  jump: ['Přejít na stránku', 'Jump to page'],
  go: ['Přejít', 'Go'],
  pageError: ['Zadej platné existující číslo stránky.', 'Enter a valid existing page number.'],
  schedule: ['Otevřít kalendář Runu', 'Open active run schedule'],
  planned: ['Plánováno', 'Planned'],
  scheduled: ['Naplánováno', 'Scheduled'],
  active: ['Probíhá', 'Active'],
  completed: ['Dokončeno', 'Completed'],
  cancelled: ['Zrušeno', 'Cancelled']
} as const

type Copy = Record<keyof typeof labels, string>
function copyFor(language: Language): Copy {
  const column = language === 'cs' ? 0 : 1
  return Object.fromEntries(Object.entries(labels).map(([key, values]) =>
    [key, values[column]])) as Copy
}

const statusNames: Exclude<SavedCalendarStatus, 'all'>[] = [
  'planned', 'scheduled', 'active', 'completed', 'cancelled'
]

function SavedCalendarForSource({ runId, branchId, t }: {
  runId: string; branchId: string; t: Copy
}): JSX.Element {
  const [season, setSeason] = useState('all')
  const [week, setWeek] = useState('all')
  const [status, setStatus] = useState<SavedCalendarStatus>('all')
  const [search, setSearch] = useState('')
  const [page, setPage] = useState(1)
  const [jump, setJump] = useState('')
  const [invalidPage, setInvalidPage] = useState(false)
  const calendarQuery = useQuery({
    queryKey: ['viewer-tour-calendar-saved-revision', runId, branchId],
    queryFn: () => getViewerRunCalendar(runId),
    retry: false,
    refetchOnWindowFocus: false
  })

  function movePage(next: number): void {
    setPage(next)
    setJump('')
    setInvalidPage(false)
  }
  function reset(): void {
    setSeason('all'); setWeek('all'); setStatus('all'); setSearch(''); movePage(1)
  }

  if (calendarQuery.isPending || calendarQuery.isFetching) {
    return <p className="status" role="status">{t.loading}</p>
  }
  if (calendarQuery.isError) {
    return <div role="alert">
      <p className="error">{t.error}</p>
      <button type="button" onClick={() => void calendarQuery.refetch()}>{t.retry}</button>
    </div>
  }
  const calendar = verifiedSavedSeasonCalendar(calendarQuery.data, runId, branchId)
  if (!calendar) return <div role="alert">
    <p className="error">{t.invalid}</p>
    <button type="button" onClick={() => void calendarQuery.refetch()}>{t.retry}</button>
  </div>

  const seasons = savedCalendarSeasonsNewestFirst(calendar)
  const weeks = savedCalendarWeeks(calendar, season)
  const found = filterSavedCalendarEvents(calendar, season, week, status, search)
  const pages = Math.ceil(found.length / SAVED_CALENDAR_PAGE_SIZE)
  const current = pages ? Math.min(page, pages) : 0
  const offset = current ? (current - 1) * SAVED_CALENDAR_PAGE_SIZE : 0
  const visible = found.slice(offset, offset + SAVED_CALENDAR_PAGE_SIZE)

  function submitJump(event: FormEvent<HTMLFormElement>): void {
    event.preventDefault()
    const next = parseSavedCalendarPage(jump, pages)
    if (next === null) setInvalidPage(true)
    else movePage(next)
  }

  return (
    <>
      <dl aria-label={t.summary} className="metadata-list viewer-metadata-list">
        <div><dt>{t.run}</dt><dd>{runId}</dd></div>
        <div><dt>{t.branch}</dt><dd>{branchId}</dd></div>
        <div><dt>{t.seasons}</dt><dd>{calendar.seasons.length}</dd></div>
        <div><dt>{t.events}</dt><dd>{calendar.eventCount}</dd></div>
      </dl>
      {calendar.eventCount === 0 ? <p className="empty-state">{t.empty}</p> : <>
        <div>
          <label htmlFor="saved-calendar-season">{t.season}</label>
          <select id="saved-calendar-season" value={season} onChange={e => {
            setSeason(e.target.value); setWeek('all'); movePage(1)
          }}>
            <option value="all">{t.allSeasons}</option>
            {seasons.map(value => <option key={value} value={value}>{value}</option>)}
          </select>
        </div>
        <div>
          <label htmlFor="saved-calendar-week">{t.week}</label>
          <select id="saved-calendar-week" value={week} onChange={e => {
            setWeek(e.target.value); movePage(1)
          }}>
            <option value="all">{t.allWeeks}</option>
            {weeks.map(value => <option key={value} value={String(value)}>W{value}</option>)}
          </select>
        </div>
        <div>
          <label htmlFor="saved-calendar-status">{t.status}</label>
          <select id="saved-calendar-status" value={status} onChange={e => {
            setStatus(e.target.value as SavedCalendarStatus); movePage(1)
          }}>
            <option value="all">{t.allStatuses}</option>
            {statusNames.map(value => <option key={value} value={value}>{t[value]}</option>)}
          </select>
        </div>
        <div>
          <label htmlFor="saved-calendar-search">{t.search}</label>
          <input id="saved-calendar-search" type="search" value={search} onChange={e => {
            setSearch(e.target.value); movePage(1)
          }} />
          <button type="button" onClick={reset}>{t.clear}</button>
        </div>

        {found.length === 0 ? <p className="empty-state">{t.noMatch}</p> :
          <div className="table-wrap">
            <table aria-label={t.list}>
              <thead><tr>
                <th scope="col">{t.season}</th><th scope="col">{t.week}</th>
                <th scope="col">{t.event}</th><th scope="col">{t.location}</th>
                <th scope="col">{t.category}</th><th scope="col">{t.tour}</th>
                <th scope="col">{t.status}</th><th scope="col">{t.yearWeek}</th>
              </tr></thead>
              <tbody>{visible.map(event => (
                <tr key={event.event_id}>
                  <td>{String(event.season)}</td>
                  <td>W{event.season_week}</td>
                  <td><Link to={viewerPlannedEventPath(runId, event.event_id)}>
                    {event.event_name || event.event_id}
                  </Link></td>
                  <td>{event.host_country}{event.host_city ? ' · ' + event.host_city : ''}</td>
                  <td>{event.category}</td>
                  <td>{event.tour_level ?? '—'}</td>
                  <td>{t[event.status]}</td>
                  <td>{event.calendar_year !== null && event.year_week !== null ?
                    String(event.calendar_year) + ' · W' + event.year_week : '—'}</td>
                </tr>
              ))}</tbody>
            </table>
          </div>}
        <p role="status">{t.shown} {found.length ? offset + 1 : 0}–{found.length ? offset + visible.length : 0} {t.of} {found.length}</p>
        {pages > 1 ? <nav aria-label={t.page}>
          <button type="button" disabled={current === 1} onClick={() => movePage(1)}>{t.first}</button>
          <button type="button" disabled={current === 1} onClick={() => movePage(current - 1)}>{t.prev}</button>
          <span>{t.page} {current} / {pages}</span>
          <button type="button" disabled={current === pages} onClick={() => movePage(current + 1)}>{t.next}</button>
          <button type="button" disabled={current === pages} onClick={() => movePage(pages)}>{t.last}</button>
          <form onSubmit={submitJump}>
            <label htmlFor="saved-calendar-page">{t.jump}</label>
            <input id="saved-calendar-page" inputMode="numeric" value={jump}
              aria-invalid={invalidPage}
              aria-describedby={invalidPage ? 'saved-calendar-page-error' : undefined}
              onChange={e => { setJump(e.target.value); setInvalidPage(false) }} />
            <button type="submit">{t.go}</button>
            {invalidPage ? <span role="alert" id="saved-calendar-page-error">{t.pageError}</span> : null}
          </form>
        </nav> : null}
      </>}
      <p className="viewer-active-run-actions">
        <Link className="viewer-active-run-link" to={viewerSeasonCalendarPath(runId)}>{t.schedule}</Link>
      </p>
    </>
  )
}

export function ViewerTourCalendarPage(): JSX.Element {
  const runId = useActiveViewerProductRunId()?.trim() ?? ''
  const { language } = useLanguage()
  const t = copyFor(language)
  const context = useViewerOfficialRunContext(runId)
  const branchId = savedCalendarViewerBranch(context.data, runId)

  return (
    <ViewerShellPage title={t.title} description={t.description}>
      <article className="viewer-active-run-card" aria-label={t.summary}>
        <h3>{t.summary}</h3>
        {!runId ?
          <p className="empty-state">{t.selectRun} <Link to={viewerRunsPath()}>{t.runs}</Link></p> :
          context.isPending || context.isFetching ?
          <p className="status" role="status">{t.resolving}</p> :
          context.isError ? <div role="alert"><p className="error">{t.contextError}</p>
            <button type="button" onClick={() => void context.refetch()}>{t.retry}</button></div> :
          !branchId ? <div role="alert"><p className="error">{t.contextMismatch}</p>
            <button type="button" onClick={() => void context.refetch()}>{t.retry}</button></div> :
          <SavedCalendarForSource key={JSON.stringify([runId, branchId])}
            runId={runId} branchId={branchId} t={t} />
        }
      </article>
    </ViewerShellPage>
  )
}
