/** Country period match RECORDS. Exact Saved Revision, full-server aggregate, paged evidence. */
import {useState} from 'react'
import {useQuery} from '@tanstack/react-query'
import {Link,useSearchParams} from 'react-router-dom'
import {getCountryMatchRecordHighlights} from '../api/client'
import type {CountryMatchRecordKey,CountryMatchRecordHighlights,CountrySavedMatch} from '../api/types'
import type {CountryPeriodRequest} from './runCountryRecordPeriods'
import {sportLabel} from './runCountryRecordPeriods'
import {calendarSeasonIndex} from './runWorldCountryTournaments'
import {formatApiError} from '../utils/apiErrors'
import {COUNTRY_EVIDENCE_PAGE_SIZE as PAGE,validCountryMatchEvidence} from './countryMatchEvidenceValidation'

type Props={runId:string;branchId:string;countryCode:string;revision:string
  request:CountryPeriodRequest;cs:boolean;selected:CountryMatchRecordKey|null
  onSelect:(key:CountryMatchRecordKey)=>void;onClose:()=>void}
const categories:CountryMatchRecordKey[]=['played_wins','played_matches']
const heading=(key:CountryMatchRecordKey,cs:boolean)=>key==='played_wins'?
  cs?'Nejvíce odehraných výher':'Most played wins':
  cs?'Nejvíce odehraných zápasů':'Most played matches'

