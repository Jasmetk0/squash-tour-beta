import {useQuery} from '@tanstack/react-query'
import {Link} from 'react-router-dom'
import {getRunCountryRecords} from '../api/client'
import type {RunCountryRecordResult,RunCountryRecords} from '../api/types'
import {formatApiError} from '../utils/apiErrors'

type Props={runId:string;branchId:string;countryCode:string;savedRevisionId:string|null
  historical:boolean;cs:boolean}
export function RunWorldCountryRecords({
  runId,branchId,countryCode,savedRevisionId,historical,cs
}:Props):JSX.Element{
  const query=useQuery({
    queryKey:['run-world-country-records',runId,branchId,countryCode,savedRevisionId],
    queryFn:()=>getRunCountryRecords(runId,branchId,countryCode,savedRevisionId!),
    enabled:Boolean(runId&&branchId&&countryCode&&savedRevisionId),
    retry:false
  })
  const data:RunCountryRecords|null=query.data?.run_id===runId&&
    query.data.branch_id===branchId&&query.data.country_code===countryCode&&
    query.data.saved_revision_id===savedRevisionId?query.data:null
  const format=(number:number)=>new Intl.NumberFormat(cs?'cs-CZ':'en-US').format(number)
  const athlete=(item:RunCountryRecordResult,id:string,name:string)=>{
    if(historical)return <>{name} <code>{id}</code></>
    return <Link to={'/admin/runs/'+encodeURIComponent(runId)+'/people/'+encodeURIComponent(id)}>{name}</Link>
  }
  const rows=(records:RunCountryRecordResult[],label:string)=>
    <div className="table-responsive"><table aria-label={label}>
      <thead><tr><th>{cs?'Sezóna / týden':'Season / week'}</th>
        <th>{cs?'Turnaj':'Tournament'}</th>
        <th>{cs?'Vítěz':'Champion'}</th><th>{cs?'Finalista':'Finalist'}</th>
        <th>{cs?'Pořadatel':'Host'}</th></tr></thead>
      <tbody>{records.map(item=><tr key={item.season+':'+item.event_id}>
        <td>{item.season} · {item.season_week}</td>
        <td>{item.event_name} <small>· {item.event_id}</small></td>
        <td>{athlete(item,item.champion_player_id,item.champion_name)}
          {' '}<small>({item.champion_country})</small></td>
        <td>{athlete(item,item.finalist_player_id,item.finalist_name)}
          {' '}<small>({item.finalist_country})</small></td>
        <td>{item.host_country}</td>
      </tr>)}</tbody>
    </table></div>
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
    {!savedRevisionId&&<p role="alert">{cs?
      'Žádná autoritativní uložená revize — rekordy nelze ověřit.':
      'No authoritative Saved Revision — records are unavailable.'}</p>}
    {savedRevisionId&&query.isPending&&<p role="status">{cs?'Načítám publikované výsledky…':
      'Loading published results…'}</p>}
    {query.error&&<p role="alert">{formatApiError(query.error)}</p>}
    {query.isSuccess&&!data&&<p role="alert">{cs?'Nesouhlasí zdroj rekordů.':'Records scope mismatch.'}</p>}
    {data&&<>
      <div className="run-world-metrics" aria-label="Country verified record totals">
        <div><span>{cs?'Tituly hráčů země':'Country player titles'}</span>
          <strong>{format(data.country_titles)}</strong></div>
        <div><span>{cs?'Druhá místa ve finále':'Country runner-up finishes'}</span>
          <strong>{format(data.country_finalists)}</strong></div>
        <div><span>{cs?'Publikované domácí výsledky':'Published hosted results'}</span>
          <strong>{format(data.hosted_published_results)}</strong></div>
      </div>
      <p className="status">{cs?'Rozsah: ':'Coverage: '}{format(data.published_result_count)}
        {cs?' publikovaných výsledků v této uložené revizi. Nejde o úplnou historickou statistiku mimo tuto revizi.':
          ' published results in this Saved Revision, not a claim about unrelated history.'}</p>
      <h5>{cs?'Výsledky hráčů této země':'Results involving players of this country'}</h5>
      {data.player_results.length?rows(data.player_results,'Country player published results'):
        <p role="status">{cs?'Zatím žádné doložené finále nebo titul.':
          'No verified final appearance or title in this saved data.'}</p>}
      <h5>{cs?'Publikované výsledky turnajů pořádaných v zemi':'Published tournament results hosted here'}</h5>
      {data.hosted_results.length?rows(data.hosted_results,'Country hosted published results'):
        <p role="status">{cs?'Zatím žádný publikovaný domácí výsledek.':
          'No published hosted result in this Saved Revision.'}</p>}
      <p className="status">{cs?
        'Neodehrané turnaje, stav „completed“ v kalendáři ani odhadované výsledky se nezapočítávají.':
        'Unplayed events, calendar-only completed statuses and hypothetical results are not counted.'}</p>
    </>}
  </section>
}
