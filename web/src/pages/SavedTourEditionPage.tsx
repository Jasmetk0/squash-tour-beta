import {useQuery} from '@tanstack/react-query'
import {useState} from 'react'
import {Link,useParams,useSearchParams} from 'react-router-dom'
import {getSavedTourEdition} from '../api/client'
import {validSavedTourEdition} from '../api/savedTour'
import {useAdminBranch} from '../admin/AdminBranchContext'
import {useAdminTime} from '../admin/AdminTimeContext'
import {useLanguage} from '../i18n/LanguageContext'
import {formatApiError} from '../utils/apiErrors'
import type {SavedTourDrawBracket,SavedTourScheduledMatch} from '../api/savedTour'

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
  const entry=model?.entry_field,draw=model?.draw
  const schedule=model?.match_schedule
  const groupSchedule=model?.group_schedule
  const groupStandings=model?.group_standings
  const pendingTieDecisions=model?.pending_group_tie_decisions??[]
  const plannedMain=schedule?.slots.filter(slot=>slot.draw_phase!=='qualification')??[]
  const plannedQualification=schedule?.slots.filter(slot=>slot.draw_phase==='qualification')??[]
  const matches=result?.matches??[]
  const main=matches.filter(m=>m.draw_type!=='qualification')
  const qualification=matches.filter(m=>m.draw_type==='qualification')
  const matchHref=(matchId:string,sourceTab:'schedule'|'results')=>{
    const q=new URLSearchParams(params)
    q.set('tab',sourceTab)
    return '/admin/runs/'+encodeURIComponent(runId)+'/tour/calendar/'
      +encodeURIComponent(eventId)+'/matches/'+encodeURIComponent(matchId)+'?'+q.toString()
  }
  const matchRow=(m:typeof matches[number])=><tr key={m.match_id}><td>{m.round_number}</td>
    <td>{m.winner_player_id}</td><td>{m.loser_player_id??'—'}</td>
    <td><span>{m.scoreline}</span>{m.loser_player_id&&<>
      {' · '}<Link to={matchHref(m.match_id,tab==='schedule'?'schedule':'results')}>
        {cs?'Detail zápasu':'Match detail'}</Link>
    </>}</td></tr>
  const matchTable=(group:typeof matches)=>group.length?
    <div className="table-responsive"><table><thead><tr>
      <th>{cs?'Kolo':'Round'}</th><th>{cs?'Vítěz':'Winner'}</th>
      <th>{cs?'Poražený':'Loser'}</th><th>{cs?'Skóre':'Score'}</th>
    </tr></thead><tbody>{group.map(matchRow)}</tbody></table></div>:
    <p>{cs?'Nejsou dostupné doložené zápasy.':'No evidenced matches available.'}</p>
  const scheduledTable=(slots:SavedTourScheduledMatch[])=>slots.length?
    <div className="table-responsive"><table aria-label="Saved Match Day order">
      <thead><tr><th>{cs?'Den':'Match Day'}</th><th>{cs?'Pořadí':'Order'}</th>
        <th>{cs?'Globální slot':'Global slot'}</th><th>{cs?'Fáze':'Phase'}</th>
        <th>{cs?'Kolo':'Round'}</th><th>{cs?'Zápas':'Match ID'}</th>
        <th>{cs?'Doložený výsledek':'Published result'}</th></tr></thead>
      <tbody>{slots.map(slot=>{
        const published=slot.match_id?matches.find(m=>m.match_id===slot.match_id):undefined
        return <tr key={slot.global_slot_ordinal}>
          <td>{slot.match_day_ordinal}</td><td>{slot.match_order}</td>
          <td>{slot.global_slot_ordinal}</td><td>{slot.draw_phase}</td><td>{slot.round_number}</td>
          <td>{slot.match_id&&published?.loser_player_id?
            <Link to={matchHref(slot.match_id,'schedule')}>{slot.match_id}</Link>:
            (slot.match_id??(cs?'Plán zápasu není uložen':'No saved match plan'))}</td>
          <td>{published?published.winner_player_id+' · '+published.scoreline:'—'}</td>
        </tr>
      })}</tbody></table></div>:
    <p>{cs?'Pro tuto část nejsou uložené zápasové sloty.':
      'No saved Match Day slots for this phase.'}</p>
  const groupStandingsTables=groupStandings&&<section aria-label="Saved group standings">
    <h4>{cs?'Konečné tabulky skupin':'Final group standings'}</h4>
    <p role="status">{cs?'Uložené výsledkové tabulky — pořadí a statistiky z kanonické autority.':
      'Saved final tables — ranks and statistics from canonical authority.'}
      {' · '}{cs?'Auditovaná rozhodnutí':'Audited decisions'}: {groupStandings.tie_decisions.length}</p>
    <div className="grid">
      {groupStandings.groups.map(group=><section className="section-subtle" key={group.group_index}>
        <h5>{cs?'Skupina':'Group'} {group.group_index}</h5>
        <div className="table-responsive"><table aria-label={'Saved group '+group.group_index+' standings'}>
          <thead><tr><th>#</th><th>{cs?'Hráč':'Player'}</th>
            <th>W</th><th>L</th><th>{cs?'Body':'Points'}</th>
            <th>{cs?'Odehráno':'Played'}</th><th>W/O +</th><th>W/O −</th>
            <th>{cs?'Sety +/−':'Games +/−'}</th><th>{cs?'Míče +/−':'Ball points +/−'}</th>
          </tr></thead>
          <tbody>{group.rows.map(r=><tr key={r.player_id}>
            <td>{r.position}</td><td>{r.player_id}</td>
            <td>{r.wins}</td><td>{r.losses}</td><td><strong>{r.group_points}</strong></td>
            <td>{r.played_matches}</td><td>{r.walkovers_received}</td><td>{r.walkovers_conceded}</td>
            <td>{r.games_won}/{r.games_lost}</td><td>{r.points_won}/{r.points_lost}</td>
          </tr>)}</tbody>
        </table></div>
      </section>)}
    </div>
    {groupStandings.tie_decisions.length>0&&<section aria-label="Saved group tie decisions">
      <h5>{cs?'Auditovaná rozhodnutí při rovnosti':'Audited tie decisions'}</h5>
      {groupStandings.tie_decisions.map(d=><p key={d.case_fingerprint}>
        {cs?'Skupina':'Group'} {d.group_index}: {d.ordered_player_ids.join(' → ')}
        {' · '}{cs?'Důvod Admina':'Admin reason'}: {d.admin_reason}
        {' · '}<code>{d.case_fingerprint.slice(0,12)}</code>
      </p>)}
    </section>}
  </section>
  const pendingTiePanel=!groupStandings&&pendingTieDecisions.length>0&&
    <section aria-label="Saved pending group tie decisions">
      <h4>{cs?'Uložená rozhodnutí shod — čeká na konečnou tabulku':
        'Saved tie decisions — final standings pending'}</h4>
      <p role="status">{cs?'Tato historická revize obsahuje auditované rozhodnutí pořadí, ale konečné skupinové tabulky dosud nebyly vytvořeny. Pořadí níže není publikovaná výsledková tabulka.':
        'This historical revision records an audited player ordering, but canonical final group standings have not yet been generated. The reviewed order below is not a published group table.'}</p>
      <ol>{pendingTieDecisions.map(d=><li key={d.case_fingerprint}>
        {cs?'Skupina':'Group'} {d.group_index}: {d.ordered_player_ids.join(' → ')}
        {' · '}{cs?'Důvod Admina':'Admin reason'}: {d.admin_reason}
        {' · '}<code>{d.case_fingerprint.slice(0,12)}</code>
      </li>)}</ol>
    </section>
  const groupScheduleTable=groupSchedule&&<section aria-label="Saved group Match Day schedule">
    <h5>{cs?'Autentický skupinový rozpis':'Authentic group Match Day schedule'}</h5>
    <p role="status">{cs?'Uložené skupiny':'Saved groups'}: {groupSchedule.group_count}
      {' · '}{cs?'Velikost skupiny':'Group size'}: {groupSchedule.group_size}
      {' · '}Match Days: {groupSchedule.match_day_count}
      {' · '}{cs?'Toto jsou pořadová čísla, nikoliv kalendářní datum nebo hodina.':
        'Days are ordinal, not calendar dates or clock times.'}</p>
    <div className="table-responsive">
      <table aria-label="Saved group matches">
        <thead><tr><th>{cs?'Skupina':'Group'}</th><th>Match Day</th>
          <th>{cs?'Pořadí':'Order'}</th><th>{cs?'Hráči':'Players'}</th>
          <th>{cs?'Formát':'Format'}</th><th>{cs?'Výsledek / detail':'Result / detail'}</th>
        </tr></thead>
        <tbody>{groupSchedule.matches.map(g=>{
          const published=matches.find(m=>m.match_id===g.match_id&&m.draw_type==='group')
          return <tr key={g.match_id}><td>{g.group_index}</td>
            <td>{g.match_day_ordinal}</td><td>{g.match_order}</td>
            <td>{g.top_player_id} – {g.bottom_player_id}</td>
            <td>BO{g.best_of}</td>
            <td>{published?<>{published.scoreline}{' · '}
              {published.loser_player_id&&<Link to={matchHref(g.match_id,'schedule')}>
                {cs?'Detail zápasu':'Match detail'}</Link>}</>:
              <span>{cs?'Bez kanonického výsledku':'Not canonically published'}</span>}</td>
          </tr>
        })}</tbody>
      </table>
    </div>
  </section>
  const statusMissing=cs?'Tento zdroj neobsahuje úplnou historickou autoritu pro tento oddíl.':
    'A complete historical authority for this section is unavailable in this source.'
  const fieldList=(label:string,ids:string[])=><section key={label} className="section-subtle">
    <h4>{label} ({ids.length})</h4>
    {ids.length?<ol>{ids.map(id=><li key={id}>{id}</li>)}</ol>:<p>—</p>}
  </section>
  const bracketView=(bracket:SavedTourDrawBracket)=><section key={bracket.section_id??bracket.draw_type}>
    <h4>{bracket.section_id??(cs?'Hlavní pavouk':'Main draw')} · {bracket.bracket_size}
      {' '}{cs?'pozic':'slots'}</h4>
    <div className="table-responsive"><table aria-label={'Saved draw '+(bracket.section_id??bracket.draw_type)}>
      <thead><tr><th>{cs?'Pozice':'Slot'}</th><th>{cs?'Účastník / pozice':'Entrant / placeholder'}</th>
        <th>{cs?'Nasazení':'Seed'}</th><th>{cs?'Vstup':'Entry'}</th></tr></thead>
      <tbody>{[...bracket.slots].sort((a,b)=>a.slot_index-b.slot_index).map(slot=><tr key={slot.slot_index}>
        <td>{slot.slot_index}</td><td>{slot.player_id??slot.placeholder_id??(slot.entrant_kind==='bye'?'BYE':'—')}</td>
        <td>{slot.seed_number??'—'}</td>
        <td>{slot.entry_status??(slot.entrant_kind==='player'?'direct':slot.entrant_kind)}</td>
      </tr>)}</tbody></table></div>
  </section>
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
        {entry?<><p role="status">{cs?'Skutečné uložené Entry Field, pořadí / revize:':
          'Authentic saved Entry Field, version:'} {entry.field_sequence} · {entry.mode}
          {' · '}{cs?'Kapacita hlavního pavouku':'Main capacity'}: {entry.main_draw_capacity}
          {' · '}BYE: {entry.effective_main_bye_count}</p>
          <div className="grid">
            {fieldList(cs?'Hlavní účastníci':'Direct Main entrants',entry.direct_main_player_ids)}
            {fieldList(cs?'Kvalifikace':'Qualification entrants',entry.qualification_player_ids)}
            {fieldList(cs?'Náhradníci':'Alternates',entry.alternate_player_ids)}
            {fieldList(cs?'Odstoupení':'Withdrawn',entry.withdrawn_player_ids)}
          </div></>:<p role="status">{cs?'Historický Entry Field pro tuto uloženou revizi není dostupný.':
            'No saved Entry Field exists in this revision.'}</p>}
        {result&&<><h4>{cs?'Doložení hráči z výsledkové autority':'Players evidenced by published results'}</h4>
          <p>{cs?'Výsledková evidence není náhradou za seznam přihlášek.':
            'Published result evidence does not substitute for the Entry Field.'}</p>
          <ul>{result.players.map(p=><li key={p.player_id}>{p.player_id} · {p.reached_stage}</li>)}</ul></>}
      </section>}
      {tab==='draw'&&<section><h3>{labels[2]}</h3>
        <p>{cs?'První kolo je z uložené Draw authority. Výsledky zápasů jsou oddělená evidence.':
          'First-round slots come from saved Draw authority. Match results are separate evidence.'}</p>
        <div className="grid"><button type="button" aria-pressed={phase==='main'}
          onClick={()=>setPhase('main')}>{cs?'Hlavní část':'Main'}</button>
          <button type="button" aria-pressed={phase==='qualification'}
          onClick={()=>setPhase('qualification')}>{cs?'Kvalifikace':'Qualification'}</button></div>
        {draw?(phase==='main'?bracketView(draw.main):draw.qualification_sections.length?
          draw.qualification_sections.map(bracketView):<p>{cs?'Uložený kvalifikační pavouk není dostupný.':
            'No saved qualification bracket is available.'}</p>):
          <p role="status">{cs?'V této revizi není uložená Draw authority.':
            'No saved Draw authority exists in this revision.'}</p>}
        {result&&<><h4>{cs?'Publikované výsledky zápasů':'Published match results'}</h4>
          {matchTable(phase==='main'?main:qualification)}</>}
      </section>}
      {tab==='schedule'&&<section><h3>{labels[3]}</h3>
        <p>{cs?'Časy zápasů se z výsledků neodvozují. Den zápasu je pořadové číslo, nikoli datum.':
          'Match start times are never inferred from results. Match Day is an ordinal, not a date.'}</p>
        {schedule?<p role="status">{cs?'Skutečný uložený rozpis Week Simulation Schedule v2.':
          'Authentic Saved Week Simulation Schedule v2.'} · {cs?'Sloty':'Slots'}: {schedule.slots.length}
          {' · '}{cs?'Zdroj':'Source'}: {schedule.source}</p>:
          !groupSchedule?<p role="status">{cs?'Uložený rozpis Match Day pro tuto edici není dostupný.':
            'An event-bound Saved Match Day schedule is unavailable for this Edition.'}</p>:null}
        {(schedule||result||groupSchedule)&&<><a href="#saved-schedule-main">{cs?'Hlavní část':'Main'}</a>
          {' · '}<a href="#saved-schedule-qualification">{cs?'Kvalifikace':'Qualification'}</a>
          <section id="saved-schedule-main"><h4>{cs?'Hlavní část':'Main'}</h4>
            {groupScheduleTable}
            {schedule?scheduledTable(plannedMain):result?<><p>{cs?'Publikovaná výsledková evidence, nezávislá na rozpisu.':
              'Published results are independent of a scheduled Match Day.'}</p>
              {matchTable(main)}</>:!groupSchedule?<p>{statusMissing}</p>:null}</section>
          <section id="saved-schedule-qualification"><h4>{cs?'Kvalifikace':'Qualification'}</h4>
            {schedule?scheduledTable(plannedQualification):<><p>{cs?'Pouze výsledková evidence, nikoli rozpis.':
              'Published result evidence only, not a schedule.'}</p>{matchTable(qualification)}</>}</section></>}
      </section>}
      {tab==='results'&&<section><h3>{labels[4]}</h3>
        {groupStandingsTables}
        {pendingTiePanel}
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
