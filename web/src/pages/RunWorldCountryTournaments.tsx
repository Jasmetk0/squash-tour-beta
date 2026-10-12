import {Link} from 'react-router-dom'
import {calendarSeasonIndex} from './runWorldCountryTournaments'
import type {CountryTournamentEdition,CountryTournaments} from './runWorldCountryTournaments'
type Props={
  runId:string;branchId:string;countryCode:string;sourceRevision:string|null;historical:boolean
  currentSeason:number|null;currentWeek:number|null;model:CountryTournaments|null
  loading:boolean;error:string|null;cs:boolean
}
export function RunWorldCountryTournaments({runId,branchId,countryCode,sourceRevision,historical,
  currentSeason,currentWeek,model,loading,error,cs}:Props):JSX.Element{
  const duplicatePrefix='Saved Calendar contains duplicate tournament event identity: '
  const duplicateId=error?.startsWith(duplicatePrefix)?error.slice(duplicatePrefix.length):null
  const now=historical?null:calendarSeasonIndex(currentSeason)
  const grouped=new Map<number,CountryTournamentEdition[]>()
  for(const e of model?.editions??[])grouped.set(e.seasonIndex,[...(grouped.get(e.seasonIndex)??[]),e])
  const sorted=[...grouped.keys()].sort((a,b)=>b-a)
  const ordered=now===null?sorted:[now,...sorted.filter(n=>n>now),...sorted.filter(n=>n<now)]
  const season=(n:number)=>String(2000+n)+'/'+String(2001+n)
  const statuses:Record<CountryTournamentEdition['status'],string>=cs?
    {planned:'Plánováno',scheduled:'Naplánováno',active:'Probíhá',completed:'Označeno jako dokončené',cancelled:'Zrušeno'}:
    {planned:'Planned',scheduled:'Scheduled',active:'Active',completed:'Marked completed',cancelled:'Cancelled'}
  return <section className="section-subtle" aria-label="Country Run-owned tournaments">
    <h4>{cs?'Turnaje pořádané zemí':'Tournaments hosted by country'} ({countryCode})</h4>
    <p className="status">{cs?'Neměnný zdroj Saved Calendar':'Immutable Saved Calendar source'}:
      {' '}<code>{sourceRevision??'—'}</code>
      {model&&<> · <code>{model.fingerprint.slice(0,14)}…</code></>}</p>
    {historical&&<p role="status">{cs?
      'Historická revize: neotevíráme současný detail turnaje.':
      'Historical revision: present-day event details are not linked.'}</p>}
    {loading&&<p role="status">{cs?'Načítám uložený kalendář…':'Loading Saved Calendar…'}</p>}
    {error&&<p role="alert">{duplicateId!==null
      ?(cs?'Nejednoznačný uložený kalendář: více balíčků používá stejné ID turnaje: ':
        'Ambiguous Saved Calendar: multiple packages reuse the tournament event ID: ')+duplicateId
      :error}</p>}
    {!loading&&!error&&!model&&<p role="alert">{cs?
      'Uložený kalendář není dostupný. Neuložená data se nepoužijí.':
      'Saved Calendar is unavailable. Unsaved data is not substituted.'}</p>}
    {model&&model.calendarCount===0&&<p role="status">{cs?
      'Tato uložená revize nemá žádný Calendar Package.':
      'This saved revision has no Calendar Package.'}</p>}
    {model&&model.calendarCount>0&&!model.editions.length&&<p role="status">{cs?
      'V uložených kalendářích nejsou žádné edice pořádané touto zemí.':
      'No editions hosted by this country are present in saved calendars.'}</p>}
    {model&&now===null&&model.editions.length>0&&<p className="status">{cs?
      'Aktuální sezóna není určena; edice jsou řazeny podle uloženého kalendáře.':
      'Present season is not positioned; editions are grouped by saved calendar seasons.'}</p>}
    {model&&now!==null&&grouped.has(now)&&<a href="#run-country-current-season">{cs?
      'Přejít na současnou sezónu':'Jump to current season'}</a>}
    {model&&ordered.filter(n=>grouped.has(n)).map(n=><section key={n}
      id={n===now?'run-country-current-season':undefined}>
      <h5>{season(n)} {n===now?(cs?'· současná sezóna':'· current season'):
        now!==null&&n>now?(cs?'· uložený budoucí plán':'· saved future plan'):
        now!==null?(cs?'· minulá sezóna':'· past season'):''}</h5>
      <div className="table-responsive"><table aria-label={'Country tournament editions '+season(n)}>
        <thead><tr><th>{cs?'Týden':'Week'}</th><th>{cs?'Edice':'Edition'}</th>
          <th>{cs?'Město':'City'}</th><th>{cs?'Kategorie':'Category'}</th>
          <th>{cs?'Stav kalendáře':'Calendar status'}</th></tr></thead>
        <tbody>{grouped.get(n)!.map(e=>{
          // Existing canonical detail validates only 2000/2001, and only a present Branch.
          const linked=!historical&&n===now&&n===0
          const url='/admin/runs/'+encodeURIComponent(runId)+'/calendar/'+encodeURIComponent(e.eventId)+
            '?branch='+encodeURIComponent(branchId)+'&calendar='+encodeURIComponent(e.packageId)
          return <tr key={e.key}><td>{e.week}{n===now&&currentWeek===e.week?' · now':''}</td>
            <td>{linked?<Link to={url}>{e.name}</Link>:e.name} <small>· {e.eventId}</small></td>
            <td>{e.city??'—'} ({e.hostCountry})</td>
            <td>{e.category??'—'}{e.tourLevel?' · '+e.tourLevel:''}</td>
            <td>{statuses[e.status]}</td></tr>
        })}</tbody>
      </table></div>
    </section>)}
    {model&&model.editions.length>0&&<p className="status">{cs?
      'Stav kalendáře není důkazem výsledku ani vítěze. Detail je dostupný jen pro podporovanou současnou sezónu.':
      'Calendar status is not evidence of results or winners. Live details are linked only for the supported current season.'}</p>}
  </section>
}
