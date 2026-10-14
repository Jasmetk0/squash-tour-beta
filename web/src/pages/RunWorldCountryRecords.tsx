import {useState} from 'react'
import {useQuery} from '@tanstack/react-query'
import {Link,useSearchParams} from 'react-router-dom'
import {getRunCountryRecords} from '../api/client'
import {RunWorldCountryMatchRecords} from './RunWorldCountryMatchRecords'
import {RunWorldCountryPlayerStandings} from './RunWorldCountryPlayerStandings'
import {calendarSeasonIndex} from './runWorldCountryTournaments'
import {lastEvidencedCountryPoint,parsePeriod,projectCountryPeriod,selectedSportPoint,sportLabel} from './runCountryRecordPeriods'
import type {CountryPeriodMode,CountryPeriodStats,CountryRecordLeader} from './runCountryRecordPeriods'
import type {RunCountryRecordResult,RunCountryRecords} from '../api/types'
import {formatApiError} from '../utils/apiErrors'

type Props={runId:string;branchId:string;countryCode:string;savedRevisionId:string|null
  historical:boolean;cs:boolean;presentSeason:number|null;presentWeek:number|null}
type Detail='titles'|'finals'|'hosted'|null

export function RunWorldCountryRecords({
  runId,branchId,countryCode,savedRevisionId,historical,cs,presentSeason,presentWeek
}:Props):JSX.Element{
  const [params,setParams]=useSearchParams()
  const [detail,setDetail]=useState<Detail>(null)
  const displayedThrough=selectedSportPoint(presentSeason,presentWeek)
  const query=useQuery({
    queryKey:['run-world-country-records',runId,branchId,countryCode,savedRevisionId],
    queryFn:()=>getRunCountryRecords(runId,branchId,countryCode,savedRevisionId!),
    enabled:Boolean(runId&&branchId&&countryCode&&savedRevisionId),
    retry:false
  })
  const data:RunCountryRecords|null=query.data?.run_id===runId&&
    query.data.branch_id===branchId&&query.data.country_code===countryCode&&
    query.data.saved_revision_id===savedRevisionId?query.data:null
  let records:CountryPeriodStats|null=null
  let periodError:string|null=null
  let lastEvidence:ReturnType<typeof lastEvidencedCountryPoint>=null
  if(data){
    try{lastEvidence=lastEvidencedCountryPoint(data)}
    catch(e){periodError=formatApiError(e)}
  }
  // An authentic published result supplies a narrower evidence ceiling only
  // when this Branch lacks an authoritative simulation clock. Never call it a clock.
  const through=displayedThrough??lastEvidence
  const request=through&&!periodError?parsePeriod(params,through):null
  if(data&&request){
    try{records=projectCountryPeriod(data,countryCode,request)}
    catch(e){periodError=formatApiError(e)}
  }
  const format=(number:number)=>new Intl.NumberFormat(cs?'cs-CZ':'en-US').format(number)
  const set=(key:string,value:string)=>{
    const next=new URLSearchParams(params)
    next.set(key,value)
    setParams(next,{replace:true})
  }
  const athlete=(id:string,name:string)=>{
    if(historical)return <>{name} <code>{id}</code></>
    return <Link to={'/admin/runs/'+encodeURIComponent(runId)+'/people/'+encodeURIComponent(id)}>{name}</Link>
  }
  const editionHref=(item:RunCountryRecordResult)=>{
    const index=calendarSeasonIndex(item.season)
    if(index===null||!savedRevisionId)return null
    // Pin the original Country view to the same immutable sporting source; the
    // selected Branch remains the URL authority for shared pre-fork ancestors.
    const origin=new URLSearchParams(params)
    origin.set('tab','records');origin.set('revision',savedRevisionId)
    const anchor='country-record-'+(detail??'titles')
    const returnTo='/admin/runs/'+encodeURIComponent(runId)+'/world/countries/'+
      encodeURIComponent(countryCode)+'?'+origin.toString()+'#'+anchor
    const q=new URLSearchParams({branch:branchId,revision:savedRevisionId,
      season:String(index),fromCountry:returnTo})
    return '/admin/runs/'+encodeURIComponent(runId)+'/tour/calendar/'+
      encodeURIComponent(item.event_id)+'?'+q.toString()
  }
  const evidence=(items:RunCountryRecordResult[],name:string)=>
    <div className="table-responsive"><table aria-label={name}>
      <thead><tr><th>{cs?'Sezona / týden':'Season / week'}</th>
        <th>{cs?'Turnaj':'Edition'}</th><th>{cs?'Vítěz':'Champion'}</th>
        <th>{cs?'Finalista':'Finalist'}</th><th>{cs?'Pořadatel':'Host'}</th></tr></thead>
      <tbody>{items.map(item=><tr key={item.season+':'+item.event_id}>
        <td>{item.season} · {item.season_week}</td>
        <td>{editionHref(item)?<Link to={editionHref(item)!}>{item.event_name}</Link>:item.event_name}
          {' '}<small>· {item.event_id}</small></td>
        <td>{athlete(item.champion_player_id,item.champion_name)}
          {' '}<small>({item.champion_country})</small></td>
        <td>{athlete(item.finalist_player_id,item.finalist_name)}
          {' '}<small>({item.finalist_country})</small></td>
        <td>{item.host_country}</td>
      </tr>)}</tbody></table></div>
  const leaders=(holders:CountryRecordLeader[])=>holders.length?
    holders.map(x=>x.name).join(', '):'—'
  const selectedTitle=detail==='titles'?(cs?'Nejvíce titulů':'Most titles'):
    detail==='finals'?(cs?'Nejvíce finálových účastí':'Most final appearances'):
    cs?'Pořádané turnaje s výsledkem':'Hosted published Editions'
  const top=detail==='titles'?records?.champions:records?.finalists
  const sourceRows=detail==='titles'?records?.athletes.filter(
    x=>x.champion_country===countryCode&&top?.some(l=>l.id===x.champion_player_id)):
    detail==='finals'?records?.athletes.filter(x=>
      top?.some(l=>l.id===x.champion_player_id&&x.champion_country===countryCode||
        l.id===x.finalist_player_id&&x.finalist_country===countryCode)):
      records?.hosted
  const value=detail==='titles'?(top?.[0]?.count??0):
    detail==='finals'?(top?.[0]?.count??0):records?.hosted.length??0

  return <section className="section-subtle" aria-label="Country published records">
    <h4>{cs?'Rekordy země — publikované výsledky':'Country records — published results'}</h4>
    <p className="status">{cs?'Zdroj: přesná Saved Revision':'Source: exact Saved Revision'}:
      {' '}<code>{savedRevisionId??'—'}</code>
      {data&&<> · {cs?'Původní branch':'Origin Branch'}: <code>{data.revision_branch_id}</code></>}</p>
    <p className="status">{cs?'Národnost hráčů a země pořadatelství jsou oddělené.':
      'Player nationality and host country are separate facts.'}</p>
    {historical&&<p role="status">{cs?
      'Historická revize: odkazy na dnešní profily hráčů jsou vypnuté.':
      'Historical revision: current player profile links are disabled.'}</p>}
    <div className="actions" aria-label="Country record period filters">
      <label>{cs?'Období':'Period'}{' '}
        <select aria-label="Country record period" value={params.get('rperiod')??'whole'}
          onChange={e=>{set('rperiod',e.target.value);setDetail(null)}}>
          <option value="whole">{cs?'Celá historie':'Whole history'}</option>
          <option value="season">{cs?'Sezona':'Season'}</option>
          <option value="custom">{cs?'Vlastní období':'Custom period'}</option>
        </select></label>
      {params.get('rperiod')==='season'&&<label>{cs?'Sportovní sezona':'Sport season'}{' '}
        <select aria-label="Country record season"
          value={params.get('rseason')??String(through?.season??0)}
          onChange={e=>{set('rseason',e.target.value);setDetail(null)}}>
          {Array.from({length:(through?.season??-1)+1},(_,i)=>
            <option key={i} value={i}>{2000+i}/{2001+i}</option>)}
        </select></label>}
      {params.get('rperiod')==='custom'&&<div className="actions">
        {(['rfromSeason','rfromWeek','rtoSeason','rtoWeek'] as const).map(key=>{
          const isWeek=key.endsWith('Week'),isFrom=key.startsWith('rfrom')
          const fallback=isFrom?(isWeek?1:0):(isWeek?through?.week:through?.season)
          return <label key={key}>{isFrom?(cs?'Od':'From'):(cs?'Do':'To')}
            {' · '}{isWeek?(cs?'týden':'week'):(cs?'sezona':'season')}{' '}
            <select aria-label={'Country record '+key}
              value={params.get(key)??String(fallback??0)}
              onChange={e=>{set(key,e.target.value);setDetail(null)}}>
              {Array.from({length:isWeek?61:50},(_,i)=>isWeek?i+1:i).map(n=>
                <option key={n} value={n}>{isWeek?n:(2000+n)+'/'+(2001+n)}</option>)}
            </select></label>
        })}</div>}
    </div>
    {!displayedThrough&&lastEvidence&&<p role="status">{cs?
      'Simulační čas není dostupný. Rozsah je omezen nejpozdějším doloženým publikovaným výsledkem této Saved Revision, nikoli odhadovaným časem Branch.':
      'Simulation clock is unavailable. This view is bounded by the latest canonical published result in this Saved Revision, NOT a guessed Branch simulation point.'}</p>}
    {!through&&!query.isPending&&<p role="alert">{cs?
      'Simulační čas ani doložený čas výsledku nejsou dostupné. Rok geografických dat jej nenahrazuje.':
      'Neither a simulation point nor a dated published result is available. Country data year is not a sporting time bound.'}</p>}
    {through&&!request&&<p role="alert">{cs?
      'Neplatný nebo budoucí interval sportovní historie. Upravte hranice období.':
      'Invalid or future sporting history interval. Adjust period boundaries.'}</p>}
    {request&&<p className="status" aria-label="Country sporting record interval">
      {cs?'Sportovní období':'Sporting period'}: {sportLabel(request.from)} → {sportLabel(request.to)}
      {' · '}{displayedThrough?
         (cs?'Horní mez zobrazené simulace':'Displayed simulation upper bound'):
         (cs?'Nejpozdější doložený výsledek':'Latest evidenced published result')}:
      {' '}{sportLabel(through!)}</p>}
    {!savedRevisionId&&<p role="alert">{cs?
      'Žádná autoritativní uložená revize — rekordy nelze ověřit.':
      'No authoritative Saved Revision — records are unavailable.'}</p>}
    {savedRevisionId&&query.isPending&&<p role="status">{cs?'Načítám publikované výsledky…':
      'Loading published results…'}</p>}
    {query.error&&<p role="alert">{formatApiError(query.error)}</p>}
    {query.isSuccess&&!data&&<p role="alert">{cs?'Nesouhlasí zdroj rekordů.':'Records scope mismatch.'}</p>}
    {periodError&&<p role="alert">{periodError}</p>}
    {records&&<section aria-label="Country period tournament achievements">
      <h5>{cs?'Turnajové úspěchy v období':'Tournament achievements in period'}</h5>
      <div className="run-world-metrics" aria-label="Country verified record totals">
        <div><span>{cs?'Tituly hráčů země':'Country player titles'}</span>
          <strong>{format(records.titles)}</strong></div>
        <div><span>{cs?'Druhá místa ve finále':'Country runner-up finishes'}</span>
          <strong>{format(records.runnerUps)}</strong></div>
        <div><span>{cs?'Publikované domácí výsledky':'Published hosted results'}</span>
          <strong>{format(records.hosted.length)}</strong></div>
      </div>
      <div className="table-responsive"><table aria-label="Country thematic records">
        <thead><tr><th>{cs?'Rekord':'Record'}</th><th>{cs?'Hodnota':'Value'}</th>
          <th>{cs?'Držitelé':'Holders'}</th><th>{cs?'Detail':'Detail'}</th></tr></thead>
        <tbody>
          <tr id="country-record-titles"><td>{cs?'Nejvíce titulů':'Most titles'}</td>
            <td>{records.champions[0]?.count??0}</td><td>{leaders(records.champions)}</td>
            <td><button type="button" onClick={()=>setDetail('titles')}>{cs?'Podklady':'Evidence'}</button></td></tr>
          <tr id="country-record-finals"><td>{cs?'Nejvíce finálových účastí':'Most final appearances'}</td>
            <td>{records.finalists[0]?.count??0}</td><td>{leaders(records.finalists)}</td>
            <td><button type="button" onClick={()=>setDetail('finals')}>{cs?'Podklady':'Evidence'}</button></td></tr>
          <tr id="country-record-hosted"><td>{cs?'Publikované domácí turnaje':'Published hosted Editions'}</td>
            <td>{records.hosted.length}</td><td>{countryCode}</td>
            <td><button type="button" onClick={()=>setDetail('hosted')}>{cs?'Podklady':'Evidence'}</button></td></tr>
        </tbody></table></div>
      {detail&&<aside className="section-subtle country-record-detail-panel" aria-label="Country record detail">
        <div className="actions"><h5>{selectedTitle}</h5>
          <button type="button" onClick={()=>setDetail(null)}>{cs?'Zavřít detail':'Close detail'}</button>
        </div>
        <p>{cs?'Hodnota':'Value'}: <strong>{format(value)}</strong>
          {' · '}{sportLabel(records.from)} → {sportLabel(records.to)}</p>
        {detail!=='hosted'&&<p>{cs?'Všichni shodní držitelé':'All tied holders'}:
          {' '}{top?.length?top.map(x=>x.name+' ('+x.id+')').join(', '):'—'}</p>}
        <p className="status">{cs?
          'Pouze autoritativní publikované výsledky v přesné revizi, žádný Official Ranking ani domyšlené zápasy.':
          'Only canonical published results from this exact revision, not Official Ranking or inferred matches.'}</p>
        {sourceRows?.length?evidence(sourceRows,'Country record source Editions'):
          <p role="status">{cs?'Pro tento rekord nejsou doložené turnaje.':
            'No evidenced source Editions for this record.'}</p>}
      </aside>}
      <h5>{cs?'Výsledky hráčů této země':'Results involving players of this country'}</h5>
      {records.athletes.length?evidence(records.athletes,'Country player published results'):
        <p role="status">{cs?'Zatím žádné doložené finále nebo titul v období.':
          'No verified final appearance or title in this period.'}</p>}
      <h5>{cs?'Publikované turnaje pořádané v zemi':'Published tournament results hosted here'}</h5>
      {records.hosted.length?evidence(records.hosted,'Country hosted published results'):
        <p role="status">{cs?'Zatím žádný publikovaný domácí výsledek v období.':
          'No published hosted result in this period.'}</p>}
      <p className="status">{cs?
        'Neodehrané turnaje, stav „completed“ v kalendáři ani odhadované výsledky se nezapočítávají.':
        'Unplayed editions, calendar-only completed statuses and hypothetical results are excluded.'}</p>
    </section>}
    <h5>{cs?'Samostatné celoživotní statistiky (vlastní filtry)':'Separate lifetime statistics (own filters)'}</h5>
    <p className="status">{cs?
      'Žebříček hráčů a zápasové statistiky níže mají vlastní celoživotní rozsah a zatím se neřídí výše vybraným obdobím. Nejde o Official Ranking.':
      'Player standings and match records below retain independent lifetime scope and filters; the period selector above does not constrain them. This is not Official Ranking.'}</p>
    <RunWorldCountryPlayerStandings
      key={['players',runId,branchId,countryCode,savedRevisionId??'none'].join(':')}
      runId={runId} branchId={branchId} countryCode={countryCode}
      savedRevisionId={savedRevisionId} historical={historical} cs={cs}/>
    <RunWorldCountryMatchRecords
      key={[runId,branchId,countryCode,savedRevisionId??'none'].join(':')}
      runId={runId} branchId={branchId} countryCode={countryCode}
      savedRevisionId={savedRevisionId} historical={historical} cs={cs}/>
  </section>
}