/** A changed source/interval/record starts at page zero before any new GET. */
export function RunWorldCountryMatchHighlights(props:Props):JSX.Element {
  const {runId,branchId,countryCode,revision,request,selected}=props
  return <CountryEvidenceBrowser key={JSON.stringify([runId,branchId,countryCode,revision,
    request.from.season,request.from.week,request.to.season,request.to.week,selected])} {...props}/>
}
function CountryEvidenceBrowser({
  runId,branchId,countryCode,revision,request,cs,selected,onSelect,onClose
}:Props):JSX.Element{
  const [params]=useSearchParams()
  const [page,setPage]=useState(0)
  const options={
    fromSeason:request.from.season,fromWeek:request.from.week,
    toSeason:request.to.season,toWeek:request.to.week,
  }
  const query=useQuery({
    queryKey:['country-period-match-records',runId,branchId,countryCode,revision,
      ...Object.values(options)],
    queryFn:()=>getCountryMatchRecordHighlights(
      runId,branchId,countryCode,revision,{...options,recordKey:null,offset:0,limit:PAGE}),
    retry:false,
  })
  const detail=useQuery({
    queryKey:['country-period-match-record-detail',runId,branchId,countryCode,revision,
      ...Object.values(options),selected,page],
    queryFn:()=>getCountryMatchRecordHighlights(runId,branchId,countryCode,revision,
      {...options,recordKey:selected,offset:page*PAGE,limit:PAGE}),
    enabled:selected!==null&&query.isSuccess&&!query.isFetching&&
      validCountryMatchEvidence(query.data,{
        runId,branchId,countryCode,revision,
        fromSeason:options.fromSeason,fromWeek:options.fromWeek,
        toSeason:options.toSeason,toWeek:options.toWeek,selected:null,offset:0}),
    retry:false,
  })
  const common={runId,branchId,countryCode,revision,
    fromSeason:options.fromSeason,fromWeek:options.fromWeek,
    toSeason:options.toSeason,toWeek:options.toWeek}
  const data=query.isSuccess&&!query.isFetching&&
    validCountryMatchEvidence(query.data,{...common,selected:null,offset:0})?query.data:null
  const candidate=selected!==null&&detail.isSuccess&&!detail.isFetching&&
    validCountryMatchEvidence(detail.data,{...common,selected,offset:page*PAGE})?detail.data:null
  // A different aggregate on two pages is not the same immutable sporting evidence.
  const info=candidate&&data&&JSON.stringify(candidate.records)===JSON.stringify(data.records)&&
    candidate.period_country_matches===data.period_country_matches&&
    candidate.period_played_matches===data.period_played_matches&&
    candidate.period_walkovers===data.period_walkovers&&
    candidate.revision_branch_id===data.revision_branch_id?candidate:null
  const outOfRange=Boolean(info&&page>0&&page*PAGE>=info.evidence_count)
  const number=(v:number)=>v.toLocaleString(cs?'cs-CZ':'en-US')
  const sourceLink=(m:CountrySavedMatch)=>{
    const season=calendarSeasonIndex(m.season)
    if(season===null)return null
    const origin=new URLSearchParams(params)
    origin.set('tab','records')
    origin.set('revision',revision)
    const fromCountry='/admin/runs/'+encodeURIComponent(runId)+'/world/countries/'+
      encodeURIComponent(countryCode)+'?'+origin.toString()+'#country-match-record-'+selected
    const q=new URLSearchParams({branch:branchId,revision,season:String(season),
      tab:'results',fromCountry})
    return '/admin/runs/'+encodeURIComponent(runId)+'/tour/calendar/'+
      encodeURIComponent(m.event_id)+'/matches/'+encodeURIComponent(m.match_id)+'?'+q.toString()
  }
  return <section className="section-subtle" aria-label="Country period match highlights">
    <h5>{cs?'Zápasové rekordy v období':'Match records in period'}</h5>
    <p className="status">{sportLabel(request.from)} → {sportLabel(request.to)}
      {' · '}{cs?'Pouze skutečně odehrané kanonické zápasy. Kontumace a BYE se nezapočítávají.':
        'Only canonical played matches. Walkovers and BYEs do not count.'}</p>
    {(query.isPending||query.isFetching)&&<p role="status">{cs?'Počítám zápasové rekordy z uložených výsledků…':
      'Aggregating saved match record evidence…'}</p>}
    {query.error&&<p role="alert">{formatApiError(query.error)}</p>}
    {query.isSuccess&&!query.isFetching&&!data&&<p role="alert">{cs?'Nesouhlasí rozsah uloženého zdroje.':
      'Saved match record identity mismatch.'}</p>}
    {data&&<>
      <p role="status">{cs?'Ověřené zápasy hráčů země v období':'Country player matches in period'}:
        {' '}{number(data.period_country_matches)}
        {' · '}{cs?'Odehrané':'Played'}: {number(data.period_played_matches)}
        {' · '}{cs?'Kontumace':'Walkovers'}: {number(data.period_walkovers)}
      </p>
      <div className="table-responsive"><table aria-label="Country period match record leaders">
        <thead><tr><th>{cs?'Rekord':'Record'}</th><th>{cs?'Hodnota':'Value'}</th>
          <th>{cs?'Všichni držitelé':'All tied holders'}</th><th>{cs?'Důkazy':'Evidence'}</th></tr></thead>
        <tbody>{categories.map(key=>{
          const r=data.records.find(rec=>rec.key===key)
          return <tr key={key} id={'country-match-record-'+key}>
            <td>{heading(key,cs)}</td><td>{number(r?.value??0)}</td>
            <td>{r?.holders.length?r.holders.map(h=>h.player_name).join(', '):'—'}</td>
            <td><button type="button" onClick={()=>{setPage(0);onSelect(key)}}>
              {cs?'Otevřít důkazy':'Open evidence'}</button></td>
          </tr>
        })}</tbody>
      </table></div>
    </>}
    {selected&&<aside className="section-subtle country-record-detail-panel"
      aria-label="Country match record detail">
      <div className="actions"><h5>{heading(selected,cs)}</h5>
        <button type="button" onClick={onClose}>{cs?'Zavřít detail':'Close detail'}</button>
      </div>
      <p>{sportLabel(request.from)} → {sportLabel(request.to)}
        {' · '}Saved Revision: <code>{revision}</code></p>
      {(detail.isPending||detail.isFetching)&&<p role="status">{cs?'Načítám doložené zápasy…':
        'Loading canonical match evidence…'}</p>}
      {detail.error&&<p role="alert">{formatApiError(detail.error)}</p>}
      {detail.isSuccess&&!detail.isFetching&&!info&&<p role="alert">{cs?'Neplatný detail historického zdroje.':
        'Historical match evidence detail mismatch.'}</p>}
      {info&&<>
        <p>{cs?'Hodnota':'Value'}: <strong>
          {number(info.records.find(x=>x.key===selected)?.value??0)}</strong>
          {' · '}{cs?'Všichni shodní držitelé':'All tied holders'}:
          {' '}{info.records.find(x=>x.key===selected)?.holders.map(
            h=>h.player_name+' ('+h.player_id+')').join(', ')||'—'}</p>
        <p className="status">{cs?'Původní branch revize':'Revision origin Branch'}:
          {' '}<code>{info.revision_branch_id}</code>
          {' · '}{cs?'Doložené zápasy':'Evidenced matches'}: {number(info.evidence_count)}</p>
        {outOfRange&&<p role="alert">{cs?'Požadovaná stránka důkazů neexistuje.':
          'Requested evidence page does not exist.'}{' '}
          <button type="button" onClick={()=>setPage(0)}>{cs?'První platná stránka':'First valid page'}</button>
          {' '}<button type="button" onClick={()=>setPage(Math.max(0,Math.ceil(info.evidence_count/PAGE)-1))}>
            {cs?'Poslední platná stránka':'Last valid page'}</button></p>}
        {!outOfRange&&info.evidence.length?
          <div className="table-responsive"><table aria-label="Country match record source matches">
            <thead><tr><th>{cs?'Sezona / týden':'Season / week'}</th>
              <th>{cs?'Turnaj a zápas':'Edition and match'}</th>
              <th>{cs?'Výsledek':'Result'}</th><th>{cs?'Skóre':'Score'}</th></tr></thead>
            <tbody>{info.evidence.map(m=><tr key={m.event_id+':'+m.match_id}>
              <td>{m.season} · {m.season_week}</td>
              <td>{sourceLink(m)?<Link to={sourceLink(m)!}>{m.event_name} · {m.match_id}</Link>:
                <span>{m.event_name} · {m.match_id}</span>}
                {' '}<small>({m.draw_type}, {m.round_number})</small></td>
              <td>{m.winner_name} ({m.winner_country}) – {m.loser_name} ({m.loser_country})</td>
              <td>{m.scoreline}</td>
            </tr>)}</tbody>
          </table></div>:
          !outOfRange&&<p role="status">{cs?'Žádné doložené zápasy.':'No evidenced matches.'}</p>}
        <div className="actions" aria-label="Country match record evidence pagination">
          <button type="button" disabled={page===0||detail.isFetching||outOfRange} onClick={()=>setPage(p=>Math.max(0,p-1))}>
            {cs?'← Předchozí':'← Previous'}</button>
          <span>{cs?'Strana':'Page'} {info.evidence_count===0?0:page+1} /
            {' '}{Math.ceil(info.evidence_count/PAGE)}</span>
          <button type="button" disabled={!info.has_more||detail.isFetching||outOfRange} onClick={()=>setPage(p=>p+1)}>
            {cs?'Další →':'Next →'}</button>
        </div>
      </>}
    </aside>}
  </section>
}
