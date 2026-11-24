import { useEffect, useRef, useState, type FormEvent } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link, useSearchParams } from 'react-router-dom'

import { getViewerRunCalendar, getViewerTournamentHistory } from '../../../api/client'
import { useLanguage, type Language } from '../../../i18n/LanguageContext'
import { useActiveViewerProductRunId } from '../../../viewer/useActiveViewerProductRunId'
import { useViewerOfficialRunContext } from '../../../viewer/useViewerOfficialRunContext'
import {
  viewerPlannedEventPath, viewerPlayerProfilePath, viewerRunsPath,
  viewerSeasonCalendarPath, viewerTournamentsPath
} from '../../../viewer/viewerRoutes'
import {
  catalogSeasonsNewestFirst, filteredSavedTournaments, parseTournamentPage,
  TOURNAMENT_PAGE_SIZE, tournamentViewerBranch, verifiedTournamentCatalog,
  type TournamentPublicationFilter
} from './viewerTournamentCatalog'

const messages = {
  title: ['Všechny turnaje', 'All Tournaments'],
  subtitle: ['Uložený turnajový kalendář a publikované výsledky pouze z ověřené Viewer Branch.', 'Saved tournament calendar and published results from a verified Viewer Branch only.'],
  heading: ['Turnajový archiv', 'Tournament archive'],
  noRun: ['Není vybraný žádný Product Run.', 'No Product Run is selected.'],
  choose: ['Vybrat Run', 'Choose Run'],
  resolving: ['Ověřuji aktuální Viewer Branch…', 'Resolving current Viewer Branch…'],
  badContext: ['Viewer Branch neodpovídá vybranému Product Runu.', 'Viewer Branch does not match the selected Product Run.'],
  contextError: ['Viewer Branch momentálně není dostupná.', 'Viewer Branch is temporarily unavailable.'],
  loading: ['Načítám uložené turnaje…', 'Loading saved tournaments…'],
  unavailable: ['Uložený kalendář nebo výsledky nejsou dostupné. Částečný přehled se nezobrazuje.', 'Saved calendar or results are unavailable. No partial view is displayed.'],
  mismatch: ['Kalendář a historie turnajů si neodpovídají. Žádný výsledek se nezobrazuje.', 'Calendar and tournament history do not agree. No results are displayed.'],
  retry: ['Načíst znovu (GET)', 'Retry read (GET)'],
  run: ['Product Run', 'Product Run'],
  branch: ['Viewer Branch', 'Viewer Branch'],
  seasons: ['Počet sezon', 'Seasons'],
  events: ['Počet turnajů v kalendáři', 'Calendar events'],
  publishedCount: ['Publikované výsledky', 'Published results'],
  selectSeason: ['Filtrovat sezonu', 'Filter season'],
  allSeasons: ['Všechny sezony', 'All seasons'],
  search: ['Hledat turnaj, ID nebo místo', 'Search event, ID or location'],
  statusFilter: ['Stav zveřejnění výsledku', 'Result publication status'],
  all: ['Všechny turnaje', 'All tournaments'],
  published: ['Výsledek publikován', 'Result published'],
  unpublished: ['Výsledek nepublikován', 'Result not published'],
  clear: ['Vymazat filtry', 'Clear filters'],
  unknownFilter: ['Neznámá hodnota', 'Unknown value'],
  invalidFilters: ['Odkaz obsahuje neplatnou nebo nedostupnou hodnotu filtru. Uprav ji nebo vymaž filtry.', 'The URL contains an invalid or unavailable filter. Correct or clear the filters.'],
  table: ['Uložené turnaje', 'Saved tournaments'],
  season: ['Sezona', 'Season'],
  week: ['Týden', 'Week'],
  event: ['Turnaj', 'Tournament'],
  country: ['Země / město', 'Country / city'],
  category: ['Kategorie', 'Category'],
  state: ['Stav v kalendáři', 'Calendar status'],
  result: ['Publikovaný výsledek', 'Published result'],
  champion: ['Vítěz (ID hráče)', 'Champion (player ID)'],
  notPublished: ['Zatím nepublikováno', 'Not published yet'],
  none: ['Kalendář neobsahuje žádný turnaj.', 'The saved calendar has no tournaments.'],
  noMatch: ['Žádný turnaj neodpovídá filtrům.', 'No tournaments match the filters.'],
  shown: ['Zobrazeno', 'Showing'],
  of: ['z', 'of'],
  page: ['Stránka', 'Page'],
  first: ['První', 'First'],
  previous: ['Předchozí', 'Previous'],
  next: ['Další', 'Next'],
  last: ['Poslední', 'Last'],
  jump: ['Přejít na stránku', 'Jump to page'],
  go: ['Přejít', 'Go'],
  badJump: ['Zadej existující celé číslo stránky.', 'Enter an existing integer page number.'],
  runTournaments: ['Otevřít turnaje Runu', 'Open Run tournaments'],
  runCalendar: ['Otevřít kalendář Runu', 'Open Run calendar'],
  runBrowser: ['Seznam Runů', 'Run browser'],
  planned: ['Plánováno', 'Planned'],
  active: ['Probíhá', 'Active'],
  completed: ['Dokončeno', 'Completed'],
  cancelled: ['Zrušeno', 'Cancelled'],
  scheduled: ['Naplánováno', 'Scheduled']
} as const
type Copy = Record<keyof typeof messages, string>
function copyFor(language: Language): Copy {
  const i = language === 'cs' ? 0 : 1
  return Object.fromEntries(Object.entries(messages).map(([key, pair]) => [key, pair[i]])) as Copy
}
function CalendarStatus({ status, t }: { status: string; t: Copy }): JSX.Element {
  return <>{status in t ? t[status as keyof Copy] : status}</>
}

