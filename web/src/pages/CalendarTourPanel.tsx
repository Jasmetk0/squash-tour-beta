import {useEffect,useRef,useState} from 'react'
import {Link} from 'react-router-dom'
import {useQueryClient} from '@tanstack/react-query'
import {inspectCalendarTour,inspectCalendarTourPlayer,previewCalendarTour,executeCalendarTour,saveCalendarTour,replayCalendarContinuation} from '../api/client'
import {validateTourView,validateTourPreview,type TourView,type TourPreview,type TourCommand,type TourAction,type TourContribution,type TourPlayer} from '../api/calendarTour'
import {newCommandId} from '../admin/branchSimulation'
import {useLanguage} from '../i18n/LanguageContext'
import {formatApiError} from '../utils/apiErrors'
import type {RunBranchListResponse} from '../api/types'

const actionLabels={approve:['Zkontrolovat schválení','Review approval'],draw:['Zkontrolovat los','Review draw'],play:['Zkontrolovat odehrání','Review play'],'confirm-result':['Zkontrolovat výsledky','Review results']}
const stageLabels:Record<string,string>={champion:'Vítěz',finalist:'Finalista',semifinal:'Semifinále',quarterfinal:'Čtvrtfinále'}
const pointStatus:Record<string,string>={counted:'Započteno',awaiting_activation:'Čeká na aktivaci',expired:'Expirováno',excluded_best_n:'Mimo Best N'}
const blockerLabels:Record<string,[string,string]>={season_transition_required:['Je nutný Season Transition.','Season Transition is required.'],saved_health_baseline_missing:['Chybí uložený Health stav.','Saved Health state is missing.'],health_healing_or_permanent_effect_authority_unsupported:['Léčení či trvalé následky vyžadují dosud nepodporovanou autoritu.','Healing or permanent effects require an unsupported authority.'],intake_source_requires_native_calendar_materialization:['Prospect intake vyžaduje nativní kalendářovou materializaci.','Prospect intake requires native calendar materialization.'],disciplinary_source_requires_native_activation_authority:['Disciplinární zdroj vyžaduje nativní aktivaci.','Disciplinary source requires native activation.'],sporting_owner_drift:['Sportovní stav se změnil mimo Tour.','Sporting state changed outside Tour.']}

