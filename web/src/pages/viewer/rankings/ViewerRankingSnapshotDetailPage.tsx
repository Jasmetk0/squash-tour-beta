import { useState, type FormEvent } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link, useParams } from 'react-router-dom'

import { getViewerOfficialRankingHistoryDetail } from '../../../api/client'
import { EmptyState, RunScopedHeader, SectionCard } from '../../../components/RunScopedUi'
import { useLanguage, type Language } from '../../../i18n/LanguageContext'
import { formatApiError } from '../../../utils/apiErrors'
import { useViewerProductRunRouteContext } from '../../../viewer/ViewerProductRunRouteContext'
import { viewerPlayerProfilePath, viewerRankingsPath } from '../../../viewer/viewerRoutes'
import {
  DETAIL_PAGE_SIZE, detailPages, legacySeasonLabel, parseDetailPage,
  parseLegacyRankingOrdinal, rankingRowsMatchingId, validViewerRankingDetail
} from './rankingSnapshotDetailBrowsing'

// Each paired message is local to this page; IDs, policy and fingerprints
// always come unchanged from the historical publication.
const messages = {
  title: ['MSA žebříčky', 'MSA Rankings'],
  subtitle: ['Historický publikovaný Official Ranking z vybrané Viewer Branch.', 'Historical published Official Ranking from the selected Viewer Branch.'],
  back: ['Zpět na historii rankingů', 'Back to ranking history'],
  invalidRoute: ['Neplatný ordinal publikace.', 'Invalid publication ordinal.'],
  context: ['Čeká se na platný kontext Runu a Viewer Branch.', 'Waiting for a valid Run and Viewer Branch context.'],
  loading: ['Načítání publikovaného rankingu…', 'Loading published ranking…'],
  failed: ['Publikovaný ranking nelze načíst:', 'Failed to load published ranking:'],
  corrupt: ['Publikace neodpovídá zvolenému zdroji nebo obsahuje neplatná či duplicitní data. Nic se nezobrazuje.', 'The publication does not match the selected source or contains invalid or duplicate data. No rows are displayed.'],
  retry: ['Opakovat čtení', 'Retry read'],
  season: ['Sezona', 'Season'],
  week: ['Týden', 'Week'],
  ordinal: ['Ordinal publikace', 'Publication ordinal'],
  policy: ['Historická policy ID', 'Historical policy ID'],
  best: ['Historické Best N', 'Historical Best N'],
  players: ['Počet hráčů', 'Player count'],
  fingerprint: ['Otisk publikace', 'Publication fingerprint'],
  empty: ['Tato publikace platně obsahuje nula hráčů.', 'This publication legitimately contains zero players.'],
  table: ['Historický Official Ranking – hráči', 'Historical Official Ranking players'],
  rank: ['Pořadí', 'Rank'],
  player: ['ID hráče (odkaz na profil)', 'Player ID (profile link)'],
  points: ['Body', 'Points'],
  search: ['Hledat podle ID hráče', 'Search by player ID'],
  hint: ['Hledání používá jen ID z tohoto uloženého snapshotu. Jména, země ani bodové rozpisy API nevrací.', 'Search uses only IDs from this saved snapshot. The API does not return names, countries or point breakdowns.'],
  noMatches: ['Žádný hráč neodpovídá hledání.', 'No players match the search.'],
  clear: ['Vymazat hledání', 'Clear search'],
  showing: ['Zobrazeno', 'Showing'],
  of: ['z', 'of'],
  page: ['Stránka', 'Page'],
  first: ['První stránka', 'First page'],
  previous: ['Předchozí stránka', 'Previous page'],
  next: ['Další stránka', 'Next page'],
  last: ['Poslední stránka', 'Last page'],
  jumpLabel: ['Přejít na stránku', 'Jump to page'],
  go: ['Přejít', 'Go'],
  badJump: ['Zadej celé číslo existující stránky.', 'Enter an existing page number as a positive integer.']
} as const

type Copy = Record<keyof typeof messages, string>
function messagesFor(language: Language): Copy {
  const slot = language === 'cs' ? 0 : 1
  return Object.fromEntries(Object.entries(messages).map(([key, pair]) => [key, pair[slot]])) as Copy
}

