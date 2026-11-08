import { useState, type FormEvent } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'

import { getViewerOfficialRunContext } from '../../../api/client'
import { listViewerSignedSeasons, readViewerSignedSeason } from '../../../api/viewerSignedSeason'
import type { TourSeasonComparison } from '../../../api/calendarTour'
import { useLanguage, type Language } from '../../../i18n/LanguageContext'
import { viewerPlayerProfilePath } from '../../../viewer/viewerRoutes'
import {
  verifiedSignedSeasonBranch, verifiedSignedSeasonComparison, verifiedSignedSeasonList
} from './viewerSignedSeasonReadModel'

const texts = {
  title: ['Uzavřené sezony – výsledky a srovnání', 'Signed seasons – results and comparison'],
  about: ['Pouze historicky uzavřené sezony vybrané uložené Viewer Branch.', 'Only historically signed seasons in the selected Saved Viewer Branch.'],
  unavailable: ['Podepsané sezony nejsou dostupné (například ještě žádná nebyla uzavřena).', 'Signed seasons unavailable (for example, no season has closed yet).'],
  invalid: ['Historický zdroj neprošel ověřením Runu, větve nebo uložené revize.', 'Historical source failed Run, Branch or Saved revision verification.'],
  resolving: ['Ověřuji Viewer Branch…', 'Resolving Viewer Branch…'],
  loading: ['Načítám uzavřené sezony…', 'Loading signed seasons…'],
  retry: ['Znovu načíst GET', 'Retry GET'],
  selected: ['Vybraná sezona', 'Selected season'],
  comparison: ['Srovnávací sezona', 'Comparison season'],
  none: ['Bez srovnání', 'No comparison'],
  show: ['Zobrazit přehled', 'Show report'],
  summary: ['Souhrn sezony', 'Season summary'],
  branch: ['Viewer Branch', 'Viewer Branch'],
  revision: ['Saved Revision', 'Saved Revision'],
  editions: ['Dokončené turnaje', 'Completed tournaments'],
  weeks: ['Týdnů v sezoně', 'Weeks in season'],
  ranking: ['Žebříček na konci sezony', 'Published end-of-season ranking'],
  player: ['Hráč', 'Player'],
  points: ['Body', 'Points'],
  titles: ['Tituly', 'Titles'],
  finals: ['Finále', 'Finals'],
  countries: ['Statistiky zemí', 'Country statistics'],
  country: ['Země', 'Country'],
  semifinals: ['Semifinále', 'Semifinals'],
  quarters: ['Čtvrtfinále', 'Quarterfinals'],
  awards: ['Udělené body', 'Awarded points'],
  participants: ['Různí hráči', 'Distinct players'],
  events: ['Turnaje sezony', 'Season editions'],
  week: ['Týden', 'Week'],
  tournament: ['Turnaj', 'Tournament'],
  winner: ['Vítěz', 'Champion'],
  finalist: ['Finalista', 'Finalist'],
  players: ['Individuální výkony', 'Player results'],
  delta: ['Změna vůči vybrané sezoně', 'Change versus comparison season'],
  noDelta: ['Srovnání není vybrané.', 'No comparison selected.'],
  noRecords: ['Žádné potvrzené turnaje.', 'No confirmed editions.'],
  noCountries: ['Žádné země s turnajovou účastí.', 'No countries with tournament participation.'],
  noPlayers: ['Žádní hráči ve výsledcích.', 'No players with recorded results.'],
  semantics: ['Udělené turnajové body a publikované rankingové body jsou rozdílné veličiny. Srovnání pochází z původních historických souhrnů.', 'Awarded tournament points differ from published ranking points. Comparisons use the original historical summaries.']
} as const
type T = (key: keyof typeof texts) => string
function translator(language: Language): T {
  const index = language === 'cs' ? 0 : 1
  return key => texts[key][index]
}

