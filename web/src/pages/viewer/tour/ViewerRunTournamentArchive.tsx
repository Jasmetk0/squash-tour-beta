import { useEffect, useMemo, useRef } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link, useSearchParams } from 'react-router-dom'
import { getViewerTournamentHistory } from '../../../api/client'
import type { ViewerTournamentHistory, ViewerTournamentHistoryItem } from '../../../api/types'
import { CurrentContextStrip, MetadataList, RunScopedHeader, SectionCard } from '../../../components/RunScopedUi'
import { useLanguage } from '../../../i18n/LanguageContext'
import { isApiNotFound } from '../../../utils/apiErrors'
import { useViewerProductRunRouteContext } from '../../../viewer/ViewerProductRunRouteContext'
import { viewerWeekDetailPath } from '../../../viewer/viewerRoutes'

const copy = {
  title: ['Turnaje', 'Tournaments'],
  subtitle: ['Kanonický vícesezonní kalendář a uložené výsledky vybrané Viewer Branch.', 'Canonical multi-season tournament schedule and saved results for the selected Viewer Branch.'],
  heading: ['Kanonická historie turnajů', 'Canonical Tournament History'],
  run: ['Aktivní Run', 'Active run'], branch: ['Viewer Branch', 'Viewer Branch'],
  count: ['Počet turnajů', 'Tournament count'], publishedCount: ['Publikované výsledky', 'Published results'],
  loading: ['Načítám uloženou historii turnajů…', 'Loading canonical tournament history…'],
  context: ['Kontext Viewer Branch není ověřený.', 'Viewer Branch context is not verified.'],
  mismatch: ['Uložená historie turnajů je neplatná nebo patří jinému zdroji.', 'Saved tournament history is invalid or belongs to another source.'],
  error: ['Historii turnajů nelze načíst.', 'Failed to load canonical tournament history.'],
  missing: ['V této Viewer Branch není dostupný uložený Calendar Package.', 'No saved Calendar Package is available for this Viewer Branch yet.'],
  empty: ['Uložený kalendář neobsahuje žádné turnaje.', 'No tournaments are present in the saved Calendar Packages.'],
  retry: ['Načíst znovu (GET)', 'Retry read (GET)'],
  seasonFilter: ['Filtrovat sezonu', 'Filter season'], allSeasons: ['Všechny sezony', 'All seasons'],
  search: ['Hledat turnaj, ID nebo místo', 'Search event, ID or location'],
  publicationFilter: ['Stav publikace výsledku', 'Result publication status'], all: ['Všechny turnaje', 'All tournaments'],
  published: ['Publikováno', 'Published'], unpublished: ['Nepublikováno', 'Not published'],
  unknown: ['Neplatná hodnota', 'Invalid value'],
  invalid: ['Odkaz obsahuje neplatné filtry nebo stránku. Uprav nebo vymaž výběr.', 'The URL contains invalid filters or page. Correct or clear the selection.'],
  clear: ['Vymazat filtry', 'Clear filters'], noMatch: ['Žádný turnaj neodpovídá filtrům.', 'No tournaments match the filters.'],
  list: ['Kanonický seznam historie turnajů', 'Canonical tournament history list'],
  id: ['ID turnaje', 'Event ID'], season: ['Sezona', 'Season'], week: ['Týden', 'Week'], template: ['Šablona', 'Template'],
  category: ['Kategorie', 'Category'], tour: ['Tour', 'Tour'], host: ['Pořadatel', 'Host'],
  draws: ['Hlavní / kvalifikační pavouk', 'Main / Qualification'], ranking: ['Stav rankingu', 'Ranking status'],
  result: ['Publikace výsledku', 'Result publication'], champion: ['Vítěz', 'Champion'], finalist: ['Finalista', 'Finalist'],
  detail: ['Otevřít detail turnaje', 'Open tournament detail'],
  page: ['Stránka', 'Page'], previous: ['Předchozí', 'Previous'], next: ['Další', 'Next'],
  showing: ['Zobrazeno', 'Showing'], of: ['z', 'of'],
} as const
type Copy = Record<keyof typeof copy, string>
const PAGE_SIZE = 25
const keys = { season: 'vtSeason', search: 'vtQ', result: 'vtResult', page: 'vtPage' } as const
const ownedKeys = Object.values(keys)
const rootKeys = ['schema_version', 'product_run_id', 'viewer_branch_id', 'tournament_count', 'published_result_count', 'tournaments']
const rowKeys = ['event_id', 'season', 'season_week', 'event_name', 'template_id', 'category', 'tour_level', 'host_country', 'host_city', 'region', 'main_draw_size', 'qualification_draw_size', 'seeds_count', 'qualifier_spots', 'wild_cards', 'byes', 'ranking_status', 'result_published', 'champion_player_id', 'finalist_player_id']

