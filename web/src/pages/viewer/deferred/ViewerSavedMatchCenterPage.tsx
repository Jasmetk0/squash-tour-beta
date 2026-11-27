import { useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link, useSearchParams } from 'react-router-dom'

import { getViewerRunCalendar, getViewerTournamentHistory, getViewerTournamentResult } from '../../../api/client'
import type { ViewerTournamentResult } from '../../../api/types'
import { useLanguage } from '../../../i18n/LanguageContext'
import { useActiveViewerProductRunId } from '../../../viewer/useActiveViewerProductRunId'
import { useViewerOfficialRunContext } from '../../../viewer/useViewerOfficialRunContext'
import {
  viewerPlannedEventPath, viewerPlayerProfilePath, viewerRunsPath, viewerTournamentDetailPath,
} from '../../../viewer/viewerRoutes'
import {
  catalogSeasonsNewestFirst, tournamentViewerBranch, verifiedTournamentCatalog,
  type SavedTournamentCatalog, type SavedTournamentEntry,
} from '../tour/viewerTournamentCatalog'
import {
  filterPublishedMatches, verifiedSavedMatchResult, type PublicMatchDraw,
} from './viewerSavedMatchCenter'

const EVENTS_PAGE_SIZE = 20
const MATCHES_PAGE_SIZE = 25
const messages = {
  title: ['Zápasové centrum', 'Match Center'],
  subtitle: ['Veřejné zápasy z výsledků skutečně publikovaných turnajů aktuální Viewer Branch.',
    'Public matches from genuinely published tournament results in the current Viewer Branch.'],
  scope: ['Zobrazuje pouze uložené výsledky legacy W61. Bez budoucích, živých nebo nepublikovaných zápasů, bez časů utkání, rally-by-rally replaye a bez odvozování chybějících kol. Historické ID hráče není jeho historická profilová karta.',
    'Shows only Saved legacy W61 results. No future, live or unpublished matches, match times, rally-by-rally replay or inferred missing rounds. A historical player ID is not a historical profile snapshot.'],
  noRun: ['Nejprve vyber Product Run.', 'Select a Product Run first.'],
  chooseRun: ['Seznam Runů', 'Run browser'],
  contextLoading: ['Ověřuji Viewer Branch…', 'Verifying Viewer Branch…'],
  badContext: ['Vybraný Run nemá ověřenou Viewer Branch.', 'The selected Run has no verified Viewer Branch.'],
  loading: ['Načítám uložené turnaje…', 'Loading Saved tournaments…'],
  readError: ['Uložený kalendář nebo historie turnajů nejsou dostupné.', 'Saved calendar or tournament history is unavailable.'],
  mismatch: ['Kalendář a historie výsledků nejsou ze stejného ověřeného zdroje.', 'Calendar and published history do not share one verified source.'],
  retry: ['Načíst znovu (GET)', 'Retry read (GET)'],
  run: ['Product Run', 'Product Run'],
  branch: ['Viewer Branch', 'Viewer Branch'],
  eventCount: ['Turnaje v kalendáři', 'Calendar events'],
  publishedCount: ['Turnaje s publikovaným výsledkem', 'Tournaments with published results'],
  season: ['Sezona', 'Season'],
  week: ['Týden', 'Week'],
  category: ['Kategorie', 'Category'],
  publishedEvents: ['Turnaje s publikovanými výsledky', 'Tournaments with published results'],
  searchEvent: ['Hledat název nebo ID turnaje', 'Search tournament name or ID'],
  allSeasons: ['Všechny sezony', 'All seasons'],
  view: ['Zobrazit zápasy', 'View matches'],
  selected: ['Zvolený turnaj', 'Selected tournament'],
  detail: ['Detail turnaje', 'Tournament detail'],
  clearSelection: ['Skrýt zápasy', 'Hide matches'],
  noEvents: ['Uložený kalendář neobsahuje žádný turnaj.', 'Saved calendar contains no tournaments.'],
  noPublished: ['Zatím není publikován žádný turnajový výsledek.', 'No tournament results have been published yet.'],
  noMatchEvent: ['Filtrům neodpovídá žádný publikovaný turnaj.', 'No published tournament matches these filters.'],
  wrongEvent: ['Požadovaný turnaj nemá výsledek publikovaný ve zvolené Viewer Branch.', 'Requested tournament has no published result in this Viewer Branch.'],
  wrongEventScope: ['Odkaz na turnaj patří jinému Runu nebo Viewer Branch, případně je neúplný.', 'The tournament link belongs to a different Run or Viewer Branch, or is incomplete.'],
  unknownSeason: ['Nedostupná sezona', 'Unavailable season'],
  eventLoading: ['Načítám publikovaný výsledek vybraného turnaje…', 'Loading the selected published tournament result…'],
  eventError: ['Publikovaný turnajový výsledek není dostupný.', 'Published tournament result is unavailable.'],
  eventMismatch: ['Detail zápasů neodpovídá publikovanému turnaji nebo obsahuje nepovolené údaje.', 'Match detail disagrees with the published tournament or contains forbidden data.'],
  champion: ['Publikovaný vítěz', 'Published champion'],
  finalist: ['Publikovaný finalista', 'Published finalist'],
  matchCount: ['Zápasů ve veřejném výsledku', 'Matches in public result'],
  matches: ['Publikované zápasy vybraného turnaje', 'Published matches for selected tournament'],
  noMatches: ['Veřejný výsledek neobsahuje žádné záznamy zápasů.', 'Public result contains no match records.'],
  noMatchRows: ['Vyhledávání neodpovídá žádný zápas.', 'No matches match these filters.'],
  searchMatches: ['Hledat ID zápasu, hráče nebo skóre', 'Search match ID, player or score'],
  draw: ['Část turnaje', 'Draw section'],
  allDraws: ['Všechny části', 'All sections'],
  qualification: ['Kvalifikace', 'Qualification'],
  main: ['Hlavní pavouk', 'Main draw'],
  group: ['Skupiny', 'Group'],
  knockout: ['Vyřazovací část', 'Knockout'],
  round: ['Kolo', 'Round'],
  position: ['Pozice v pavouku', 'Bracket position'],
  matchId: ['ID zápasu', 'Match ID'],
  winner: ['Vítěz (ID hráče)', 'Winner (player ID)'],
  loser: ['Poražený (ID hráče)', 'Loser (player ID)'],
  score: ['Zveřejněné skóre', 'Published score'],
  clear: ['Vymazat filtry', 'Clear filters'],
  matchLink: ['Přímý odkaz na zápas', 'Direct match link'],
  invalidMatch: ['Požadovaný zápas není v ověřeném výsledku tohoto turnaje nebo je odkaz nejednoznačný.', 'The requested match is not in this verified tournament result, or the link is ambiguous.'],
  clearMatch: ['Zobrazit všechny zápasy', 'Show all matches'],
  showing: ['Zobrazeno', 'Showing'],
  of: ['z', 'of'],
  page: ['Stránka', 'Page'],
  previous: ['Předchozí', 'Previous'],
  next: ['Další', 'Next'],
} as const
type Key = keyof typeof messages
type T = (key: Key) => string
type DrawKey = 'qualification' | 'main' | 'group' | 'knockout'
function drawLabel(draw: DrawKey, t: T): string {
  return t(draw)
}
function sortEvents(a: SavedTournamentEntry, b: SavedTournamentEntry): number {
  return String(b.event.season).localeCompare(String(a.event.season), 'cs', { numeric: true }) ||
    b.event.season_week - a.event.season_week ||
    a.event.event_id.localeCompare(b.event.event_id)
}

