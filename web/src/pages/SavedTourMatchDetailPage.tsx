/** Exact historical Run Tour Edition match detail and archived rally replay. */
import {useState} from 'react'
import {useQuery} from '@tanstack/react-query'
import {Link,useParams,useSearchParams} from 'react-router-dom'
import {getSavedTourMatchDetail} from '../api/client'
import {validSavedTourMatchDetail} from '../api/savedTour'
import {useAdminBranch} from '../admin/AdminBranchContext'
import {useAdminTime} from '../admin/AdminTimeContext'
import {useLanguage} from '../i18n/LanguageContext'
import {formatApiError} from '../utils/apiErrors'
import {parseSavedReplayRally} from './savedReplayNavigation'
import {savedSeasonFinalLookupHref} from './savedTourCalendarDiscovery'

const PAGE=25
export function SavedTourMatchDetailPage():JSX.Element{
  const {runId='',eventId='',matchId=''}=useParams()
  const [params]=useSearchParams()
  const {selectedBranch}=useAdminBranch()
  const time=useAdminTime()
  // Key by full immutable scope. A link to another revision cannot reuse a
  // prior match's nonzero rally cursor during its first render.
  const key=JSON.stringify([runId,selectedBranch?.branch_id,params.get('branch'),
    params.get('revision'),params.get('season'),eventId,matchId,time.mode])
  return <HistoricalMatchReplay key={key}/>
}

