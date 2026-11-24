import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'

import { getViewerRunCalendar, getViewerTournamentHistory } from '../../../api/client'
import { ViewerEmptyState } from '../../../components/viewer/ViewerLandingComponents'
import { useLanguage, type Language } from '../../../i18n/LanguageContext'
import { useActiveViewerProductRunId } from '../../../viewer/useActiveViewerProductRunId'
import { useViewerOfficialRunContext } from '../../../viewer/useViewerOfficialRunContext'
import {
  viewerPlannedEventPath, viewerPlayerProfilePath, viewerRunsPath,
} from '../../../viewer/viewerRoutes'
import {
  catalogSeasonsNewestFirst, tournamentViewerBranch, verifiedTournamentCatalog,
  type SavedTournamentCatalog, type SavedTournamentEntry,
} from '../tour/viewerTournamentCatalog'

type ArchiveKind = 'categories' | 'champions'
const PAGE_SIZE = 25

const copy = {
  categoriesTitle: ['Kategorie turnajů', 'Tournament Categories'],
  championsTitle: ['Minulí vítězové', 'Past Champions'],
  description: [
    'Veřejný archiv pouze z ověřeného uloženého kalendáře a historie výsledků.',
    'Public archive derived only from the verified Saved calendar and published results.',
  ],
  sourceNote: [
    'Zobrazuje uložené publikace aktuální Viewer Branch; nejde o rekonstrukci libovolného zvoleného týdne.',
    'Shows publications from the current Saved Viewer Branch, not a reconstruction of any arbitrarily selected week.',
  ],
  chooseRun: ['Nejprve vyber Product Run.', 'Select a Product Run first.'],
  runs: ['Seznam Runů', 'Run browser'],
  resolving: ['Ověřuji uloženou Viewer Branch…', 'Resolving saved Viewer Branch…'],
  invalidContext: [
    'Viewer Branch neodpovídá vybranému Product Runu nebo není dostupná.',
    'Viewer Branch does not match the selected Product Run or is unavailable.',
  ],
  loading: ['Načítám uložený archiv…', 'Loading Saved archive…'],
  unavailable: ['Kalendář nebo historie výsledků nejsou dostupné.', 'Calendar or result history is unavailable.'],
  corrupt: [
    'Kalendář a historie výsledků nemají shodný ověřený zdroj. Archiv se nezobrazuje.',
    'Calendar and results do not have the same verified source. No archive is shown.',
  ],
  retry: ['Znovu načíst (GET)', 'Retry read (GET)'],
  run: ['Product Run', 'Product Run'],
  branch: ['Viewer Branch', 'Viewer Branch'],
  scheduled: ['Uložené turnaje', 'Saved tournaments'],
  published: ['Publikované výsledky', 'Published results'],
  season: ['Sezona', 'Season'],
  allSeasons: ['Všechny sezony', 'All seasons'],
  category: ['Kategorie', 'Category'],
  allCategories: ['Všechny kategorie', 'All categories'],
  search: ['Hledat turnaj nebo ID vítěze', 'Search event or champion ID'],
  clear: ['Vymazat filtry', 'Clear filters'],
  categoriesTable: ['Souhrn kategorií uložených turnajů', 'Saved tournament category summary'],
  championsTable: ['Historie publikovaných vítězů', 'Published past champions'],
  eventsTable: ['Turnaje vybrané kategorie', 'Selected category tournaments'],
  events: ['Turnaje', 'Tournaments'],
  event: ['Turnaj', 'Tournament'],
  week: ['Týden', 'Week'],
  champion: ['Vítěz (historické ID)', 'Champion (historical ID)'],
  finalist: ['Finalista (historické ID)', 'Finalist (historical ID)'],
  unpublished: ['Bez publikovaného výsledku', 'Result not published'],
  none: ['V uloženém archivu nejsou žádné turnaje.', 'No saved tournaments are available.'],
  noChampions: ['Zatím nebyl publikován žádný vítěz.', 'No champions have been published yet.'],
  noResults: ['Zvoleným filtrům neodpovídají žádné záznamy.', 'No records match the selected filters.'],
  shown: ['Zobrazeno', 'Showing'],
  of: ['z', 'of'],
  previous: ['Předchozí', 'Previous'],
  next: ['Další', 'Next'],
  page: ['Stránka', 'Page'],
  provenance: [
    'Jména hráčů se nedoplňují z jejich současných profilů; archiv používá historická ID publikovaných výsledků.',
    'Player names are not backfilled from present-day profiles; this archive uses published historical IDs.',
  ],
} as const

type MessageKey = keyof typeof copy
type T = (key: MessageKey) => string

type CategoryRow = { category: string; events: number; published: number }
function categoryLabel(raw: string): string {
  return raw.trim() || '—'
}

