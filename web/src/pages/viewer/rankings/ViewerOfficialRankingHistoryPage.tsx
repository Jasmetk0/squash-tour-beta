import { useEffect, useMemo, useRef, useState, type FormEvent } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link, useSearchParams } from 'react-router-dom'

import { listViewerOfficialRankingHistory } from '../../../api/client'
import type { ViewerOfficialRankingHistoryItem } from '../../../api/types'
import { EmptyState, RunScopedHeader, SectionCard } from '../../../components/RunScopedUi'
import { useLanguage, type Language } from '../../../i18n/LanguageContext'
import { formatApiError } from '../../../utils/apiErrors'
import { useViewerProductRunRouteContext } from '../../../viewer/ViewerProductRunRouteContext'
import { viewerRankingSnapshotPath } from '../../../viewer/viewerRoutes'
import {
  filterRankingHistory, legacyRankingSeasonLabel, rankingHistoryPageCount,
  rankingHistoryPageJump, RANKING_HISTORY_PAGE_SIZE, validRankingHistory,
  type RankingHistoryOrder
} from './rankingHistoryBrowsing'

// Keep both translations for each key together. This avoids duplicate
// locale-specific object structures while preserving literal copy.
const translations = {
  title: ["MSA žebříčky", "MSA Rankings"],
  subtitle: ["Historické publikace Official Rankingu z vybrané Viewer Branch.", "Historically faithful Official Ranking publications from the selected Viewer Branch."],
  section: ["Historie publikovaných Official Rankingů", "Official Ranking publication history"],
  loading: ["Načítání historie Official Rankingů…", "Loading Official Ranking history…"],
  context: ["Čeká se na platný kontext Product Runu a Viewer Branch.", "Waiting for a valid Product Run and Viewer Branch context."],
  failed: ["Historii Official Rankingů se nepodařilo načíst:", "Failed to load Official Ranking history:"],
  invalid: ["Vrácená historie neodpovídá zdroji nebo obsahuje neplatné či duplicitní publikace. Záznamy se nezobrazují.", "The returned history does not match this source or contains invalid or duplicate publications. No records are shown."],
  retry: ["Zkusit znovu", "Retry read"],
  empty: ["Pro tuto Viewer Branch zatím nejsou publikovány žádné Official Rankingy.", "No Official Rankings have been published for this Viewer Branch yet."],
  none: ["Žádné publikace neodpovídají zvoleným filtrům.", "No publications match the selected filters."],
  season: ["Sezona", "Season"],
  allSeasons: ["Všechny sezony", "All seasons"],
  week: ["Týden", "Week"],
  players: ["Hráči", "Players"],
  bestN: ["Historické Best N", "Historical Best N"],
  allBestN: ["Všechna Best N", "All Best N"],
  publication: ["Publikace", "Publication"],
  ordinal: ["Ordinal", "Ordinal"],
  policy: ["Policy ID", "Policy ID"],
  search: ["Hledat policy_id nebo ordinal publikace", "Search policy_id or publication ordinal"],
  searchHint: ["Hledání prochází jen metadata publikací, nikoli hráče uvnitř snapshotů.", "Search covers publication metadata only, not players inside snapshots."],
  sort: ["Řazení", "Order"],
  newest: ["Od nejnovějších", "Newest first"],
  oldest: ["Od nejstarších", "Oldest first"],
  clear: ["Vymazat filtry", "Clear filters"],
  table: ["Historie publikací Official Rankingu", "Official Ranking publication history"],
  open: ["Otevřít ranking týdne", "Open Week"],
  openSuffix: ["", " ranking"],
  published: ["Celkem publikací:", "Total publications:"],
  showing: ["Zobrazeno", "Showing"],
  of: ["z", "of"],
  first: ["První stránka", "First page"],
  previous: ["Předchozí stránka", "Previous page"],
  next: ["Další stránka", "Next page"],
  last: ["Poslední stránka", "Last page"],
  page: ["Stránka", "Page"],
  jumpLabel: ["Přejít na stránku", "Jump to page"],
  jump: ["Přejít", "Go"],
  invalidJump: ["Zadej celé číslo existující stránky.", "Enter an existing page number as a positive integer."],
  unknownFilter: ["Neznámá hodnota filtru", "Unknown filter value"],
  invalidFilters: ["Odkaz obsahuje neplatný nebo nedostupný filtr. Oprav ho nebo vymaž filtry.", "The URL contains an invalid or unavailable filter. Correct it or clear the filters."]
} as const
type Text = Record<keyof typeof translations, string>
function copyForLanguage(language: Language): Text {
  const column = language === 'cs' ? 0 : 1
  return Object.fromEntries(
    Object.entries(translations).map(([key, pair]) => [key, pair[column]])
  ) as Text
}

