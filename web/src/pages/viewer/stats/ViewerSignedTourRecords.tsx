import { useState, type FormEvent } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'

import { getViewerOfficialRunContext } from '../../../api/client'
import { getViewerSignedTourRecords, type ViewerSignedRecordsFilters } from '../../../api/viewerSignedTourRecords'
import type { TourCareerRecords } from '../../../api/calendarTour'
import { useLanguage, type Language } from '../../../i18n/LanguageContext'
import { viewerCountryProfilePath, viewerPlayerProfilePath } from '../../../viewer/viewerRoutes'
import { verifiedViewerSignedTourRecords, viewerRecordsBranch } from './viewerSignedTourRecords'

const words = {
  title: ['Historické rekordy dokončených sezon', 'Records from completed seasons'],
  about: ['Pouze skutečně potvrzené sezony z uložené Viewer Branch. Rozpracované výsledky se nezobrazují.', 'Only signed seasons of the saved Viewer Branch. Uncommitted results are never shown.'],
  resolving: ['Ověřuji Viewer Branch…', 'Resolving Viewer Branch…'],
  unavailable: ['Záznamy nejsou dostupné. Run nemusí mít uzavřenou sezonu, nebo zdroj není platný.', 'Records are unavailable. This Run may have no signed season, or the source could be invalid.'],
  invalid: ['Odpověď neprošla ověřením Runu, Viewer Branch a historických dat. Nic se nezobrazuje.', 'Run, Viewer Branch or historical evidence failed validation. Nothing is displayed.'],
  loading: ['Načítám historické záznamy…', 'Loading historical records…'],
  retry: ['Znovu načíst (GET)', 'Retry read (GET)'],
  seasonTo: ['Stav k sezoně', 'As of season'],
  from: ['Od sezony', 'From season'],
  country: ['Země ISO-3 (nepovinné)', 'ISO-3 country (optional)'],
  all: ['Všechny země', 'All countries'],
  latest: ['Nejnovější uzavřená', 'Latest closed'],
  apply: ['Zobrazit vybrané rekordy', 'Show selected records'],
  reset: ['Výchozí období', 'Default period'],
  badFilter: ['Vyber uzavřené sezony ve správném pořadí a případně třípísmenný kód země.', 'Select signed seasons in order and, optionally, a three-letter country code.'],
  period: ['Období', 'Period'],
  run: ['Product Run', 'Product Run'],
  branch: ['Viewer Branch', 'Viewer Branch'],
  revision: ['Uložená revize', 'Saved revision'],
  editions: ['Potvrzené turnaje', 'Confirmed tournaments'],
  holders: ['Držitelé rekordu', 'Record holders'],
  leaderboard: ['Žebříček', 'Leaderboard'],
  history: ['Historie držitelů', 'Holder history'],
  noHolders: ['Zatím žádný držitel rekordu.', 'No record holder yet.'],
  noHistory: ['Zatím žádné změny držitelů.', 'No holder changes yet.'],
  noRanking: ['Žádné kladné výsledky.', 'No positive results.'],
  rank: ['Pořadí', 'Rank'],
  entity: ['Hráč nebo země', 'Player or country'],
  metricValue: ['Hodnota', 'Value'],
  season: ['Sezona', 'Season'],
  change: ['Změna', 'Change'],
  total: ['Celkový počet v žebříčku', 'Total ranked'],
  player: ['Hráči', 'Players'],
  countryScope: ['Země', 'Countries'],
  titles: ['Tituly', 'Titles'],
  finals: ['Finále', 'Finals'],
  awarded_points: ['Přidělené body', 'Awarded points'],
  established: ['Nový rekord', 'Established'],
  improved: ['Zlepšení rekordu', 'Improved'],
  tied: ['Vyrovnání / spoludržitelé', 'Tied / co-holders'],
  scopeNote: ['Tato evidence pokrývá tituly, finále a přidělené body v nativní Tour; není úplným katalogem všech rekordů.', 'This covers native Tour titles, finals and awarded points; it is not the complete record catalog.']
} as const

function copy(language: Language) {
  const index = language === 'cs' ? 0 : 1
  return (key: keyof typeof words): string => words[key][index]
}

const initial: ViewerSignedRecordsFilters = { asOfSeason: null, fromSeason: 0, countryCode: null }