const exactMatchKeys = ['match', 'matchRun', 'matchBranch'] as const
const resultFilterKeys = [...exactMatchKeys, 'matchSearch', 'matchDraw', 'matchPage'] as const
function uniqueParam(params: URLSearchParams, key: string): string | null {
  const values = params.getAll(key)
  return values.length === 1 ? values[0] : null
}
function readPage(params: URLSearchParams, key: string): number {
  const raw = uniqueParam(params, key)
  if (!raw || !/^[1-9]\d*$/.test(raw)) return 1
  const n = Number(raw)
  return Number.isSafeInteger(n) ? n : 1
}
function readDraw(params: URLSearchParams): PublicMatchDraw {
  const raw = uniqueParam(params, 'matchDraw')
  return raw === 'qualification' || raw === 'main' || raw === 'group' || raw === 'knockout'
    ? raw : 'all'
}

function ResultMatches({ entry, runId, branchId, t }: {
  entry: SavedTournamentEntry; runId: string; branchId: string; t: T
}): JSX.Element {
  const [params, setParams] = useSearchParams()
  const search = uniqueParam(params, 'matchSearch') ?? ''
  const draw = readDraw(params)
  const page = readPage(params, 'matchPage')
  const matchId = uniqueParam(params, 'match')
  const hasMatch = params.has('match')
  const hasMatchScope = params.has('matchRun') || params.has('matchBranch')
  const invalidMatchScope = hasMatchScope && (!hasMatch ||
    uniqueParam(params, 'matchRun') !== runId ||
    uniqueParam(params, 'matchBranch') !== branchId)
  function changeResult(update: (next: URLSearchParams) => void, replace = false): void {
    setParams(previous => {
      const next = new URLSearchParams(previous)
      update(next)
      return next
    }, { replace })
  }
  function clearResultFilters(): void {
    changeResult(next => resultFilterKeys.forEach(key => next.delete(key)))
  }
  const query = useQuery({
    queryKey: ['viewer-saved-match-result', runId, branchId, entry.event.event_id],
    queryFn: () => getViewerTournamentResult(runId, entry.event.event_id),
    enabled: !invalidMatchScope,
    retry: false, refetchOnWindowFocus: false,
  })
  if (invalidMatchScope) return <div role="alert">
    <p>{t('invalidMatch')}</p>
    <button type="button" onClick={clearResultFilters}>{t('clearMatch')}</button>
  </div>
  if (query.isPending || query.isFetching) return <p role="status">{t('eventLoading')}</p>
  if (query.isError) return <div role="alert">
    <p>{t('eventError')}</p>
    <button type="button" onClick={() => void query.refetch()}>{t('retry')}</button>
  </div>
  const source = verifiedSavedMatchResult(query.data, entry, runId, branchId)
  if (!source) return <div role="alert">
    <p>{t('eventMismatch')}</p>
    <button type="button" onClick={() => void query.refetch()}>{t('retry')}</button>
  </div>
  if (hasMatch && (!matchId || !source.matches.some(match => match.match_id === matchId))) {
    return <div role="alert"><p>{t('invalidMatch')}</p>
      <button type="button" onClick={clearResultFilters}>{t('clearMatch')}</button>
    </div>
  }
  return <SavedMatchRows source={source} runId={runId} t={t}
    exactMatch={matchId} matchLink={id => {
      const next = new URLSearchParams(params)
      resultFilterKeys.forEach(key => next.delete(key))
      next.set('match', id)
      next.set('matchRun', runId)
      next.set('matchBranch', branchId)
      return '?' + next.toString()
    }}
    search={search} onSearch={value => changeResult(next => {
      exactMatchKeys.forEach(key => next.delete(key)); next.delete('matchPage')
      if (value) next.set('matchSearch', value); else next.delete('matchSearch')
    }, true)}
    draw={draw} onDraw={value => changeResult(next => {
      exactMatchKeys.forEach(key => next.delete(key)); next.delete('matchPage')
      if (value === 'all') next.delete('matchDraw'); else next.set('matchDraw', value)
    })}
    page={page} onPage={value => changeResult(next => {
      if (value === 1) next.delete('matchPage'); else next.set('matchPage', String(value))
    })}
    onClear={clearResultFilters}
  />
}

