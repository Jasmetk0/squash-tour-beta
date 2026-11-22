import { useMemo, useState } from 'react'
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

function ResultMatches({ entry, runId, branchId, t }: {
  entry: SavedTournamentEntry; runId: string; branchId: string; t: T
}): JSX.Element {
  const [search, setSearch] = useState('')
  const [draw, setDraw] = useState<PublicMatchDraw>('all')
  const [page, setPage] = useState(1)
  const query = useQuery({
    queryKey: ['viewer-saved-match-result', runId, branchId, entry.event.event_id],
    queryFn: () => getViewerTournamentResult(runId, entry.event.event_id),
    retry: false, refetchOnWindowFocus: false,
  })
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
  return <SavedMatchRows source={source} runId={runId} t={t}
    search={search} onSearch={value => { setSearch(value); setPage(1) }}
    draw={draw} onDraw={value => { setDraw(value); setPage(1) }}
    page={page} onPage={setPage}
    onClear={() => { setSearch(''); setDraw('all'); setPage(1) }}
  />
}

function SavedMatchRows({ source, runId, t, search, onSearch, draw, onDraw, page, onPage, onClear }: {
  source: ViewerTournamentResult; runId: string; t: T
  search: string; onSearch: (v: string) => void
  draw: PublicMatchDraw; onDraw: (v: PublicMatchDraw) => void
  page: number; onPage: (v: number | ((n: number) => number)) => void
  onClear: () => void
}): JSX.Element {
  const filtered = useMemo(
    () => filterPublishedMatches(source.matches, search, draw),
    [source, search, draw],
  )
  const pages = Math.ceil(filtered.length / MATCHES_PAGE_SIZE)
  const current = Math.min(page, pages || 1)
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
      </div>
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
              <td>{match.match_id}</td>
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
          onClick={() => onPage(n => Math.max(1, n - 1))}>{t('previous')}</button>
        <span>{t('page')} {current} / {pages}</span>
        <button type="button" disabled={current === pages}
          onClick={() => onPage(n => Math.min(pages, n + 1))}>{t('next')}</button>
      </nav> : null}
    </>}
  </div>
}

function MatchCenterCatalog({ catalog, runId, branchId, t }: {
  catalog: SavedTournamentCatalog; runId: string; branchId: string; t: T
}): JSX.Element {
  const [urlParams, setUrlParams] = useSearchParams()
  const [season, setSeason] = useState('all')
  const [search, setSearch] = useState('')
  const [page, setPage] = useState(1)
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
  const requestedEventId = urlParams.get('event')
  const selected = published.find(item => item.event.event_id === requestedEventId) ?? null
  function selectEvent(eventId: string | null): void {
    setUrlParams(previous => {
      const next = new URLSearchParams(previous)
      if (eventId) next.set('event', eventId)
      else next.delete('event')
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
            onChange={e => { setSeason(e.target.value); setPage(1) }}>
            <option value="all">{t('allSeasons')}</option>
            {seasons.map(value => <option key={value} value={value}>{value}</option>)}
          </select>
          <label htmlFor="viewer-match-events-search">{t('searchEvent')}</label>
          <input id="viewer-match-events-search" type="search" value={search}
            onChange={e => { setSearch(e.target.value); setPage(1) }} />
          <button type="button" onClick={() => { setSeason('all'); setSearch(''); setPage(1) }}>
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
            onClick={() => setPage(n => Math.max(1, n - 1))}>{t('previous')}</button>
          <span>{t('page')} {current} / {pages}</span>
          <button type="button" disabled={current === pages}
            onClick={() => setPage(n => Math.min(pages, n + 1))}>{t('next')}</button>
        </nav> : null}
      </>}
    {requestedEventId && !selected ? <div role="alert">
      <p>{t('wrongEvent')}</p>
      <button type="button" onClick={() => selectEvent(null)}>{t('clearSelection')}</button>
    </div> : null}
    {selected ? <section aria-label={t('selected')} className="viewer-active-run-card">
      <h3>{selected.event.event_name || selected.event.event_id} · W{selected.event.season_week}</h3>
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
