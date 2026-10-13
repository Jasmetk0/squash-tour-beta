import {useQuery} from '@tanstack/react-query'
import {useState} from 'react'
import {Link,useParams,useSearchParams} from 'react-router-dom'
import {getSavedTourEdition} from '../api/client'
import {validSavedTourEdition} from '../api/savedTour'
import {useAdminBranch} from '../admin/AdminBranchContext'
import {useAdminTime} from '../admin/AdminTimeContext'
import {useLanguage} from '../i18n/LanguageContext'
import {formatApiError} from '../utils/apiErrors'

type Tab='overview'|'entries'|'draw'|'schedule'|'results'|'settings'
const tabs:Tab[]=['overview','entries','draw','schedule','results','settings']
export function SavedTourEditionPage():JSX.Element {
  const {runId='',eventId=''}=useParams()
  const [params,setParams]=useSearchParams()
  const {selectedBranch,isLoading,error:branchError}=useAdminBranch()
  const time=useAdminTime(),{language}=useLanguage(),cs=language==='cs'
  const branch=selectedBranch?.run_id===runId?selectedBranch.branch_id:null
  const explicitBranch=params.get('branch'),revision=params.get('revision')
  const raw=params.get('season')
  const season=raw!==null&&/^(0|[1-9]\d*)$/.test(raw)?Number(raw):null
  const goodSeason=season!==null&&season<50
  const eligible=Boolean(runId&&eventId&&branch&&revision&&revision.trim()===revision
    &&explicitBranch===branch&&goodSeason&&time.mode==='present'
    &&!isLoading&&!branchError&&!time.isLoading&&!time.error)
  const query=useQuery({queryKey:['saved-tour-edition',runId,branch,revision,season,eventId],
    queryFn:()=>getSavedTourEdition(runId,branch!,revision!,season!,eventId),
    enabled:eligible,retry:false})
  const model=eligible&&query.data&&validSavedTourEdition(query.data,runId,branch!,revision!,season!,eventId)
    ?query.data:null
  const tab=tabs.includes(params.get('tab') as Tab)?params.get('tab') as Tab:'overview'
  const [phase,setPhase]=useState<'main'|'qualification'>('main')
  const changeTab=(next:Tab)=>{
    const p=new URLSearchParams(params);p.set('tab',next);setParams(p)
  }
  const back=new URLSearchParams(params);back.delete('tab')
  const returnTo='/admin/runs/'+encodeURIComponent(runId)+'/tour/calendar?'+back.toString()
  const labels=cs?['Přehled','Přihlášky a účastníci','Pavouk / skupiny','Program a zápasy','Výsledky','Nastavení']:
    ['Overview','Entries & participants','Draw / groups','Schedule & matches','Results','Settings']
  const e=model?.edition,result=model?.published_result
  const matches=result?.matches??[]
  const main=matches.filter(m=>m.draw_type!=='qualification')
  const qualification=matches.filter(m=>m.draw_type==='qualification')
  const matchRow=(m:typeof matches[number])=><tr key={m.match_id}><td>{m.round_number}</td>
    <td>{m.winner_player_id}</td><td>{m.loser_player_id??'—'}</td><td>{m.scoreline}</td></tr>
  const matchTable=(group:typeof matches)=>group.length?
    <div className="table-responsive"><table><thead><tr>
      <th>{cs?'Kolo':'Round'}</th><th>{cs?'Vítěz':'Winner'}</th>
      <th>{cs?'Poražený':'Loser'}</th><th>{cs?'Skóre':'Score'}</th>
    </tr></thead><tbody>{group.map(matchRow)}</tbody></table></div>:
    <p>{cs?'Nejsou dostupné doložené zápasy.':'No evidenced matches available.'}</p>
  const statusMissing=cs?'Tento zdroj neobsahuje úplnou historickou autoritu pro tento oddíl.':
    'A complete historical authority for this section is unavailable in this source.'
  return <section className="panel">
    <Link to={returnTo}>← {cs?'Zpět na kalendář':'Back to calendar'}</Link>
    <div className="page-intro"><p className="eyebrow">RUN → TOUR → EDITION</p>
      <h2>{e?.event_name??(cs?'Detail edice':'Edition detail')}</h2>
      <p className="status">Run: <code>{runId}</code> · Branch: <code>{branch??'—'}</code>
        {' · '}Saved Revision: <code>{revision??'—'}</code></p>
    </div>
    {!eligible&&!isLoading&&!time.isLoading&&<p role="alert">{branchError||time.error||
      (time.mode==='checkpoint'?(cs?'Checkpoint nemá ověřenou vazbu na Saved Revision.':
        'Checkpoint is not mapped to a Saved Revision.'):
        (cs?'Chybí přesná Run/Branch/revize/sezona v odkazu.':
        'The link must name the exact Run/Branch/revision/season.'))}</p>}
    {query.isPending&&eligible&&<p role="status">{cs?'Načítám uloženou edici…':'Loading saved Edition…'}</p>}
    {query.error&&<p role="alert">{formatApiError(query.error)}</p>}
    {eligible&&query.data&&!model&&<p role="alert">{cs?'Neplatná nebo zastaralá identita Edition.':
      'Invalid or stale Edition identity.'}</p>}
    {e&&<><p className="status">{e.season} · {cs?'Týden':'Week'} {e.season_week} · {e.host_country}
      {' · '}{cs?'Kanonicky publikovaný výsledek':'Canonical published result'}: {e.result_published?'✓':'—'}</p>
      <nav className="saved-tour-edition-tabs" aria-label="Edition sections">
        {tabs.map((name,i)=><button key={name} type="button" aria-current={tab===name?'page':undefined}
          className={tab===name?'active':''} onClick={()=>changeTab(name)}>{labels[i]}</button>)}
      </nav>
      {tab==='overview'&&<section><h3>{labels[0]}</h3>
        <p>{e.category} · {e.tour_level??'—'} · {e.host_city??'—'} ({e.host_country})</p>
        <p>{cs?'Stav autoritativního lifecycle: není dostupný. Stav kalendáře není důkaz výsledku.':
          'Authoritative lifecycle status: unavailable. A calendar label is not proof of results.'}</p>
        {result&&<p>{cs?'Vítěz':'Champion'}: {result.champion_player_id}
          {' · '}{cs?'Finalista':'Finalist'}: {result.finalist_player_id}</p>}
        {!result&&<p>{cs?'V této revizi není publikován kanonický výsledek.':
          'No canonical result was published in this revision.'}</p>}
      </section>}
      {tab==='entries'&&<section><h3>{labels[1]}</h3>
        <p>{statusMissing}</p>
        {result&&<><p>{cs?'Doložení účastníci z publikovaného výsledku (nikoli historické přihlášky):':
          'Evidenced participants from published results (not an Entry Field snapshot):'}</p>
          <ul>{result.players.map(p=><li key={p.player_id}>{p.player_id} · {p.reached_stage}</li>)}</ul></>}
      </section>}
      {tab==='draw'&&<section><h3>{labels[2]}</h3>
        <p>{statusMissing} {cs?'Dostupné jsou pouze publikované zápasy.':
          'Only published matches are shown.'}</p>
        <div className="grid"><button type="button" aria-pressed={phase==='main'}
          onClick={()=>setPhase('main')}>{cs?'Hlavní část':'Main'}</button>
          <button type="button" aria-pressed={phase==='qualification'}
          onClick={()=>setPhase('qualification')}>{cs?'Kvalifikace':'Qualification'}</button></div>
        {matchTable(phase==='main'?main:qualification)}
      </section>}
      {tab==='schedule'&&<section><h3>{labels[3]}</h3>
        <p>{statusMissing} {cs?'Časy zápasů se z výsledků neodvozují.':
          'Match start times are never inferred from results.'}</p>
        {result&&<><a href="#saved-schedule-main">{cs?'Hlavní část':'Main'}</a>
          {' · '}<a href="#saved-schedule-qualification">{cs?'Kvalifikace':'Qualification'}</a>
          <section id="saved-schedule-main"><h4>{cs?'Hlavní část':'Main'}</h4>{matchTable(main)}</section>
          <section id="saved-schedule-qualification"><h4>{cs?'Kvalifikace':'Qualification'}</h4>{matchTable(qualification)}</section></>}
      </section>}
      {tab==='results'&&<section><h3>{labels[4]}</h3>
        {!result?<p>{cs?'Kanonické výsledky nejsou v této revizi publikovány.':
          'Canonical results are not published in this revision.'}</p>:<>
          <a href="#saved-results-main">{cs?'Hlavní část':'Main'}</a>
          {' · '}<a href="#saved-results-qualification">{cs?'Kvalifikace':'Qualification'}</a>
          <section id="saved-results-main"><h4>{cs?'Hlavní část':'Main'}</h4>{matchTable(main)}</section>
          <section id="saved-results-qualification"><h4>{cs?'Kvalifikace':'Qualification'}</h4>{matchTable(qualification)}</section>
        </>}
      </section>}
      {tab==='settings'&&<section><h3>{labels[5]}</h3>
        <p>{cs?'Uložené parametry edice (nikoli neuložený editor):':
          'Saved Edition parameters (not the live settings editor):'}</p>
        <dl><dt>{cs?'Hlavní pavouk':'Main draw size'}</dt><dd>{e.main_draw_size}</dd>
          <dt>{cs?'Kvalifikace':'Qualification draw size'}</dt><dd>{e.qualification_draw_size}</dd>
          <dt>{cs?'Nasazení':'Seeds'}</dt><dd>{e.seeds_count}</dd>
          <dt>{cs?'Místa kvalifikantů':'Qualifier slots'}</dt><dd>{e.qualifier_spots}</dd>
          <dt>Wild cards</dt><dd>{e.wild_cards}</dd><dt>BYE</dt><dd>{e.byes}</dd>
        </dl></section>}
    </>}
  </section>
}
