import { useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'

import { getViewerPlayers } from '../../../api/client'
import type { ViewerPlayers } from '../../../api/types'
import { useLanguage } from '../../../i18n/LanguageContext'
import { useActiveViewerProductRunId } from '../../../viewer/useActiveViewerProductRunId'
import { useViewerOfficialRunContext } from '../../../viewer/useViewerOfficialRunContext'
import {
  viewerCountryProfilePath, viewerPlayerProfilePath, viewerPlayersPath, viewerRunsPath,
  viewerTopAllPlayersPath, viewerTopActivePlayersPath, viewerTopRetiredPlayersPath,
} from '../../../viewer/viewerRoutes'
import {
  filteredPlayerDirectory, playerDirectoryCountries, playerViewerBranch,
  verifiedViewerPlayers, PLAYER_DIRECTORY_PAGE_SIZE,
  type PlayerDirectorySort, type PlayerOriginFilter, type PlayerStatusFilter,
} from '../people/viewerPlayerDirectory'
import type { ViewerPlayersDeferredKind } from './viewerDeferredConfigs'

const copy = {
  titleAll: ['Všichni hráči', 'All Players'],
  titleActive: ['Aktivní hráči', 'Active Players'],
  titleRetired: ['Hráči po kariéře', 'Retired Players'],
  description: [
    'Ověřený veřejný seznam hráčů z aktuální uložené Viewer Branch.',
    'Verified public player directory from the current Saved Viewer Branch.',
  ],
  scope: [
    'Status, věk a veřejné OVR odpovídají uloženému týdnu níže, nikoli libovolnému týdnu vybranému v navigaci. Soukromé atributy a budoucí změny nejsou zobrazeny.',
    'Status, age and public OVR reflect the Saved week below, not any arbitrary week selected in navigation. Private attributes and future changes are never shown.',
  ],
  noRun: ['Nejprve vyber Product Run.', 'Select a Product Run first.'],
  runs: ['Seznam Runů', 'Run browser'],
  contextLoading: ['Ověřuji uloženou Viewer Branch…', 'Verifying Saved Viewer Branch…'],
  contextError: [
    'Viewer Branch není dostupná nebo neodpovídá vybranému Runu.',
    'Viewer Branch is unavailable or does not match the selected Run.',
  ],
  loading: ['Načítám veřejný uložený seznam hráčů…', 'Loading the public Saved player directory…'],
  readError: ['Veřejný seznam hráčů není dostupný.', 'Public player directory is unavailable.'],
  invalid: [
    'Zdroj hráčů neodpovídá Runu/Viewer Branch nebo obsahuje nepovolená data.',
    'Player source does not match this Run/Viewer Branch or contains forbidden data.',
  ],
  retry: ['Znovu načíst (GET)', 'Retry read (GET)'],
  run: ['Product Run', 'Product Run'],
  branch: ['Viewer Branch', 'Viewer Branch'],
  clock: ['Uložený týden', 'Saved week'],
  total: ['Celkem hráčů', 'Total players'],
  active: ['Aktivní', 'Active'],
  retired: ['Po kariéře', 'Retired'],
  all: ['Všichni', 'All'],
  search: ['Hledat hráče nebo zemi', 'Search player or country'],
  country: ['Země', 'Country'],
  countriesAll: ['Všechny země', 'All countries'],
  origin: ['Původ hráče', 'Player origin'],
  originAll: ['Všichni hráči', 'All origins'],
  initial: ['Počáteční svět', 'Initial World'],
  prospect: ['Nový talent Runu', 'Run prospect'],
  sort: ['Řazení', 'Sort'],
  name: ['Jméno A–Z', 'Name A–Z'],
  ovr: ['Veřejné OVR sestupně', 'Public OVR descending'],
  age: ['Věk sestupně', 'Age descending'],
  clear: ['Vymazat filtry', 'Clear filters'],
  tableAll: ['Veřejný seznam všech hráčů', 'All public players'],
  tableActive: ['Veřejný seznam aktivních hráčů', 'Active public players'],
  tableRetired: ['Veřejný seznam hráčů po kariéře', 'Retired public players'],
  player: ['Hráč', 'Player'],
  playerId: ['ID hráče', 'Player ID'],
  playerAge: ['Věk', 'Age'],
  playerOvr: ['Veřejné OVR', 'Public OVR'],
  noPlayers: ['V uloženém Runu nejsou žádní hráči v této kategorii.', 'No players in this category exist in this Saved Run.'],
  noMatch: ['Filtrům neodpovídá žádný hráč.', 'No players match these filters.'],
  showing: ['Zobrazeno', 'Showing'],
  of: ['z', 'of'],
  page: ['Stránka', 'Page'],
  previous: ['Předchozí', 'Previous'],
  next: ['Další', 'Next'],
  runDirectory: ['Přejít na seznam vybraného Runu', 'Open selected Run directory'],
  navigation: ['Kategorie hráčů', 'Player categories'],
} as const
type Key = keyof typeof copy
type T = (name: Key) => string
type DirectoryKind = ViewerPlayersDeferredKind

function directoryTitle(kind: DirectoryKind): 'titleAll' | 'titleActive' | 'titleRetired' {
  return kind === 'active' ? 'titleActive' : kind === 'retired' ? 'titleRetired' : 'titleAll'
}
function tableTitle(kind: DirectoryKind): 'tableAll' | 'tableActive' | 'tableRetired' {
  return kind === 'active' ? 'tableActive' : kind === 'retired' ? 'tableRetired' : 'tableAll'
}

function VerifiedPlayerDirectory({ source, runId, kind, t }: {
  source: ViewerPlayers; runId: string; kind: DirectoryKind; t: T
}): JSX.Element {
  const [search, setSearch] = useState('')
  const [country, setCountry] = useState('all')
  const [origin, setOrigin] = useState<PlayerOriginFilter>('all')
  const [sort, setSort] = useState<PlayerDirectorySort>('name')
  const [page, setPage] = useState(1)
  const countries = useMemo(() => playerDirectoryCountries(source), [source])
  const status: PlayerStatusFilter = kind === 'all' ? 'all' : kind
  const filtered = useMemo(() => filteredPlayerDirectory(source, {
    status, search, country, origin, sort,
  }), [source, status, search, country, origin, sort])
  const eligibleCount = kind === 'active' ? source.active_player_count
    : kind === 'retired' ? source.retired_player_count : source.player_count
  const pages = Math.ceil(filtered.length / PLAYER_DIRECTORY_PAGE_SIZE)
  const visiblePage = Math.min(page, pages || 1)
  const start = (visiblePage - 1) * PLAYER_DIRECTORY_PAGE_SIZE
  const visible = filtered.slice(start, start + PLAYER_DIRECTORY_PAGE_SIZE)
  function reset(): void {
    setSearch(''); setCountry('all'); setOrigin('all'); setSort('name'); setPage(1)
  }
  return <article className="viewer-active-run-card">
    <dl className="metadata-list viewer-metadata-list">
      <div><dt>{t('run')}</dt><dd>{runId}</dd></div>
      <div><dt>{t('branch')}</dt><dd>{source.viewer_branch_id}</dd></div>
      <div><dt>{t('clock')}</dt><dd>{source.season_index} · W{source.week}</dd></div>
      <div><dt>{t('total')}</dt><dd>{source.player_count}</dd></div>
      <div><dt>{t('active')}</dt><dd>{source.active_player_count}</dd></div>
      <div><dt>{t('retired')}</dt><dd>{source.retired_player_count}</dd></div>
    </dl>
    <nav aria-label={t('navigation')} className="viewer-active-run-actions">
      <Link to={viewerTopAllPlayersPath()} aria-current={kind === 'all' ? 'page' : undefined}>{t('all')}</Link>{' '}
      <Link to={viewerTopActivePlayersPath()} aria-current={kind === 'active' ? 'page' : undefined}>{t('active')}</Link>{' '}
      <Link to={viewerTopRetiredPlayersPath()} aria-current={kind === 'retired' ? 'page' : undefined}>{t('retired')}</Link>
    </nav>
    {eligibleCount === 0 ? <p className="empty-state">{t('noPlayers')}</p> : <>
      <div className="viewer-filters">
        <label htmlFor="saved-player-search">{t('search')}</label>
        <input id="saved-player-search" type="search" value={search}
          onChange={e => { setSearch(e.target.value); setPage(1) }} />
        <label htmlFor="saved-player-country">{t('country')}</label>
        <select id="saved-player-country" value={country}
          onChange={e => { setCountry(e.target.value); setPage(1) }}>
          <option value="all">{t('countriesAll')}</option>
          {countries.map(value => <option key={value} value={value}>{value}</option>)}
        </select>
        <label htmlFor="saved-player-origin">{t('origin')}</label>
        <select id="saved-player-origin" value={origin}
          onChange={e => { setOrigin(e.target.value as PlayerOriginFilter); setPage(1) }}>
          <option value="all">{t('originAll')}</option>
          <option value="initial_world">{t('initial')}</option>
          <option value="run_prospect">{t('prospect')}</option>
        </select>
        <label htmlFor="saved-player-sort">{t('sort')}</label>
        <select id="saved-player-sort" value={sort}
          onChange={e => { setSort(e.target.value as PlayerDirectorySort); setPage(1) }}>
          <option value="name">{t('name')}</option>
          <option value="public_ovr">{t('ovr')}</option>
          <option value="age">{t('age')}</option>
        </select>
        <button type="button" onClick={reset}>{t('clear')}</button>
      </div>
      {filtered.length === 0 ? <p className="empty-state">{t('noMatch')}</p> : (
        <div className="table-wrap">
          <table aria-label={t(tableTitle(kind))}>
            <thead><tr>
              <th scope="col">{t('player')}</th>
              <th scope="col">{t('playerId')}</th>
              <th scope="col">{t('country')}</th>
              <th scope="col">{t('playerAge')}</th>
              <th scope="col">{t('playerOvr')}</th>
              <th scope="col">{t('origin')}</th>
            </tr></thead>
            <tbody>{visible.map(player => <tr key={player.player_id}>
              <td><Link to={viewerPlayerProfilePath(runId, player.player_id)}>{player.name}</Link></td>
              <td>{player.player_id}</td>
              <td><Link to={viewerCountryProfilePath(runId, player.country_code)}>{player.country_code}</Link></td>
              <td>{player.age}</td>
              <td>{player.current_ovr ?? '—'}</td>
              <td>{player.identity_source === 'initial_world' ? t('initial') : t('prospect')}</td>
            </tr>)}</tbody>
          </table>
        </div>
      )}
      <p role="status">{t('showing')} {filtered.length ? start + 1 : 0}–
        {filtered.length ? start + visible.length : 0} {t('of')} {filtered.length}</p>
      {pages > 1 ? <nav aria-label={t('page')}>
        <button type="button" disabled={visiblePage === 1}
          onClick={() => setPage(n => Math.max(1, n - 1))}>{t('previous')}</button>
        <span>{t('page')} {visiblePage} / {pages}</span>
        <button type="button" disabled={visiblePage === pages}
          onClick={() => setPage(n => Math.min(pages, n + 1))}>{t('next')}</button>
      </nav> : null}
    </>}
    <p className="viewer-active-run-actions">
      <Link to={viewerPlayersPath(runId)}>{t('runDirectory')}</Link>
    </p>
  </article>
}

export function ViewerSavedPlayerDirectoriesPage({ kind }: { kind: DirectoryKind }): JSX.Element {
  const runId = useActiveViewerProductRunId()?.trim() ?? ''
  const { language } = useLanguage()
  const t: T = key => copy[key][language === 'cs' ? 0 : 1]
  const context = useViewerOfficialRunContext(runId)
  const branchId = playerViewerBranch(context.data, runId)
  const validContext = Boolean(runId && branchId && !context.isPending && !context.isFetching && !context.isError)
  const query = useQuery({
    // Reuse the exact public source cache of the canonical Run player page.
    // A branch change invalidates this view and never mixes foreign rows.
    queryKey: ['viewer-players-hub-canonical', runId, branchId],
    queryFn: () => getViewerPlayers(runId),
    enabled: validContext,
    retry: false,
    refetchOnWindowFocus: false,
  })
  return <section className="panel viewer-shell-page">
    <div className="page-intro">
      <h2>{t(directoryTitle(kind))}</h2>
      <p className="subtitle">{t('description')}</p>
    </div>
    <p className="subtitle">{t('scope')}</p>
    {!runId ? <p className="empty-state">{t('noRun')} <Link to={viewerRunsPath()}>{t('runs')}</Link></p> :
      context.isPending || context.isFetching ? <p className="status" role="status">{t('contextLoading')}</p> :
      !validContext ? <div role="alert">
        <p>{t('contextError')}</p>
        <button type="button" onClick={() => void context.refetch()}>{t('retry')}</button>
      </div> :
      query.isPending || query.isFetching ? <p className="status" role="status">{t('loading')}</p> :
      query.isError ? <div role="alert">
        <p>{t('readError')}</p>
        <button type="button" onClick={() => void query.refetch()}>{t('retry')}</button>
      </div> : (() => {
        const source = verifiedViewerPlayers(query.data, runId, branchId ?? '')
        return source
          ? <VerifiedPlayerDirectory key={JSON.stringify([runId, branchId, kind])}
              source={source} runId={runId} kind={kind} t={t} />
          : <div role="alert">
              <p>{t('invalid')}</p>
              <button type="button" onClick={() => void query.refetch()}>{t('retry')}</button>
            </div>
      })()}
  </section>
}
