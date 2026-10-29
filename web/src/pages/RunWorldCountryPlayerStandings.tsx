/** Evidence-only player standings over the complete exact Saved Revision. */
import {useState} from 'react'
import {useQuery} from '@tanstack/react-query'
import {Link} from 'react-router-dom'
import {getCountryPlayerStandings} from '../api/client'
import {formatApiError} from '../utils/apiErrors'
import {COUNTRY_STANDINGS_PAGE_SIZE as PAGE_SIZE,parseStandingPage,standingsPages,
  validCountryStandingPage} from './countrySavedStandingsNavigation'

type Props={runId:string;branchId:string;countryCode:string;
  savedRevisionId:string|null;historical:boolean;cs:boolean}

export function RunWorldCountryPlayerStandings({
  runId,branchId,countryCode,savedRevisionId,historical,cs
}:Props):JSX.Element{
  const sourceKey=JSON.stringify([runId,branchId,countryCode,savedRevisionId])
  const [pageSelection,setPageSelection]=useState({sourceKey,page:0})
  const [jumpInput,setJumpInput]=useState({sourceKey,value:'1'})
  // Never reuse a page from another country, Branch or Saved Revision.
  const page=pageSelection.sourceKey===sourceKey?pageSelection.page:0
  const offset=page*PAGE_SIZE
  const jump=jumpInput.sourceKey===sourceKey?jumpInput.value:'1'
  const enabled=Boolean(runId&&branchId&&countryCode&&savedRevisionId)
  const query=useQuery({
    queryKey:['country-player-standings',runId,branchId,countryCode,savedRevisionId,offset],
    queryFn:()=>getCountryPlayerStandings(
      runId,branchId,countryCode,savedRevisionId!,offset,PAGE_SIZE),
    enabled,retry:false
  })
  const result=query.isSuccess&&!query.isFetching&&savedRevisionId&&
    validCountryStandingPage(query.data,{
      runId,branchId,countryCode,revision:savedRevisionId,offset,
    })?query.data:null
  const pages=result?standingsPages(result.total_players):0
  const outOfRange=Boolean(result&&page>0&&offset>=result.total_players)
  const move=(target:number)=>{
    setPageSelection({sourceKey,page:target})
    setJumpInput({sourceKey,value:String(target+1)})
  }
  const targetPage=parseStandingPage(jump,pages)
  const format=(n:number)=>n.toLocaleString(cs?'cs-CZ':'en-US')
  return <section className="section-subtle" aria-label="Country canonical player standings">
    <h4>{cs?'Nejúspěšnější hráči země':'Country player standings'}</h4>
    <p className="status">{cs?
      'Pořadí: tituly, účasti ve finále, odehrané výhry, nejméně odehraných proher, ID. Jde o statistické pořadí, ne oficiální žebříček ani body.':
      'Ordered by titles, final appearances, played wins, fewest played losses, and ID. This is an evidence-based list, not Official Ranking points.'}</p>
    {!savedRevisionId&&<p role="alert">{cs?
      'Žádná uložená revize — pořadí nelze ověřit.':
      'No Saved Revision — player standings are unavailable.'}</p>}
    {enabled&&(query.isPending||query.isFetching)&&<p role="status">{cs?'Načítám ověřené pořadí…':
      'Loading verified player standings…'}</p>}
    {enabled&&query.error&&<p role="alert">{formatApiError(query.error)}</p>}
    {enabled&&query.isSuccess&&!query.isFetching&&!result&&<p role="alert">{cs?
      'Zdroj pořadí neodpovídá požadované uložené revizi.':
      'Leaderboard evidence differs from the requested Saved Revision.'}</p>}
    {result&&<>
      <p role="status">{cs?'Hráči s publikovaným výsledkem nebo zápasem':
        'Players with a published finish or actual match'}:
        {' '}<strong>{format(result.total_players)}</strong>
        {' '}· Saved Revision: <code>{result.saved_revision_id}</code>
        {' '}· {cs?'Původní branch':'Origin Branch'}: <code>{result.revision_branch_id}</code>
      </p>
      {outOfRange&&<p role="alert">{cs?
        'Požadovaná stránka pořadí neexistuje v této uložené revizi.':
        'Requested standings page does not exist in this Saved Revision.'}{' '}
        <button type="button" onClick={()=>move(0)}>{cs?'První platná stránka':'First valid page'}</button>
        {' '}<button type="button" onClick={()=>move(Math.max(0,pages-1))}>
          {cs?'Poslední platná stránka':'Last valid page'}</button>
      </p>}
      {!outOfRange&&result.players.length>0?
        <div className="table-responsive">
          <table aria-label="Country player standings table">
            <thead><tr>
              <th>#</th><th>{cs?'Hráč':'Player'}</th>
              <th>{cs?'Tituly':'Titles'}</th>
              <th>{cs?'Finále':'Finals'}</th>
              <th>{cs?'Druhá místa':'Runner-up'}</th>
              <th>{cs?'Odehrané V':'Played W'}</th>
              <th>{cs?'Odehrané P':'Played L'}</th>
              <th>{cs?'Kontumace V/P':'W/O W/L'}</th>
            </tr></thead>
            <tbody>{result.players.map(player=><tr key={player.player_id}>
              <td>{format(player.position)}</td>
              <td>{historical?<>{player.player_name} <small>· {player.player_id}</small></>:
                <Link to={'/admin/runs/'+encodeURIComponent(runId)+'/people/'+
                  encodeURIComponent(player.player_id)}>{player.player_name}</Link>}</td>
              <td>{format(player.titles)}</td>
              <td>{format(player.final_appearances)}</td>
              <td>{format(player.runner_up_finishes)}</td>
              <td>{format(player.played_wins)}</td>
              <td>{format(player.played_losses)}</td>
              <td>{format(player.walkover_wins)} / {format(player.walkover_losses)}</td>
            </tr>)}</tbody>
          </table>
        </div>:!outOfRange&&<p role="status">{cs?
          'V této revizi zatím žádný hráč nemá publikovaný turnajový výsledek ani zápas.':
          'No player has a published tournament finish or match in this revision.'}</p>}
      <div className="actions" aria-label="Country player standings pagination">
        <button type="button" disabled={page===0||query.isFetching} onClick={()=>move(0)}>
          {cs?'První':'First'}</button>
        <button type="button" disabled={page===0||query.isFetching}
          onClick={()=>move(Math.max(0,page-1))}>
          {cs?'← Předchozí':'← Previous'}</button>
        <span aria-live="polite">{cs?'Strana':'Page'} {pages===0?0:page+1} / {pages}</span>
        <button type="button" disabled={!result.has_more||query.isFetching||outOfRange}
          onClick={()=>move(page+1)}>
          {cs?'Další →':'Next →'}</button>
        <button type="button" disabled={pages===0||page>=pages-1||query.isFetching}
          onClick={()=>move(pages-1)}>{cs?'Poslední':'Last'}</button>
        <label>{cs?'Přejít na stránku':'Go to page'}{' '}
          <input aria-label="Country standings page number" inputMode="numeric"
            value={jump} disabled={pages===0||query.isFetching}
            onChange={e=>setJumpInput({sourceKey,value:e.target.value})}
            style={{width:'5rem'}}/>
        </label>
        <button type="button" disabled={targetPage===null||targetPage===page||outOfRange||query.isFetching}
          onClick={()=>{if(targetPage!==null)move(targetPage)}}>
          {cs?'Přejít':'Go'}</button>
      </div>
    </>}
    <p className="status">{cs?
      'BYE nejsou zápasy; kontumace nejsou odehrané výhry. Historická revize nikdy neodkazuje na současné profily.':
      'BYEs are not matches; walkovers are not played wins. Historical revisions never link to present player profiles.'}</p>
  </section>
}