function HistoricalRankingSource({
  runId, branchId, ordinal, copy: t
}: {
  runId: string
  branchId: string
  ordinal: number
  copy: Copy
}): JSX.Element {
  // The keyed source boundary resets local player search and page synchronously.
  const [search, setSearch] = useState('')
  const [page, setPage] = useState(1)
  const [jump, setJump] = useState('')
  const [jumpInvalid, setJumpInvalid] = useState(false)

  const query = useQuery({
    queryKey: ['viewer-official-ranking-history-detail', runId, branchId, ordinal],
    queryFn: () => getViewerOfficialRankingHistoryDetail(runId, ordinal),
    retry: false,
    refetchOnWindowFocus: false
  })
  const valid = query.data && validViewerRankingDetail(query.data, runId, branchId, ordinal)
  const detail = valid ? query.data : null
  const matching = rankingRowsMatchingId(detail?.rows ?? [], search)
  const pageCount = detailPages(matching.length)
  const actualPage = pageCount > 0 ? Math.min(page, pageCount) : 0
  const start = actualPage ? (actualPage - 1) * DETAIL_PAGE_SIZE : 0
  const visible = matching.slice(start, start + DETAIL_PAGE_SIZE)

  function changePage(next: number): void {
    setPage(next)
    setJump('')
    setJumpInvalid(false)
  }
  function submitPage(event: FormEvent<HTMLFormElement>): void {
    event.preventDefault()
    const target = parseDetailPage(jump, pageCount)
    if (target === null) setJumpInvalid(true)
    else changePage(target)
  }
  if (query.isPending) return <p className="status" role="status">{t.loading}</p>
  if (query.isError || !detail) return (
    <div role="alert">
      <p className="error">{query.isError ? t.failed + ' ' + formatApiError(query.error) : t.corrupt}</p>
      <button type="button" onClick={() => void query.refetch()}>{t.retry}</button>
    </div>
  )

  return (
    <SectionCard title={t.season + ' ' + legacySeasonLabel(detail.season_index) + ' · ' + t.week + ' ' + detail.week}>
      <dl>
        <dt>{t.ordinal}</dt><dd>{detail.week_ordinal}</dd>
        <dt>{t.policy}</dt><dd>{detail.policy_id}</dd>
        <dt>{t.best}</dt><dd>{detail.best_n}</dd>
        <dt>{t.players}</dt><dd>{detail.row_count}</dd>
        <dt>{t.fingerprint}</dt><dd><code>{detail.snapshot_fingerprint}</code></dd>
      </dl>
      {detail.row_count === 0 ? <EmptyState message={t.empty} /> : (
        <>
          <label htmlFor="official-detail-player-search">{t.search}</label>
          <input
            id="official-detail-player-search"
            type="search"
            value={search}
            onChange={event => {
              setSearch(event.target.value)
              changePage(1)
            }}
          />
          <p>{t.hint}</p>
          <button type="button" onClick={() => { setSearch(''); changePage(1) }}>{t.clear}</button>
          {matching.length === 0 ? <EmptyState message={t.noMatches} /> : (
            <table aria-label={t.table}>
              <thead><tr><th scope="col">{t.rank}</th><th scope="col">{t.player}</th><th scope="col">{t.points}</th></tr></thead>
              <tbody>
                {visible.map(row => (
                  <tr key={row.player_id}>
                    <td>{row.rank}</td>
                    <td><Link to={viewerPlayerProfilePath(runId, row.player_id)}>{row.player_id}</Link></td>
                    <td>{row.points}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </>
      )}
      <p role="status">{t.showing} {matching.length ? start + 1 : 0}–{matching.length ? start + visible.length : 0} {t.of} {matching.length}</p>
      {pageCount > 1 ? (
        <nav aria-label={t.page}>
          <button type="button" disabled={actualPage === 1} onClick={() => changePage(1)}>{t.first}</button>
          <button type="button" disabled={actualPage === 1} onClick={() => changePage(actualPage - 1)}>{t.previous}</button>
          <span>{t.page} {actualPage} / {pageCount}</span>
          <button type="button" disabled={actualPage === pageCount} onClick={() => changePage(actualPage + 1)}>{t.next}</button>
          <button type="button" disabled={actualPage === pageCount} onClick={() => changePage(pageCount)}>{t.last}</button>
          <form onSubmit={submitPage}>
            <label htmlFor="official-detail-jump">{t.jumpLabel}</label>
            <input id="official-detail-jump" type="text" inputMode="numeric"
              value={jump} onChange={event => { setJump(event.target.value); setJumpInvalid(false) }}
              aria-invalid={jumpInvalid} aria-describedby={jumpInvalid ? 'official-detail-jump-error' : undefined}
            />
            <button type="submit">{t.go}</button>
            {jumpInvalid ? <span id="official-detail-jump-error" role="alert">{t.badJump}</span> : null}
          </form>
        </nav>
      ) : null}
    </SectionCard>
  )
}

export function ViewerRankingSnapshotDetailPage(): JSX.Element {
  const { runId: routeRunId = '', snapshotSequence = '' } = useParams()
  const ordinal = parseLegacyRankingOrdinal(snapshotSequence)
  const { language } = useLanguage()
  const t = messagesFor(language)
  const { productRunId, officialBranchId, officialContext, isLoading, isStale } = useViewerProductRunRouteContext()
  const validRoute = Boolean(
    routeRunId === productRunId && productRunId.trim() && officialBranchId.trim() &&
    officialContext?.product_run_id === productRunId &&
    officialContext?.official_branch_id === officialBranchId &&
    !isLoading && !isStale
  )

  return (
    <section className="panel">
      <RunScopedHeader title={t.title} runId={productRunId} subtitle={t.subtitle} />
      <p><Link to={viewerRankingsPath(productRunId)}>{t.back}</Link></p>
      {ordinal === null ? <p className="error" role="alert">{t.invalidRoute}</p> : validRoute ? (
        <HistoricalRankingSource
          key={JSON.stringify([productRunId, officialBranchId, ordinal])}
          runId={productRunId}
          branchId={officialBranchId}
          ordinal={ordinal}
          copy={t}
        />
      ) : <p className="status" role="status">{t.context}</p>}
    </section>
  )
}
