import { useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'

import { getViewerRunCalendar, getViewerTournamentHistory } from '../../../api/client'
import { useLanguage } from '../../../i18n/LanguageContext'
import { useActiveViewerProductRunId } from '../../../viewer/useActiveViewerProductRunId'
import { useViewerOfficialRunContext } from '../../../viewer/useViewerOfficialRunContext'
import { viewerPlayerProfilePath, viewerPlannedEventPath, viewerRunsPath } from '../../../viewer/viewerRoutes'
import { catalogSeasonsNewestFirst, tournamentViewerBranch, verifiedTournamentCatalog, type SavedTournamentCatalog } from '../tour/viewerTournamentCatalog'

const PAGE_SIZE = 25
const messages = {
  title: ['Vítězové podle publikovaných titulů', 'Leaders by published titles'],
  description: ['Pouze skutečné publikované turnaje aktuální uložené Viewer Branch.', 'Only real published tournaments in the current Saved Viewer Branch.'],
  scope: [
    'Jde o počty doložených publikovaných vítězství, ne o úplný kariérní rekord ani historický pohled na libovolný zvolený týden. Chybějící výsledky se nedopočítávají.',
    'These are counts of evidenced published wins, not complete career records or a snapshot at any arbitrarily selected week. Missing results are not extrapolated.',
  ],
  noRun: ['Nejprve vyber Product Run.', 'Select a Product Run first.'],
  runs: ['Seznam Runů', 'Run browser'],
  contextLoading: ['Ověřuji uloženou Viewer Branch…', 'Verifying Saved Viewer Branch…'],
  badContext: ['Zdrojová Viewer Branch není pro vybraný Run ověřená.', 'The Saved Viewer Branch is not verified for the selected Run.'],
  loading: ['Načítám publikované výsledky…', 'Loading published results…'],
  unavailable: ['Uložený kalendář nebo historie turnajů není dostupná.', 'Saved calendar or tournament history is unavailable.'],
  mismatch: ['Uložený kalendář a historie výsledků se neshodují. Žádné pořadí se nezobrazuje.', 'Saved calendar and results disagree. No leaderboard is displayed.'],
  retry: ['Načíst znovu (GET)', 'Retry read (GET)'],
  run: ['Product Run', 'Product Run'],
  branch: ['Viewer Branch', 'Viewer Branch'],
  total: ['Publikovaných výsledků', 'Published results'],
  allSeasons: ['Všechny uložené sezony', 'All saved seasons'],
  season: ['Sezona', 'Season'],
  category: ['Kategorie', 'Category'],
  allCategories: ['Všechny kategorie', 'All categories'],
  search: ['Hledat ID vítěze', 'Search champion ID'],
  clear: ['Vymazat filtry', 'Clear filters'],
  table: ['Pořadí publikovaných vítězů', 'Published title leaderboard'],
  rank: ['Pořadí', 'Rank'],
  player: ['Hráč (historické ID)', 'Player (historical ID)'],
  titles: ['Publikované tituly', 'Published titles'],
  seasons: ['Sezony s vítězstvím', 'Seasons with a win'],
  latest: ['Poslední doložené vítězství', 'Latest evidenced win'],
  noTitles: ['Zatím není publikován žádný vítěz.', 'No champions have been published yet.'],
  noMatch: ['Filtrům neodpovídá žádný publikovaný vítěz.', 'No published champion matches these filters.'],
  showing: ['Zobrazeno', 'Showing'],
  of: ['z', 'of'],
  page: ['Stránka', 'Page'],
  previous: ['Předchozí', 'Previous'],
  next: ['Další', 'Next'],
} as const
type CopyKey = keyof typeof messages
type Translator = (key: CopyKey) => string

export type PublishedTitleLeader = {
  playerId: string
  titleCount: number
  seasonCount: number
  latestEventId: string
  latestEventName: string
  latestSeason: string
  latestWeek: number
}

// All inputs have already passed the exact two-source Saved catalog proof.
// Calculate only successes explicitly marked result_published. Stable player IDs
// are never looked up from today's roster and no win is inferred from status.
export function publishedTitleLeaders(
  catalog: SavedTournamentCatalog,
  season = 'all',
  category = 'all',
  search = '',
): PublishedTitleLeader[] {
  const order = new Map(catalogSeasonsNewestFirst(catalog).map((s, index) => [s, index]))
  const needle = search.trim().toLocaleLowerCase()
  const map = new Map<string, PublishedTitleLeader & { seenSeasons: Set<string> }>()

  for (const { event, publication } of catalog.entries) {
    if (!publication.result_published || !publication.champion_player_id) continue
    const eventSeason = String(event.season)
    if (season !== 'all' && eventSeason !== season) continue
    if (category !== 'all' && event.category !== category) continue
    const playerId = publication.champion_player_id
    if (needle && !playerId.toLocaleLowerCase().includes(needle)) continue

    const previous = map.get(playerId)
    if (!previous) {
      map.set(playerId, {
        playerId, titleCount: 1, seasonCount: 1, seenSeasons: new Set([eventSeason]),
        latestEventId: event.event_id, latestEventName: event.event_name || event.event_id,
        latestSeason: eventSeason, latestWeek: event.season_week,
      })
      continue
    }
    previous.titleCount++
    previous.seenSeasons.add(eventSeason)
    previous.seasonCount = previous.seenSeasons.size
    const newSeasonRank = order.get(eventSeason) ?? Number.MAX_SAFE_INTEGER
    const previousSeasonRank = order.get(previous.latestSeason) ?? Number.MAX_SAFE_INTEGER
    if (newSeasonRank < previousSeasonRank ||
        (newSeasonRank === previousSeasonRank &&
          (event.season_week > previous.latestWeek ||
            (event.season_week === previous.latestWeek && event.event_id < previous.latestEventId)))) {
      previous.latestEventId = event.event_id
      previous.latestEventName = event.event_name || event.event_id
      previous.latestSeason = eventSeason
      previous.latestWeek = event.season_week
    }
  }

  return [...map.values()].map(({ seenSeasons: _seenSeasons, ...leader }) => leader)
    .sort((a, b) => b.titleCount - a.titleCount || a.playerId.localeCompare(b.playerId, 'cs'))
}

function Leaderboard({ catalog, runId, branchId, t }: {
  catalog: SavedTournamentCatalog; runId: string; branchId: string; t: Translator
}): JSX.Element {
  const [season, setSeason] = useState('all')
  const [category, setCategory] = useState('all')
  const [search, setSearch] = useState('')
  const [page, setPage] = useState(1)
  const seasons = useMemo(() => catalogSeasonsNewestFirst(catalog), [catalog])
  const categories = useMemo(() => [...new Set(catalog.entries.map(x => x.event.category))].sort(), [catalog])
  const leaders = useMemo(() =>
    publishedTitleLeaders(catalog, season, category, search),
    [catalog, season, category, search]
  )
  const pages = Math.ceil(leaders.length / PAGE_SIZE)
  const currentPage = Math.min(page, pages || 1)
  const offset = (currentPage - 1) * PAGE_SIZE
  const visible = leaders.slice(offset, offset + PAGE_SIZE)

  function reset(): void {
    setSeason('all'); setCategory('all'); setSearch(''); setPage(1)
  }
  return (
    <article className="viewer-active-run-card">
      <dl className="metadata-list viewer-metadata-list">
        <div><dt>{t('run')}</dt><dd>{runId}</dd></div>
        <div><dt>{t('branch')}</dt><dd>{branchId}</dd></div>
        <div><dt>{t('total')}</dt><dd>{catalog.publishedCount}</dd></div>
      </dl>
      {catalog.publishedCount === 0 ? <p className="empty-state">{t('noTitles')}</p> : <>
        <div className="viewer-filters">
          <label htmlFor="title-leaders-season">{t('season')}</label>
          <select id="title-leaders-season" value={season} onChange={e => { setSeason(e.target.value); setPage(1) }}>
            <option value="all">{t('allSeasons')}</option>
            {seasons.map(value => <option key={value} value={value}>{value}</option>)}
          </select>
          <label htmlFor="title-leaders-category">{t('category')}</label>
          <select id="title-leaders-category" value={category} onChange={e => { setCategory(e.target.value); setPage(1) }}>
            <option value="all">{t('allCategories')}</option>
            {categories.map(value => <option key={value} value={value}>{value}</option>)}
          </select>
          <label htmlFor="title-leaders-search">{t('search')}</label>
          <input id="title-leaders-search" type="search" value={search}
            onChange={e => { setSearch(e.target.value); setPage(1) }} />
          <button type="button" onClick={reset}>{t('clear')}</button>
        </div>
        {leaders.length === 0 ? <p className="empty-state">{t('noMatch')}</p> : (
          <div className="table-wrap">
            <table aria-label={t('table')}>
              <thead><tr>
                <th scope="col">{t('rank')}</th>
                <th scope="col">{t('player')}</th>
                <th scope="col">{t('titles')}</th>
                <th scope="col">{t('seasons')}</th>
                <th scope="col">{t('latest')}</th>
              </tr></thead>
              <tbody>{visible.map((leader, index) => (
                <tr key={leader.playerId}>
                  <td>{offset + index + 1}</td>
                  <td><Link to={viewerPlayerProfilePath(runId, leader.playerId)}>{leader.playerId}</Link></td>
                  <td>{leader.titleCount}</td>
                  <td>{leader.seasonCount}</td>
                  <td>{leader.latestSeason} · W{leader.latestWeek} · {' '}
                    <Link to={viewerPlannedEventPath(runId, leader.latestEventId)}>{leader.latestEventName}</Link>
                  </td>
                </tr>
              ))}</tbody>
            </table>
          </div>
        )}
        <p role="status">{t('showing')} {leaders.length ? offset + 1 : 0}–
          {leaders.length ? offset + visible.length : 0} {t('of')} {leaders.length}</p>
        {pages > 1 ? <nav aria-label={t('page')}>
          <button type="button" disabled={currentPage === 1} onClick={() => setPage(currentPage - 1)}>{t('previous')}</button>
          <span>{t('page')} {currentPage} / {pages}</span>
          <button type="button" disabled={currentPage === pages} onClick={() => setPage(currentPage + 1)}>{t('next')}</button>
        </nav> : null}
      </>}
    </article>
  )
}

export function ViewerPublishedTitleLeadersPage(): JSX.Element {
  const runId = useActiveViewerProductRunId()?.trim() ?? ''
  const { language } = useLanguage()
  const t: Translator = key => messages[key][language === 'cs' ? 0 : 1]
  const context = useViewerOfficialRunContext(runId)
  const branchId = tournamentViewerBranch(context.data, runId)
  const validContext = Boolean(runId && branchId && !context.isPending && !context.isFetching && !context.isError)
  const query = useQuery({
    queryKey: ['viewer-published-title-leaders', runId, branchId],
    queryFn: async () => {
      const [calendar, history] = await Promise.all([
        getViewerRunCalendar(runId), getViewerTournamentHistory(runId),
      ])
      return { calendar, history }
    },
    enabled: validContext,
    retry: false,
    refetchOnWindowFocus: false,
  })

  return (
    <section className="panel viewer-shell-page">
      <div className="page-intro">
        <h2>{t('title')}</h2>
        <p className="subtitle">{t('description')}</p>
      </div>
      <p className="subtitle">{t('scope')}</p>
      {!runId ? <p className="empty-state">{t('noRun')} <Link to={viewerRunsPath()}>{t('runs')}</Link></p> :
        context.isPending || context.isFetching ? <p role="status">{t('contextLoading')}</p> :
        !validContext ? <div role="alert">
          <p>{t('badContext')}</p>
          <button type="button" onClick={() => void context.refetch()}>{t('retry')}</button>
        </div> :
        query.isPending || query.isFetching ? <p role="status">{t('loading')}</p> :
        query.isError ? <div role="alert">
          <p>{t('unavailable')}</p>
          <button type="button" onClick={() => void query.refetch()}>{t('retry')}</button>
        </div> : (() => {
          const catalog = verifiedTournamentCatalog(query.data.calendar, query.data.history, runId, branchId ?? '')
          return catalog ? <Leaderboard key={JSON.stringify([runId, branchId])}
            catalog={catalog} runId={runId} branchId={branchId ?? ''} t={t} /> :
            <div role="alert">
              <p>{t('mismatch')}</p>
              <button type="button" onClick={() => void query.refetch()}>{t('retry')}</button>
            </div>
        })()}
    </section>
  )
}
