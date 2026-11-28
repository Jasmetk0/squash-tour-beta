import { useMemo, useState } from 'react'
import { useQueries, useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'

import {
  getViewerRunCalendar, getViewerTournamentHistory, getViewerTournamentResult,
} from '../../../api/client'
import { useLanguage } from '../../../i18n/LanguageContext'
import { useActiveViewerProductRunId } from '../../../viewer/useActiveViewerProductRunId'
import { useViewerOfficialRunContext } from '../../../viewer/useViewerOfficialRunContext'
import {
  viewerPlayerProfilePath, viewerRunsPath, viewerTournamentDetailPath, viewerTopTourMatchesPath,
} from '../../../viewer/viewerRoutes'
import {
  catalogSeasonsNewestFirst, tournamentViewerBranch, verifiedTournamentCatalog,
  type SavedTournamentCatalog, type SavedTournamentEntry,
} from '../tour/viewerTournamentCatalog'
import {
  MAX_SELECTED_H2H_EVENTS, selectedPublishedH2H,
} from './viewerSelectedPublishedH2H'

const PAGE_SIZE = 20
const copy = {
  title: ['Vzájemné zápasy v publikovaných turnajích', 'H2H in Published Tournaments'],
  subtitle: ['Přesné výsledky dvou hráčů ze zvolených uložených turnajů.',
    'Exact results between two players in explicitly selected Saved tournaments.'],
  scope: [
    'Zkoumá jen vybrané veřejné výsledky legacy W61. Nejde o kompletní kariérní H2H: nevybrané, nepublikované nebo jinak uložené turnaje se nepočítají. Evidované výsledky mohou zahrnovat i skreče a kontumace; počet záznamů není počet skutečně odehraných utkání. Bez Rally Replaye a bez historických jmen odvozených ze současných profilů.',
    'Only chosen published legacy W61 sources are examined. This is not an all-career H2H: unselected, unpublished and otherwise stored events are not counted. Recorded outcomes may include retirements and walkovers; result records are not necessarily on-court matches. No rally replay or historical names inferred from current profiles.',
  ],
  noRun: ['Nejprve vyber Product Run.', 'Select a Product Run first.'],
  choose: ['Seznam Runů', 'Run browser'],
  contextLoading: ['Ověřuji Viewer Branch…', 'Verifying Viewer Branch…'],
  badContext: ['Vybraný Product Run nemá ověřenou Viewer Branch.', 'Selected Product Run has no verified Viewer Branch.'],
  sourceLoading: ['Načítám publikované turnaje…', 'Loading published tournaments…'],
  sourceError: ['Kalendář nebo historie turnajů není dostupná.', 'Calendar or tournament history is unavailable.'],
  sourceMismatch: ['Kalendář a turnajové výsledky neodpovídají stejné uložené Viewer Branch.', 'Calendar and results do not belong to the same Saved Viewer Branch.'],
  retry: ['Načíst znovu (GET)', 'Retry read (GET)'],
  run: ['Product Run', 'Product Run'],
  branch: ['Viewer Branch', 'Viewer Branch'],
  events: ['Turnajů v kalendáři', 'Calendar events'],
  published: ['Turnajů s výsledkem', 'Published result events'],
  noEvents: ['Zatím nejsou publikované žádné turnajové výsledky.', 'No tournament results are published yet.'],
  playerA: ['ID hráče A', 'Player A ID'],
  playerB: ['ID hráče B', 'Player B ID'],
  players: ['Vyber dva různé hráče podle stabilních ID z výsledků turnajů.', 'Enter two distinct stable player IDs from tournament results.'],
  season: ['Filtrovat sezonu', 'Filter season'],
  allSeasons: ['Všechny sezony', 'All seasons'],
  search: ['Hledat turnaj nebo ID', 'Search event or ID'],
  selections: ['Vybrat zdroje pro H2H', 'Select H2H sources'],
  limit: ['Nejvýše osm publikovaných turnajů. Otevřou se jen jejich explicitně vybrané výsledky.', 'Up to eight published tournaments. Only explicitly selected results are fetched.'],
  selected: ['Vybráno turnajů', 'Selected tournaments'],
  selectedList: ['Všechny vybrané zdroje (včetně zdrojů mimo aktuální filtr)', 'All selected sources (including those outside the current filter)'],
  remove: ['Odebrat turnaj', 'Remove tournament'],
  invalidSelection: ['Některý vybraný turnaj již není publikovaný v ověřené historii. Zruš výběr a vyber zdroje znovu.', 'A selected event is no longer published in the verified history. Clear the selection and choose sources again.'],
  matchLink: ['Otevřít přesný zápas v Match Center', 'Open exact match in Match Center'],
  select: ['Zahrnout turnaj', 'Include tournament'],
  noMatches: ['Filtrům neodpovídá žádný turnaj.', 'No tournament matches these filters.'],
  analyze: ['Spočítat H2H z vybraných publikací', 'Calculate H2H from selected publications'],
  validSelection: ['Zadej dvě různá ID hráčů a vyber alespoň jeden publikovaný turnaj.', 'Enter two different player IDs and select at least one published event.'],
  clear: ['Zrušit výběr', 'Clear selection'],
  loading: ['Načítám zvolené veřejné výsledky…', 'Reading selected public results…'],
  error: ['Alespoň jeden zvolený výsledek není dostupný. Souhrn se nezobrazuje.', 'At least one selected result is unavailable. No partial total is shown.'],
  invalid: ['Alespoň jeden výsledek neodpovídá ověřenému zdroji nebo obsahuje neveřejné údaje. Souhrn se nezobrazuje.', 'At least one result mismatches its verified source or contains private data. No partial total is shown.'],
  results: ['Ověřené H2H vybraných publikací', 'Verified selected-publication H2H'],
  counted: ['Prověřené publikované turnaje', 'Verified published tournaments'],
  records: ['Celkem záznamů zápasů ve zdrojích', 'All match records in selected sources'],
  encounters: ['Vzájemné výsledkové záznamy', 'H2H result records'],
  wins: ['Vítězství v záznamech', 'Wins in records'],
  playerStats: ['Zápasové statistiky hráčů z vybraných publikací', 'Player outcomes in selected publications'],
  playerStatsScope: [
    'Jen publikované výsledkové záznamy vybraných turnajů. Výhry a prohry vyžadují uvedeného soupeře; skreč či kontumace však mohou být stále výsledkem. Záznam bez soupeře se eviduje zvlášť. Nulová účast znamená pouze nepřítomnost v těchto zdrojích.',
    'Only published outcomes in selected tournaments. Wins and losses require a named opponent, but can still be retirements or walkovers. Outcomes without a named opponent are reported separately. Zero appearances means absence from these selected sources only.',
  ],
  selectedEntries: ['Záznam v soupiskách turnajů', 'Listed in selected tournament results'],
  recordedWins: ['Výhry se soupeřem', 'Wins with named opponent'],
  recordedLosses: ['Prohry se soupeřem', 'Losses with named opponent'],
  unopposed: ['Výsledky bez uvedeného soupeře', 'Outcomes without named opponent'],
  opponents: ['Různých uvedených soupeřů', 'Distinct named opponents'],
  sourceAbsent: ['Hráč se nevyskytuje v soupiskách zvolených publikací.', 'Player does not appear in the selected source player lists.'],
  playerEventTable: ['Výsledky hráčů podle vybraného turnaje', 'Player outcome records by selected event'],
  listed: ['Na soupisce zdroje', 'Listed in source'],
  yes: ['Ano', 'Yes'],
  no: ['Ne', 'No'],
  zero: ['Ve vybraných publikacích nebyl nalezen žádný vzájemný výsledek. To není důkaz nulové bilance za kariéru.', 'No H2H outcomes were found in the selected publications. This does not prove a zero career record.'],
  table: ['Konkrétní vzájemné zápasy', 'Exact H2H outcome records'],
  event: ['Turnaj', 'Tournament'],
  week: ['Týden rozpisu', 'Scheduled week'],
  drawTable: ['Bilance podle části turnaje ve vybraných zdrojích', 'Outcomes by draw section in selected sources'],
  qualification: ['Kvalifikace', 'Qualification'],
  group: ['Skupiny', 'Group'],
  main: ['Hlavní pavouk', 'Main draw'],
  knockout: ['Vyřazovací část', 'Knockout'],
  sectionWins: ['Výhry v části', 'Section wins'],
  sectionLosses: ['Prohry v části', 'Section losses'],
  matchId: ['ID zápasu', 'Match ID'],
  draw: ['Část', 'Draw'],
  round: ['Kolo', 'Round'],
  winner: ['Vítěz', 'Winner'],
  loser: ['Poražený', 'Loser'],
  score: ['Publikované skóre', 'Published score'],
  page: ['Stránka', 'Page'],
  showing: ['Zobrazeno', 'Showing'],
  of: ['z', 'of'],
  previous: ['Předchozí', 'Previous'],
  next: ['Další', 'Next'],
} as const
type Key = keyof typeof copy
type T = (key: Key) => string

function H2HReport({ events, runId, branchId, a, b, t }: {
  events: SavedTournamentEntry[]
  runId: string; branchId: string; a: string; b: string; t: T
}): JSX.Element {
  const queries = useQueries({
    queries: events.map(({ event }) => ({
      queryKey: ['viewer-saved-match-result', runId, branchId, event.event_id],
      queryFn: () => getViewerTournamentResult(runId, event.event_id),
      retry: false,
      refetchOnWindowFocus: false,
    })),
  })
  const retry = () => { void Promise.all(queries.map(query => query.refetch())) }
  if (queries.some(query => query.isPending || query.isFetching))
    return <p role="status">{t('loading')}</p>
  if (queries.some(query => query.isError))
    return <div role="alert"><p>{t('error')}</p>
      <button type="button" onClick={retry}>{t('retry')}</button></div>

  const report = selectedPublishedH2H(
    events.map((entry, i) => ({ entry, data: queries[i].data })),
    runId, branchId, a, b,
  )
  if (!report) return <div role="alert"><p>{t('invalid')}</p>
    <button type="button" onClick={retry}>{t('retry')}</button></div>

  return <section aria-label={t('results')} className="viewer-active-run-card">
    <h3>{t('results')}</h3>
    <p>{t('counted')}: {report.eventCount} · {t('records')}: {report.publicationMatchCount}</p>
    <p>{t('encounters')}: {report.encounters.length}</p>
    <dl className="metadata-list viewer-metadata-list">
      <div><dt>{t('wins')} — {report.playerA}</dt><dd>{report.winsA}</dd></div>
      <div><dt>{t('wins')} — {report.playerB}</dt><dd>{report.winsB}</dd></div>
    </dl>
    <p><Link to={viewerPlayerProfilePath(runId, report.playerA)}>{report.playerA}</Link>
      {' · '}<Link to={viewerPlayerProfilePath(runId, report.playerB)}>{report.playerB}</Link></p>
    <section aria-label={t('playerStats')}>
      <h4>{t('playerStats')}</h4>
      <p className="subtitle">{t('playerStatsScope')}</p>
      {([report.playerAStats, report.playerBStats]).map(stats =>
        <div key={stats.playerId} className="viewer-active-run-card">
          <h5>{stats.playerId}</h5>
          <dl className="metadata-list viewer-metadata-list">
            <div><dt>{t('selectedEntries')}</dt><dd>{stats.listedInEvents}/{report.eventCount}</dd></div>
            <div><dt>{t('recordedWins')}</dt><dd>{stats.winsAgainstNamedOpponents}</dd></div>
            <div><dt>{t('recordedLosses')}</dt><dd>{stats.lossesAgainstNamedOpponents}</dd></div>
            <div><dt>{t('unopposed')}</dt><dd>{stats.noOpponentOutcomes}</dd></div>
            <div><dt>{t('opponents')}</dt><dd>{stats.uniqueNamedOpponents}</dd></div>
          </dl>
          {stats.listedInEvents === 0 ? <p className="empty-state">{t('sourceAbsent')}</p> : null}
        </div>)}
      <div className="table-wrap">
        <table aria-label={t('drawTable')}>
          <thead><tr>
            <th scope="col">{t('draw')}</th>
            <th scope="col">{report.playerA} · {t('sectionWins')}</th>
            <th scope="col">{report.playerA} · {t('sectionLosses')}</th>
            <th scope="col">{report.playerB} · {t('sectionWins')}</th>
            <th scope="col">{report.playerB} · {t('sectionLosses')}</th>
          </tr></thead>
          <tbody>{report.playerAStats.byDraw.map((row, index) => <tr key={row.draw}>
            <th scope="row">{t(row.draw)}</th>
            <td>{row.wins}</td><td>{row.losses}</td>
            <td>{report.playerBStats.byDraw[index].wins}</td><td>{report.playerBStats.byDraw[index].losses}</td>
          </tr>)}</tbody>
        </table>
      </div>
      <div className="table-wrap">
        <table aria-label={t('playerEventTable')}>
          <thead><tr>
            <th scope="col">{t('playerA')} / {t('playerB')}</th>
            <th scope="col">{t('event')}</th>
            <th scope="col">{t('week')}</th>
            <th scope="col">{t('listed')}</th>
            <th scope="col">{t('recordedWins')}</th>
            <th scope="col">{t('recordedLosses')}</th>
            <th scope="col">{t('unopposed')}</th>
          </tr></thead>
          <tbody>{([report.playerAStats, report.playerBStats]).flatMap(stats =>
            stats.byEvent.map(row => <tr key={JSON.stringify([stats.playerId, row.eventId])}>
              <td>{stats.playerId}</td>
              <td><Link to={viewerTournamentDetailPath(runId, row.eventId)}>
                {row.eventName || row.eventId}</Link> ({row.season})</td>
              <td>W{row.week}</td>
              <td>{row.listedAsParticipant ? t('yes') : t('no')}</td>
              <td>{row.wins}</td><td>{row.losses}</td><td>{row.noOpponentOutcomes}</td>
            </tr>))}</tbody>
        </table>
      </div>
    </section>
    {report.encounters.length === 0
      ? <p className="empty-state">{t('zero')}</p> :
      <div className="table-wrap">
        <table aria-label={t('table')}>
          <thead><tr>
            <th scope="col">{t('event')}</th><th scope="col">{t('week')}</th>
            <th scope="col">{t('draw')}</th><th scope="col">{t('round')}</th>
            <th scope="col">{t('matchId')}</th><th scope="col">{t('winner')}</th>
            <th scope="col">{t('loser')}</th><th scope="col">{t('score')}</th>
          </tr></thead>
          <tbody>{report.encounters.map(match => <tr key={JSON.stringify([match.eventId, match.matchId])}>
            <td><Link to={viewerTournamentDetailPath(runId, match.eventId)}>
              {match.eventName || match.eventId}</Link> ({match.season})</td>
            <td>W{match.week}</td><td>{t(match.draw)}</td><td>{match.round}</td>
            <td><Link title={t('matchLink')} to={viewerTopTourMatchesPath() + '?' + new URLSearchParams({
              event: match.eventId, match: match.matchId, matchRun: runId, matchBranch: branchId,
            }).toString()}>{match.matchId}</Link></td>
            <td>{match.winnerId}</td><td>{match.loserId}</td><td>{match.scoreline}</td>
          </tr>)}</tbody>
        </table>
      </div>}
  </section>
}

function PublishedH2HCatalog({ catalog, runId, branchId, t }: {
  catalog: SavedTournamentCatalog; runId: string; branchId: string; t: T
}): JSX.Element {
  const [a, setA] = useState('')
  const [b, setB] = useState('')
  const [season, setSeason] = useState('all')
  const [search, setSearch] = useState('')
  const [page, setPage] = useState(1)
  const [selectedIds, setSelectedIds] = useState<string[]>([])
  const [submitted, setSubmitted] = useState<{ a: string; b: string; ids: string[] } | null>(null)
  const published = useMemo(() => catalog.entries
    .filter(item => item.publication.result_published)
    .sort((x, y) =>
      String(y.event.season).localeCompare(String(x.event.season), undefined, { numeric: true }) ||
      y.event.season_week - x.event.season_week || x.event.event_id.localeCompare(y.event.event_id)
    ), [catalog])
  const seasons = useMemo(() => catalogSeasonsNewestFirst(catalog), [catalog])
  const filtered = useMemo(() => {
    const term = search.trim().toLocaleLowerCase()
    return published.filter(({ event }) =>
      (season === 'all' || String(event.season) === season) &&
      (!term || [event.event_id, event.event_name, event.category, event.host_country]
        .some(value => value.toLocaleLowerCase().includes(term)))
    )
  }, [published, season, search])
  const pages = Math.ceil(filtered.length / PAGE_SIZE)
  const current = Math.min(page, pages || 1)
  const offset = (current - 1) * PAGE_SIZE
  const shown = filtered.slice(offset, offset + PAGE_SIZE)
  const chosen = published.filter(({ event }) => selectedIds.includes(event.event_id))
  const selected = submitted ? published.filter(({ event }) => submitted.ids.includes(event.event_id)) : []
  const invalidSelection = chosen.length !== selectedIds.length ||
    (submitted !== null && selected.length !== submitted.ids.length)
  const canSubmit = Boolean(!invalidSelection && a.trim() && b.trim() && a.trim() !== b.trim() &&
    selectedIds.length > 0 && selectedIds.length <= MAX_SELECTED_H2H_EVENTS)
  function toggle(eventId: string, enabled: boolean): void {
    setSelectedIds(old => enabled
      ? old.includes(eventId) || old.length >= MAX_SELECTED_H2H_EVENTS ? old : [...old, eventId]
      : old.filter(id => id !== eventId))
    setSubmitted(null)
  }
  return <article className="viewer-active-run-card">
    <dl className="metadata-list viewer-metadata-list">
      <div><dt>{t('run')}</dt><dd>{runId}</dd></div>
      <div><dt>{t('branch')}</dt><dd>{branchId}</dd></div>
      <div><dt>{t('events')}</dt><dd>{catalog.eventCount}</dd></div>
      <div><dt>{t('published')}</dt><dd>{catalog.publishedCount}</dd></div>
    </dl>
    {published.length === 0 ? <p className="empty-state">{t('noEvents')}</p> : <>
      <p>{t('players')}</p>
      <div className="viewer-filters">
        <label htmlFor="selected-h2h-a">{t('playerA')}</label>
        <input id="selected-h2h-a" type="search" value={a}
          onChange={e => { setA(e.target.value); setSubmitted(null) }} />
        <label htmlFor="selected-h2h-b">{t('playerB')}</label>
        <input id="selected-h2h-b" type="search" value={b}
          onChange={e => { setB(e.target.value); setSubmitted(null) }} />
        <label htmlFor="selected-h2h-season">{t('season')}</label>
        <select id="selected-h2h-season" value={season}
          onChange={e => { setSeason(e.target.value); setPage(1) }}>
          <option value="all">{t('allSeasons')}</option>
          {seasons.map(value => <option key={value} value={value}>{value}</option>)}
        </select>
        <label htmlFor="selected-h2h-search">{t('search')}</label>
        <input id="selected-h2h-search" type="search" value={search}
          onChange={e => { setSearch(e.target.value); setPage(1) }} />
      </div>
      <p>{t('limit')} {t('selected')}: {selectedIds.length}/{MAX_SELECTED_H2H_EVENTS}</p>
      {invalidSelection ? <p role="alert">{t('invalidSelection')}</p> : null}
      {chosen.length > 0 ? <section aria-label={t('selectedList')}>
        <h4>{t('selectedList')}</h4>
        <ul className="viewer-home-list">
          {chosen.map(({ event }) => <li key={event.event_id}>
            {event.event_name || event.event_id} · {String(event.season)} · W{event.season_week}{' '}
            <button type="button" aria-label={t('remove') + ': ' + (event.event_name || event.event_id) + ' (' + event.event_id + ')'}
              onClick={() => toggle(event.event_id, false)}>{t('remove')}</button>
          </li>)}
        </ul>
      </section> : null}
      {filtered.length === 0 ? <p className="empty-state">{t('noMatches')}</p> :
        <fieldset aria-label={t('selections')}>
          <legend>{t('selections')}</legend>
          {shown.map(({ event }) => <div key={event.event_id}>
            <label>
              <input type="checkbox" aria-label={t('select') + ': ' + (event.event_name || event.event_id)}
                checked={selectedIds.includes(event.event_id)}
                disabled={!selectedIds.includes(event.event_id) &&
                  selectedIds.length >= MAX_SELECTED_H2H_EVENTS}
                onChange={e => toggle(event.event_id, e.target.checked)} />
              {event.event_name || event.event_id} · {String(event.season)} · W{event.season_week} · {event.category}
            </label>
          </div>)}
        </fieldset>}
      {pages > 1 ? <nav aria-label={t('page')}>
        <button type="button" disabled={current === 1}
          onClick={() => setPage(n => Math.max(1, n - 1))}>{t('previous')}</button>
        <span>{t('page')} {current} / {pages}</span>
        <button type="button" disabled={current === pages}
          onClick={() => setPage(n => Math.min(pages, n + 1))}>{t('next')}</button>
      </nav> : null}
      <p>{t('showing')} {filtered.length ? offset + 1 : 0}–
        {filtered.length ? offset + shown.length : 0} {t('of')} {filtered.length}</p>
      <button type="button" disabled={!canSubmit} onClick={() => setSubmitted({
        a: a.trim(), b: b.trim(), ids: [...selectedIds],
      })}>{t('analyze')}</button>
      <button type="button" onClick={() => { setSelectedIds([]); setSubmitted(null) }}>
        {t('clear')}</button>
      {!canSubmit ? <p>{t('validSelection')}</p> : null}
      {submitted && !invalidSelection ? <H2HReport key={JSON.stringify([runId, branchId, submitted])}
        events={selected} runId={runId} branchId={branchId}
        a={submitted.a} b={submitted.b} t={t} /> : null}
    </>}
  </article>
}

export function ViewerSelectedPublishedH2HPage(): JSX.Element {
  const runId = useActiveViewerProductRunId()?.trim() ?? ''
  const { language } = useLanguage()
  const t: T = key => copy[key][language === 'cs' ? 0 : 1]
  const context = useViewerOfficialRunContext(runId)
  const branchId = tournamentViewerBranch(context.data, runId)
  const ready = Boolean(runId && branchId && !context.isPending &&
    !context.isFetching && !context.isError)
  const source = useQuery({
    queryKey: ['viewer-selected-publication-h2h-source', runId, branchId],
    queryFn: async () => {
      const [calendar, history] = await Promise.all([
        getViewerRunCalendar(runId), getViewerTournamentHistory(runId),
      ])
      return { calendar, history }
    },
    enabled: ready, retry: false, refetchOnWindowFocus: false,
  })
  let content: JSX.Element
  if (!runId) content = <p className="empty-state">{t('noRun')} <Link to={viewerRunsPath()}>{t('choose')}</Link></p>
  else if (context.isPending || context.isFetching) content = <p role="status">{t('contextLoading')}</p>
  else if (!ready) content = <div role="alert"><p>{t('badContext')}</p>
    <button type="button" onClick={() => void context.refetch()}>{t('retry')}</button></div>
  else if (source.isPending || source.isFetching) content = <p role="status">{t('sourceLoading')}</p>
  else if (source.isError) content = <div role="alert"><p>{t('sourceError')}</p>
    <button type="button" onClick={() => void source.refetch()}>{t('retry')}</button></div>
  else {
    const catalog = verifiedTournamentCatalog(
      source.data.calendar, source.data.history, runId, branchId ?? '',
    )
    content = catalog
      ? <PublishedH2HCatalog key={JSON.stringify([runId, branchId])}
          catalog={catalog} runId={runId} branchId={branchId ?? ''} t={t} />
      : <div role="alert"><p>{t('sourceMismatch')}</p>
          <button type="button" onClick={() => void source.refetch()}>{t('retry')}</button></div>
  }
  return <section className="panel viewer-shell-page">
    <div className="page-intro"><h2>{t('title')}</h2><p className="subtitle">{t('subtitle')}</p></div>
    <p className="subtitle">{t('scope')}</p>
    {content}
  </section>
}
