import { useMemo, useState, type FormEvent } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'

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

const copy = {
  cs: {
    title: 'MSA žebříčky',
    subtitle: 'Historické publikace Official Rankingu z vybrané Viewer Branch.',
    section: 'Historie publikovaných Official Rankingů',
    loading: 'Načítání historie Official Rankingů…',
    context: 'Čeká se na platný kontext Product Runu a Viewer Branch.',
    failed: 'Historii Official Rankingů se nepodařilo načíst:',
    invalid: 'Vrácená historie neodpovídá zdroji nebo obsahuje neplatné či duplicitní publikace. Záznamy se nezobrazují.',
    retry: 'Zkusit znovu',
    empty: 'Pro tuto Viewer Branch zatím nejsou publikovány žádné Official Rankingy.',
    none: 'Žádné publikace neodpovídají zvoleným filtrům.',
    season: 'Sezona',
    allSeasons: 'Všechny sezony',
    week: 'Týden',
    players: 'Hráči',
    bestN: 'Historické Best N',
    allBestN: 'Všechna Best N',
    publication: 'Publikace',
    ordinal: 'Ordinal',
    policy: 'Policy ID',
    search: 'Hledat policy_id nebo ordinal publikace',
    searchHint: 'Hledání prochází jen metadata publikací, nikoli hráče uvnitř snapshotů.',
    sort: 'Řazení',
    newest: 'Od nejnovějších',
    oldest: 'Od nejstarších',
    clear: 'Vymazat filtry',
    table: 'Historie publikací Official Rankingu',
    open: 'Otevřít ranking týdne',
    published: 'Celkem publikací:',
    showing: 'Zobrazeno',
    of: 'z',
    first: 'První stránka',
    previous: 'Předchozí stránka',
    next: 'Další stránka',
    last: 'Poslední stránka',
    page: 'Stránka',
    jumpLabel: 'Přejít na stránku',
    jump: 'Přejít',
    invalidJump: 'Zadej celé číslo existující stránky.'
  },
  en: {
    title: 'MSA Rankings',
    subtitle: 'Historically faithful Official Ranking publications from the selected Viewer Branch.',
    section: 'Official Ranking publication history',
    loading: 'Loading Official Ranking history…',
    context: 'Waiting for a valid Product Run and Viewer Branch context.',
    failed: 'Failed to load Official Ranking history:',
    invalid: 'The returned history does not match this source or contains invalid or duplicate publications. No records are shown.',
    retry: 'Retry read',
    empty: 'No Official Rankings have been published for this Viewer Branch yet.',
    none: 'No publications match the selected filters.',
    season: 'Season',
    allSeasons: 'All seasons',
    week: 'Week',
    players: 'Players',
    bestN: 'Historical Best N',
    allBestN: 'All Best N',
    publication: 'Publication',
    ordinal: 'Ordinal',
    policy: 'Policy ID',
    search: 'Search policy_id or publication ordinal',
    searchHint: 'Search covers publication metadata only, not players inside snapshots.',
    sort: 'Order',
    newest: 'Newest first',
    oldest: 'Oldest first',
    clear: 'Clear filters',
    table: 'Official Ranking publication history',
    open: 'Open Week',
    published: 'Total publications:',
    showing: 'Showing',
    of: 'of',
    first: 'First page',
    previous: 'Previous page',
    next: 'Next page',
    last: 'Last page',
    page: 'Page',
    jumpLabel: 'Jump to page',
    jump: 'Go',
    invalidJump: 'Enter an existing page number as a positive integer.'
  }
} satisfies Record<Language, Record<string, string>>

type Text = typeof copy.en

function RankingHistoryForSource({ productRunId, viewerBranchId, text: t }: {
  productRunId: string
  viewerBranchId: string
  text: Text
}): JSX.Element {
  // This child is keyed by BOTH source identities. Its pagination/filter state
  // unmounts synchronously on source change, before any cached data can render.
  const [season, setSeason] = useState('')
  const [bestN, setBestN] = useState('')
  const [search, setSearch] = useState('')
  const [order, setOrder] = useState<RankingHistoryOrder>('newest')
  const [page, setPage] = useState(1)
  const [jump, setJump] = useState('')
  const [jumpError, setJumpError] = useState(false)

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
  const filtered = useMemo(
    () => filterRankingHistory(publications, { season, bestN, search, order }),
    [publications, season, bestN, search, order]
  )
  const pages = rankingHistoryPageCount(filtered.length)
  const currentPage = pages > 0 ? Math.min(page, pages) : 0
  const from = currentPage ? (currentPage - 1) * RANKING_HISTORY_PAGE_SIZE : 0
  const shown: ViewerOfficialRankingHistoryItem[] = filtered.slice(from, from + RANKING_HISTORY_PAGE_SIZE)

  function changedFilters(change: () => void): void {
    change()
    setPage(1)
    setJump('')
    setJumpError(false)
  }
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
  if (history.publication_count === 0) return <EmptyState message={t.empty} />

  return (
    <>
      <p>{t.published} {history.publication_count}</p>
      <div className="viewer-filters">
        <label htmlFor="ranking-history-season">{t.season}</label>
        <select id="ranking-history-season" value={season} onChange={(event) => changedFilters(() => setSeason(event.target.value))}>
          <option value="">{t.allSeasons}</option>
          {seasons.map((index) => <option key={index} value={String(index)}>{legacyRankingSeasonLabel(index)}</option>)}
        </select>
        <label htmlFor="ranking-history-best">{t.bestN}</label>
        <select id="ranking-history-best" value={bestN} onChange={(event) => changedFilters(() => setBestN(event.target.value))}>
          <option value="">{t.allBestN}</option>
          {bestValues.map((value) => <option key={value} value={String(value)}>{value}</option>)}
        </select>
        <label htmlFor="ranking-history-search">{t.search}</label>
        <input id="ranking-history-search" type="search" value={search} onChange={(event) => changedFilters(() => setSearch(event.target.value))} />
        <p>{t.searchHint}</p>
        <label htmlFor="ranking-history-order">{t.sort}</label>
        <select id="ranking-history-order" value={order} onChange={(event) => changedFilters(() => setOrder(event.target.value as RankingHistoryOrder))}>
          <option value="newest">{t.newest}</option>
          <option value="oldest">{t.oldest}</option>
        </select>
        <button type="button" onClick={() => changedFilters(() => { setSeason(''); setBestN(''); setSearch(''); setOrder('newest') })}>{t.clear}</button>
      </div>
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
                <td><Link to={viewerRankingSnapshotPath(productRunId, item.week_ordinal)}>{t.open} {item.week} {t.week.toLowerCase() === 'week' ? 'ranking' : '– ranking'} (#{item.week_ordinal})</Link></td>
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
  const t = copy[language]
  const { productRunId, officialBranchId, officialContext, isLoading, isStale } = useViewerProductRunRouteContext()
  const validRoute = Boolean(
    productRunId?.trim() && officialBranchId?.trim() &&
    officialContext?.product_run_id === productRunId &&
    officialContext?.official_branch_id === officialBranchId &&
    !isLoading && !isStale
  )

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
          />
        ) : <p className="status" role="status">{t.context}</p>}
      </SectionCard>
    </section>
  )
}