function SignedRecordsForBranch({ runId, branchId, language }: {
  runId: string; branchId: string; language: Language
}): JSX.Element {
  const t = copy(language)
  const [seasonDraft, setSeasonDraft] = useState('latest')
  const [startDraft, setStartDraft] = useState('0')
  const [countryDraft, setCountryDraft] = useState('')
  const [filterError, setFilterError] = useState(false)
  const [applied, setApplied] = useState<ViewerSignedRecordsFilters | null>(null)

  const baselineQuery = useQuery({
    queryKey: ['viewer-signed-tour-records', runId, branchId, 'baseline'],
    queryFn: ({ signal }) => getViewerSignedTourRecords(runId, initial, signal),
    retry: false,
    refetchOnMount: 'always',
    refetchOnWindowFocus: true
  })
  const selectedQuery = useQuery({
    queryKey: ['viewer-signed-tour-records', runId, branchId, 'selection',
      applied?.asOfSeason, applied?.fromSeason, applied?.countryCode],
    queryFn: ({ signal }) => getViewerSignedTourRecords(runId, applied ?? initial, signal),
    enabled: applied !== null,
    retry: false,
    refetchOnMount: 'always',
    refetchOnWindowFocus: true
  })

  if (baselineQuery.isPending || baselineQuery.isFetching) return <p role="status" className="status">{t('loading')}</p>
  if (baselineQuery.isError) return <div role="alert">
    <p className="error">{t('unavailable')}</p>
    <button type="button" onClick={() => void baselineQuery.refetch()}>{t('retry')}</button>
  </div>

  const baseline = verifiedViewerSignedTourRecords(baselineQuery.data, runId, branchId, initial)
  if (!baseline) return <div role="alert">
    <p className="error">{t('invalid')}</p>
    <button type="button" onClick={() => void baselineQuery.refetch()}>{t('retry')}</button>
  </div>

  const seasonOptions = baseline.completed_seasons
  const labels = new Map(baseline.source_seasons.map(s => [s.season_index, s.season_label]))
  const target = seasonDraft === 'latest' ? baseline.as_of_season_index : Number(seasonDraft)
  const fromOptions = seasonOptions.filter(s => s <= target)
  const reportQuery = applied ? selectedQuery : baselineQuery
  const filters = applied ?? initial
  const report = reportQuery.isSuccess
    ? verifiedViewerSignedTourRecords(reportQuery.data, runId, branchId, filters)
    : null

  function submit(event: FormEvent<HTMLFormElement>): void {
    event.preventDefault()
    const start = Number(startDraft)
    const country = countryDraft.trim().toUpperCase()
    if (!seasonOptions.includes(target) || !fromOptions.includes(start) ||
        (country.length > 0 && !/^[A-Z]{3}$/.test(country))) {
      setFilterError(true)
      return
    }
    setFilterError(false)
    setApplied({ asOfSeason: target, fromSeason: start, countryCode: country || null })
  }

  function reset(): void {
    setSeasonDraft('latest')
    setStartDraft('0')
    setCountryDraft('')
    setApplied(null)
    setFilterError(false)
  }

  function link(scope: string, id: string, label: string) {
    return <Link to={scope === 'player'
      ? viewerPlayerProfilePath(runId, id)
      : viewerCountryProfilePath(runId, id)}>{label}</Link>
  }

  return <>
    <form onSubmit={submit} aria-label={t('title')}>
      <div>
        <label htmlFor="viewer-records-asof">{t('seasonTo')}</label>{' '}
        <select id="viewer-records-asof" value={seasonDraft} onChange={e => {
          const next = e.target.value
          setSeasonDraft(next)
          const maximum = next === 'latest' ? baseline.as_of_season_index : Number(next)
          if (Number(startDraft) > maximum) setStartDraft(String(seasonOptions[0]))
          setFilterError(false)
        }}>
          <option value="latest">{t('latest')}</option>
          {seasonOptions.map(i => <option value={i} key={i}>{labels.get(i)}</option>)}
        </select>
      </div>
      <div>
        <label htmlFor="viewer-records-from">{t('from')}</label>{' '}
        <select id="viewer-records-from" value={startDraft} onChange={e => {
          setStartDraft(e.target.value); setFilterError(false)
        }}>
          {fromOptions.map(i => <option key={i} value={i}>{labels.get(i)}</option>)}
        </select>
      </div>
      <div>
        <label htmlFor="viewer-records-country">{t('country')}</label>{' '}
        <input id="viewer-records-country" value={countryDraft} maxLength={3}
          placeholder={t('all')} onChange={e => {
            setCountryDraft(e.target.value.toUpperCase()); setFilterError(false)
          }} />
      </div>
      <p>
        <button type="submit">{t('apply')}</button>{' '}
        <button type="button" onClick={reset}>{t('reset')}</button>
      </p>
      {filterError ? <p className="error" role="alert">{t('badFilter')}</p> : null}
    </form>

    {reportQuery.isPending || reportQuery.isFetching ? <p className="status" role="status">{t('loading')}</p> :
      reportQuery.isError ? <div role="alert"><p className="error">{t('unavailable')}</p>
        <button type="button" onClick={() => void reportQuery.refetch()}>{t('retry')}</button></div> :
      !report ? <div role="alert"><p className="error">{t('invalid')}</p>
        <button type="button" onClick={() => void reportQuery.refetch()}>{t('retry')}</button></div> :
      <RecordsReport report={report} runId={runId} link={link} t={t} />
    }
  </>
}

