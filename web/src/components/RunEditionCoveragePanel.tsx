import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  getRunPackageState, getRunOwnedCalendar, listRunBranches
} from '../api/client'
import { getRunEditionEntryTiming } from '../api/runEditionEntryTimingClient'
import { runCalendarPackageIds } from '../api/runFirstTournament'
import { useLanguage } from '../i18n/LanguageContext'
import {
  inspectRunEditionCoverage, ENTRY_COVERAGE_MAX_EDITIONS,
  type EditionCoverageReport, type EntryCoverageState
} from '../pages/runEditionCoverageAudit'

const copy = {
  cs: {
    title:'Hromadná kontrola Entry přípravy', info:'Pouze čtecí kontrola každé Edition z vybraného Run-owned Calendar Package. Bez přihlášení hráčů, automatické eligibility, potvrzení nebo Save.',
    packages:'Načíst Calendar Packages', choose:'Kalendářový balíček', none:'Vyber Calendar Package',
    inspect:'Prověřit Editions', again:'Prověřit znovu', loading:'Načítám jednotlivé Entry plány…',
    sources:'Ověřuji dostupné Calendar Packages…', notFound:'Žádný Calendar Package není v této Branch dostupný.',
    errors:'Některé informace nelze ověřit. Chybějící data nejsou považována za připravená.',
    rejected:'Zdroj se změnil nebo není důvěryhodný. Zahaj novou kontrolu.',
    summary:'Počet Editions', source:'Zdroje', week:'Týden', edition:'Edition', state:'Stav', blockers:'Blokátory',
    filter:'Filtr stavu', all:'Všechny stavy', search:'Hledat Edition', open:'Otevřít Entry detail',
    no_plan:'Chybí Entry plán', missing_ranking:'Chybí ranking/prerekvizita',
    configuration_ready:'Ranking připraven k potvrzení', bound:'Ranking navázán v Draftu',
    blocked:'Blokováno', unsupported:'Sportovní provedení nepodporováno', unavailable:'Neověřeno',
    complete:'Všechny GET dokončeny', incomplete:'Část GET selhala',
    configured:'Entry plány vytvořeny', notConfigured:'Některé plány nejsou vytvořeny',
    warning:'Jde o kontrolu aktuálního Working Draftu, ne atomický dlouhodobý snapshot ani potvrzení Saved revize. Uložený rankingový zdroj neprokazuje eligibility hráčů, field, draw ani provedení turnaje.',
    max:'Maximálně 200 Editions v jedné kontrole; požadavky běží nejvýše po čtyřech současně.',
    inspectSource:'Ověřená zdrojová verze', noMatches:'Pro tento filtr není žádná Edition.',
    refresh:'Po změně Package, Runu či Branche spusť celou kontrolu znovu.'
  },
  en: {
    title:'Bulk Edition Entry preparation audit', info:'Read-only inspection of every Edition in the selected Run-owned Calendar Package. No player applications, automatic eligibility, confirmation or Save.',
    packages:'Load Calendar Packages', choose:'Calendar Package', none:'Choose Calendar Package',
    inspect:'Inspect Editions', again:'Inspect again', loading:'Reading each Edition Entry plan…',
    sources:'Checking available Calendar Packages…', notFound:'No Calendar Package exists in the selected Branch.',
    errors:'Some evidence could not be verified. Missing data is never considered ready.',
    rejected:'Source changed or cannot be trusted. Start a new audit.',
    summary:'Editions', source:'Sources', week:'Week', edition:'Edition', state:'Status', blockers:'Blockers',
    filter:'Status filter', all:'All statuses', search:'Find Edition', open:'Open Entry detail',
    no_plan:'Entry plan missing', missing_ranking:'Ranking/prerequisite missing',
    configuration_ready:'Ranking ready for explicit confirmation', bound:'Ranking bound in Draft',
    blocked:'Blocked', unsupported:'Sporting execution unsupported', unavailable:'Unverified',
    complete:'All GET requests completed', incomplete:'Some GET requests failed',
    configured:'Entry plans configured', notConfigured:'Some plans missing',
    warning:'This inspects the current Working Draft, not an atomic historical snapshot or confirmed Saved Revision. Ranking availability does not prove player eligibility, field, draw or tournament execution.',
    max:'Maximum 200 Editions per audit, at most four requests concurrently.',
    inspectSource:'Verified source versions', noMatches:'No Editions match this filter.',
    refresh:'After a Package, Run or Branch change, run the whole inspection again.'
  }
} as const

const states: EntryCoverageState[] = [
  'no_plan','missing_ranking','configuration_ready','bound','blocked','unsupported','unavailable'
]

