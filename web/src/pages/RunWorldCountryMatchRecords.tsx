/** Historical-safe national match table; filters are applied by the Saved API before paging. */
import {useEffect,useState} from 'react'
import {useQuery} from '@tanstack/react-query'
import {Link} from 'react-router-dom'
import {getCountrySavedMatchRecords} from '../api/client'
import type {CountryMatchOutcome,CountryMatchResultKind,
  CountrySavedMatchRecords,CountrySavedMatch} from '../api/types'
import {formatApiError} from '../utils/apiErrors'

const PAGE_SIZE=25
type Props={runId:string;branchId:string;countryCode:string
  savedRevisionId:string|null;historical:boolean;cs:boolean}

export function RunWorldCountryMatchRecords({
  runId,branchId,countryCode,savedRevisionId,historical,cs
}:Props):JSX.Element{
  const [season,setSeason]=useState('all')
  const [resultKind,setResultKind]=useState<CountryMatchResultKind>('all')
  const [outcome,setOutcome]=useState<CountryMatchOutcome>('all')
  const [page,setPage]=useState(0)
  const [availableSeasons,setAvailableSeasons]=useState<number[]>([])
  const seasonIndex=season==='all'?null:Number(season)
  const offset=page*PAGE_SIZE
  const enabled=Boolean(runId&&branchId&&countryCode&&savedRevisionId)
  const q=useQuery({
    queryKey:['run-world-country-saved-matches',runId,branchId,countryCode,
      savedRevisionId,seasonIndex,resultKind,outcome,offset],
    queryFn:()=>getCountrySavedMatchRecords(
      runId,branchId,countryCode,savedRevisionId!,
      {seasonIndex,resultKind,outcome,offset,limit:PAGE_SIZE}),
    enabled,retry:false
  })
  const data:CountrySavedMatchRecords|null=q.data?.run_id===runId&&
    q.data.branch_id===branchId&&q.data.saved_revision_id===savedRevisionId&&
    q.data.country_code===countryCode&&q.data.season_index===seasonIndex&&
    q.data.result_kind===resultKind&&q.data.outcome===outcome&&
    q.data.offset===offset&&q.data.limit===PAGE_SIZE?q.data:null
  useEffect(()=>{
    // Season choices must not disappear while a filtered page is loading.
    if(data)setAvailableSeasons(data.available_seasons)
  },[data])
  const fmt=(n:number)=>n.toLocaleString(cs?'cs-CZ':'en-US')
  const profile=(id:string,name:string)=>{
    if(historical)return <>{name} <small>({id})</small></>
    return <Link to={'/admin/runs/'+encodeURIComponent(runId)+'/people/'+encodeURIComponent(id)}>{name}</Link>
  }
  const matchLink=(m:CountrySavedMatch)=>{
    if(historical)return <code>{m.match_id}</code>
    return <Link to={'/admin/runs/'+encodeURIComponent(runId)+'/people/'+
      encodeURIComponent(m.winner_player_id)+'/matches/'+
      encodeURIComponent(m.event_id)+'/'+encodeURIComponent(m.match_id)}>
      {cs?'Zápas':'Match'} {m.match_id}</Link>
  }
  return <section className="section-subtle" aria-label="Country saved match records">
    <h4>{cs?'Zápasové statistiky země':'Country match records'}</h4>
    <p className="status">{cs?
      'Pouze kanonicky publikované zápasy v přesné uložené revizi. Statistiky níže jsou celkové; filtry mění seznam a počet nalezených zápasů.':
      'Only canonical published matches from the exact Saved Revision. Totals below cover the entire revision; filters narrow the list and matching count.'}</p>
    {savedRevisionId
      ? <p className="status">Saved Revision: <code>{savedRevisionId}</code>
          {data&&<> · {cs?'Zdrojová branch':'Origin Branch'}: <code>{data.revision_branch_id}</code></>}</p>
      : <p role="alert">{cs?'Chybí uložená revize; zápasy nelze ověřit.':
        'No Saved Revision; matches cannot be verified.'}</p>}
    <div className="actions" aria-label="Country match filters">
      <label>{cs?'Sezóna':'Season'}{' '}
        <select aria-label="Country match season" value={season}
          onChange={e=>{setSeason(e.target.value);setPage(0)}}>
          <option value="all">{cs?'Všechny sezóny':'All seasons'}</option>
          {availableSeasons.map(index=>
            <option key={index} value={String(index)}>{2000+index}/{2001+index}</option>)}
        </select>
      </label>
      <label>{cs?'Průběh':'Completion'}{' '}
        <select aria-label="Country match completion" value={resultKind}
          onChange={e=>{setResultKind(e.target.value as CountryMatchResultKind);setPage(0)}}>
          <option value="all">{cs?'Vše':'All'}</option>
          <option value="played">{cs?'Odehráno':'Played'}</option>
          <option value="walkover">{cs?'Kontumace':'Walkovers'}</option>
        </select>
      </label>
      <label>{cs?'Výsledek hráče země':'Country player outcome'}{' '}
        <select aria-label="Country match outcome" value={outcome}
          onChange={e=>{setOutcome(e.target.value as CountryMatchOutcome);setPage(0)}}>
          <option value="all">{cs?'Výhry i prohry':'Wins and losses'}</option>
          <option value="win">{cs?'Výhra':'Win'}</option>
          <option value="loss">{cs?'Prohra':'Loss'}</option>
        </select>
      </label>
    </div>
    {enabled&&q.isPending&&<p role="status">{cs?'Načítám ověřené zápasy…':'Loading verified matches…'}</p>}
    {enabled&&q.error&&<p role="alert">{formatApiError(q.error)}</p>}
    {enabled&&q.isSuccess&&!data&&<p role="alert">{cs?
      'Odpověď zápasů nesouhlasí s požadovaným Runem, revizí nebo filtry.':
      'Match response does not match requested Run, revision or filters.'}</p>}
    {data&&<>
      <div className="run-world-metrics" aria-label="Country saved match totals">
        <div><span>{cs?'Odehrané výhry':'Played wins'}</span><strong>{fmt(data.country_played_wins)}</strong></div>
        <div><span>{cs?'Odehrané prohry':'Played losses'}</span><strong>{fmt(data.country_played_losses)}</strong></div>
        <div><span>{cs?'Výhry kontumací':'Walkover wins'}</span><strong>{fmt(data.country_walkover_wins)}</strong></div>
        <div><span>{cs?'Prohry kontumací':'Walkover losses'}</span><strong>{fmt(data.country_walkover_losses)}</strong></div>
        <div><span>{cs?'Odehrané domácí zápasy':'Played hosted matches'}</span>
          <strong>{fmt(data.hosted_played_matches)}</strong></div>
      </div>
      <p role="status">{cs?'Zápasů odpovídajících filtrům':'Matches matching filters'}:
        {' '}<strong>{fmt(data.filtered_match_count)}</strong>
        {' '}· {cs?'Celkem zápasů hráčů země':'Total country player matches'}:
        {' '}{fmt(data.country_match_count)}
      </p>
      {data.matches.length>0
        ? <div className="table-responsive"><table aria-label="Country canonical saved matches">
            <thead><tr>
              <th>{cs?'Sezóna / týden':'Season / week'}</th>
              <th>{cs?'Turnaj / zápas':'Event / match'}</th>
              <th>{cs?'Vítěz':'Winner'}</th><th>{cs?'Poražený':'Loser'}</th>
              <th>{cs?'Skóre':'Score'}</th><th>{cs?'Dokončení':'Completion'}</th>
            </tr></thead>
            <tbody>{data.matches.map(m=><tr key={m.event_id+':'+m.match_id}>
              <td>{m.season} · {m.season_week}</td>
              <td>{m.event_name} <small>({m.host_country})</small>
                <div>{matchLink(m)}</div></td>
              <td>{profile(m.winner_player_id,m.winner_name)} <small>({m.winner_country})</small></td>
              <td>{profile(m.loser_player_id,m.loser_name)} <small>({m.loser_country})</small></td>
              <td>{m.scoreline}</td>
              <td>{m.completion==='walkover'?(cs?'Kontumace':'Walkover'):(cs?'Odehráno':'Played')}</td>
            </tr>)}</tbody>
          </table></div>
        : <p role="status">{cs?'V této revizi nejsou zápasy odpovídající zvoleným filtrům.':
            'No saved matches match these filters in the selected revision.'}</p>}
      <div className="actions" aria-label="Country match pagination">
        <button type="button" disabled={page===0} onClick={()=>setPage(p=>Math.max(0,p-1))}>
          {cs?'← Předchozí':'← Previous'}</button>
        <span>{cs?'Strana':'Page'} {page+1} / {Math.max(1,Math.ceil(data.filtered_match_count/PAGE_SIZE))}</span>
        <button type="button" disabled={!data.has_more} onClick={()=>setPage(p=>p+1)}>
          {cs?'Další →':'Next →'}</button>
      </div>
    </>}
    <p className="status">{cs?
      'BYE se nezapočítávají, kontumace nejsou odehrané výhry. Zápas dvou hráčů země znamená jednu její výhru i prohru.':
      'BYEs are excluded; walkovers are not played wins. A match between two players of this country counts one win and one loss.'}</p>
  </section>
}