// Ranking history owns only these keys; unrelated query parameters are preserved.
const RANKING_FILTER_KEYS = ['rhSeason', 'rhBestN', 'rhSearch', 'rhOrder'] as const
type RankingFilterKey = typeof RANKING_FILTER_KEYS[number]

function rankingFilterInteger(raw: string, allowZero: boolean): number | null {
  if (!/^(0|[1-9][0-9]*)$/.test(raw)) return null
  const value = Number(raw)
  return Number.isSafeInteger(value) && (allowZero || value > 0) ? value : null
}

function RankingHistoryForSource({ productRunId, viewerBranchId, text: t, ignoreUrlFilters }: {
  productRunId: string
  viewerBranchId: string
  text: Text
  ignoreUrlFilters: boolean
}): JSX.Element {
  // Keyed by both identities; local pagination never crosses a Run/Branch.
  const [searchParams, setSearchParams] = useSearchParams()
  const activeParams = ignoreUrlFilters ? new URLSearchParams() : searchParams
  const season = activeParams.get('rhSeason') ?? ''
  const bestN = activeParams.get('rhBestN') ?? ''
  const search = activeParams.get('rhSearch') ?? ''
  const rawOrder = activeParams.get('rhOrder') ?? ''
  const order: RankingHistoryOrder = rawOrder === 'oldest' ? 'oldest' : 'newest'
  const orderInvalid = rawOrder !== '' && rawOrder !== 'newest' && rawOrder !== 'oldest'
  const [page, setPage] = useState(1)
  const [jump, setJump] = useState('')
  const [jumpError, setJumpError] = useState(false)

  // Browser Back/Forward and direct URL changes reset only local pagination.
  useEffect(() => {
    setPage(1)
    setJump('')
    setJumpError(false)
  }, [season, bestN, search, rawOrder])

  function changeUrlFilter(key: RankingFilterKey, value: string, replace = false): void {
    setSearchParams((previous) => {
      const next = new URLSearchParams(previous)
      if (ignoreUrlFilters) RANKING_FILTER_KEYS.forEach((name) => next.delete(name))
      if (value !== '' && !(key === 'rhOrder' && value === 'newest')) next.set(key, value)
      else next.delete(key)
      return next
    }, { replace })
    setPage(1)
    setJump('')
    setJumpError(false)
  }

  function clearUrlFilters(): void {
    setSearchParams((previous) => {
      const next = new URLSearchParams(previous)
      RANKING_FILTER_KEYS.forEach((name) => next.delete(name))
      return next
    })
    setPage(1)
    setJump('')
    setJumpError(false)
  }

  const query = useQuery({
    queryKey: ['viewer-official-ranking-history', productRunId, viewerBranchId],
    queryFn: () => listViewerOfficialRankingHistory(productRunId),
    // Mounted only under a valid route context. Never retry mutations: this
    // endpoint and the explicit retry below are GET-only.
    retry: false,
    refetchOnWindowFocus: false
  })
  const valid = query.data && validRankingHistory(query.data, productRunId, viewerBranchId)
  const history = valid ? query.data : null
  const publications = history?.publications ?? []
  const seasons = useMemo(() => [...new Set(publications.map((item) => item.season_index))].sort((a, b) => a - b), [publications])
  const bestValues = useMemo(() => [...new Set(publications.map((item) => item.best_n))].sort((a, b) => a - b), [publications])
  const seasonInvalid = season !== '' && (rankingFilterInteger(season, true) === null || !seasons.includes(Number(season)))
  const bestInvalid = bestN !== '' && (rankingFilterInteger(bestN, false) === null || !bestValues.includes(Number(bestN)))
  const filtersInvalid = seasonInvalid || bestInvalid || orderInvalid
  const filtered = useMemo(
    () => filtersInvalid ? [] : filterRankingHistory(publications, { season, bestN, search, order }),
    [publications, season, bestN, search, order, filtersInvalid]
  )
  const pages = rankingHistoryPageCount(filtered.length)
  const currentPage = pages > 0 ? Math.min(page, pages) : 0
  const from = currentPage ? (currentPage - 1) * RANKING_HISTORY_PAGE_SIZE : 0
  const shown: ViewerOfficialRankingHistoryItem[] = filtered.slice(from, from + RANKING_HISTORY_PAGE_SIZE)

  function changePage(next: number): void {
    setPage(next)
    setJump('')
    setJumpError(false)
  }
  function submitJump(event: FormEvent<HTMLFormElement>): void {
    event.preventDefault()
    const target = rankingHistoryPageJump(jump, pages)
    if (target === null) {
      setJumpError(true)
    } else {
      changePage(target)
    }
  }

  if (query.isPending) return <p className="status" role="status">{t.loading}</p>
  if (query.isError || (query.data && !valid)) return (
    <div role="alert">
      <p className="error">{query.isError ? t.failed + ' ' + formatApiError(query.error) : t.invalid}</p>
      <button type="button" onClick={() => void query.refetch()}>{t.retry}</button>
    </div>
  )
  if (!history) return <p className="status" role="status">{t.loading}</p>
  if (history.publication_count === 0) return <><p>{t.published} 0</p><EmptyState message={t.empty} /><p role="status">{t.showing} 0–0 {t.of} 0</p></>

  return (
    <>
      <p>{t.published} {history.publication_count}</p>
      <div className="viewer-filters">
        <label htmlFor="ranking-history-season">{t.season}</label>
        <select id="ranking-history-season" value={season} onChange={(event) => changeUrlFilter('rhSeason', event.target.value)}>
          <option value="">{t.allSeasons}</option>
          {seasonInvalid ? <option value={season}>{t.unknownFilter}: {season}</option> : null}
          {seasons.map((index) => <option key={index} value={String(index)}>{legacyRankingSeasonLabel(index)}</option>)}
        </select>
        <label htmlFor="ranking-history-best">{t.bestN}</label>
        <select id="ranking-history-best" value={bestN} onChange={(event) => changeUrlFilter('rhBestN', event.target.value)}>
          <option value="">{t.allBestN}</option>
          {bestInvalid ? <option value={bestN}>{t.unknownFilter}: {bestN}</option> : null}
          {bestValues.map((value) => <option key={value} value={String(value)}>{value}</option>)}
        </select>
        <label htmlFor="ranking-history-search">{t.search}</label>
        <input id="ranking-history-search" type="search" value={search} onChange={(event) => changeUrlFilter('rhSearch', event.target.value, true)} />
        <p>{t.searchHint}</p>
        <label htmlFor="ranking-history-order">{t.sort}</label>
        <select id="ranking-history-order" value={rawOrder || 'newest'} onChange={(event) => changeUrlFilter('rhOrder', event.target.value)}>
          {orderInvalid ? <option value={rawOrder}>{t.unknownFilter}: {rawOrder}</option> : null}
          <option value="newest">{t.newest}</option>
          <option value="oldest">{t.oldest}</option>
        </select>
        <button type="button" onClick={clearUrlFilters}>{t.clear}</button>
      </div>
      {filtersInvalid ? <p role="alert">{t.invalidFilters}</p> : null}
      {filtered.length === 0 ? <EmptyState message={t.none} /> : (
        <table aria-label={t.table}>
          <thead><tr><th scope="col">{t.season}</th><th scope="col">{t.week}</th><th scope="col">{t.ordinal}</th><th scope="col">{t.policy}</th><th scope="col">{t.players}</th><th scope="col">Best N</th><th scope="col">{t.publication}</th></tr></thead>
          <tbody>
            {shown.map((item) => (
              <tr key={item.week_ordinal}>
                <td>{legacyRankingSeasonLabel(item.season_index)}</td>
                <td>{item.week}</td>
                <td>{item.week_ordinal}</td>
                <td>{item.policy_id}</td>
                <td>{item.row_count}</td>
                <td>{item.best_n}</td>
                <td><Link to={viewerRankingSnapshotPath(productRunId, item.week_ordinal)}>{t.open} {item.week}{t.openSuffix} (#{item.week_ordinal})</Link></td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      <p role="status">{t.showing} {filtered.length ? from + 1 : 0}–{filtered.length ? from + shown.length : 0} {t.of} {filtered.length}</p>
      {pages > 0 ? (
        <nav aria-label={t.page}>
          <button type="button" aria-label={t.first} disabled={currentPage === 1} onClick={() => changePage(1)}>{t.first}</button>
          <button type="button" aria-label={t.previous} disabled={currentPage === 1} onClick={() => changePage(currentPage - 1)}>{t.previous}</button>
          <span>{t.page} {currentPage} / {pages}</span>
          <button type="button" aria-label={t.next} disabled={currentPage === pages} onClick={() => changePage(currentPage + 1)}>{t.next}</button>
          <button type="button" aria-label={t.last} disabled={currentPage === pages} onClick={() => changePage(pages)}>{t.last}</button>
          <form onSubmit={submitJump}>
            <label htmlFor="ranking-history-jump">{t.jumpLabel}</label>
            <input id="ranking-history-jump" type="text" inputMode="numeric" value={jump} onChange={(event) => { setJump(event.target.value); setJumpError(false) }} aria-invalid={jumpError} aria-describedby={jumpError ? 'ranking-history-jump-error' : undefined} />
            <button type="submit">{t.jump}</button>
            {jumpError ? <span role="alert" id="ranking-history-jump-error">{t.invalidJump}</span> : null}
          </form>
        </nav>
      ) : null}
    </>
  )
}

export function ViewerOfficialRankingHistoryPage(): JSX.Element {
  const { language } = useLanguage()
  const t = copyForLanguage(language)
  const { productRunId, officialBranchId, officialContext, isLoading, isStale } = useViewerProductRunRouteContext()
  const [searchParams, setSearchParams] = useSearchParams()
  const validRoute = Boolean(
    productRunId?.trim() && officialBranchId?.trim() &&
    officialContext?.product_run_id === productRunId &&
    officialContext?.official_branch_id === officialBranchId &&
    !isLoading && !isStale
  )
  const sourceKey = validRoute ? JSON.stringify([productRunId, officialBranchId]) : null
  const previousSource = useRef<string | null>(null)
  const sourceChanged = Boolean(sourceKey && previousSource.current && sourceKey !== previousSource.current)

  // A filter link is valid on first mount, but must not carry state across an
  // in-app Run or Viewer Branch switch. Clearing is URL-only and never a GET/write.
  useEffect(() => {
    if (!sourceKey) return
    if (sourceChanged) {
      const next = new URLSearchParams(searchParams)
      RANKING_FILTER_KEYS.forEach((name) => next.delete(name))
      if (next.toString() !== searchParams.toString()) setSearchParams(next, { replace: true })
    }
    previousSource.current = sourceKey
  }, [sourceKey, sourceChanged, searchParams, setSearchParams])

  return (
    <section className="panel">
      <RunScopedHeader title={t.title} runId={productRunId} subtitle={t.subtitle} />
      <SectionCard title={t.section}>
        {validRoute ? (
          <RankingHistoryForSource
            key={JSON.stringify([productRunId, officialBranchId])}
            productRunId={productRunId}
            viewerBranchId={officialBranchId}
            text={t}
            ignoreUrlFilters={sourceChanged}
          />
        ) : <p className="status" role="status">{t.context}</p>}
      </SectionCard>
    </section>
  )
}
