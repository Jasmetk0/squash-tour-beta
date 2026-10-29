import { useState, type FormEvent } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'

import { getViewerFinalsRace } from '../../../api/client'
import type { ViewerFinalsRacePublication, ViewerFinalsRaceRow } from '../../../api/types'
import { useLanguage, type Language } from '../../../i18n/LanguageContext'
import { formatApiError } from '../../../utils/apiErrors'
import { useActiveViewerProductRunId } from '../../../viewer/useActiveViewerProductRunId'
import { useViewerOfficialRunContext } from '../../../viewer/useViewerOfficialRunContext'
import { useViewerProductRunRouteContext } from '../../../viewer/ViewerProductRunRouteContext'
import { viewerPlayerProfilePath, viewerRacePath, viewerRunsPath } from '../../../viewer/viewerRoutes'
import {
  filterRacePlayerRows, parseRacePage, raceSeasonLabel, raceSeasonsNewestFirst,
  RACE_PAGE_SIZE, validViewerRaceHistory, viewerRaceBranch
} from './finalsRaceBrowsing'

// Paired UI strings only; saved sporting identifiers and results are never translated.
const messages = {
  title: ['Race to Finals', 'Race to Finals'],
  subtitle: ['Uložené sezónní publikace Race z vybrané Viewer Branch.', 'Saved seasonal Race publications from the selected Viewer Branch.'],
  choose: ['Nejprve vyber Product Run.', 'Select a Product Run first.'],
  chooseLink: ['Otevřít seznam Runů', 'Browse Product Runs'],
  contextLoading: ['Ověřuji aktuální Viewer Branch…', 'Resolving current Viewer Branch…'],
  contextError: ['Nepodařilo se načíst Viewer Branch:', 'Could not load Viewer Branch:'],
  contextInvalid: ['Kontext neodpovídá zvolenému Runu / Viewer Branch.', 'Context does not match the selected Run / Viewer Branch.'],
  loading: ['Načítám publikované Race…', 'Loading published Race…'],
  error: ['Race se nepodařilo načíst:', 'Could not load Race:'],
  invalid: ['Race obsahuje cizí nebo neplatná data. Žádná publikace není zobrazena.', 'Race contains foreign or invalid data. No publication is displayed.'],
  retry: ['Zkusit načíst znovu', 'Retry read'],
  empty: ['V této Viewer Branch zatím není žádná publikovaná Race.', 'No Race publication has been saved in this Viewer Branch yet.'],
  season: ['Cílová sezona', 'Target season'],
  latest: ['Nejnovější uložená sezona', 'Latest saved season'],
  selected: ['Zvolená publikace', 'Selected publication'],
  history: ['Historie sezónních publikací', 'Seasonal publication history'],
  cutoff: ['Uzávěrka', 'Cutoff'],
  best: ['Historické Best N', 'Historical Best N'],
  players: ['Počet hráčů', 'Player count'],
  branch: ['Viewer Branch ID', 'Viewer Branch ID'],
  finals: ['Výběr účastníků Finals', 'Finals selection'],
  finalsEvent: ['Turnaj Finals', 'Finals event'],
  yes: ['Publikováno', 'Published'],
  pending: ['Zatím nepublikováno', 'Not published yet'],
  standings: ['Uložené pořadí Race', 'Saved Race standings'],
  rank: ['Pořadí', 'Rank'],
  player: ['ID hráče', 'Player ID'],
  points: ['Race body', 'Race points'],
  counted: ['Započtené turnaje', 'Counted tournaments'],
  status: ['Stav Finals', 'Finals status'],
  results: ['Započtené výsledky', 'Counted results'],
  notSelected: ['Nevybrán', 'Not selected'],
  selectionPending: ['Výběr zatím neproběhl', 'Selection pending'],
  direct: ['Přímý vstup', 'Direct entry'],
  race: ['Kvalifikace z Race', 'Race qualified'],
  seed: ['nasazení', 'seed'],
  none: ['Žádné', 'None'],
  noPlayers: ['Tato publikace obsahuje nula hráčů.', 'This publication contains zero players.'],
  search: ['Hledat ID hráče', 'Search player ID'],
  noMatch: ['Hledání neodpovídá žádnému hráči této publikace.', 'No players in this publication match the search.'],
  clear: ['Vymazat hledání', 'Clear search'],
  first: ['První', 'First'],
  previous: ['Předchozí', 'Previous'],
  next: ['Další', 'Next'],
  last: ['Poslední', 'Last'],
  page: ['Stránka', 'Page'],
  jump: ['Přejít na stránku', 'Jump to page'],
  go: ['Přejít', 'Go'],
  jumpError: ['Zadej existující celé číslo stránky.', 'Enter an existing integer page number.'],
  showing: ['Zobrazeno', 'Showing'],
  of: ['z', 'of'],
  participants: ['účastníků Finals', 'Finals participants'],
  openRun: ['Otevřít Race v Runu', 'Open run-scoped Race']
} as const
type Copy = Record<keyof typeof messages, string>
function copyFor(language: Language): Copy {
  const column = language === 'cs' ? 0 : 1
  return Object.fromEntries(Object.entries(messages).map(([key, pair]) => [key, pair[column]])) as Copy
}

