import { useState, type FormEvent } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'

import { getViewerPlayers } from '../../../api/client'
import { useLanguage, type Language } from '../../../i18n/LanguageContext'
import { useActiveViewerProductRunId } from '../../../viewer/useActiveViewerProductRunId'
import { useViewerOfficialRunContext } from '../../../viewer/useViewerOfficialRunContext'
import {
  viewerCountryProfilePath, viewerPlayerProfilePath, viewerPlayersPath, viewerRunsPath
} from '../../../viewer/viewerRoutes'
import {
  filteredPlayerDirectory, parsePlayerDirectoryPage, playerDirectoryCountries,
  playerViewerBranch, verifiedViewerPlayers, PLAYER_DIRECTORY_PAGE_SIZE,
  type PlayerDirectoryFilters, type PlayerDirectorySort,
  type PlayerOriginFilter, type PlayerStatusFilter
} from './viewerPlayerDirectory'

const labels = {
  title: ['Hráči', 'Players'],
  description: ['Úplný veřejný seznam hráčů uloženého Product Runu.', 'Complete public player directory of the selected Saved Product Run.'],
  summary: ['Uložení hráči', 'Saved players'],
  choose: ['Nejprve vyber Product Run.', 'Select a Product Run first.'],
  chooseLink: ['Seznam Runů', 'Browse Runs'],
  resolving: ['Ověřuji uloženou Viewer Branch…', 'Resolving saved Viewer Branch…'],
  contextError: ['Nepodařilo se ověřit Viewer Branch.', 'Viewer Branch context could not be loaded.'],
  invalidContext: ['Viewer Branch neodpovídá vybranému Product Runu.', 'Viewer Branch does not match the selected Product Run.'],
  loading: ['Načítám uložené hráče…', 'Loading Saved players…'],
  readError: ['Seznam hráčů není dostupný.', 'Saved player list is unavailable.'],
  corrupt: ['Seznam hráčů obsahuje neplatná nebo cizí data. Nic se nezobrazuje.', 'Player list contains invalid or foreign source data. No players are displayed.'],
  retry: ['Načíst znovu (GET)', 'Retry read (GET)'],
  run: ['Product Run', 'Product Run'],
  branch: ['Viewer Branch', 'Viewer Branch'],
  clock: ['Uložený týden', 'Saved week'],
  total: ['Všichni hráči', 'Total players'],
  activeCount: ['Aktivní hráči', 'Active players'],
  retiredCount: ['Hráči po kariéře', 'Retired players'],
  search: ['Hledat jméno, ID nebo zemi', 'Search name, ID or country'],
  status: ['Kariéra', 'Career status'],
  all: ['Vše', 'All'],
  active: ['Aktivní', 'Active'],
  retired: ['Po kariéře', 'Retired'],
  origin: ['Původ hráče', 'Player origin'],
  initial: ['Počáteční svět', 'Initial World'],
  prospect: ['Nový talent Runu', 'Run prospect'],
  country: ['Země', 'Country'],
  countriesAll: ['Všechny země', 'All countries'],
  sort: ['Řazení', 'Sort by'],
  sortName: ['Jméno A–Z', 'Name A–Z'],
  sortOvr: ['Veřejné OVR sestupně', 'Public OVR descending'],
  sortAge: ['Věk sestupně', 'Age descending'],
  clear: ['Vymazat filtry', 'Clear filters'],
  table: ['Uložený seznam hráčů', 'Saved player directory'],
  player: ['Hráč', 'Player'],
  id: ['ID hráče', 'Player ID'],
  age: ['Věk', 'Age'],
  power: ['Veřejné OVR', 'Public OVR'],
  noPlayers: ['V tomto Runu nejsou žádní uložení hráči.', 'No Saved players exist in this Run.'],
  noMatch: ['Žádní hráči neodpovídají filtrům.', 'No players match the filters.'],
  showing: ['Zobrazeno', 'Showing'],
  of: ['z', 'of'],
  first: ['První', 'First'],
  previous: ['Předchozí', 'Previous'],
  next: ['Další', 'Next'],
  last: ['Poslední', 'Last'],
  page: ['Stránka', 'Page'],
  pageJump: ['Přejít na stránku', 'Jump to page'],
  go: ['Přejít', 'Go'],
  pageError: ['Zadej platné existující číslo stránky.', 'Enter a valid existing page number.'],
  runPlayers: ['Hráči vybraného Runu', 'Open Product Run players'],
  allRuns: ['Otevřít seznam Runů', 'Open Run browser']
} as const

