import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'

import { getViewerOfficialRanking, getViewerOfficialRunContext } from '../../../api/client'
import { useLanguage, type Language } from '../../../i18n/LanguageContext'
import { formatApiError } from '../../../utils/apiErrors'
import { useActiveViewerProductRunId } from '../../../viewer/useActiveViewerProductRunId'
import {
  viewerPlayerProfilePath, viewerRankingSnapshotPath, viewerRankingsPath, viewerRunsPath
} from '../../../viewer/viewerRoutes'
import {
  currentRankingViewerBranch, legacyCurrentRankingSeason, validCurrentOfficialRanking
} from './currentOfficialRanking'

// Local CS/EN copy: never translate identities or historic policy values.
const messages = {
  title: ['MSA žebříčky', 'MSA Rankings'],
  subtitle: ['Aktuálně publikovaný Official Ranking vybrané Viewer Branch, pouze ze skutečně uložených dat.', 'Currently published Official Ranking from the selected Viewer Branch, using saved data only.'],
  current: ['Aktuální Official Ranking', 'Current Official Ranking'],
  card: ['Aktuálně publikovaný žebříček', 'Currently published ranking'],
  choose: ['Není vybrán žádný Product Run.', 'No Product Run is selected.'],
  chooseLink: ['Otevřít Product Runy', 'Browse Product Runs'],
  contextLoading: ['Ověřuji aktuální Viewer Branch…', 'Resolving current Viewer Branch…'],
  contextError: ['Nepodařilo se ověřit Viewer Branch:', 'Could not resolve Viewer Branch:'],
  contextInvalid: ['Kontext Viewer Branch neodpovídá zvolenému Product Runu. Žádná data se nezobrazují.', 'Viewer Branch context does not match the selected Product Run. No data is displayed.'],
  rankingLoading: ['Načítání publikovaného rankingu…', 'Loading published ranking…'],
  rankingError: ['Aktuální Official Ranking nelze načíst:', 'Current Official Ranking could not be loaded:'],
  rankingInvalid: ['Publikace neodpovídá Product Runu/Viewer Branch nebo obsahuje neplatné důkazy. Žádná data se nezobrazují.', 'The publication belongs to another Product Run/Viewer Branch or contains invalid evidence. No data is displayed.'],
  retry: ['Opakovat pouze čtení', 'Retry read only'],
  run: ['Product Run ID', 'Product Run ID'],
  branch: ['Viewer Branch ID', 'Viewer Branch ID'],
  season: ['Sezona', 'Season'],
  week: ['Týden', 'Week'],
  ordinal: ['Ordinal publikace', 'Publication ordinal'],
  players: ['Počet hráčů', 'Player count'],
  best: ['Historické Best N', 'Historical Best N'],
  policy: ['Policy ID', 'Policy ID'],
  fingerprint: ['Otisk publikace', 'Publication fingerprint'],
  top: ['Prvních 10 hráčů Official Rankingu', 'Top 10 published Official Ranking players'],
  rank: ['Pořadí', 'Rank'],
  player: ['ID hráče', 'Player ID'],
  points: ['Body', 'Points'],
  table: ['První desítka Official Rankingu', 'Current Official Ranking Top 10'],
  zero: ['Publikovaný ranking obsahuje přesně 0 hráčů.', 'The published ranking contains exactly 0 players.'],
  tableNote: ['Zobrazená ID, pořadí a body pocházejí z publikace. API neposkytuje jména, země, posuny ani rozpis výsledků; nic z toho se nedopočítává.', 'IDs, ranks and points come from the publication. The API does not supply names, countries, movements or result breakdowns; none are inferred.'],
  all: ['Otevřít úplnou historii publikací', 'Open full publication history'],
  detail: ['Otevřít tento publikovaný snapshot', 'Open this published snapshot']
} as const

type Copy = Record<keyof typeof messages, string>
function copyFor(language: Language): Copy {
  const index = language === 'cs' ? 0 : 1
  return Object.fromEntries(Object.entries(messages).map(([key, pair]) => [key, pair[index]])) as Copy
}