export function savedTourCategoryRows(
  catalog: SavedTournamentCatalog, season: string,
): CategoryRow[] {
  const counts = new Map<string, CategoryRow>()
  for (const { event, publication } of catalog.entries) {
    if (season !== 'all' && String(event.season) !== season) continue
    const category = categoryLabel(event.category)
    const existing = counts.get(category) ?? { category, events: 0, published: 0 }
    existing.events += 1
    if (publication.result_published) existing.published += 1
    counts.set(category, existing)
  }
  return [...counts.values()].sort((a, b) => a.category.localeCompare(b.category, 'cs'))
}

function latestFirst(a: SavedTournamentEntry, b: SavedTournamentEntry): number {
  // Match the existing catalog's real season/week ordering; never infer a date.
  const bySeason = catalogSeasonsNewestFirst({
    seasons: [String(a.event.season), String(b.event.season)],
    entries: [], eventCount: 0, publishedCount: 0,
  })
  if (bySeason[0] !== bySeason[1]) {
    return String(a.event.season) === bySeason[0] ? -1 : 1
  }
  return b.event.season_week - a.event.season_week ||
    a.event.event_id.localeCompare(b.event.event_id)
}

function ArchiveView({ catalog, kind, runId, branchId, t }: {
  catalog: SavedTournamentCatalog
  kind: ArchiveKind
  runId: string
  branchId: string
  t: T
}): JSX.Element {
  const [season, setSeason] = useState('all')
  const [category, setCategory] = useState('all')
  const [query, setQuery] = useState('')
  const [page, setPage] = useState(1)
  const seasons = catalogSeasonsNewestFirst(catalog)
  const categories = savedTourCategoryRows(catalog, 'all').map(row => row.category)
  const categoryRows = savedTourCategoryRows(catalog, season)
  const needle = query.trim().toLocaleLowerCase()
  const eligible = catalog.entries.filter(({ event, publication }) =>
    (season === 'all' || String(event.season) === season) &&
    (category === 'all' || categoryLabel(event.category) === category) &&
    (kind !== 'champions' || publication.result_published) &&
    (!needle || [
      event.event_name, event.event_id,
      event.host_country ?? '', event.host_city ?? '',
      ...(publication.result_published ? [publication.champion_player_id ?? ''] : []),
    ].some(value => value.toLocaleLowerCase().includes(needle)))
  ).sort(latestFirst)
  const pages = Math.ceil(eligible.length / PAGE_SIZE)
  const visiblePage = Math.min(page, pages || 1)
  const visible = eligible.slice((visiblePage - 1) * PAGE_SIZE, visiblePage * PAGE_SIZE)

  const setFilter = (apply: () => void) => { apply(); setPage(1) }
  const title = kind === 'categories' ? t('categoriesTitle') : t('championsTitle')
  return (
    <article className="viewer-active-run-card" aria-label={title}>
      <h3>{title}</h3>
      <dl className="metadata-list viewer-metadata-list">
        <div><dt>{t('run')}</dt><dd>{runId}</dd></div>
        <div><dt>{t('branch')}</dt><dd>{branchId}</dd></div>
        <div><dt>{t('scheduled')}</dt><dd>{catalog.eventCount}</dd></div>
        <div><dt>{t('published')}</dt><dd>{catalog.publishedCount}</dd></div>
      </dl>
      {catalog.eventCount === 0 ? <ViewerEmptyState>{t('none')}</ViewerEmptyState> : (
        <>
          <div className="viewer-filters">
            <label htmlFor="archive-season">{t('season')}</label>
            <select id="archive-season" value={season}
              onChange={e => setFilter(() => setSeason(e.target.value))}>
              <option value="all">{t('allSeasons')}</option>
              {seasons.map(value => <option key={value} value={value}>{value}</option>)}
            </select>
            <label htmlFor="archive-category">{t('category')}</label>
            <select id="archive-category" value={category}
              onChange={e => setFilter(() => setCategory(e.target.value))}>
              <option value="all">{t('allCategories')}</option>
              {categories.map(value => <option key={value} value={value}>{value}</option>)}
            </select>
            <label htmlFor="archive-search">{t('search')}</label>
            <input id="archive-search" type="search" value={query}
              onChange={e => setFilter(() => setQuery(e.target.value))} />
            <button type="button" onClick={() => setFilter(() => {
              setSeason('all'); setCategory('all'); setQuery('')
            })}>{t('clear')}</button>
          </div>
          {kind === 'categories' ? (
            <div className="table-wrap">
              <table aria-label={t('categoriesTable')}>
                <thead><tr>
                  <th scope="col">{t('category')}</th>
                  <th scope="col">{t('events')}</th>
                  <th scope="col">{t('published')}</th>
                </tr></thead>
                <tbody>{categoryRows.map(row => (
                  <tr key={row.category}>
                    <td>{row.category}</td>
                    <td>{row.events}</td>
                    <td>{row.published}</td>
                  </tr>
                ))}</tbody>
              </table>
            </div>
          ) : <p className="subtitle">{t('provenance')}</p>}
          {eligible.length === 0 ? (
            <p className="empty-state">{kind === 'champions' && catalog.publishedCount === 0
              ? t('noChampions') : t('noResults')}</p>
          ) : (
            <div className="table-wrap">
              <table aria-label={kind === 'categories' ? t('eventsTable') : t('championsTable')}>
                <thead><tr>
                  <th scope="col">{t('season')}</th>
                  <th scope="col">{t('week')}</th>
                  <th scope="col">{t('event')}</th>
                  <th scope="col">{t('category')}</th>
                  <th scope="col">{kind === 'categories' ? t('published') : t('champion')}</th>
                  {kind === 'champions' ? <th scope="col">{t('finalist')}</th> : null}
                </tr></thead>
                <tbody>{visible.map(({ event, publication }) => (
                  <tr key={event.event_id}>
                    <td>{String(event.season)}</td>
                    <td>W{event.season_week}</td>
                    <td><Link to={viewerPlannedEventPath(runId, event.event_id)}>
                      {event.event_name || event.event_id}
                    </Link></td>
                    <td>{categoryLabel(event.category)}</td>
                    <td>{kind === 'categories' ? (
                      publication.result_published ? t('published') : t('unpublished')
                    ) : (
                      <Link to={viewerPlayerProfilePath(runId, publication.champion_player_id!)}>
                        {publication.champion_player_id}
                      </Link>
                    )}</td>
                    {kind === 'champions' ? <td>
                      <Link to={viewerPlayerProfilePath(runId, publication.finalist_player_id!)}>
                        {publication.finalist_player_id}
                      </Link>
                    </td> : null}
                  </tr>
                ))}</tbody>
              </table>
            </div>
          )}
          <p role="status">{t('shown')} {eligible.length ? (visiblePage - 1) * PAGE_SIZE + 1 : 0}–
            {eligible.length ? (visiblePage - 1) * PAGE_SIZE + visible.length : 0}
            {' '}{t('of')} {eligible.length}</p>
          {pages > 1 ? <nav aria-label={t('page')}>
            <button type="button" disabled={visiblePage === 1}
              onClick={() => setPage(n => Math.max(1, n - 1))}>{t('previous')}</button>
            <span>{t('page')} {visiblePage} / {pages}</span>
            <button type="button" disabled={visiblePage === pages}
              onClick={() => setPage(n => Math.min(pages, n + 1))}>{t('next')}</button>
          </nav> : null}
        </>
      )}
    </article>
  )
}

