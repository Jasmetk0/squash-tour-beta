import { useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'

import {
  getViewerOfficialRankingHistoryDetail, listViewerOfficialRankingHistory,
} from '../../../api/client'
import type { ViewerOfficialRanking, ViewerOfficialRankingHistoryItem } from '../../../api/types'
import { useLanguage } from '../../../i18n/LanguageContext'
import { useActiveViewerProductRunId } from '../../../viewer/useActiveViewerProductRunId'
import { useViewerOfficialRunContext } from '../../../viewer/useViewerOfficialRunContext'
import {
  viewerPlayerProfilePath, viewerRankingSnapshotPath, viewerRankingsPath, viewerRunsPath,
} from '../../../viewer/viewerRoutes'
import { playerViewerBranch } from '../people/viewerPlayerDirectory'
import {
  legacyRankingSeasonLabel, validRankingHistory,
} from '../rankings/rankingHistoryBrowsing'
import { validViewerRankingDetail } from '../rankings/rankingSnapshotDetailBrowsing'

const PAGE_SIZE = 10
const copy = {
  title: ['Historie publikovaných jedniček', 'Published No. 1 History'],
  description: [
    'Prohlížej skutečně publikované Official Rankingy a ověř jejich hráče na 1. místě.',
    'Browse actual Official Ranking publications and inspect their first-ranked players.',
  ],
  scope: [
    'První místo lze určit až z detailu konkrétní publikace. Detaily se načítají jednotlivě na vyžádání, nikoliv hromadně. Nejde o úplnou kariérní historii ani výpočet týdnů na 1. místě: mezery mezi publikacemi se nedopočítávají a uložená historie může být neúplná. Tato veřejná projekce je pouze legacy W61.',
    'No. 1 is established only by an individual publication detail. Details are loaded individually on demand, never in bulk. This is neither a complete career history nor weeks-at-No.1 counting: gaps between publications are never filled and the Saved history may be incomplete. This public projection is legacy W61 only.',
  ],
  noRun: ['Nejprve vyber Product Run.', 'Select a Product Run first.'],
  runs: ['Seznam Runů', 'Run browser'],
  contextLoading: ['Ověřuji Viewer Branch…', 'Verifying Viewer Branch…'],
  contextError: ['Nelze ověřit Viewer Branch tohoto Runu.', 'Cannot verify this Run’s Viewer Branch.'],
  loading: ['Načítám seznam publikací…', 'Loading publication history…'],
  readError: ['Historie Official Rankingu není dostupná.', 'Official Ranking history is unavailable.'],
  mismatch: ['Historie neodpovídá zvolenému Runu a Viewer Branch nebo je neplatná.', 'History mismatches the selected Run and Viewer Branch or is invalid.'],
  retry: ['Načíst znovu (GET)', 'Retry read (GET)'],
  run: ['Product Run', 'Product Run'],
  branch: ['Viewer Branch', 'Viewer Branch'],
  published: ['Publikací v uloženém zdroji', 'Publications in Saved source'],
  head: ['Poslední zveřejněný ordinal', 'Public head ordinal'],
  history: ['Úplná historie publikací', 'All ranking publications'],
  season: ['Sezona', 'Season'],
  allSeasons: ['Všechny sezony', 'All seasons'],
  policy: ['Hledat Policy ID nebo ordinal', 'Search Policy ID or ordinal'],
  clear: ['Vymazat filtry', 'Clear filters'],
  table: ['Publikace pro ověření hráče č. 1', 'Publications for No. 1 verification'],
  week: ['Týden', 'Week'],
  ordinal: ['Ordinal', 'Ordinal'],
  rows: ['Počet hráčů', 'Ranked players'],
  proof: ['Hráč na 1. místě podle publikace', 'No. 1 in publication'],
  inspect: ['Ověřit hráče č. 1 (GET)', 'Verify No. 1 (GET)'],
  hide: ['Skrýt detail', 'Hide detail'],
  emptyRanking: ['Publikovaný žebříček má 0 hráčů.', 'Published ranking has 0 players.'],
  inspectLoading: ['Načítám detail publikace…', 'Loading publication detail…'],
  inspectError: ['Detail publikace není dostupný.', 'Publication detail is unavailable.'],
  inspectMismatch: [
    'Detail se neshoduje s historií, identitou zdroje nebo publikovaným otiskem.',
    'Detail disagrees with history, source identity or published fingerprint.',
  ],
  verified: ['Ověřené 1. místo', 'Verified No. 1'],
  points: ['Body', 'Points'],
  open: ['Otevřít ranking', 'Open ranking'],
  zero: ['Nejsou dostupné žádné publikace.', 'No publications are available.'],
  noMatch: ['Filtrům neodpovídá žádná publikace.', 'No publication matches these filters.'],
  showing: ['Zobrazeno', 'Showing'],
  of: ['z', 'of'],
  page: ['Stránka', 'Page'],
  previous: ['Předchozí', 'Previous'],
  next: ['Další', 'Next'],
} as const
type T = (key: keyof typeof copy) => string

// Metadata provenance must agree with the individually fetched immutable
// publication. Checking ordinal and branch alone cannot prove which version
// of the ranking was actually published.
export function verifiedNo1Publication(
  data: unknown, metadata: ViewerOfficialRankingHistoryItem,
  runId: string, branchId: string,
): ViewerOfficialRanking | null {
  if (!validViewerRankingDetail(data, runId, branchId, metadata.week_ordinal)) return null
  if (
    data.season_index !== metadata.season_index ||
    data.week !== metadata.week ||
    data.snapshot_fingerprint !== metadata.snapshot_fingerprint ||
    data.policy_id !== metadata.policy_id ||
    data.best_n !== metadata.best_n ||
    data.row_count !== metadata.row_count
  ) return null
  return data
}

function PublishedLeader({ metadata, runId, branchId, t }: {
  metadata: ViewerOfficialRankingHistoryItem
  runId: string
  branchId: string
  t: T
}): JSX.Element {
  const [inspect, setInspect] = useState(false)
  const detail = useQuery({
    queryKey: ['viewer-official-ranking-history-detail', runId, branchId, metadata.week_ordinal],
    queryFn: () => getViewerOfficialRankingHistoryDetail(runId, metadata.week_ordinal),
    enabled: inspect && metadata.row_count > 0,
    retry: false, refetchOnWindowFocus: false,
  })
  if (metadata.row_count === 0) return <span>{t('emptyRanking')}</span>
  const proven = detail.data && !detail.isFetching
    ? verifiedNo1Publication(detail.data, metadata, runId, branchId)
    : null
  const first = proven?.rows[0]

  return <>
    <button type="button" onClick={() => setInspect(value => !value)}>
      {inspect ? t('hide') : t('inspect')}
    </button>
    {inspect ? detail.isPending || detail.isFetching
      ? <p role="status">{t('inspectLoading')}</p>
      : detail.isError ? <div role="alert">
          <p>{t('inspectError')}</p>
          <button type="button" onClick={() => void detail.refetch()}>{t('retry')}</button>
        </div>
      : !proven || !first ? <div role="alert">
          <p>{t('inspectMismatch')}</p>
          <button type="button" onClick={() => void detail.refetch()}>{t('retry')}</button>
        </div>
      : <div>
          <span>{t('verified')}: </span>
          <Link to={viewerPlayerProfilePath(runId, first.player_id)}>{first.player_id}</Link>
          {' · '}{t('points')}: {first.points}
        </div>
    : null}
  </>
}

function PublishedNo1Browser({ runId, branchId, t }: {
  runId: string; branchId: string; t: T
}): JSX.Element {
  const [season, setSeason] = useState('all')
  const [policy, setPolicy] = useState('')
  const [page, setPage] = useState(1)
  const historyQuery = useQuery({
    queryKey: ['viewer-official-ranking-history', runId, branchId],
    queryFn: () => listViewerOfficialRankingHistory(runId),
    retry: false, refetchOnWindowFocus: false,
  })

  if (historyQuery.isPending || historyQuery.isFetching) return <p role="status">{t('loading')}</p>
  if (historyQuery.isError) return <div role="alert">
    <p>{t('readError')}</p>
    <button type="button" onClick={() => void historyQuery.refetch()}>{t('retry')}</button>
  </div>
  if (!validRankingHistory(historyQuery.data, runId, branchId)) return <div role="alert">
    <p>{t('mismatch')}</p>
    <button type="button" onClick={() => void historyQuery.refetch()}>{t('retry')}</button>
  </div>
  return <No1VerifiedHistory
    key={JSON.stringify([runId, branchId, historyQuery.data.public_head_ordinal,
      historyQuery.data.publication_count])}
    source={historyQuery.data} runId={runId} branchId={branchId} t={t}
    season={season} onSeason={next => { setSeason(next); setPage(1) }}
    policy={policy} onPolicy={next => { setPolicy(next); setPage(1) }}
    page={page} onPage={setPage}
    onClear={() => { setSeason('all'); setPolicy(''); setPage(1) }}
  />
}

function No1VerifiedHistory({ source, runId, branchId, t,
  season, onSeason, policy, onPolicy, page, onPage, onClear,
}: {
  source: { public_head_ordinal: number; publication_count: number;
    publications: ViewerOfficialRankingHistoryItem[] }
  runId: string; branchId: string; t: T
  season: string; onSeason: (value: string) => void
  policy: string; onPolicy: (value: string) => void
  page: number; onPage: (value: number | ((previous: number) => number)) => void
  onClear: () => void
}): JSX.Element {
  const seasons = useMemo(
    () => [...new Set(source.publications.map(item => item.season_index))].sort((a, b) => b - a),
    [source],
  )
  const filtered = useMemo(() => {
    const q = policy.trim().toLocaleLowerCase().replace(/^#/, '')
    return source.publications.filter(item =>
      (season === 'all' || item.season_index === Number(season)) &&
      (!q || item.policy_id.toLocaleLowerCase().includes(q) ||
        String(item.week_ordinal).includes(q))
    ).sort((a, b) => b.week_ordinal - a.week_ordinal)
  }, [source, season, policy])
  const pages = Math.ceil(filtered.length / PAGE_SIZE)
  const currentPage = Math.min(page, pages || 1)
  const start = (currentPage - 1) * PAGE_SIZE
  const shown = filtered.slice(start, start + PAGE_SIZE)

  return <article className="viewer-active-run-card">
    <dl className="metadata-list viewer-metadata-list">
      <div><dt>{t('run')}</dt><dd>{runId}</dd></div>
      <div><dt>{t('branch')}</dt><dd>{branchId}</dd></div>
      <div><dt>{t('published')}</dt><dd>{source.publication_count}</dd></div>
      <div><dt>{t('head')}</dt><dd>{source.public_head_ordinal}</dd></div>
    </dl>
    <p><Link to={viewerRankingsPath(runId)}>{t('history')}</Link></p>
    {source.publication_count === 0 ? <p className="empty-state">{t('zero')}</p> : <>
      <div className="viewer-filters">
        <label htmlFor="published-no1-season">{t('season')}</label>
        <select id="published-no1-season" value={season} onChange={e => onSeason(e.target.value)}>
          <option value="all">{t('allSeasons')}</option>
          {seasons.map(value =>
            <option key={value} value={value}>{legacyRankingSeasonLabel(value)}</option>)}
        </select>
        <label htmlFor="published-no1-search">{t('policy')}</label>
        <input id="published-no1-search" type="search" value={policy}
          onChange={e => onPolicy(e.target.value)} />
        <button type="button" onClick={onClear}>{t('clear')}</button>
      </div>
      {filtered.length === 0 ? <p className="empty-state">{t('noMatch')}</p> :
        <div className="table-wrap">
          <table aria-label={t('table')}>
            <thead><tr>
              <th scope="col">{t('season')}</th>
              <th scope="col">{t('week')}</th>
              <th scope="col">{t('ordinal')}</th>
              <th scope="col">{t('rows')}</th>
              <th scope="col">{t('proof')}</th>
              <th scope="col">{t('open')}</th>
            </tr></thead>
            <tbody>{shown.map(item =>
              <tr key={item.week_ordinal}>
                <td>{legacyRankingSeasonLabel(item.season_index)}</td>
                <td>{item.week}</td>
                <td>{item.week_ordinal}</td>
                <td>{item.row_count}</td>
                <td><PublishedLeader key={JSON.stringify([runId, branchId, item.week_ordinal,
                  item.snapshot_fingerprint])} metadata={item} runId={runId} branchId={branchId} t={t} /></td>
                <td><Link to={viewerRankingSnapshotPath(runId, item.week_ordinal)}>
                  {t('open')} #{item.week_ordinal}
                </Link></td>
              </tr>)}</tbody>
          </table>
        </div>
      }
      <p role="status">{t('showing')} {filtered.length ? start + 1 : 0}–
        {filtered.length ? start + shown.length : 0} {t('of')} {filtered.length}</p>
      {pages > 1 ? <nav aria-label={t('page')}>
        <button type="button" disabled={currentPage === 1}
          onClick={() => onPage(n => Math.max(1, n - 1))}>{t('previous')}</button>
        <span>{t('page')} {currentPage} / {pages}</span>
        <button type="button" disabled={currentPage === pages}
          onClick={() => onPage(n => Math.min(pages, n + 1))}>{t('next')}</button>
      </nav> : null}
    </>}
  </article>
}

export function ViewerNo1PublishedHistoryPage(): JSX.Element {
  const runId = useActiveViewerProductRunId()?.trim() ?? ''
  const { language } = useLanguage()
  const t: T = key => copy[key][language === 'cs' ? 0 : 1]
  const context = useViewerOfficialRunContext(runId)
  const branchId = playerViewerBranch(context.data, runId)
  const validContext = Boolean(runId && branchId && !context.isPending &&
    !context.isFetching && !context.isError)

  return <section className="panel viewer-shell-page">
    <div className="page-intro">
      <h2>{t('title')}</h2>
      <p className="subtitle">{t('description')}</p>
    </div>
    <p className="subtitle">{t('scope')}</p>
    {!runId ? <p className="empty-state">
      {t('noRun')} <Link to={viewerRunsPath()}>{t('runs')}</Link>
    </p> : context.isPending || context.isFetching ?
      <p role="status">{t('contextLoading')}</p> :
      !validContext ? <div role="alert">
        <p>{t('contextError')}</p>
        <button type="button" onClick={() => void context.refetch()}>{t('retry')}</button>
      </div> :
      <PublishedNo1Browser key={JSON.stringify([runId, branchId])}
        runId={runId} branchId={branchId ?? ''} t={t} />}
  </section>
}