function SignedSeasonsBody({ runId, branchId, t }: {
  runId: string; branchId: string; t: T
}): JSX.Element {
  const [selected, setSelected] = useState<number | null>(null)
  const [comparison, setComparison] = useState<number | null>(null)
  const [requested, setRequested] = useState<{ selected: number; comparison: number | null } | null>(null)
  const list = useQuery({
    queryKey: ['viewer-signed-season-list', runId, branchId],
    queryFn: ({ signal }) => listViewerSignedSeasons(runId, signal),
    retry: false,
    refetchOnMount: 'always',
    refetchOnWindowFocus: true
  })
  const available = list.isSuccess ? verifiedSignedSeasonList(list.data, runId, branchId) : null
  const indices = available?.seasons.map(s => s.index) ?? []
  const chosen = selected ?? indices[indices.length - 1] ?? null
  const actualRequest = requested &&
    indices.includes(requested.selected) &&
    (requested.comparison === null || indices.includes(requested.comparison)) ?
      requested : null

  const reportQuery = useQuery({
    queryKey: ['viewer-signed-season-summary', runId, branchId, available?.savedHead,
      actualRequest?.selected, actualRequest?.comparison],
    queryFn: ({ signal }) => readViewerSignedSeason(
      runId, actualRequest?.selected ?? 0, actualRequest?.comparison ?? null, signal
    ),
    enabled: Boolean(available && actualRequest),
    retry: false,
    refetchOnMount: 'always',
    refetchOnWindowFocus: true
  })
  // A list refetch is allowed to invalidate an old report at any time.
  const report = available && actualRequest && reportQuery.isSuccess
    ? verifiedSignedSeasonComparison(reportQuery.data, runId, branchId,
        available.savedHead, actualRequest.selected, actualRequest.comparison, indices)
    : null

  function submit(event: FormEvent<HTMLFormElement>): void {
    event.preventDefault()
    if (chosen === null || !indices.includes(chosen) ||
      (comparison !== null && (!indices.includes(comparison) || comparison === chosen))) return
    setRequested({ selected: chosen, comparison })
  }

  if (list.isPending || list.isFetching) return <p role="status" className="status">{t('loading')}</p>
  if (list.isError) return <div role="alert">
    <p>{t('unavailable')}</p>
    <button type="button" onClick={() => void list.refetch()}>{t('retry')}</button>
  </div>
  if (!available) return <div role="alert">
    <p>{t('invalid')}</p>
    <button type="button" onClick={() => void list.refetch()}>{t('retry')}</button>
  </div>

  return <>
    <form onSubmit={submit} aria-label={t('title')}>
      <label htmlFor="signed-season-select">{t('selected')}</label>{' '}
      <select id="signed-season-select" value={chosen ?? ''} onChange={e => {
        setSelected(Number(e.target.value))
        if (comparison === Number(e.target.value)) setComparison(null)
        setRequested(null)
      }}>
        {available.seasons.map(s =>
          <option key={s.index} value={s.index}>{s.label}</option>
        )}
      </select>{' '}
      <label htmlFor="signed-season-compare">{t('comparison')}</label>{' '}
      <select id="signed-season-compare" value={comparison ?? ''} onChange={e => {
        setComparison(e.target.value === '' ? null : Number(e.target.value))
        setRequested(null)
      }}>
        <option value="">{t('none')}</option>
        {available.seasons.filter(s => s.index !== chosen).map(s =>
          <option key={s.index} value={s.index}>{s.label}</option>
        )}
      </select>{' '}
      <button type="submit">{t('show')}</button>
    </form>
    {reportQuery.isPending && actualRequest ? <p role="status">{t('loading')}</p> :
      reportQuery.isError && actualRequest ? <div role="alert">
        <p>{t('unavailable')}</p><button type="button" onClick={() => void reportQuery.refetch()}>{t('retry')}</button>
      </div> :
      actualRequest && reportQuery.isSuccess && !report ? <div role="alert">
        <p>{t('invalid')}</p><button type="button" onClick={() => void reportQuery.refetch()}>{t('retry')}</button>
      </div> : null}
    {report && actualRequest ? <SignedSeasonReport key={JSON.stringify([report.saved_head_revision_id,
      actualRequest.selected, actualRequest.comparison])} runId={runId}
      branchId={branchId} result={report} t={t} /> : null}
  </>
}