export function RunEditionCoveragePanel({
  runId,branchId,head,weeksPerYear
}: {runId:string;branchId:string;head:string;weeksPerYear:number}): JSX.Element {
  const { language } = useLanguage()
  const t = copy[language]
  const [packages,setPackages] = useState<string[]|null>(null)
  const [packageId,setPackageId] = useState('')
  const [report,setReport] = useState<EditionCoverageReport|null>(null)
  const [error,setError] = useState<string|null>(null)
  const [busy,setBusy] = useState(false)
  const [filter,setFilter] = useState<EntryCoverageState|''>('')
  const [search,setSearch] = useState('')
  const request=useRef(0)
  useEffect(()=>()=>{request.current++},[])
  const loadPackages=async()=>{
    const stamp=++request.current
    setReport(null);setError(null);setBusy(true);setPackages(null);setPackageId('')
    try {
      const v=await getRunPackageState(runId,branchId)
      if (stamp===request.current) setPackages(runCalendarPackageIds(v.state))
    } catch(e) {
      if(stamp===request.current)setError(e instanceof Error?e.message:t.rejected)
    } finally {if(stamp===request.current)setBusy(false)}
  }
  const inspect=async()=>{
    if (!packageId || busy)return
    const stamp=++request.current
    setReport(null);setError(null);setBusy(true)
    try {
      const v=await inspectRunEditionCoverage({
        branches:listRunBranches,
        packageState:getRunPackageState,
        calendar:getRunOwnedCalendar,
        timing:getRunEditionEntryTiming
      },runId,branchId,head,packageId,weeksPerYear)
      if(stamp===request.current)setReport(v)
    } catch(e) {
      if(stamp===request.current)setError(e instanceof Error?e.message:t.rejected)
    } finally {if(stamp===request.current)setBusy(false)}
  }
  const shown=report?.run_id===runId && report.branch_id===branchId
    && report.saved_head_revision_id===head && report.calendar_package_id===packageId?report:null
  const shownRows=shown?.rows.filter(row=>(!filter||row.status===filter)
    &&(!search||row.name.toLocaleLowerCase().includes(search.toLocaleLowerCase())
      ||row.event_id.toLocaleLowerCase().includes(search.toLocaleLowerCase())))??[]
  return <section className="panel" aria-label={t.title}>
    <h3>{t.title}</h3>
    <p className="status">{t.info}</p>
    <p className="status">{t.max}</p>
    <button type="button" disabled={busy} onClick={()=>void loadPackages()}>{t.packages}</button>
    {packages && <>
      {packages.length===0?<p>{t.notFound}</p>:<>
        <label htmlFor="coverage-calendar-package">{t.choose}</label>
        <select id="coverage-calendar-package" disabled={busy} value={packageId} onChange={e=>{
          request.current++;setPackageId(e.target.value);setReport(null);setError(null)
        }}>
          <option value="">{t.none}</option>
          {packages.map(pkg=><option key={pkg} value={pkg}>{pkg}</option>)}
        </select>
        <button type="button" disabled={busy||!packageId} onClick={()=>void inspect()}>
          {shown?t.again:t.inspect}
        </button>
      </>}
    </>}
    {busy && <p role="status">{packages?t.loading:t.sources}</p>}
    {error && <p role="alert" className="error">{t.rejected} {error}</p>}
    {shown && !busy && !error && <>
      <p className="status">{t.warning}</p>
      <p>{t.summary}: <strong>{shown.row_count}</strong> · {shown.complete_reads?t.complete:t.incomplete}
        {' · '}{shown.all_plans_configured?t.configured:t.notConfigured}</p>
      <p className="status">{t.inspectSource}: <code>{shown.saved_head_revision_id}</code>
        {' · '}<code>{shown.package_state_fingerprint}</code>
        {' · '}<code>{shown.calendar_fingerprint}</code></p>
      <ul className="run-home-feed">{states.map(status=><li key={status}>
        {t[status]}: <strong>{shown.counts[status]}</strong>
      </li>)}</ul>
      {!shown.complete_reads && <p role="alert" className="error">{t.errors}</p>}
      <label htmlFor="coverage-filter">{t.filter}</label>
      <select id="coverage-filter" value={filter} onChange={e=>setFilter(e.target.value as EntryCoverageState|'')}>
        <option value="">{t.all}</option>
        {states.map(status=><option key={status} value={status}>{t[status]}</option>)}
      </select>
      <label htmlFor="coverage-search">{t.search}</label>
      <input id="coverage-search" value={search} onChange={e=>setSearch(e.target.value)}/>
      {shownRows.length===0?<p>{t.noMatches}</p>:
        <table><thead><tr><th>{t.week}</th><th>{t.edition}</th><th>{t.state}</th><th>{t.blockers}</th></tr></thead>
          <tbody>{shownRows.map(row=><tr key={row.event_id}>
            <td>W{row.week}</td><td>{row.name}<small><code>{row.event_id}</code></small>
              <Link to={'/admin/runs/'+encodeURIComponent(runId)+'/calendar/'
                +encodeURIComponent(row.event_id)+'?branch='+encodeURIComponent(branchId)
                +'&calendar='+encodeURIComponent(packageId)}>{t.open}</Link>
            </td><td>{t[row.status]}</td>
            <td>{row.error?<span className="error">{row.error}</span>:
              row.blockers.length?<details><summary>{row.blockers.length}</summary><ul>
                {row.blockers.map((b,i)=><li key={b.code+':'+i}><code>{b.code}</code> · {b.detail}</li>)}
              </ul></details>:'—'}</td>
          </tr>)}</tbody></table>}
      <p className="status">{t.refresh}</p>
    </>}
  </section>
}