function SavedMatchRows({ source, runId, t, exactMatch, matchLink, search, onSearch, draw, onDraw, page, onPage, onClear }: {
  source: ViewerTournamentResult; runId: string; t: T
  search: string; onSearch: (v: string) => void
  draw: PublicMatchDraw; onDraw: (v: PublicMatchDraw) => void
  exactMatch: string | null; matchLink: (id: string) => string
  page: number; onPage: (v: number) => void
  onClear: () => void
}): JSX.Element {
  const filtered = useMemo(
    () => exactMatch ? source.matches.filter(match => match.match_id === exactMatch)
      : filterPublishedMatches(source.matches, search, draw),
    [source, search, draw, exactMatch],
  )
  const pages = Math.ceil(filtered.length / MATCHES_PAGE_SIZE)
  const current = exactMatch ? 1 : Math.min(page, pages || 1)
  const offset = (current - 1) * MATCHES_PAGE_SIZE
  const visible = filtered.slice(offset, offset + MATCHES_PAGE_SIZE)
  return <div>
    <dl className="metadata-list viewer-metadata-list">
      <div><dt>{t('champion')}</dt><dd><Link to={viewerPlayerProfilePath(runId, source.champion_player_id)}>
        {source.champion_player_id}</Link></dd></div>
      <div><dt>{t('finalist')}</dt><dd><Link to={viewerPlayerProfilePath(runId, source.finalist_player_id)}>
        {source.finalist_player_id}</Link></dd></div>
      <div><dt>{t('matchCount')}</dt><dd>{source.matches.length}</dd></div>
    </dl>
    {source.matches.length === 0 ? <p className="empty-state">{t('noMatches')}</p> : <>
      {exactMatch ? <button type="button" onClick={onClear}>{t('clearMatch')}</button> :
      <div className="viewer-filters">
        <label htmlFor="viewer-match-search">{t('searchMatches')}</label>
        <input id="viewer-match-search" type="search" value={search}
          onChange={e => onSearch(e.target.value)} />
        <label htmlFor="viewer-match-draw">{t('draw')}</label>
        <select id="viewer-match-draw" value={draw}
          onChange={e => onDraw(e.target.value as PublicMatchDraw)}>
          <option value="all">{t('allDraws')}</option>
          <option value="qualification">{t('qualification')}</option>
          <option value="main">{t('main')}</option>
          <option value="group">{t('group')}</option>
          <option value="knockout">{t('knockout')}</option>
        </select>
        <button type="button" onClick={onClear}>{t('clear')}</button>
      </div>}
      {filtered.length === 0 ? <p className="empty-state">{t('noMatchRows')}</p> :
        <div className="table-wrap">
          <table aria-label={t('matches')}>
            <thead><tr>
              <th scope="col">{t('draw')}</th>
              <th scope="col">{t('round')}</th>
              <th scope="col">{t('position')}</th>
              <th scope="col">{t('matchId')}</th>
              <th scope="col">{t('winner')}</th>
              <th scope="col">{t('loser')}</th>
              <th scope="col">{t('score')}</th>
            </tr></thead>
            <tbody>{visible.map(match => <tr key={match.match_id}>
              <td>{drawLabel(match.draw_type, t)}</td>
              <td>{match.round_number}</td>
              <td>{match.bracket_position}</td>
              <td><Link to={matchLink(match.match_id)} title={t('matchLink')}>{match.match_id}</Link></td>
              <td><Link to={viewerPlayerProfilePath(runId, match.winner_player_id)}>
                {match.winner_player_id}</Link></td>
              <td>{match.loser_player_id
                ? <Link to={viewerPlayerProfilePath(runId, match.loser_player_id)}>
                    {match.loser_player_id}</Link>
                : '—'}</td>
              <td>{match.scoreline || '—'}</td>
            </tr>)}</tbody>
          </table>
        </div>}
      <p role="status">{t('showing')} {filtered.length ? offset + 1 : 0}–
        {filtered.length ? offset + visible.length : 0} {t('of')} {filtered.length}</p>
      {pages > 1 ? <nav aria-label={t('page')}>
        <button type="button" disabled={current === 1}
          onClick={() => onPage(Math.max(1, current - 1))}>{t('previous')}</button>
        <span>{t('page')} {current} / {pages}</span>
        <button type="button" disabled={current === pages}
          onClick={() => onPage(Math.min(pages, current + 1))}>{t('next')}</button>
      </nav> : null}
    </>}
  </div>
}