type Copy = Record<keyof typeof labels, string>
function copyFor(language: Language): Copy {
  const i = language === 'cs' ? 0 : 1
  return Object.fromEntries(Object.entries(labels).map(([key, pair]) =>
    [key, pair[i]])) as Copy
}

const defaultFilters: PlayerDirectoryFilters = {
  search: '', status: 'all', origin: 'all', country: 'all', sort: 'name'
}

function PlayerDirectoryForBranch({ runId, branchId, t }: { runId: string; branchId: string; t: Copy }): JSX.Element {
  const [filters, setFilters] = useState<PlayerDirectoryFilters>(defaultFilters)
  const [page, setPage] = useState(1)
  const [jump, setJump] = useState('')
  const [badJump, setBadJump] = useState(false)
  const query = useQuery({
    queryKey: ['viewer-players-hub-canonical', runId, branchId],
    queryFn: () => getViewerPlayers(runId),
    retry: false, refetchOnWindowFocus: false
  })

  function movePage(to: number): void {
    setPage(to); setJump(''); setBadJump(false)
  }
  function changeFilter<K extends keyof PlayerDirectoryFilters>(key: K, value: PlayerDirectoryFilters[K]): void {
    setFilters(current => ({ ...current, [key]: value }))
    movePage(1)
  }
  if (query.isPending || query.isFetching) return <p role="status" className="status">{t.loading}</p>
  if (query.isError) return <div role="alert"><p className="error">{t.readError}</p>
    <button type="button" onClick={() => void query.refetch()}>{t.retry}</button></div>

  const source = verifiedViewerPlayers(query.data, runId, branchId)
  if (!source) return <div role="alert"><p className="error">{t.corrupt}</p>
    <button type="button" onClick={() => void query.refetch()}>{t.retry}</button></div>

  const countries = playerDirectoryCountries(source)
  const found = filteredPlayerDirectory(source, filters)
  const pages = Math.ceil(found.length / PLAYER_DIRECTORY_PAGE_SIZE)
  const currentPage = pages ? Math.min(page, pages) : 0
  const start = currentPage ? (currentPage - 1) * PLAYER_DIRECTORY_PAGE_SIZE : 0
  const visible = found.slice(start, start + PLAYER_DIRECTORY_PAGE_SIZE)
  function submitJump(event: FormEvent<HTMLFormElement>): void {
    event.preventDefault()
    const next = parsePlayerDirectoryPage(jump, pages)
    if (next === null) setBadJump(true)
    else movePage(next)
  }

  return (
    <>
      <dl className="metadata-list viewer-metadata-list" aria-label={t.summary}>
        <div><dt>{t.run}</dt><dd>{runId}</dd></div>
        <div><dt>{t.branch}</dt><dd>{branchId}</dd></div>
        <div><dt>{t.clock}</dt><dd>{source.season_index} · W{source.week}</dd></div>
        <div><dt>{t.total}</dt><dd>{source.player_count}</dd></div>
        <div><dt>{t.activeCount}</dt><dd>{source.active_player_count}</dd></div>
        <div><dt>{t.retiredCount}</dt><dd>{source.retired_player_count}</dd></div>
      </dl>
      {source.player_count === 0 ? <p className="empty-state">{t.noPlayers}</p> : (
        <>
          <div>
            <label htmlFor="player-directory-search">{t.search}</label>
            <input id="player-directory-search" type="search" value={filters.search}
              onChange={event => changeFilter('search', event.target.value)} />
          </div>
          <div>
            <label htmlFor="player-directory-status">{t.status}</label>
            <select id="player-directory-status" value={filters.status}
              onChange={event => changeFilter('status', event.target.value as PlayerStatusFilter)}>
              <option value="all">{t.all}</option>
              <option value="active">{t.active}</option>
              <option value="retired">{t.retired}</option>
            </select>
          </div>
          <div>
            <label htmlFor="player-directory-origin">{t.origin}</label>
            <select id="player-directory-origin" value={filters.origin}
              onChange={event => changeFilter('origin', event.target.value as PlayerOriginFilter)}>
              <option value="all">{t.all}</option>
              <option value="initial_world">{t.initial}</option>
              <option value="run_prospect">{t.prospect}</option>
            </select>
          </div>
          <div>
            <label htmlFor="player-directory-country">{t.country}</label>
            <select id="player-directory-country" value={filters.country}
              onChange={event => changeFilter('country', event.target.value)}>
              <option value="all">{t.countriesAll}</option>
              {countries.map(country => <option key={country} value={country}>{country}</option>)}
            </select>
          </div>
          <div>
            <label htmlFor="player-directory-sort">{t.sort}</label>
            <select id="player-directory-sort" value={filters.sort}
              onChange={event => changeFilter('sort', event.target.value as PlayerDirectorySort)}>
              <option value="name">{t.sortName}</option>
              <option value="public_ovr">{t.sortOvr}</option>
              <option value="age">{t.sortAge}</option>
            </select>
            <button type="button" onClick={() => { setFilters(defaultFilters); movePage(1) }}>{t.clear}</button>
          </div>
          {found.length === 0 ? <p className="empty-state">{t.noMatch}</p> :
            <div className="table-wrap">
              <table aria-label={t.table}>
                <thead><tr>
                  <th scope="col">{t.player}</th><th scope="col">{t.id}</th><th scope="col">{t.country}</th>
                  <th scope="col">{t.age}</th><th scope="col">{t.status}</th>
                  <th scope="col">{t.power}</th><th scope="col">{t.origin}</th>
                </tr></thead>
                <tbody>{visible.map(player => (
                  <tr key={player.player_id}>
                    <td><Link to={viewerPlayerProfilePath(runId, player.player_id)}>{player.name}</Link></td>
                    <td>{player.player_id}</td>
                    <td><Link to={viewerCountryProfilePath(runId, player.country_code)}>{player.country_code}</Link></td>
                    <td>{player.age}</td>
                    <td>{player.status === 'active' ? t.active : t.retired}</td>
                    <td>{player.current_ovr ?? '—'}</td>
                    <td>{player.identity_source === 'initial_world' ? t.initial : t.prospect}</td>
                  </tr>
                ))}</tbody>
              </table>
            </div>
          }
          <p role="status">{t.showing} {found.length ? start + 1 : 0}–{found.length ? start + visible.length : 0} {t.of} {found.length}</p>
          {pages > 1 ? <nav aria-label={t.page}>
            <button type="button" disabled={currentPage === 1} onClick={() => movePage(1)}>{t.first}</button>
            <button type="button" disabled={currentPage === 1} onClick={() => movePage(currentPage - 1)}>{t.previous}</button>
            <span>{t.page} {currentPage} / {pages}</span>
            <button type="button" disabled={currentPage === pages} onClick={() => movePage(currentPage + 1)}>{t.next}</button>
            <button type="button" disabled={currentPage === pages} onClick={() => movePage(pages)}>{t.last}</button>
            <form onSubmit={submitJump}>
              <label htmlFor="player-directory-jump">{t.pageJump}</label>
              <input id="player-directory-jump" inputMode="numeric" value={jump}
                aria-invalid={badJump} aria-describedby={badJump ? 'player-directory-error' : undefined}
                onChange={event => { setJump(event.target.value); setBadJump(false) }} />
              <button type="submit">{t.go}</button>
              {badJump ? <span role="alert" id="player-directory-error">{t.pageError}</span> : null}
            </form>
          </nav> : null}
        </>
      )}
      <nav aria-label={t.summary} className="viewer-active-run-actions">
        <Link className="viewer-active-run-link" to={viewerPlayersPath(runId)}>{t.runPlayers}</Link>{' '}
        <Link className="viewer-active-run-link" to={viewerRunsPath()}>{t.allRuns}</Link>
      </nav>
    </>
  )
}

