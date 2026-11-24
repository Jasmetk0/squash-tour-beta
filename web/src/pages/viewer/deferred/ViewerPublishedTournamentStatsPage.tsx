import { useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'

import { getViewerRunCalendar, getViewerTournamentHistory } from '../../../api/client'
import { useLanguage } from '../../../i18n/LanguageContext'
import { useActiveViewerProductRunId } from '../../../viewer/useActiveViewerProductRunId'
import { useViewerOfficialRunContext } from '../../../viewer/useViewerOfficialRunContext'
import { viewerPlannedEventPath, viewerRunsPath } from '../../../viewer/viewerRoutes'
import {
  catalogSeasonsNewestFirst, tournamentViewerBranch, verifiedTournamentCatalog,
  type SavedTournamentCatalog,
} from '../tour/viewerTournamentCatalog'

const PAGE_SIZE = 25

const copy = {
  title: ['Statistiky uložených turnajů', 'Saved Tournament Stats'],
  description: [
    'Rozdělení skutečného uloženého kalendáře a publikovaných výsledků vybrané Viewer Branch.',
    'Breakdown of the real Saved calendar and published results in the selected Viewer Branch.',
  ],
  scope: [
    'Počty se týkají pouze dostupné uložené historie. Dokončený kalendářní turnaj a publikovaný výsledek jsou různé údaje. Nejde o statistiku zápasů ani o rekonstrukci libovolného historického týdne.',
    'Counts cover only the available Saved history. A completed calendar event and a published result are different facts. This is neither match statistics nor a reconstruction of any arbitrary historical week.',
  ],
  noRun: ['Nejprve vyber Product Run.', 'Select a Product Run first.'],
  runs: ['Seznam Runů', 'Run browser'],
  contextLoading: ['Ověřuji Viewer Branch…', 'Verifying Viewer Branch…'],
  badContext: ['Nelze ověřit Viewer Branch tohoto Runu.', 'Cannot verify the Viewer Branch of this Run.'],
  loading: ['Načítám uložené turnaje…', 'Loading Saved tournaments…'],
  unavailable: ['Uložený kalendář nebo výsledky nejsou dostupné.', 'Saved calendar or results are unavailable.'],
  mismatch: ['Kalendář a historie výsledků neodpovídají stejnému uloženému zdroji.', 'Calendar and result history do not match the same Saved source.'],
  retry: ['Načíst znovu (GET)', 'Retry read (GET)'],
  run: ['Product Run', 'Product Run'],
  branch: ['Viewer Branch', 'Viewer Branch'],
  allEvents: ['Turnaje v kalendáři', 'Calendar events'],
  allPublished: ['Publikované výsledky', 'Published results'],
  allSeasons: ['Všechny sezony', 'All seasons'],
  allCategories: ['Všechny kategorie', 'All categories'],
  allHosts: ['Všechny pořadatelské země', 'All host countries'],
  season: ['Sezona', 'Season'],
  category: ['Kategorie', 'Category'],
  host: ['Pořadatelská země', 'Host country'],
  clear: ['Vymazat filtry', 'Clear filters'],
  table: ['Statistiky turnajů podle sezony a kategorie', 'Tournament statistics by season and category'],
  total: ['Celkem turnajů', 'Total tournaments'],
  completed: ['Dokončené v kalendáři', 'Completed in calendar'],
  published: ['Publikované výsledky', 'Published results'],
  winners: ['Různí publikovaní vítězové', 'Distinct published winners'],
  hosts: ['Pořadatelské země', 'Host countries'],
  latest: ['Poslední uložený turnaj', 'Latest Saved event'],
  noEvents: ['Kalendář této Viewer Branch neobsahuje turnaje.', 'The calendar in this Viewer Branch contains no events.'],
  noMatch: ['Filtrům neodpovídají žádné turnaje.', 'No tournaments match these filters.'],
  shown: ['Zobrazeno', 'Showing'],
  of: ['z', 'of'],
  page: ['Stránka', 'Page'],
  previous: ['Předchozí', 'Previous'],
  next: ['Další', 'Next'],
} as const

type Key = keyof typeof copy
type T = (key: Key) => string

export type SavedTournamentStatsRow = {
  season: string
  category: string
  eventCount: number
  completedCount: number
  publishedCount: number
  distinctWinners: number
  hostCount: number
  latestEventId: string
  latestEventName: string
  latestWeek: number
}

// Only records already proven to come from matching calendar/history Saved GETs.
// Separate completed calendar events from published sporting results; never
// backfill a champion or infer matches from an event's calendar status.
export function savedTournamentStatsRows(
  catalog: SavedTournamentCatalog,
  season = 'all',
  category = 'all',
  host = 'all',
): SavedTournamentStatsRow[] {
  type Internal = SavedTournamentStatsRow & { winnerIds: Set<string>; hostCodes: Set<string> }
  const rows = new Map<string, Internal>()
  const seasonOrder = new Map(catalogSeasonsNewestFirst(catalog).map((value, i) => [value, i]))

  for (const { event, publication } of catalog.entries) {
    const eventSeason = String(event.season)
    if (season !== 'all' && eventSeason !== season) continue
    if (category !== 'all' && event.category !== category) continue
    if (host !== 'all' && event.host_country !== host) continue
    const key = JSON.stringify([eventSeason, event.category])
    let row = rows.get(key)
    if (!row) {
      row = {
        season: eventSeason, category: event.category,
        eventCount: 0, completedCount: 0, publishedCount: 0,
        distinctWinners: 0, hostCount: 0,
        latestEventId: event.event_id, latestEventName: event.event_name || event.event_id,
        latestWeek: event.season_week,
        winnerIds: new Set(), hostCodes: new Set(),
      }
      rows.set(key, row)
    }
    row.eventCount++
    row.hostCodes.add(event.host_country)
    if (event.status === 'completed') row.completedCount++
    if (publication.result_published) {
      row.publishedCount++
      if (publication.champion_player_id) row.winnerIds.add(publication.champion_player_id)
    }
    if (event.season_week > row.latestWeek ||
      (event.season_week === row.latestWeek && event.event_id < row.latestEventId)) {
      row.latestEventId = event.event_id
      row.latestEventName = event.event_name || event.event_id
      row.latestWeek = event.season_week
    }
  }

  return [...rows.values()]
    .map(({ winnerIds, hostCodes, ...row }) => ({
      ...row,
      distinctWinners: winnerIds.size,
      hostCount: hostCodes.size,
    }))
    .sort((a, b) =>
      (seasonOrder.get(a.season) ?? Number.MAX_SAFE_INTEGER) -
      (seasonOrder.get(b.season) ?? Number.MAX_SAFE_INTEGER) ||
      a.category.localeCompare(b.category, 'cs')
    )
}

function TournamentStats({ catalog, runId, branchId, t }: {
  catalog: SavedTournamentCatalog; runId: string; branchId: string; t: T
}): JSX.Element {
  const [season, setSeason] = useState('all')
  const [category, setCategory] = useState('all')
  const [host, setHost] = useState('all')
  const [page, setPage] = useState(1)
  const seasons = useMemo(() => catalogSeasonsNewestFirst(catalog), [catalog])
  const categories = useMemo(() =>
    [...new Set(catalog.entries.map(({ event }) => event.category))].sort(), [catalog]
  )
  const hosts = useMemo(() =>
    [...new Set(catalog.entries.map(({ event }) => event.host_country))].sort(), [catalog]
  )
  const rows = useMemo(() => savedTournamentStatsRows(catalog, season, category, host),
    [catalog, season, category, host])
  const pages = Math.ceil(rows.length / PAGE_SIZE)
  const currentPage = Math.min(page, pages || 1)
  const offset = (currentPage - 1) * PAGE_SIZE
  const visible = rows.slice(offset, offset + PAGE_SIZE)

  function clear(): void {
    setSeason('all'); setCategory('all'); setHost('all'); setPage(1)
  }

  return <article className="viewer-active-run-card">
    <dl className="metadata-list viewer-metadata-list">
      <div><dt>{t('run')}</dt><dd>{runId}</dd></div>
      <div><dt>{t('branch')}</dt><dd>{branchId}</dd></div>
      <div><dt>{t('allEvents')}</dt><dd>{catalog.eventCount}</dd></div>
      <div><dt>{t('allPublished')}</dt><dd>{catalog.publishedCount}</dd></div>
    </dl>
    {catalog.eventCount === 0 ? <p className="empty-state">{t('noEvents')}</p> : <>
      <div className="viewer-filters">
        <label htmlFor="tournament-stats-season">{t('season')}</label>
        <select id="tournament-stats-season" value={season}
          onChange={e => { setSeason(e.target.value); setPage(1) }}>
          <option value="all">{t('allSeasons')}</option>
          {seasons.map(value => <option key={value} value={value}>{value}</option>)}
        </select>
        <label htmlFor="tournament-stats-category">{t('category')}</label>
        <select id="tournament-stats-category" value={category}
          onChange={e => { setCategory(e.target.value); setPage(1) }}>
          <option value="all">{t('allCategories')}</option>
          {categories.map(value => <option key={value} value={value}>{value}</option>)}
        </select>
        <label htmlFor="tournament-stats-host">{t('host')}</label>
        <select id="tournament-stats-host" value={host}
          onChange={e => { setHost(e.target.value); setPage(1) }}>
          <option value="all">{t('allHosts')}</option>
          {hosts.map(value => <option key={value} value={value}>{value}</option>)}
        </select>
        <button type="button" onClick={clear}>{t('clear')}</button>
      </div>
      {rows.length === 0 ? <p className="empty-state">{t('noMatch')}</p> :
        <div className="table-wrap">
          <table aria-label={t('table')}>
            <thead><tr>
              <th scope="col">{t('season')}</th>
              <th scope="col">{t('category')}</th>
              <th scope="col">{t('total')}</th>
              <th scope="col">{t('completed')}</th>
              <th scope="col">{t('published')}</th>
              <th scope="col">{t('winners')}</th>
              <th scope="col">{t('hosts')}</th>
              <th scope="col">{t('latest')}</th>
            </tr></thead>
            <tbody>{visible.map(row => <tr key={JSON.stringify([row.season, row.category])}>
              <td>{row.season}</td>
              <td>{row.category}</td>
              <td>{row.eventCount}</td>
              <td>{row.completedCount}</td>
              <td>{row.publishedCount}</td>
              <td>{row.distinctWinners}</td>
              <td>{row.hostCount}</td>
              <td>W{row.latestWeek} · {' '}
                <Link to={viewerPlannedEventPath(runId, row.latestEventId)}>{row.latestEventName}</Link>
              </td>
            </tr>)}</tbody>
          </table>
        </div>}
      <p role="status">{t('shown')} {rows.length ? offset + 1 : 0}–
        {rows.length ? offset + visible.length : 0} {t('of')} {rows.length}</p>
      {pages > 1 ? <nav aria-label={t('page')}>
        <button type="button" disabled={currentPage === 1}
          onClick={() => setPage(n => Math.max(1, n - 1))}>{t('previous')}</button>
        <span>{t('page')} {currentPage} / {pages}</span>
        <button type="button" disabled={currentPage === pages}
          onClick={() => setPage(n => Math.min(pages, n + 1))}>{t('next')}</button>
      </nav> : null}
    </>}
  </article>
}

export function ViewerPublishedTournamentStatsPage(): JSX.Element {
  const runId = useActiveViewerProductRunId()?.trim() ?? ''
  const { language } = useLanguage()
  const t: T = key => copy[key][language === 'cs' ? 0 : 1]
  const context = useViewerOfficialRunContext(runId)
  const branchId = tournamentViewerBranch(context.data, runId)
  const validContext = Boolean(runId && branchId && !context.isPending && !context.isFetching && !context.isError)
  const query = useQuery({
    // One shared key across the two compatible Saved statistics destinations:
    // React Query can reuse the same verified public bytes without new GETs.
    queryKey: ['viewer-saved-tournament-stats', runId, branchId],
    queryFn: async () => {
      const [calendar, history] = await Promise.all([
        getViewerRunCalendar(runId), getViewerTournamentHistory(runId),
      ])
      return { calendar, history }
    },
    enabled: validContext, retry: false, refetchOnWindowFocus: false,
  })

  return <section className="panel viewer-shell-page">
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
        const catalog = verifiedTournamentCatalog(
          query.data.calendar, query.data.history, runId, branchId ?? ''
        )
        return catalog ? <TournamentStats key={JSON.stringify([runId, branchId])}
          catalog={catalog} runId={runId} branchId={branchId ?? ''} t={t} /> :
          <div role="alert">
            <p>{t('mismatch')}</p>
            <button type="button" onClick={() => void query.refetch()}>{t('retry')}</button>
          </div>
      })()}
  </section>
}