function MatchCenterCatalog({ catalog, runId, branchId, t }: {
  catalog: SavedTournamentCatalog; runId: string; branchId: string; t: T
}): JSX.Element {
  const [urlParams, setUrlParams] = useSearchParams()
  const season = uniqueParam(urlParams, 'eventSeason') ?? 'all'
  const search = uniqueParam(urlParams, 'eventSearch') ?? ''
  const page = readPage(urlParams, 'eventPage')
  function changeCatalog(key: string, value: string, fallback: string, replace = false): void {
    setUrlParams(previous => {
      const next = new URLSearchParams(previous)
      if (key !== 'eventPage') next.delete('eventPage')
      if (value === fallback) next.delete(key)
      else next.set(key, value)
      return next
    }, { replace })
  }
  function clearCatalog(): void {
    setUrlParams(previous => {
      const next = new URLSearchParams(previous)
      for (const key of ['eventSeason', 'eventSearch', 'eventPage']) next.delete(key)
      return next
    })
  }
  const published = useMemo(
    () => catalog.entries.filter(entry => entry.publication.result_published).sort(sortEvents),
    [catalog],
  )
  const seasons = useMemo(() => catalogSeasonsNewestFirst(catalog), [catalog])
  const filtered = useMemo(() => {
    const term = search.trim().toLocaleLowerCase()
    return published.filter(({ event }) =>
      (season === 'all' || String(event.season) === season) &&
      (!term || [event.event_name, event.event_id, event.category, event.host_country]
        .some(value => value.toLocaleLowerCase().includes(term)))
    )
  }, [published, season, search])
  const pages = Math.ceil(filtered.length / EVENTS_PAGE_SIZE)
  const current = Math.min(page, pages || 1)
  const offset = (current - 1) * EVENTS_PAGE_SIZE
  const visible = filtered.slice(offset, offset + EVENTS_PAGE_SIZE)
  const eventParams = urlParams.getAll('event')
  const requestedEventId = eventParams.length === 1 ? eventParams[0] : null
  const hasEventScope = urlParams.has('eventRun') || urlParams.has('eventBranch')
  const wrongEventScope = hasEventScope && (!requestedEventId ||
    uniqueParam(urlParams, 'eventRun') !== runId ||
    uniqueParam(urlParams, 'eventBranch') !== branchId)
  const selected = wrongEventScope ? null :
    published.find(item => item.event.event_id === requestedEventId) ?? null
  function selectEvent(eventId: string | null): void {
    setUrlParams(previous => {
      const next = new URLSearchParams(previous)
      resultFilterKeys.forEach(key => next.delete(key))
      if (eventId) {
        next.set('event', eventId)
        next.set('eventRun', runId)
        next.set('eventBranch', branchId)
      } else {
        for (const key of ['event', 'eventRun', 'eventBranch']) next.delete(key)
      }
      return next
    })
  }
  return <article className="viewer-active-run-card">
    <dl className="metadata-list viewer-metadata-list">
      <div><dt>{t('run')}</dt><dd>{runId}</dd></div>
      <div><dt>{t('branch')}</dt><dd>{branchId}</dd></div>
      <div><dt>{t('eventCount')}</dt><dd>{catalog.eventCount}</dd></div>
      <div><dt>{t('publishedCount')}</dt><dd>{catalog.publishedCount}</dd></div>
    </dl>
    {catalog.eventCount === 0 ? <p className="empty-state">{t('noEvents')}</p> :
      published.length === 0 ? <p className="empty-state">{t('noPublished')}</p> : <>
        <div className="viewer-filters">
          <label htmlFor="viewer-match-season">{t('season')}</label>
          <select id="viewer-match-season" value={season}
            onChange={e => changeCatalog('eventSeason', e.target.value, 'all')}>
            <option value="all">{t('allSeasons')}</option>
            {season !== 'all' && !seasons.includes(season) ?
              <option value={season}>{t('unknownSeason')}: {season}</option> : null}
            {seasons.map(value => <option key={value} value={value}>{value}</option>)}
          </select>
          <label htmlFor="viewer-match-events-search">{t('searchEvent')}</label>
          <input id="viewer-match-events-search" type="search" value={search}
            onChange={e => changeCatalog('eventSearch', e.target.value, '', true)} />
          <button type="button" onClick={clearCatalog}>
            {t('clear')}
          </button>
        </div>
        {filtered.length === 0 ? <p className="empty-state">{t('noMatchEvent')}</p> :
          <div className="table-wrap">
            <table aria-label={t('publishedEvents')}>
              <thead><tr><th scope="col">{t('season')}</th><th scope="col">{t('week')}</th>
                <th scope="col">{t('category')}</th><th scope="col">{t('selected')}</th>
                <th scope="col">{t('view')}</th></tr></thead>
              <tbody>{visible.map(({ event }) => <tr key={event.event_id}>
                <td>{String(event.season)}</td>
                <td>W{event.season_week}</td>
                <td>{event.category}</td>
                <td><Link to={viewerPlannedEventPath(runId, event.event_id)}>
                  {event.event_name || event.event_id}</Link></td>
                <td><button type="button"
                  onClick={() => selectEvent(event.event_id)}>{t('view')}</button></td>
              </tr>)}</tbody>
            </table>
          </div>}
        <p role="status">{t('showing')} {filtered.length ? offset + 1 : 0}–
          {filtered.length ? offset + visible.length : 0} {t('of')} {filtered.length}</p>
        {pages > 1 ? <nav aria-label={t('page')}>
          <button type="button" disabled={current === 1}
            onClick={() => changeCatalog('eventPage', String(current - 1), '1')}>{t('previous')}</button>
          <span>{t('page')} {current} / {pages}</span>
          <button type="button" disabled={current === pages}
            onClick={() => changeCatalog('eventPage', String(current + 1), '1')}>{t('next')}</button>
        </nav> : null}
      </>}
    {(eventParams.length > 0 || hasEventScope) && !selected ? <div role="alert">
      <p>{t(wrongEventScope ? 'wrongEventScope' : 'wrongEvent')}</p>
      <button type="button" onClick={() => selectEvent(null)}>{t('clearSelection')}</button>
    </div> : null}
    {selected ? <section aria-label={t('selected')} className="viewer-active-run-card">
      <h3>{selected.event.event_name || selected.event.event_id} · {String(selected.event.season)} · W{selected.event.season_week}</h3>
      <p><Link to={viewerTournamentDetailPath(runId, selected.event.event_id)}>
        {t('detail')}</Link></p>
      <button type="button" onClick={() => selectEvent(null)}>{t('clearSelection')}</button>
      <ResultMatches key={JSON.stringify([runId, branchId, selected.event.event_id])}
        entry={selected} runId={runId} branchId={branchId} t={t} />
    </section> : null}
  </article>
}