const TOURNAMENT_URL_FILTERS = {
  season: 'vtSeason', search: 'vtQ', result: 'vtResult'
} as const
const TOURNAMENT_URL_KEYS = Object.values(TOURNAMENT_URL_FILTERS)

function TournamentCatalogForBranch({ runId, branchId, t, ignoreUrlFilters }: {
  runId: string; branchId: string; t: Copy; ignoreUrlFilters: boolean
}): JSX.Element {
  const [searchParams, setSearchParams] = useSearchParams()
  const active = ignoreUrlFilters ? new URLSearchParams() : searchParams
  const season = active.get(TOURNAMENT_URL_FILTERS.season) ?? 'all'
  const search = active.get(TOURNAMENT_URL_FILTERS.search) ?? ''
  const resultFilter = (active.get(TOURNAMENT_URL_FILTERS.result) ?? 'all') as TournamentPublicationFilter
  const [page, setPage] = useState(1)
  const [jump, setJump] = useState('')
  const [badJump, setBadJump] = useState(false)
  useEffect(() => {
    setPage(1)
    setJump('')
    setBadJump(false)
  }, [season, search, resultFilter])

  function updateFilter(name: string, value: string, fallback: string, replace = false): void {
    setSearchParams(previous => {
      const next = new URLSearchParams(previous)
      if (ignoreUrlFilters) TOURNAMENT_URL_KEYS.forEach(key => next.delete(key))
      if (value === fallback) next.delete(name)
      else next.set(name, value)
      return next
    }, { replace })
    changePage(1)
  }
  const calendarQuery = useQuery({
    queryKey: ['viewer-tournaments-calendar', runId, branchId],
    queryFn: () => getViewerRunCalendar(runId),
    retry: false, refetchOnWindowFocus: false
  })
  const historyQuery = useQuery({
    queryKey: ['viewer-tournaments-history', runId, branchId],
    queryFn: () => getViewerTournamentHistory(runId),
    retry: false, refetchOnWindowFocus: false
  })
  function retry(): void {
    void Promise.all([calendarQuery.refetch(), historyQuery.refetch()])
  }
  function changePage(value: number): void {
    setPage(value); setJump(''); setBadJump(false)
  }
  function clear(): void {
    setSearchParams(previous => {
      const next = new URLSearchParams(previous)
      TOURNAMENT_URL_KEYS.forEach(key => next.delete(key))
      return next
    })
    changePage(1)
  }
  if (calendarQuery.isPending || historyQuery.isPending) {
    return <p className="status" role="status">{t.loading}</p>
  }
  if (calendarQuery.isError || historyQuery.isError) return (
    <div role="alert"><p className="error">{t.unavailable}</p>
      <button type="button" onClick={retry}>{t.retry}</button></div>
  )
  const catalog = verifiedTournamentCatalog(calendarQuery.data, historyQuery.data, runId, branchId)
  if (!catalog) return <div role="alert"><p className="error">{t.mismatch}</p>
    <button type="button" onClick={retry}>{t.retry}</button></div>

  const seasons = catalogSeasonsNewestFirst(catalog)
  const invalidSeason = season !== 'all' && !seasons.includes(season)
  const invalidResult = !['all', 'published', 'unpublished'].includes(resultFilter)
  const invalidFilters = invalidSeason || invalidResult
  // Never reinterpret a link requesting an unknown season/status as "all".
  const filtered = invalidFilters ? [] : filteredSavedTournaments(catalog, season, search, resultFilter)
  const totalPages = Math.ceil(filtered.length / TOURNAMENT_PAGE_SIZE)
  const visiblePage = totalPages ? Math.min(page, totalPages) : 0
  const offset = visiblePage ? (visiblePage - 1) * TOURNAMENT_PAGE_SIZE : 0
  const rows = filtered.slice(offset, offset + TOURNAMENT_PAGE_SIZE)
  function submitJump(event: FormEvent<HTMLFormElement>): void {
    event.preventDefault()
    const next = parseTournamentPage(jump, totalPages)
    if (next === null) setBadJump(true)
    else changePage(next)
  }

  return (
    <>
      <dl className="metadata-list viewer-metadata-list" aria-label={t.heading}>
        <div><dt>{t.run}</dt><dd>{runId}</dd></div>
        <div><dt>{t.branch}</dt><dd>{branchId}</dd></div>
        <div><dt>{t.seasons}</dt><dd>{catalog.seasons.length}</dd></div>
        <div><dt>{t.events}</dt><dd>{catalog.eventCount}</dd></div>
        <div><dt>{t.publishedCount}</dt><dd>{catalog.publishedCount}</dd></div>
      </dl>
      {catalog.eventCount === 0 ? <p className="empty-state">{t.none}</p> : (
        <>
          {invalidFilters ? <p role="alert">{t.invalidFilters}</p> : null}
          <div>
            <label htmlFor="tournament-season">{t.selectSeason}</label>
            <select id="tournament-season" value={season} onChange={event =>
              updateFilter(TOURNAMENT_URL_FILTERS.season, event.target.value, 'all')}>
              {invalidSeason ? <option value={season}>{t.unknownFilter}: {season}</option> : null}
              <option value="all">{t.allSeasons}</option>
              {seasons.map(value => <option key={value} value={value}>{value}</option>)}
            </select>
          </div>
          <div>
            <label htmlFor="tournament-search">{t.search}</label>
            <input id="tournament-search" type="search" value={search}
              onChange={event => updateFilter(TOURNAMENT_URL_FILTERS.search, event.target.value, '', true)} />
          </div>
          <div>
            <label htmlFor="tournament-result-filter">{t.statusFilter}</label>
            <select id="tournament-result-filter" value={resultFilter}
              onChange={event => updateFilter(TOURNAMENT_URL_FILTERS.result, event.target.value, 'all')}>
              {invalidResult ? <option value={resultFilter}>{t.unknownFilter}: {resultFilter}</option> : null}
              <option value="all">{t.all}</option>
              <option value="published">{t.published}</option>
              <option value="unpublished">{t.unpublished}</option>
            </select>
            <button type="button" onClick={clear}>{t.clear}</button>
          </div>
          {filtered.length === 0 ? <p className="empty-state">{t.noMatch}</p> : (
            <div className="table-wrap">
              <table aria-label={t.table}>
                <thead><tr>
                  <th scope="col">{t.season}</th><th scope="col">{t.week}</th>
                  <th scope="col">{t.event}</th><th scope="col">{t.country}</th>
                  <th scope="col">{t.category}</th><th scope="col">{t.state}</th>
                  <th scope="col">{t.result}</th><th scope="col">{t.champion}</th>
                </tr></thead>
                <tbody>{rows.map(({ event, publication }) => (
                  <tr key={event.event_id}>
                    <td>{String(event.season)}</td>
                    <td>W{event.season_week}</td>
                    <td><Link to={viewerPlannedEventPath(runId, event.event_id)}>{event.event_name || event.event_id}</Link></td>
                    <td>{event.host_country}{event.host_city ? ' · ' + event.host_city : ''}</td>
                    <td>{event.category}</td>
                    <td><CalendarStatus status={event.status} t={t} /></td>
                    <td>{publication.result_published ? t.published : t.notPublished}</td>
                    <td>{publication.result_published && publication.champion_player_id ?
                      <Link to={viewerPlayerProfilePath(runId, publication.champion_player_id)}>
                        {publication.champion_player_id}
                      </Link> : '—'}</td>
                  </tr>
                ))}</tbody>
              </table>
            </div>
          )}
          <p role="status">{t.shown} {filtered.length ? offset + 1 : 0}–{filtered.length ? offset + rows.length : 0} {t.of} {filtered.length}</p>
          {totalPages > 1 ? <nav aria-label={t.page}>
            <button type="button" disabled={visiblePage === 1} onClick={() => changePage(1)}>{t.first}</button>
            <button type="button" disabled={visiblePage === 1} onClick={() => changePage(visiblePage - 1)}>{t.previous}</button>
            <span>{t.page} {visiblePage} / {totalPages}</span>
            <button type="button" disabled={visiblePage === totalPages} onClick={() => changePage(visiblePage + 1)}>{t.next}</button>
            <button type="button" disabled={visiblePage === totalPages} onClick={() => changePage(totalPages)}>{t.last}</button>
            <form onSubmit={submitJump}>
              <label htmlFor="tournament-page-jump">{t.jump}</label>
              <input id="tournament-page-jump" inputMode="numeric" value={jump}
                aria-invalid={badJump} aria-describedby={badJump ? 'tournament-page-error' : undefined}
                onChange={event => { setJump(event.target.value); setBadJump(false) }} />
              <button type="submit">{t.go}</button>
              {badJump ? <span role="alert" id="tournament-page-error">{t.badJump}</span> : null}
            </form>
          </nav> : null}
        </>
      )}
      <nav aria-label={t.heading} className="viewer-active-run-actions">
        <Link className="viewer-active-run-link" to={viewerTournamentsPath(runId)}>{t.runTournaments}</Link>{' '}
        <Link className="viewer-active-run-link" to={viewerSeasonCalendarPath(runId)}>{t.runCalendar}</Link>{' '}
        <Link className="viewer-active-run-link" to={viewerRunsPath()}>{t.runBrowser}</Link>
      </nav>
    </>
  )
}