function rowStatus(row: ViewerFinalsRaceRow, t: Copy): string {
  if (row.finals_selected === null) return t.selectionPending
  if (!row.finals_selected) return t.notSelected
  const qualification = row.qualification_source === 'direct_entry' ? t.direct : t.race
  return row.finals_seed === null ? qualification : qualification + ' · ' + t.seed + ' ' + row.finals_seed
}
function resultsLabel(row: ViewerFinalsRaceRow, t: Copy): string {
  return row.counted_results.length
    ? row.counted_results.map(r =>
      r.event_id + ': ' + r.race_points + ' (' + raceSeasonLabel(r.completed_season_index) + ' · W' + r.completed_week + ')'
    ).join(' · ')
    : t.none
}

function SelectedRacePublication({ publication, runId, t }: {
  publication: ViewerFinalsRacePublication
  runId: string
  t: Copy
}): JSX.Element {
  const [search, setSearch] = useState('')
  const [page, setPage] = useState(1)
  const [jump, setJump] = useState('')
  const [badJump, setBadJump] = useState(false)
  const found = filterRacePlayerRows(publication.rows, search)
  const totalPages = Math.ceil(found.length / RACE_PAGE_SIZE)
  const currentPage = totalPages ? Math.min(page, totalPages) : 0
  const start = currentPage ? (currentPage - 1) * RACE_PAGE_SIZE : 0
  const visible = found.slice(start, start + RACE_PAGE_SIZE)
  function changePage(value: number): void {
    setPage(value); setJump(''); setBadJump(false)
  }
  function jumpToPage(event: FormEvent<HTMLFormElement>): void {
    event.preventDefault()
    const next = parseRacePage(jump, totalPages)
    if (next === null) setBadJump(true)
    else changePage(next)
  }
  return (
    <>
      <h3>{t.selected}: {raceSeasonLabel(publication.target_season_index)}</h3>
      <dl className="metadata-list viewer-metadata-list">
        <div><dt>{t.branch}</dt><dd>{publication.viewer_branch_id}</dd></div>
        <div><dt>{t.season}</dt><dd>{raceSeasonLabel(publication.target_season_index)}</dd></div>
        <div><dt>{t.cutoff}</dt><dd>{raceSeasonLabel(publication.cutoff_season_index)} · W{publication.cutoff_week}</dd></div>
        <div><dt>{t.best}</dt><dd>{publication.best_n}</dd></div>
        <div><dt>{t.players}</dt><dd>{publication.rows.length}</dd></div>
        <div><dt>{t.finals}</dt><dd>{publication.selection_published ? t.yes : t.pending}</dd></div>
        <div><dt>{t.finalsEvent}</dt><dd>{publication.finals_event_id ?? t.pending}</dd></div>
      </dl>
      {publication.rows.length === 0 ? <p className="empty-state">{t.noPlayers}</p> : (
        <>
          <label htmlFor="race-player-search">{t.search}</label>
          <input id="race-player-search" type="search" value={search} onChange={e => { setSearch(e.target.value); changePage(1) }} />
          <button type="button" onClick={() => { setSearch(''); changePage(1) }}>{t.clear}</button>
          {found.length === 0 ? <p className="empty-state">{t.noMatch}</p> : (
            <div className="table-wrap">
              <table aria-label={t.standings}>
                <thead><tr><th scope="col">{t.rank}</th><th scope="col">{t.player}</th><th scope="col">{t.points}</th><th scope="col">{t.counted}</th><th scope="col">{t.status}</th><th scope="col">{t.results}</th></tr></thead>
                <tbody>{visible.map(row => (
                  <tr key={row.player_id}>
                    <td>{row.rank}</td>
                    <td><Link to={viewerPlayerProfilePath(runId, row.player_id)}>{row.player_id}</Link></td>
                    <td>{row.race_points}</td>
                    <td>{row.tournaments_counted}</td>
                    <td>{rowStatus(row, t)}</td>
                    <td>{resultsLabel(row, t)}</td>
                  </tr>
                ))}</tbody>
              </table>
            </div>
          )}
        </>
      )}
      <p role="status">{t.showing} {found.length ? start + 1 : 0}–{found.length ? start + visible.length : 0} {t.of} {found.length}</p>
      {totalPages > 1 ? (
        <nav aria-label={t.page}>
          <button type="button" disabled={currentPage === 1} onClick={() => changePage(1)}>{t.first}</button>
          <button type="button" disabled={currentPage === 1} onClick={() => changePage(currentPage - 1)}>{t.previous}</button>
          <span>{t.page} {currentPage} / {totalPages}</span>
          <button type="button" disabled={currentPage === totalPages} onClick={() => changePage(currentPage + 1)}>{t.next}</button>
          <button type="button" disabled={currentPage === totalPages} onClick={() => changePage(totalPages)}>{t.last}</button>
          <form onSubmit={jumpToPage}>
            <label htmlFor="race-page-jump">{t.jump}</label>
            <input id="race-page-jump" inputMode="numeric" value={jump} onChange={e => { setJump(e.target.value); setBadJump(false) }} aria-invalid={badJump} aria-describedby={badJump ? 'race-page-jump-error' : undefined} />
            <button type="submit">{t.go}</button>
            {badJump ? <span role="alert" id="race-page-jump-error">{t.jumpError}</span> : null}
          </form>
        </nav>
      ) : null}
    </>
  )
}