function HistoricalMatchReplay():JSX.Element{
  const {runId='',eventId='',matchId=''}=useParams()
  const [params]=useSearchParams()
  const {selectedBranch,isLoading,error}=useAdminBranch()
  const time=useAdminTime(),{language}=useLanguage(),cs=language==='cs'
  const branch=selectedBranch?.run_id===runId?selectedBranch.branch_id:null
  const revision=params.get('revision'),explicitBranch=params.get('branch')
  const raw=params.get('season')
  const season=raw!==null&&/^(0|[1-9]\d*)$/.test(raw)?Number(raw):null
  const [index,setIndex]=useState(0)
  const [rallyInput,setRallyInput]=useState('')
  const offset=Math.floor(index/PAGE)*PAGE
  const ready=Boolean(branch&&explicitBranch===branch&&revision&&revision.trim()===revision
    &&season!==null&&season<=49&&eventId&&matchId&&time.mode==='present'
    &&!time.error&&!time.isLoading&&!isLoading&&!error)
  const q=useQuery({
    queryKey:['saved-tour-match-detail',runId,branch,revision,season,eventId,matchId,offset],
    queryFn:()=>getSavedTourMatchDetail(runId,branch!,revision!,season!,eventId,matchId,offset,PAGE),
    enabled:ready,retry:false,
  })
  // Disabling a query does not clear React Query's previous cached data.
  // Never render historical sporting authority outside its verified time/context,
  // nor accept a response belonging to a different immutable revision or page.
  const data=ready&&q.isSuccess&&!q.isFetching&&q.data&&validSavedTourMatchDetail(
    q.data,runId,branch!,revision!,season!,eventId,matchId,offset,PAGE
  )?q.data:null
  const invalid=Boolean(ready&&q.isSuccess&&!q.isFetching&&q.data&&!data)
  const frame=data?.rallies.find(r=>r.rally_index===index+1)
  const target=parseSavedReplayRally(rallyInput,data?.total_rallies??0)
  // Player profile is current-HEAD-only. Never substitute it for a prior Saved match.
  const sameHead=Boolean(data&&revision&&selectedBranch?.run_id===runId
    &&selectedBranch?.saved_head_revision_id===revision)
  const participant=(id:string)=>sameHead?
    <Link to={'/admin/runs/'+encodeURIComponent(runId)+'/people/'+
      encodeURIComponent(id)+'?tab=career'}>{id}</Link>:id
  const finalLookup=(id:string)=>savedSeasonFinalLookupHref(runId,branch!,revision!,season!,id,params)
  const parentParams=new URLSearchParams(params)
  // Preserve the actual originating Edition section, including Draw / groups.
  // Results is only the safe fallback for an absent/invalid section marker.
  const requestedTab=parentParams.get('tab')
  const tab=['overview','entries','draw','schedule','results','settings'].includes(requestedTab??'')
    ?requestedTab!:'results'
  parentParams.set('tab',tab)
  const back='/admin/runs/'+encodeURIComponent(runId)+'/tour/calendar/'
    +encodeURIComponent(eventId)+'?'+parentParams.toString()
  return <section className="panel">
    <Link to={back} aria-label={tab==='draw'?(cs?'Zpět na pavouk edice':'Back to Edition draw'):
      cs?'Zpět na výsledky edice':'Back to Edition results'}>
      ← {tab==='draw'?(cs?'Zpět na pavouk edice':'Back to Edition draw'):
        cs?'Zpět na výsledky edice':'Back to Edition results'}</Link>
    <div className="page-intro"><p className="eyebrow">RUN → TOUR → EDITION → MATCH</p>
      <h2>{cs?'Historický detail zápasu':'Historical match detail'}</h2>
      <p>{cs?'Pouze výsledek a případný archiv výměn z přesné Saved Revision.':
        'Only the result and any archived rally log from the exact Saved Revision.'}</p>
    </div>
    <p className="status">Run: <code>{runId}</code> · Branch: <code>{branch??'—'}</code>
      {' · '}Saved Revision: <code>{revision??'—'}</code>
      {' · '}{cs?'Sezona':'Season'}: {season??'—'}</p>
    {!ready&&!isLoading&&!time.isLoading&&<p role="alert">{error||time.error||
      (time.mode==='checkpoint'?(cs?'Checkpoint není bezpečně mapovaný na Saved Revision.':
        'Checkpoint is not bound to a proven Saved Revision.'):
        (cs?'Chybí přesný Run, Branch, Saved Revision nebo sezona.':
          'Exact Run, Branch, Saved Revision or season is missing.'))}</p>}
    {ready&&(q.isPending||q.isFetching)&&<p role="status">{cs?'Načítám ověřený zápas…':'Loading canonical match…'}</p>}
    {ready&&q.error&&<p role="alert">{formatApiError(q.error)}</p>}
    <button type="button" disabled={!ready||q.isFetching}
      onClick={()=>{void q.refetch()}}>{cs?'Obnovit zápas / archiv':'Retry match / archive read'}</button>
    {invalid&&<p role="alert">{cs?
      'Archivovaný zápas neodpovídá vybrané Run/Branch/revizi nebo stránce výměn.':
      'Archived match does not match the selected Run/Branch/revision or rally page.'}</p>}
    {data&&<><div className="run-home-status-block">
      <p>{cs?'Turnaj':'Edition'}: <code>{eventId}</code> · {cs?'Zápas':'Match'}: <code>{matchId}</code></p>
      <h3>{participant(data.match.winner_player_id)} – {participant(data.match.loser_player_id!)}</h3>
      <p>{data.match.draw_type==='main'?(cs?'Hlavní část':'Main'):data.match.draw_type==='qualification'?(cs?'Kvalifikace':'Qualification'):data.match.draw_type==='group'?(cs?'Skupina':'Group'):data.match.draw_type} · {cs?'Kolo':'Round'} {data.match.round_number}
        {' · '}{cs?'Pozice':'Position'} {data.match.bracket_position}
        {' · '}{cs?'Výsledek':'Result'}: <strong>{data.match.scoreline}</strong></p>
      <p>{cs?'Vítěz':'Winner'}: <strong>{data.match.winner_player_id}</strong>
        {' · '}{cs?'Zdrojová Branch revize':'Revision source Branch'}:
        {' '}<code>{data.revision_branch_id}</code></p>
      <p>{cs?'Doložená finálová umístění v této sezoně, pokud existují':
        'Published final finishes in this season, if any'}:
        {' '}<Link to={finalLookup(data.match.winner_player_id)}
          aria-label={(cs?'Dohledat publikovaná finále hráče ':'Find published finals for ')+data.match.winner_player_id}>
          {data.match.winner_player_id}</Link>
        {' · '}<Link to={finalLookup(data.match.loser_player_id!)}
          aria-label={(cs?'Dohledat publikovaná finále hráče ':'Find published finals for ')+data.match.loser_player_id}>
          {data.match.loser_player_id}</Link></p>
    </div>
    <h3>{cs?'Archivovaný průběh výměn':'Archived rally replay'}</h3>
    {data.replay_status==='unavailable'&&<p role="status">{cs?
      'Ověřený archiv výměn pro tuto uloženou revizi neexistuje. Výsledek je doložen, průběh nevytváříme.':
      'No verified rally archive exists in this Saved Revision. The result is real; no replay is fabricated.'}</p>}
    {data.replay_status==='available'&&<>
      <p className="status">{cs?'Archivovaných výměn':'Archived rallies'}: {data.total_rallies}
        {' · '}{data.player_a_id} (A) – {data.player_b_id} (B)</p>
      {frame?<div className="run-home-status-block">
        <p><strong>{cs?'Výměna':'Rally'} {frame.rally_index}/{data.total_rallies}</strong>
          {' · '}{cs?'Set':'Game'} {frame.set_number}</p>
        <p>{frame.score_a_before} : {frame.score_b_before} → <strong>
          {frame.score_a_after} : {frame.score_b_after}</strong></p>
        <p>{cs?'Stav setů':'Games'}: {frame.sets_a_after} : {frame.sets_b_after}</p>
        <p>{cs?'Podává':'Server'}: {frame.server_player_id}
          {' · '}{cs?'Vítěz výměny':'Rally winner'}: {frame.winner_player_id??'—'}</p>
        {frame.match_complete&&<p role="status">{cs?'Konec zápasu':'Match completed'}</p>}
      </div>:<p role="status">{cs?'Tato výměna není v načtené stránce.':
        'This rally is absent from the loaded archive page.'}</p>}
      <div className="grid">
        <button type="button" disabled={q.isFetching||!frame||index===0}
          onClick={()=>setIndex(0)}>{cs?'První výměna':'First rally'}</button>
        <button type="button" disabled={q.isFetching||!frame||index===0}
          onClick={()=>setIndex(v=>Math.max(0,v-1))}>
          {cs?'← Předchozí výměna':'← Previous rally'}</button>
        <button type="button" disabled={q.isFetching||!frame||index+1>=data.total_rallies}
          onClick={()=>setIndex(v=>Math.min(data.total_rallies-1,v+1))}>
          {cs?'Další výměna →':'Next rally →'}</button>
        <button type="button" disabled={q.isFetching||!frame||index+1>=data.total_rallies}
          onClick={()=>setIndex(data.total_rallies-1)}>{cs?'Poslední výměna':'Last rally'}</button>
      </div>
      <form className="grid" onSubmit={event=>{
        event.preventDefault()
        if(frame&&target!==null){
          setIndex(target-1)
          setRallyInput('')
        }
      }}>
        <label>{cs?'Přejít na výměnu':'Go to rally'}
          <input type="number" inputMode="numeric" min={1} max={data.total_rallies} step={1}
            aria-label={cs?'Číslo archivované výměny':'Archived rally number'}
            value={rallyInput} onChange={event=>setRallyInput(event.target.value)}/></label>
        <button type="submit" disabled={q.isFetching||!frame||target===null}>
          {cs?'Přejít':'Jump to rally'}</button>
      </form>
      <p className="status">{cs?'Přehrání jen čte archiv, simulaci znovu neprovádí.':
        'The replay reads archived events only; it never reruns the simulation.'}</p>
    </>}
    </>}
    <Link to={back}>← {cs?'Zpět na edici':'Back to Edition'}</Link>
  </section>
}