export function ViewerTournamentsPage(): JSX.Element {
  const runId = useActiveViewerProductRunId()?.trim() ?? ''
  const { language } = useLanguage()
  const t = copyFor(language)
  const context = useViewerOfficialRunContext(runId)
  const branchId = tournamentViewerBranch(context.data, runId)
  const [searchParams, setSearchParams] = useSearchParams()
  const sourceKey = branchId && !context.isPending && !context.isFetching && !context.isError
    ? JSON.stringify([runId, branchId]) : null
  const previousSource = useRef<string | null>(null)
  const sourceChanged = Boolean(sourceKey && previousSource.current && sourceKey !== previousSource.current)
  useEffect(() => {
    if (!sourceKey) return
    if (sourceChanged) {
      const next = new URLSearchParams(searchParams)
      TOURNAMENT_URL_KEYS.forEach(key => next.delete(key))
      if (next.toString() !== searchParams.toString()) setSearchParams(next, { replace: true })
    }
    previousSource.current = sourceKey
  }, [sourceKey, sourceChanged, searchParams, setSearchParams])
  return (
    <section className="panel viewer-shell-page">
      <div className="page-intro"><h2>{t.title}</h2><p className="subtitle">{t.subtitle}</p></div>
      <article className="viewer-active-run-card" aria-label={t.heading}>
        <h3>{t.heading}</h3>
        {!runId ? <p className="empty-state">{t.noRun} <Link to={viewerRunsPath()}>{t.choose}</Link></p> :
          context.isPending || context.isFetching ? <p className="status" role="status">{t.resolving}</p> :
          context.isError ? <div role="alert"><p className="error">{t.contextError}</p>
            <button type="button" onClick={() => void context.refetch()}>{t.retry}</button></div> :
          !branchId ? <div role="alert"><p className="error">{t.badContext}</p>
            <button type="button" onClick={() => void context.refetch()}>{t.retry}</button></div> :
          <TournamentCatalogForBranch key={JSON.stringify([runId, branchId])} runId={runId} branchId={branchId}
            t={t} ignoreUrlFilters={sourceChanged} />}
      </article>
    </section>
  )
}