function exactKeys(value: unknown, expected: readonly string[]): boolean {
  return Boolean(value && typeof value === 'object' && !Array.isArray(value) &&
    Object.keys(value).length === expected.length &&
    expected.every(key => Object.prototype.hasOwnProperty.call(value, key)))
}
const id = (value: unknown): value is string => typeof value === 'string' && value.trim().length > 0
const natural = (value: unknown): value is number => typeof value === 'number' && Number.isSafeInteger(value) && value >= 0

// Canonical legacy public DTO, not native W52/W80 or an independent result authority.
export function verifiedRunTournamentHistory(value: unknown, runId: string, branchId: string): ViewerTournamentHistory | null {
  if (!id(runId) || !id(branchId) || !exactKeys(value, rootKeys)) return null
  const data = value as ViewerTournamentHistory
  if (data.schema_version !== 'viewer_tournament_history.v1' || data.product_run_id !== runId ||
      data.viewer_branch_id !== branchId || !natural(data.tournament_count) || !natural(data.published_result_count) ||
      !Array.isArray(data.tournaments) || data.tournaments.length !== data.tournament_count) return null
  const seen = new Set<string>()
  let published = 0
  for (const item of data.tournaments) {
    if (!item || !exactKeys(item, rowKeys) || !id(item.event_id) || seen.has(item.event_id) ||
        !id(item.season) || !natural(item.season_week) || item.season_week < 1 || item.season_week > 61 ||
        typeof item.event_name !== 'string' || !id(item.template_id) || typeof item.category !== 'string' ||
        (item.tour_level !== null && typeof item.tour_level !== 'string') ||
        !id(item.host_country) || item.host_country.length !== 3 ||
        (item.host_city !== null && typeof item.host_city !== 'string') || !id(item.region) ||
        ![item.main_draw_size, item.qualification_draw_size, item.seeds_count, item.qualifier_spots, item.wild_cards, item.byes].every(natural) ||
        typeof item.ranking_status !== 'string' || typeof item.result_published !== 'boolean' ||
        (item.result_published
          ? !id(item.champion_player_id) || !id(item.finalist_player_id) || item.champion_player_id === item.finalist_player_id
          : item.champion_player_id !== null || item.finalist_player_id !== null)) return null
    seen.add(item.event_id)
    if (item.result_published) published++
  }
  return published === data.published_result_count ? data : null
}

function compareEvents(a: ViewerTournamentHistoryItem, b: ViewerTournamentHistoryItem): number {
  return b.season.localeCompare(a.season, undefined, { numeric: true }) ||
    a.season_week - b.season_week || a.event_id.localeCompare(b.event_id)
}