export function CalendarTourPanel({runId,branchId,head}:{runId:string;branchId:string;head:string}) {
  const cs=useLanguage().language==='cs',client=useQueryClient()
  const scope=[runId,branchId,head].join('|'),current=useRef(scope),epoch=useRef(0)
  const inputs=useRef(0)
  if(current.current!==scope){current.current=scope;epoch.current++}
  const [view,setView]=useState<TourView|null>(null),[error,setError]=useState<string|null>(null)
  const [busy,setBusy]=useState(false),[review,setReview]=useState<TourPreview|null>(null)
  const [consent,setConsent]=useState(false),[saveConsent,setSaveConsent]=useState(false)
  const [reason,setReason]=useState(''),[seed,setSeed]=useState('231')
  const [name,setName]=useState(''),[editionId,setEditionId]=useState(''),[size,setSize]=useState(8)
  const [week,setWeek]=useState(''),[slot,setSlot]=useState('1')
  const [points,setPoints]=useState({champion:'100',finalist:'60',semifinal:'30',quarterfinal:'15'})
  const [selected,setSelected]=useState<string[]>([]),[contributions,setContributions]=useState<TourContribution[]|null>(null)
  const [notice,setNotice]=useState<string|null>(null)
  const [player,setPlayer]=useState(''),[playerDetail,setPlayerDetail]=useState<TourPlayer|null>(null)
  const detailRequest=useRef(0)
  const invalidate=()=>{inputs.current++;setReview(null);setConsent(false);setSaveConsent(false);setPlayerDetail(null);detailRequest.current++}
  const read=async(signal?:AbortSignal)=>validateTourView(await inspectCalendarTour(runId,branchId,signal),runId,branchId)
  useEffect(()=>{
    const stamp=epoch.current
    const controller=new AbortController()
    let active=true
    const valid=()=>active&&epoch.current===stamp
    setView(null);setError(null);setReview(null);setConsent(false);setSaveConsent(false);setSelected([]);setContributions(null);setNotice(null);setPlayer('');setPlayerDetail(null);detailRequest.current++;setBusy(true)
    void read(controller.signal).then(v=>{if(valid()){setView(v);setWeek(String((v.state?.week.week??2)+2))}})
      .catch(e=>{if(valid())setError(formatApiError(e))})
      .finally(()=>{if(valid())setBusy(false)})
    return()=>{active=false;controller.abort()}
  },[scope])
  const perform=async(action:TourAction|'commit'|'save'|'refresh',id:string|null=null)=>{
    if(!view)return
    const stamp=epoch.current
    const inputStamp=inputs.current
    const valid=()=>epoch.current===stamp&&current.current===scope&&inputs.current===inputStamp
    setBusy(true);setError(null);setNotice(null)
    try {
      if(action==='save'){
        if(!saveConsent||!view.tour_fingerprint)return
        const saved=await saveCalendarTour(runId,branchId,view.draft_version,view.tour_fingerprint)
        if(!valid())return
        if(saved.schema_version!=='calendar_tour_save_receipt.v1'||saved.run_id!==runId||saved.branch_id!==branchId||saved.saved_revision.run_id!==runId||saved.saved_revision.branch_id!==branchId||!/^[0-9a-f]{64}$/.test(saved.saved_revision.content_hash))throw Error('Tour Save source scope is invalid')
        invalidate()
        const key=['admin-run-branches',runId]
        const branches=client.getQueryData<RunBranchListResponse>(key)
        if(branches?.run_branches.some(b=>b.branch_id===branchId&&b.run_id===runId)){
          // The confirmed Save already supplies the new authoritative HEAD.
          // Updating the shared selection starts ONE full read in the effect,
          // instead of loading the same large history before and after HEAD.
          setView(null)
          client.setQueryData<RunBranchListResponse>(key,{...branches,run_branches:branches.run_branches.map(b=>b.branch_id===branchId?{...b,saved_head_revision_id:saved.saved_revision.revision_id}:b)})
          void client.invalidateQueries();return
        }
        const next=await read();if(epoch.current===stamp)setView(next)
        return
      }
      if(action==='commit'){
        if(!review||!consent)return
        await executeCalendarTour(runId,branchId,review.command,review.preview_fingerprint)
        if(!valid())return
        const next=await read();if(!valid())return
        invalidate();setView(next);setNotice(cs?'Změna je v Working Draft. Proveďte ruční Save.':'Change is in Working Draft. Save manually.');return
      }
      if(action==='refresh'){
        const next=await read();if(!valid())return
        invalidate();setView(next);return
      }
      if(!view.checkpoint_fingerprint||!reason.trim()||!Number.isSafeInteger(Number(seed)))return
      let data:Record<string,unknown>={}
      if(action==='create-edition'){
        if(!view.state)return
        const date={...view.state.week,calendar:view.run_calendar??view.state.week.calendar,week:Number(week)}
        const table=Object.fromEntries(Object.entries(points).filter(([k])=>size===8||k!=='quarterfinal').map(([k,v])=>[k,Number(v)]))
        data={edition_id:editionId,name,week:date,announcement_week:{...date,week:view.state.week.week+1},start_slot:Number(slot),main_entrant_count:size,ranked:true,point_table:table,validity_weeks:date.calendar.weeks_per_year}
      } else if(action==='submit') data={player_ids:selected}
      const command:TourCommand={action,command_id:newCommandId(),edition_id:id,expected_saved_head:view.saved_head_revision_id,expected_checkpoint_fingerprint:view.checkpoint_fingerprint,expected_tour_fingerprint:view.tour_fingerprint,seed:Number(seed),operator_label:'Admin',audit_reason:reason.trim(),data}
      const checked=validateTourPreview(await previewCalendarTour(runId,branchId,command),command,runId,branchId)
      if(!valid())return
      setReview(checked);setConsent(false)
    }catch(e){if(valid()){invalidate();setError(formatApiError(e))}}
    finally{if(epoch.current===stamp&&current.current===scope)setBusy(false)}
  }
  const names=new Map(view?.players.map(p=>[p.player_id,p.name])??[])
  const ready=Boolean(view&&!busy&&reason.trim()&&/^-?\d+$/.test(seed)&&Number.isSafeInteger(Number(seed))&&(view.saved||view.state))
  const latest=view?.state?.rankings[view.state.rankings.length-1]
  return <section className="panel" aria-label="Configured native Tour" data-active-head={head} data-saved-head={view?.saved_head_revision_id}>
    <h2>{cs?'Tour · Edition a oficiální týden':'Tour · Editions and Official week'}</h2>
    <p>{cs?'Přihlášky, schválení a los lze připravit v jednom Working Draft. Před zápasy, potvrzením výsledků a Week Transition proveďte ruční Save.':'Applications, approval and draw can share one Working Draft. Save manually before matches, result confirmation and Week Transition.'}</p>
    {error&&<p role="alert" className="error">{error}</p>}{notice&&<p role="status">{notice}</p>}
    {!view&&<p>{cs?'Načítání autorit…':'Loading authorities…'}</p>}
    {view&&<>
      <p>{cs?'Stav':'State'}: {view.saved?'Saved':'Working Draft'} · {view.state&&`${cs?'Týden':'Week'} ${view.state.week.week}/${view.state.week.calendar.weeks_per_year}`}</p>
      <label>{cs?'Důvod operace':'Operation reason'}<input aria-label="Tour operation reason" value={reason} onChange={e=>{setReason(e.target.value);invalidate()}}/></label>
      <label>{cs?'Seed simulace':'Simulation seed'}<input aria-label="Tour seed" value={seed} onChange={e=>{setSeed(e.target.value);invalidate()}}/></label>
      <button disabled={busy} onClick={()=>void perform('refresh')}>{cs?'Obnovit stav':'Refresh state'}</button>
      {!view.state&&<>
        <p>{cs?'Nejprve připravte a uložte populaci, zdraví, úvodní knockout a sportovní týden 2.':'First prepare and Save population, Health, opening knockout and sporting Week 2.'}</p>
        <button disabled={busy||!view.can_initialize||!reason.trim()} onClick={()=>void perform('initialize')}>{cs?'Zkontrolovat zahájení Tour':'Review Tour initialization'}</button>
      </>}
      {view.state&&<>
        <details><summary>{cs?'Nová Tournament Edition':'New Tournament Edition'}</summary>
          <label>ID<input aria-label="Tour Edition ID" value={editionId} onChange={e=>{setEditionId(e.target.value);invalidate()}}/></label>
          <label>{cs?'Název':'Name'}<input aria-label="Tour Edition name" value={name} onChange={e=>{setName(e.target.value);invalidate()}}/></label>
          <label>{cs?'Týden':'Week'}<input aria-label="Tour Edition week" type="number" value={week} onChange={e=>{setWeek(e.target.value);invalidate()}}/></label>
          <label>{cs?'První globální slot':'First global slot'}<input aria-label="Tour Edition slot" type="number" value={slot} onChange={e=>{setSlot(e.target.value);invalidate()}}/></label>
          <label>{cs?'Účastníci':'Participants'}<select aria-label="Tour Edition size" value={size} onChange={e=>{setSize(Number(e.target.value));invalidate()}}><option>8</option><option>4</option></select></label>
          {Object.entries(points).filter(([k])=>size===8||k!=='quarterfinal').map(([stage,value])=><label key={stage}>{cs?stageLabels[stage]:stage}<input aria-label={`Tour points ${stage}`} type="number" value={value} onChange={e=>{setPoints({...points,[stage]:e.target.value});invalidate()}}/></label>)}
          <p>{cs?'Platnost bodů':'Point validity'}: {view.state.week.calendar.weeks_per_year} {cs?'týdnů od prvního oficiálního rankingu':'weeks from first Official ranking'}</p>
          <button disabled={!ready||!editionId.trim()||!name.trim()} onClick={()=>void perform('create-edition')}>{cs?'Zkontrolovat novou Edition':'Review new Edition'}</button>
        </details>
        {view.state.editions.map(a=>{
          const id=a.edition.edition_id,active=a.edition.week.week===view.state!.week.week&&a.edition.week.season_index===view.state!.week.season_index
          const next: keyof typeof actionLabels=!a.field?'approve':!a.draw?'draw':!a.tournament_fingerprint?'play':'confirm-result'
          return <section key={id} aria-label={`Edition ${id}`}>
            <h3>{a.edition.name} · W{a.edition.week.week}</h3>
            <p>{cs?'Přihlášky':'Applications'}: {a.submissions.length} · {cs?'Schválení':'Approved'}: {a.field?.direct_main_player_ids.length??0} · {a.result_confirmed?(cs?'Výsledky potvrzeny':'Results confirmed'):a.tournament_fingerprint?(cs?'Odehráno':'Played'):a.draw?(cs?'Vylosováno':'Drawn'):(cs?'Příprava':'Preparation')}</p>
            <p>{cs?'Bodová tabulka':'Point table'}: {Object.entries(a.edition.point_table).map(([k,v])=>`${cs?stageLabels[k]:k} ${v}`).join(' · ')}</p>
            {!a.field&&active&&<><select multiple aria-label={`Tour applicants ${id}`} value={selected} onChange={e=>{setSelected(Array.from(e.target.selectedOptions,o=>o.value));invalidate()}}>{view.players.filter(p=>p.status!=='retired'&&!a.submissions.some(s=>s.player_id===p.player_id)).map(p=><option key={p.player_id} value={p.player_id}>{p.name}</option>)}</select>
              <button disabled={!ready||!selected.length} onClick={()=>void perform('submit',id)}>{cs?'Zkontrolovat přihlášky':'Review applications'}</button></>}
            {a.field&&<p>{cs?'Schválený field':'Approved field'}: {a.field.direct_main_player_ids.map(p=>names.get(p)??p).join(', ')}</p>}
            {a.draw&&<ol>{a.draw.main.slots.map(s=><li key={s.slot_index}>{names.get(s.player_id)??s.player_id}</li>)}</ol>}
            {view.edition_evidence[id]&&<>
              <table aria-label={`Played matches ${id}`}><thead><tr><th>Slot</th><th>{cs?'Zápas':'Match'}</th><th>{cs?'Vítěz':'Winner'}</th><th>{cs?'Rally':'Rallies'}</th></tr></thead><tbody>{view.edition_evidence[id].matches.map(m=><tr key={m.match_id}><td>{m.slot}</td><td>{names.get(m.player_a_id)} / {names.get(m.player_b_id)}</td><td>{names.get(m.winner_player_id)}</td><td>{m.rally_count}</td></tr>)}</tbody></table>
              <table aria-label={`Edition results ${id}`}><thead><tr><th>{cs?'Hráč':'Player'}</th><th>{cs?'Výsledek':'Result'}</th><th>{cs?'Body':'Points'}</th></tr></thead><tbody>{view.edition_evidence[id].results.map(r=><tr key={r.player_id}><td>{names.get(r.player_id)}</td><td>{cs?stageLabels[r.stage]:r.stage}</td><td>{r.main_points}</td></tr>)}</tbody></table>
            </>}
            {active&&!a.result_confirmed&&<button disabled={!ready||(!view.saved&&(next==='play'||next==='confirm-result'))} onClick={()=>void perform(next,id)}>{actionLabels[next][cs?0:1]}</button>}
            {a.tournament_fingerprint&&<button disabled={busy} onClick={()=>{
              const stamp=epoch.current;setBusy(true)
              void replayCalendarContinuation(runId,branchId,`${id}:final`).then(r=>{if(epoch.current===stamp)setNotice(`${cs?'Přesný replay':'Exact replay'}: ${r.exact_replay}`)}).catch(e=>{if(epoch.current===stamp)setError(formatApiError(e))}).finally(()=>{if(epoch.current===stamp)setBusy(false)})
            }}>{cs?'Replay finále':'Replay final'}</button>}
          </section>
        })}
        <h3>{cs?'Připravenost týdne':'Week readiness'}</h3>
        {view.transition_blockers.length?<ul>{view.transition_blockers.map(b=><li key={b}>{b.startsWith('edition_not_terminal:')?`${cs?'Edition není dokončena':'Edition is not complete'}: ${b.slice(21)}`:blockerLabels[b]?.[cs?0:1]??b}</li>)}</ul>:<p>{cs?'Povinné Edition dokončeny.':'Mandatory Editions completed.'}</p>}
        <button disabled={!ready||!view.saved||view.transition_blockers.length>0} onClick={()=>void perform('transition')}>{cs?'Zkontrolovat Week Transition':'Review Week Transition'}</button>
        {latest&&<><h3>{cs?'Oficiální ranking':'Official ranking'} · W{latest.week.week} · Best {latest.policy.best_n}</h3>
          <p>{view.saved?(cs?'Publikováno v Saved Revision.':'Published in Saved revision.'):(cs?'Kandidát ve Working Draft; Viewer stále čte poslední Saved Revision.':'Working Draft candidate; Viewer still reads the last Saved revision.')}</p>
          <table><thead><tr><th>#</th><th>{cs?'Hráč':'Player'}</th><th>{cs?'Body':'Points'}</th></tr></thead><tbody>{latest.rows.map(r=><tr key={r.player_id}><td>{r.rank}</td><td>{names.get(r.player_id)??r.player_id}</td><td><button onClick={()=>setContributions(view.contributions?.[r.player_id]??r.counted_results)}>{r.points}</button></td></tr>)}</tbody></table></>}
        {contributions&&<aside aria-label="Official point contributions"><h4>{cs?'Bodové příspěvky':'Point contributions'}</h4>{contributions.map(r=><p key={r.edition_id}>{r.edition_id}: {r.main_points+r.qualification_points} · {cs?pointStatus[r.status??'counted']:r.status??'counted'} · {cs?'První ranking':'First ranking'} W{r.first_publication_week.week} · {r.validity_weeks} {cs?'týdnů':'weeks'} · <code>{r.source_fingerprint}</code></p>)}<button onClick={()=>setContributions(null)}>{cs?'Zavřít':'Close'}</button></aside>}
        <details><summary>{cs?'Aktuální stav hráče':'Current player state'}</summary>
          <select aria-label="Tour player state" value={player} disabled={busy} onChange={e=>{
            const id=e.target.value;setPlayer(id);setPlayerDetail(null);const request=++detailRequest.current,stamp=epoch.current
            if(!id)return
            void inspectCalendarTourPlayer(runId,branchId,id).then(detail=>{
              if(epoch.current!==stamp||request!==detailRequest.current)return
              if(detail.run_id!==runId||detail.branch_id!==branchId||detail.saved_head_revision_id!==view.saved_head_revision_id||detail.checkpoint_fingerprint!==view.checkpoint_fingerprint||detail.record.player_id!==id)throw Error('Player state source changed; refresh Tour')
              setPlayerDetail(detail)
            }).catch(e=>{if(epoch.current===stamp&&request===detailRequest.current)setError(formatApiError(e))})
          }}><option value="">{cs?'Vyberte hráče':'Select player'}</option>{view.players.map(p=><option key={p.player_id} value={p.player_id}>{p.name}</option>)}</select>
          {playerDetail&&<><p>{cs?'Věk / stav':'Age / status'}: {playerDetail.lifecycle?.age} / {playerDetail.lifecycle?.status} · Form: {playerDetail.record.current_form} · {cs?'Rozehranost':'Sharpness'}: {playerDetail.record.match_sharpness} · {cs?'Únava':'Fatigue'}: {playerDetail.record.long_term_fatigue}</p><table aria-label="Current 57 attributes"><tbody>{playerDetail.record.attributes.map(([name,value])=><tr key={name}><th>{name}</th><td>{value}</td></tr>)}</tbody></table></>}
        </details>
        <Link to={`/admin/runs/${encodeURIComponent(runId)}/branches?branch=${encodeURIComponent(branchId)}`}>{cs?'Uložená historie a obnova':'Saved history and restore'}</Link>
      </>}
      {review&&<section aria-label="Tour command review"><h3>{cs?'Kontrola operace':'Operation review'}: {review.command.action}</h3>
        <p>HEAD: <code>{review.command.expected_saved_head}</code></p>
        {review.command.action==='create-edition'&&<p>{String(review.command.data.name)} · W{String((review.command.data.week as {week:number}).week)} · {cs?'Účastníci':'Participants'}: {String(review.command.data.main_entrant_count)} · {Object.entries(review.command.data.point_table as Record<string,number>).map(([k,v])=>`${cs?stageLabels[k]:k} ${v}`).join(' · ')}</p>}
        {review.command.action==='submit'&&<p>{cs?'Přihlášky':'Applications'}: {(review.command.data.player_ids as string[]).map(id=>names.get(id)??id).join(', ')}</p>}
        {review.impact.approved_field&&<p>{cs?'Schválený field':'Approved field'}: {review.impact.approved_field.direct_main_player_ids.map(id=>names.get(id)??id).join(', ')}</p>}
        {review.impact.draw&&<ol>{review.impact.draw.main.slots.map(s=><li key={s.slot_index}>{names.get(s.player_id)??s.player_id}</li>)}</ol>}
        {review.impact.entrant_ids&&<p>{cs?'Účastníci podle uloženého losu':'Participants from Saved draw'}: {review.impact.entrant_ids.map(id=>names.get(id)??id).join(', ')}</p>}
        {review.impact.results&&<p>{cs?'Výsledné body':'Result points'}: {review.impact.results.map(r=>`${names.get(r.player_id)??r.player_id}: ${r.main_points}`).join(' · ')}</p>}
        {review.impact.ranking&&<p>{cs?'Nový týden':'New week'}: {review.impact.target_week?.week} · {cs?'Klasifikovaní hráči':'Classified players'}: {review.impact.ranking.rows.length} · {cs?'Změnění hráči':'Changed players'}: {review.impact.sporting?.changed_player_count} · {cs?'Změny atributů':'Attribute changes'}: {review.impact.sporting?.attribute_change_count}</p>}
        {review.impact.sporting?.changes&&<details><summary>{cs?'Dopady na hráče':'Player impacts'}</summary><table><thead><tr><th>{cs?'Hráč':'Player'}</th><th>{cs?'Změny atributů':'Attribute changes'}</th><th>Form</th><th>{cs?'Rozehranost':'Sharpness'}</th><th>{cs?'Únava':'Fatigue'}</th></tr></thead><tbody>{review.impact.sporting.changes.map(p=><tr key={p.player_id}><td>{names.get(p.player_id)??p.player_id}</td><td>{p.changed_attributes}</td><td>{p.form_before} → {p.form_after}</td><td>{p.sharpness_before} → {p.sharpness_after}</td><td>{p.fatigue_before} → {p.fatigue_after}</td></tr>)}</tbody></table></details>}
        <label><input aria-label="Confirm Tour command" type="checkbox" checked={consent} onChange={e=>setConsent(e.target.checked)}/>{cs?'Potvrzuji tuto operaci nad zobrazeným vstupem.':'I confirm this operation over the displayed inputs.'}</label>
        <button disabled={busy||!consent} onClick={()=>void perform('commit')}>{cs?'Provést potvrzenou operaci':'Execute confirmed operation'}</button></section>}
      {view.state&&!view.saved&&<><label><input aria-label="Confirm Tour Save" type="checkbox" checked={saveConsent} onChange={e=>setSaveConsent(e.target.checked)}/>{cs?'Uložit společně Tour, sportovní stav a ranking.':'Save Tour, sporting state and ranking together.'}</label><button disabled={busy||!saveConsent} onClick={()=>void perform('save')}>{cs?'Ruční Save Tour':'Manual Tour Save'}</button></>}
    </>}
  </section>
}