export function ViewerSavedMatchCenterPage(): JSX.Element {
  const runId = useActiveViewerProductRunId()?.trim() ?? ''
  const { language } = useLanguage()
  const t: T = key => messages[key][language === 'cs' ? 0 : 1]
  const context = useViewerOfficialRunContext(runId)
  const branchId = tournamentViewerBranch(context.data, runId)
  const ready = Boolean(runId && branchId && !context.isPending && !context.isFetching && !context.isError)
  const query = useQuery({
    queryKey: ['viewer-saved-match-center-catalog', runId, branchId],
    queryFn: async () => {
      const [calendar, history] = await Promise.all([
        getViewerRunCalendar(runId), getViewerTournamentHistory(runId),
      ])
      return { calendar, history }
    },
    enabled: ready, retry: false, refetchOnWindowFocus: false,
  })
  return <section className="panel viewer-shell-page">
    <div className="page-intro">
      <h2>{t('title')}</h2>
      <p className="subtitle">{t('subtitle')}</p>
    </div>
    <p className="subtitle">{t('scope')}</p>
    {!runId ? <p className="empty-state">{t('noRun')} <Link to={viewerRunsPath()}>{t('chooseRun')}</Link></p> :
      context.isPending || context.isFetching ? <p role="status">{t('contextLoading')}</p> :
      !ready ? <div role="alert">
        <p>{t('badContext')}</p>
        <button type="button" onClick={() => void context.refetch()}>{t('retry')}</button>
      </div> :
      query.isPending || query.isFetching ? <p role="status">{t('loading')}</p> :
      query.isError ? <div role="alert">
        <p>{t('readError')}</p>
        <button type="button" onClick={() => void query.refetch()}>{t('retry')}</button>
      </div> : (() => {
        const catalog = verifiedTournamentCatalog(
          query.data.calendar, query.data.history, runId, branchId ?? '',
        )
        return catalog
          ? <MatchCenterCatalog key={JSON.stringify([runId, branchId])}
              catalog={catalog} runId={runId} branchId={branchId ?? ''} t={t} />
          : <div role="alert">
              <p>{t('mismatch')}</p>
              <button type="button" onClick={() => void query.refetch()}>{t('retry')}</button>
            </div>
      })()}
  </section>
}