function RaceForSource({ runId, branchId, t }: { runId: string; branchId: string; t: Copy }): JSX.Element {
  const [season, setSeason] = useState<number | null>(null)
  const query = useQuery({
    queryKey: ['viewer-canonical-finals-race', runId, branchId],
    queryFn: () => getViewerFinalsRace(runId),
    retry: false,
    refetchOnWindowFocus: false
  })
  if (query.isPending) return <p className="status" role="status">{t.loading}</p>
  if (query.isError || !validViewerRaceHistory(query.data, runId, branchId)) return (
    <div role="alert">
      <p className="error">{query.isError ? t.error + ' ' + formatApiError(query.error) : t.invalid}</p>
      <button type="button" onClick={() => void query.refetch()}>{t.retry}</button>
    </div>
  )
  const history = raceSeasonsNewestFirst(query.data)
  if (!history.length) return <p className="empty-state">{t.empty}</p>
  const chosen = history.find(p => p.target_season_index === season) ?? history[0]
  return (
    <>
      <h3>{t.history}</h3>
      <label htmlFor="race-publication-season">{t.season}</label>
      <select id="race-publication-season" value={chosen.target_season_index}
        onChange={e => setSeason(Number(e.target.value))}>
        {history.map(p => <option key={p.target_season_index} value={p.target_season_index}>
          {raceSeasonLabel(p.target_season_index)}
        </option>)}
      </select>
      <ul aria-label={t.history} className="viewer-home-list">
        {history.map(p => (
          <li key={p.target_season_index}>
            <button type="button" aria-current={p.target_season_index === chosen.target_season_index ? 'true' : undefined}
              onClick={() => setSeason(p.target_season_index)}>{raceSeasonLabel(p.target_season_index)}</button>
            {' · '}{t.cutoff} W{p.cutoff_week} · {p.rows.length} {t.players.toLocaleLowerCase()} ·
            {' '}{p.selection_published ? p.rows.filter(row => row.finals_selected).length + ' ' + t.participants : t.selectionPending}
          </li>
        ))}
      </ul>
      <SelectedRacePublication key={chosen.target_season_index} publication={chosen} runId={runId} t={t} />
    </>
  )
}
function RaceContent({ runId, branchId, validScope, pending, error, retryContext, showRunLink }: {
  runId: string
  branchId: string | null
  validScope: boolean
  pending: boolean
  error: unknown
  retryContext: () => void
  showRunLink: boolean
}): JSX.Element {
  const { language } = useLanguage()
  const t = copyFor(language)
  return (
    <section className="panel viewer-shell-page">
      <div className="page-intro">
        <h2>{t.title}</h2>
        <p className="subtitle">{t.subtitle}</p>
      </div>
      {!runId ? <p className="empty-state">{t.choose} <Link to={viewerRunsPath()}>{t.chooseLink}</Link></p> :
        pending ? <p className="status" role="status">{t.contextLoading}</p> :
        error ? <div role="alert"><p className="error">{t.contextError} {formatApiError(error)}</p><button onClick={retryContext}>{t.retry}</button></div> :
        !validScope || !branchId ? <div role="alert"><p className="error">{t.contextInvalid}</p><button onClick={retryContext}>{t.retry}</button></div> :
        <>
          {showRunLink ? <p><Link to={viewerRacePath(runId)}>{t.openRun}</Link></p> : null}
          <RaceForSource key={JSON.stringify([runId, branchId])} runId={runId} branchId={branchId} t={t} />
        </>}
    </section>
  )
}

export function ViewerRacePage(): JSX.Element {
  const runId = useActiveViewerProductRunId()?.trim() ?? ''
  const context = useViewerOfficialRunContext(runId)
  const branchId = viewerRaceBranch(context.data, runId)
  return <RaceContent runId={runId} branchId={branchId}
    validScope={Boolean(branchId)} pending={Boolean(runId && (context.isPending || context.isFetching))}
    error={context.isError ? context.error : null}
    retryContext={() => { void context.refetch() }} showRunLink />
}

export function ViewerRunRacePage(): JSX.Element {
  const { productRunId, officialBranchId, officialContext, isLoading, isStale } = useViewerProductRunRouteContext()
  const branchId = viewerRaceBranch(officialContext, productRunId)
  return <RaceContent runId={productRunId} branchId={branchId}
    validScope={Boolean(branchId && branchId === officialBranchId)} pending={isLoading || isStale}
    error={null} retryContext={() => undefined} showRunLink={false} />
}