export function ViewerPlayersPage(): JSX.Element {
  const runId = useActiveViewerProductRunId()?.trim() ?? ''
  const { language } = useLanguage()
  const t = copyFor(language)
  const context = useViewerOfficialRunContext(runId)
  const branchId = playerViewerBranch(context.data, runId)

  return (
    <section className="panel viewer-shell-page">
      <div className="page-intro"><h2>{t.title}</h2><p className="subtitle">{t.description}</p></div>
      <article className="viewer-active-run-card" aria-label={t.summary}>
        <h3>{t.summary}</h3>
        {!runId ? <p className="empty-state">{t.choose} <Link to={viewerRunsPath()}>{t.chooseLink}</Link></p> :
          context.isPending || context.isFetching ? <p className="status" role="status">{t.resolving}</p> :
          context.isError ? <div role="alert"><p className="error">{t.contextError}</p>
            <button type="button" onClick={() => void context.refetch()}>{t.retry}</button></div> :
          !branchId ? <div role="alert"><p className="error">{t.invalidContext}</p>
            <button type="button" onClick={() => void context.refetch()}>{t.retry}</button></div> :
          <PlayerDirectoryForBranch key={JSON.stringify([runId, branchId])}
            runId={runId} branchId={branchId} t={t} />
        }
      </article>
    </section>
  )
}