export function ViewerTourArchivePage({ kind }: { kind: ArchiveKind }): JSX.Element {
  const runId = useActiveViewerProductRunId()?.trim() ?? ''
  const context = useViewerOfficialRunContext(runId)
  const branchId = tournamentViewerBranch(context.data, runId)
  const validSource = Boolean(runId && branchId && !context.isPending && !context.isFetching && !context.isError)
  const { language } = useLanguage()
  const t: T = key => copy[key][language === 'cs' ? 0 : 1]
  const title = kind === 'categories' ? t('categoriesTitle') : t('championsTitle')
  const archive = useQuery({
    queryKey: ['viewer-tour-public-archive', runId, branchId],
    queryFn: async () => {
      const [calendar, history] = await Promise.all([
        getViewerRunCalendar(runId), getViewerTournamentHistory(runId),
      ])
      return { calendar, history }
    },
    enabled: validSource,
    retry: false,
    refetchOnWindowFocus: false,
  })

  return (
    <section className="panel viewer-shell-page">
      <div className="page-intro">
        <h2>{title}</h2>
        <p className="subtitle">{t('description')}</p>
      </div>
      <p className="subtitle">{t('sourceNote')}</p>
      {!runId ? (
        <ViewerEmptyState>{t('chooseRun')} <Link to={viewerRunsPath()}>{t('runs')}</Link></ViewerEmptyState>
      ) : context.isPending || context.isFetching ? (
        <p className="status" role="status">{t('resolving')}</p>
      ) : !validSource ? (
        <div role="alert">
          <p>{t('invalidContext')}</p>
          <button type="button" onClick={() => void context.refetch()}>{t('retry')}</button>
        </div>
      ) : archive.isPending || archive.isFetching ? (
        <p className="status" role="status">{t('loading')}</p>
      ) : archive.isError ? (
        <div role="alert">
          <p>{t('unavailable')}</p>
          <button type="button" onClick={() => void archive.refetch()}>{t('retry')}</button>
        </div>
      ) : (() => {
        const catalog = verifiedTournamentCatalog(
          archive.data.calendar, archive.data.history, runId, branchId ?? '',
        )
        return catalog ? (
          <ArchiveView key={JSON.stringify([runId, branchId, kind])}
            catalog={catalog} kind={kind} runId={runId} branchId={branchId ?? ''} t={t} />
        ) : (
          <div role="alert">
            <p>{t('corrupt')}</p>
            <button type="button" onClick={() => void archive.refetch()}>{t('retry')}</button>
          </div>
        )
      })()}
    </section>
  )
}