function RecordsReport({ report, runId, link, t }: {
  report: TourCareerRecords; runId: string
  link: (scope: string, id: string, label: string) => JSX.Element
  t: ReturnType<typeof copy>
}): JSX.Element {
  return <>
    <dl className="metadata-list viewer-metadata-list" aria-label={t('title')}>
      <div><dt>{t('run')}</dt><dd>{runId}</dd></div>
      <div><dt>{t('branch')}</dt><dd>{report.branch_id}</dd></div>
      <div><dt>{t('revision')}</dt><dd><code>{report.saved_head_revision_id}</code></dd></div>
      <div><dt>{t('period')}</dt><dd>{report.source_seasons[0].season_label} – {report.source_seasons[report.source_seasons.length - 1].season_label}</dd></div>
      <div><dt>{t('country')}</dt><dd>{report.country_code ?? t('all')}</dd></div>
      <div><dt>{t('editions')}</dt><dd>{report.completed_edition_count}</dd></div>
    </dl>
    {(['player', 'country'] as const).map(scope => (
      <section key={scope} aria-label={t(scope === 'player' ? 'player' : 'countryScope')}>
        <h4>{t(scope === 'player' ? 'player' : 'countryScope')}</h4>
        {report.records.filter(r => r.scope === scope).map(record => (
          <details key={record.record_id}>
            <summary>{t(record.metric)}: <strong>{record.value}</strong> · {t('holders')}: {
              record.holders.length
                ? record.holders.map(h => h.label).join(', ')
                : t('noHolders')
            }</summary>
            <h5>{t('holders')}</h5>
            {record.holders.length ? <p>{record.holders.map((h, i) =>
              <span key={h.entity_id}>{i > 0 ? ', ' : ''}{link(scope, h.entity_id, h.label)}</span>
            )}</p> : <p>{t('noHolders')}</p>}
            <h5>{t('leaderboard')} · {t('total')}: {record.leaderboard_total}</h5>
            {record.leaderboard.length ? <div className="table-wrap">
              <table aria-label={t(scope === 'player' ? 'player' : 'countryScope') + ' – ' + t(record.metric)}>
                <thead><tr><th scope="col">{t('rank')}</th><th scope="col">{t('entity')}</th>
                  <th scope="col">{t('metricValue')}</th></tr></thead>
                <tbody>{record.leaderboard.map(row => <tr key={row.entity_id}>
                  <td>{row.rank}</td><td>{link(scope, row.entity_id, row.label)}</td>
                  <td>{row[record.metric]}</td>
                </tr>)}</tbody>
              </table>
            </div> : <p>{t('noRanking')}</p>}
            <h5>{t('history')}</h5>
            {record.holder_history.length ? <div className="table-wrap">
              <table aria-label={t('history') + ' – ' + t(record.metric) + ' – ' + t(scope === 'player' ? 'player' : 'countryScope')}>
                <thead><tr><th scope="col">{t('season')}</th><th scope="col">{t('metricValue')}</th>
                  <th scope="col">{t('holders')}</th><th scope="col">{t('change')}</th></tr></thead>
                <tbody>{record.holder_history.map(h => <tr key={h.season_index}>
                  <td>{h.season_label}</td><td>{h.record_value}</td><td>{h.holder_labels.join(', ')}</td>
                  <td>{t(h.change)}</td>
                </tr>)}</tbody>
              </table>
            </div> : <p>{t('noHistory')}</p>}
          </details>
        ))}
      </section>
    ))}
    <p className="subtitle">{t('scopeNote')}</p>
  </>
}

export function ViewerSignedTourRecords({ runId }: { runId: string }): JSX.Element {
  const { language } = useLanguage()
  const t = copy(language)
  const context = useQuery({
    queryKey: ['viewer-signed-tour-records-context', runId],
    queryFn: () => getViewerOfficialRunContext(runId),
    retry: false,
    refetchOnWindowFocus: true,
    refetchOnMount: 'always'
  })
  const branchId = viewerRecordsBranch(context.data, runId)

  return <section aria-label={t('title')}>
    <h3>{t('title')}</h3>
    <p className="subtitle">{t('about')}</p>
    {context.isPending || context.isFetching ? <p className="status" role="status">{t('resolving')}</p> :
      context.isError ? <div role="alert"><p className="error">{t('unavailable')}</p>
        <button type="button" onClick={() => void context.refetch()}>{t('retry')}</button></div> :
      !branchId ? <div role="alert"><p className="error">{t('invalid')}</p>
        <button type="button" onClick={() => void context.refetch()}>{t('retry')}</button></div> :
      <SignedRecordsForBranch key={JSON.stringify([runId, branchId])}
        runId={runId} branchId={branchId} language={language} />}
  </section>
}