function SignedSeasonReport({ runId, branchId, result, t }: {
  runId: string; branchId: string; result: TourSeasonComparison; t: T
}): JSX.Element {
  const season = result.selected
  const [showAllPlayers, setShowAllPlayers] = useState(false)
  const [showAllCountries, setShowAllCountries] = useState(false)
  const players = showAllPlayers ? season.players : season.players.slice(0, 20)
  const countries = showAllCountries ? season.countries : season.countries.slice(0, 20)
  return <article aria-label={t('summary')}>
    <h4>{t('summary')}: {season.season_label}</h4>
    <dl className="metadata-list viewer-metadata-list">
      <div><dt>{t('branch')}</dt><dd>{branchId}</dd></div>
      <div><dt>{t('revision')}</dt><dd><code>{result.saved_head_revision_id}</code></dd></div>
      <div><dt>{t('editions')}</dt><dd>{season.completed_edition_count}</dd></div>
      <div><dt>{t('weeks')}</dt><dd>{season.weeks_per_season}</dd></div>
    </dl>
    <h5>{t('events')}</h5>
    {season.editions.length ? <div className="table-wrap"><table aria-label={t('events')}>
      <thead><tr><th scope="col">{t('week')}</th><th scope="col">{t('tournament')}</th>
        <th scope="col">{t('winner')}</th><th scope="col">{t('finalist')}</th></tr></thead>
      <tbody>{season.editions.map(e => <tr key={e.edition_id}>
        <td>W{e.week}</td><td>{e.name}</td>
        <td>{e.champion_player_id ?
          <Link to={viewerPlayerProfilePath(runId, e.champion_player_id)}>
            {e.champion_name || e.champion_player_id}</Link> : '—'}</td>
        <td>{e.finalist_player_id ?
          <Link to={viewerPlayerProfilePath(runId, e.finalist_player_id)}>
            {e.finalist_name || e.finalist_player_id}</Link> : '—'}</td>
      </tr>)}</tbody>
    </table></div> : <p>{t('noRecords')}</p>}
    <h5>{t('countries')}</h5>
    {countries.length ? <div className="table-wrap"><table aria-label={t('countries')}>
      <thead><tr><th scope="col">{t('country')}</th><th scope="col">{t('titles')}</th>
        <th scope="col">{t('finals')}</th><th scope="col">{t('semifinals')}</th>
        <th scope="col">{t('quarters')}</th><th scope="col">{t('awards')}</th>
        <th scope="col">{t('participants')}</th></tr></thead>
      <tbody>{countries.map(c => <tr key={c.country_code}>
        <td>{c.country_code}</td><td>{c.titles}</td><td>{c.finals}</td>
        <td>{c.semifinals}</td><td>{c.quarterfinals}</td>
        <td>{c.awarded_points}</td><td>{c.distinct_players}</td>
      </tr>)}</tbody>
    </table></div> : <p>{t('noCountries')}</p>}
    {!showAllCountries && season.countries.length > 20 ? <button type="button"
      onClick={() => setShowAllCountries(true)}>+{season.countries.length - 20}</button> : null}
    <h5>{t('players')}</h5>
    {players.length ? <div className="table-wrap"><table aria-label={t('players')}>
      <thead><tr><th scope="col">{t('player')}</th><th scope="col">{t('country')}</th>
        <th scope="col">{t('titles')}</th><th scope="col">{t('finals')}</th>
        <th scope="col">{t('awards')}</th></tr></thead>
      <tbody>{players.map(p => <tr key={p.player_id}>
        <td><Link to={viewerPlayerProfilePath(runId, p.player_id)}>{p.name}</Link></td>
        <td>{p.country_code}</td><td>{p.titles}</td><td>{p.finals}</td>
        <td>{p.awarded_points}</td>
      </tr>)}</tbody>
    </table></div> : <p>{t('noPlayers')}</p>}
    {!showAllPlayers && season.players.length > 20 ? <button type="button"
      onClick={() => setShowAllPlayers(true)}>+{season.players.length - 20}</button> : null}
    <h5>{t('ranking')}</h5>
    <div className="table-wrap"><table aria-label={t('ranking')}>
      <thead><tr><th scope="col">#</th><th scope="col">{t('player')}</th><th scope="col">{t('points')}</th></tr></thead>
      <tbody>{season.last_week_published_ranking.top_players.map(p =>
        <tr key={p.player_id}><td>{p.rank}</td>
          <td><Link to={viewerPlayerProfilePath(runId, p.player_id)}>{p.player_id}</Link></td>
          <td>{p.points}</td></tr>
      )}</tbody>
    </table></div>
    <h5>{t('delta')}</h5>
    {result.comparison ? <>
      <p>{season.season_label} ↔ {result.comparison.season_label}</p>
      <div className="table-wrap"><table aria-label={t('delta')}>
        <thead><tr><th scope="col">{t('country')}</th><th scope="col">{t('titles')}</th>
          <th scope="col">{t('finals')}</th><th scope="col">{t('awards')}</th></tr></thead>
        <tbody>{result.country_deltas.map(c =>
          <tr key={c.country_code}><td>{c.country_code}</td>
            <td>{c.titles_delta > 0 ? '+' : ''}{c.titles_delta}</td>
            <td>{c.finals_delta > 0 ? '+' : ''}{c.finals_delta}</td>
            <td>{c.awarded_points_delta > 0 ? '+' : ''}{c.awarded_points_delta}</td></tr>)}</tbody>
      </table></div>
    </> : <p>{t('noDelta')}</p>}
    <p className="subtitle">{t('semantics')}</p>
  </article>
}

export function ViewerSignedSeasonComparison({ runId }: { runId: string }): JSX.Element {
  const { language } = useLanguage()
  const t = translator(language)
  const contextQuery = useQuery({
    queryKey: ['viewer-signed-season-context', runId],
    queryFn: () => getViewerOfficialRunContext(runId),
    retry: false,
    refetchOnWindowFocus: true,
    refetchOnMount: 'always'
  })
  const branchId = verifiedSignedSeasonBranch(contextQuery.data, runId)
  return <section aria-label={t('title')}>
    <h3>{t('title')}</h3><p className="subtitle">{t('about')}</p>
    {contextQuery.isPending || contextQuery.isFetching ? <p role="status">{t('resolving')}</p> :
      contextQuery.isError ? <div role="alert"><p>{t('unavailable')}</p>
        <button type="button" onClick={() => void contextQuery.refetch()}>{t('retry')}</button></div> :
      !branchId ? <div role="alert"><p>{t('invalid')}</p>
        <button type="button" onClick={() => void contextQuery.refetch()}>{t('retry')}</button></div> :
      <SignedSeasonsBody key={JSON.stringify([runId, branchId])} runId={runId} branchId={branchId} t={t} />}
  </section>
}