export function ViewerRunTournamentArchive({ detailPath }: {
  detailPath: (runId: string, eventId: string) => string
}): JSX.Element {
  const { productRunId: runId, officialBranchId: branchId, officialContext, isLoading, isStale, refetch } = useViewerProductRunRouteContext()
  const { language } = useLanguage()
  const t = Object.fromEntries(Object.entries(copy).map(([key, pair]) => [key, pair[language === 'cs' ? 0 : 1]])) as Copy
  const [params, setParams] = useSearchParams()
  const validContext = Boolean(id(runId) && id(branchId) && officialContext?.product_run_id === runId &&
    officialContext?.official_branch_id === branchId && !isLoading && !isStale)
  const source = validContext ? JSON.stringify([runId, branchId]) : null
  const previous = useRef<string | null>(null)
  const changed = Boolean(source && previous.current && source !== previous.current)
  const active = changed ? new URLSearchParams() : params
  useEffect(() => {
    if (!source) return
    if (changed) {
      const next = new URLSearchParams(params)
      ownedKeys.forEach(key => next.delete(key))
      if (next.toString() !== params.toString()) setParams(next, { replace: true })
    }
    previous.current = source
  }, [source, changed, params, setParams])
  function setFilter(key: string, value: string, fallback: string, replace = false): void {
    setParams(old => {
      const next = new URLSearchParams(old)
      if (changed) ownedKeys.forEach(k => next.delete(k))
      next.delete(keys.page)
      if (value === fallback) next.delete(key)
      else next.set(key, value)
      return next
    }, { replace })
  }
  function clear(): void {
    setParams(old => {
      const next = new URLSearchParams(old)
      ownedKeys.forEach(key => next.delete(key))
      return next
    })
  }
  function go(page: number): void {
    setParams(old => {
      const next = new URLSearchParams(old)
      if (page === 1) next.delete(keys.page)
      else next.set(keys.page, String(page))
      return next
    })
  }
  const query = useQuery({
    queryKey: ['viewer-run-tournament-archive', runId, branchId],
    queryFn: () => getViewerTournamentHistory(runId),
    enabled: validContext, retry: false,
  })
  const history = useMemo(() => verifiedRunTournamentHistory(query.data, runId, branchId), [query.data, runId, branchId])
  const sorted = useMemo(() => history ? [...history.tournaments].sort(compareEvents) : [], [history])
  const seasons = useMemo(() => [...new Set(sorted.map(item => item.season))], [sorted])
  const season = active.get(keys.season) ?? 'all'
  const search = active.get(keys.search) ?? ''
  const result = active.get(keys.result) ?? 'all'
  const rawPage = active.get(keys.page) ?? '1'
  const page = /^[1-9][0-9]*$/.test(rawPage) ? Number(rawPage) : NaN
  const invalidSeason = season !== 'all' && !seasons.includes(season)
  const invalidResult = !['all', 'published', 'unpublished'].includes(result)
  const duplicate = ownedKeys.some(key => active.getAll(key).length > 1)
  const filtered = useMemo(() => {
    const needle = search.trim().toLocaleLowerCase()
    return sorted.filter(item => (season === 'all' || item.season === season) &&
      (result === 'all' || item.result_published === (result === 'published')) &&
      (!needle || [item.event_name, item.event_id, item.host_country, item.host_city ?? '', item.category, item.template_id]
        .some(value => value.toLocaleLowerCase().includes(needle))))
  }, [sorted, season, search, result])
  const totalPages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE))
  const invalid = invalidSeason || invalidResult || duplicate || !Number.isSafeInteger(page) || page > totalPages
  const offset = invalid ? 0 : (page - 1) * PAGE_SIZE
  const rows = invalid ? [] : filtered.slice(offset, offset + PAGE_SIZE)
  const ready = validContext && !query.isFetching && !query.isPending && !query.isError && Boolean(history)
  return (
    <section className="panel">
      <RunScopedHeader title={t.title} runId={runId} subtitle={t.subtitle} />
      <CurrentContextStrip items={[
        { label: t.run, value: runId || '—' },
        { label: t.branch, value: validContext ? branchId : '—' },
        { label: t.count, value: ready ? history!.tournament_count : '—' },
        { label: t.publishedCount, value: ready ? history!.published_result_count : '—' },
      ]} />
      <SectionCard title={t.heading}>
        {isLoading ? <p role="status">{t.loading}</p> : !validContext ?
          <div role="alert"><p>{t.context}</p><button type="button" onClick={refetch}>{t.retry}</button></div> :
          query.isPending || query.isFetching ? <p role="status">{t.loading}</p> :
          query.isError ? <div role="alert"><p>{isApiNotFound(query.error) ? t.missing : t.error}</p><button type="button" onClick={() => void query.refetch()}>{t.retry}</button></div> :
          !history ? <div role="alert"><p>{t.mismatch}</p><button type="button" onClick={() => void query.refetch()}>{t.retry}</button></div> : <>
          <label htmlFor="run-tournament-season">{t.seasonFilter}</label>
          <select id="run-tournament-season" value={season} onChange={e => setFilter(keys.season, e.target.value, 'all')}>
            {invalidSeason ? <option value={season}>{t.unknown}: {season}</option> : null}
            <option value="all">{t.allSeasons}</option>
            {seasons.map(value => <option key={value} value={value}>{value}</option>)}
          </select>
          <label htmlFor="run-tournament-search">{t.search}</label>
          <input id="run-tournament-search" type="search" value={search} onChange={e => setFilter(keys.search, e.target.value, '', true)} />
          <label htmlFor="run-tournament-result">{t.publicationFilter}</label>
          <select id="run-tournament-result" value={result} onChange={e => setFilter(keys.result, e.target.value, 'all')}>
            {invalidResult ? <option value={result}>{t.unknown}: {result}</option> : null}
            <option value="all">{t.all}</option><option value="published">{t.published}</option><option value="unpublished">{t.unpublished}</option>
          </select>
          <button type="button" onClick={clear}>{t.clear}</button>
          {invalid ? <p role="alert">{t.invalid}</p> : !history.tournaments.length ? <p>{t.empty}</p> : !rows.length ? <p>{t.noMatch}</p> :
            <ul className="item-list" aria-label={t.list}>
              {rows.map(event => <li key={event.event_id} id={`event-${event.event_id}`}>
                <strong>{event.event_name || event.event_id}</strong>
                <MetadataList items={[
                  { label: t.id, value: event.event_id }, { label: t.season, value: event.season },
                  { label: t.week, value: <Link to={viewerWeekDetailPath(runId, event.season_week)}>{`W${event.season_week}`}</Link> },
                  { label: t.template, value: event.template_id }, { label: t.category, value: event.category || '—' },
                  { label: t.tour, value: event.tour_level?.replace(/_/g, ' ') ?? '—' },
                  { label: t.host, value: [event.host_city, event.host_country].filter(Boolean).join(', ') },
                  { label: t.draws, value: `${event.main_draw_size} / ${event.qualification_draw_size}` },
                  { label: t.ranking, value: event.ranking_status }, { label: t.result, value: event.result_published ? t.published : t.unpublished },
                  { label: t.champion, value: event.champion_player_id ?? '—' }, { label: t.finalist, value: event.finalist_player_id ?? '—' },
                ]} />
                <p><Link to={detailPath(runId, event.event_id)}>{t.detail}</Link></p>
              </li>)}
            </ul>}
          {!invalid ? <p role="status">{t.showing} {rows.length ? offset + 1 : 0}–{offset + rows.length} {t.of} {filtered.length}</p> : null}
          {!invalid && totalPages > 1 ? <nav aria-label={t.page}>
            <button type="button" disabled={page === 1} onClick={() => go(page - 1)}>{t.previous}</button>
            <span>{t.page} {page} / {totalPages}</span>
            <button type="button" disabled={page === totalPages} onClick={() => go(page + 1)}>{t.next}</button>
          </nav> : null}
        </>}
      </SectionCard>
    </section>
  )
}