function CurrentRankingFromBranch({
  runId, branchId, t
}: {
  runId: string
  branchId: string
  t: Copy
}): JSX.Element {
  const rankingQuery = useQuery({
    queryKey: ['viewer-current-official-ranking', runId, branchId],
    queryFn: () => getViewerOfficialRanking(runId),
    retry: false,
    refetchOnWindowFocus: true
  })
  if (rankingQuery.isPending) return <p className="status" role="status">{t.rankingLoading}</p>
  if (rankingQuery.isError) return (
    <div role="alert">
      <p className="error">{t.rankingError} {formatApiError(rankingQuery.error)}</p>
      <button type="button" onClick={() => void rankingQuery.refetch()}>{t.retry}</button>
    </div>
  )
  const current = rankingQuery.data
  if (!validCurrentOfficialRanking(current, runId, branchId)) return (
    <div role="alert">
      <p className="error">{t.rankingInvalid}</p>
      <button type="button" onClick={() => void rankingQuery.refetch()}>{t.retry}</button>
    </div>
  )

  return (
    <>
      <dl className="metadata-list viewer-metadata-list" aria-label={t.card}>
        <div><dt>{t.run}</dt><dd>{current.product_run_id}</dd></div>
        <div><dt>{t.branch}</dt><dd>{current.viewer_branch_id}</dd></div>
        <div><dt>{t.season}</dt><dd>{legacyCurrentRankingSeason(current.season_index)}</dd></div>
        <div><dt>{t.week}</dt><dd>{current.week}</dd></div>
        <div><dt>{t.ordinal}</dt><dd>{current.week_ordinal}</dd></div>
        <div><dt>{t.players}</dt><dd>{current.row_count}</dd></div>
        <div><dt>{t.best}</dt><dd>{current.best_n}</dd></div>
        <div><dt>{t.policy}</dt><dd>{current.policy_id}</dd></div>
        <div><dt>{t.fingerprint}</dt><dd><code>{current.snapshot_fingerprint}</code></dd></div>
      </dl>
      {current.row_count === 0 ? <p className="empty-state">{t.zero}</p> : (
        <>
          <h4>{t.top}</h4>
          <table aria-label={t.table}>
            <thead><tr><th scope="col">{t.rank}</th><th scope="col">{t.player}</th><th scope="col">{t.points}</th></tr></thead>
            <tbody>{current.rows.slice(0, 10).map(row => (
              <tr key={row.player_id}>
                <td>{row.rank}</td>
                <td><Link to={viewerPlayerProfilePath(runId, row.player_id)}>{row.player_id}</Link></td>
                <td>{row.points}</td>
              </tr>
            ))}</tbody>
          </table>
          <p>{t.tableNote}</p>
        </>
      )}
      <nav aria-label={t.card}>
        <p><Link to={viewerRankingSnapshotPath(runId, current.week_ordinal)}>{t.detail}</Link></p>
        <p><Link to={viewerRankingsPath(runId)}>{t.all}</Link></p>
      </nav>
    </>
  )
}

export function ViewerRankingsPage(): JSX.Element {
  const productRunId = useActiveViewerProductRunId()
  const runId = productRunId?.trim() ?? ''
  const { language } = useLanguage()
  const t = copyFor(language)
  const contextQuery = useQuery({
    queryKey: ['viewer-current-official-context', runId],
    queryFn: () => getViewerOfficialRunContext(runId),
    enabled: Boolean(runId),
    retry: false,
    refetchOnMount: 'always',
    refetchOnWindowFocus: true
  })
  const branchId = currentRankingViewerBranch(contextQuery.data, runId)

  return (
    <section className="panel viewer-shell-page">
      <div className="page-intro">
        <h2>{t.title}</h2>
        <p className="subtitle">{t.subtitle}</p>
      </div>
      <article className="viewer-active-run-card viewer-active-run-card--summary" aria-label={t.card}>
        <h3>{t.current}</h3>
        {!runId ? <p className="empty-state">{t.choose} <Link to={viewerRunsPath()}>{t.chooseLink}</Link></p> :
          contextQuery.isPending || contextQuery.isFetching ? <p className="status" role="status">{t.contextLoading}</p> :
          contextQuery.isError ? (
            <div role="alert"><p className="error">{t.contextError} {formatApiError(contextQuery.error)}</p>
              <button type="button" onClick={() => void contextQuery.refetch()}>{t.retry}</button></div>
          ) : !branchId ? (
            <div role="alert"><p className="error">{t.contextInvalid}</p>
              <button type="button" onClick={() => void contextQuery.refetch()}>{t.retry}</button></div>
          ) : (
            <CurrentRankingFromBranch key={JSON.stringify([runId, branchId])}
              runId={runId} branchId={branchId} t={t} />
          )}
      </article>
    </section>
  )
}
