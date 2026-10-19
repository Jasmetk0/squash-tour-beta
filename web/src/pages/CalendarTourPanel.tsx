import {useEffect,useRef,useState} from 'react'
import {Link} from 'react-router-dom'
import {useQueryClient} from '@tanstack/react-query'
import {inspectCalendarTour,inspectCalendarTourPlayer,previewCalendarTour,executeCalendarTour,saveCalendarTour,replayCalendarContinuation,inspectCalendarTourSeason,inspectCalendarTourRecords,inspectNativeTourProspectIntake,previewCalendarTourNativeBirthSporting} from '../api/client'
import {validateTourView,validateTourPreview,validateTourSeasonComparison,validateTourCareerRecords,validateNativeProspectIntake,validateNativeSportingBirthPreflight,type NativeSportingBirthPreflight,type NativeProspectIntakePreflight,type TourCareerRecords,type TourSeasonComparison,type TourView,type TourPreview,type TourCommand,type TourAction,type TourContribution,type TourPlayer} from '../api/calendarTour'
import {newCommandId} from '../admin/branchSimulation'
import {tourWeekOffset,scheduleTourEdition} from '../api/nativeTourCalendar'
import {useLanguage} from '../i18n/LanguageContext'
import {formatApiError} from '../utils/apiErrors'
import type {RunBranchListResponse} from '../api/types'

const actionLabels={approve:['Zkontrolovat schválení','Review approval'],draw:['Zkontrolovat los','Review draw'],play:['Zkontrolovat odehrání','Review play'],'confirm-result':['Zkontrolovat výsledky','Review results']}
const stageLabels:Record<string,string>={champion:'Vítěz',finalist:'Finalista',semifinal:'Semifinále',quarterfinal:'Čtvrtfinále'}
const pointStatus:Record<string,string>={counted:'Započteno',awaiting_activation:'Čeká na aktivaci',expired:'Expirováno',excluded_best_n:'Mimo Best N'}
const blockerLabels:Record<string,[string,string]>={season_transition_required:['Je nutný Season Transition.','Season Transition is required.'],season_transition_requires_last_week:['Season Transition lze provést až po posledním týdnu.','Season Transition requires the last week.'],season_transition_horizon_exhausted:['Další sezóna je mimo horizont Runu; nejprve prodlužte horizont.','The next season is beyond the Run horizon; extend it first.'],saved_health_baseline_missing:['Chybí uložený Health stav.','Saved Health state is missing.'],health_healing_or_permanent_effect_authority_unsupported:['Léčení či trvalé následky vyžadují dosud nepodporovanou autoritu.','Healing or permanent effects require an unsupported authority.'],intake_source_requires_native_calendar_materialization:['Prospect intake vyžaduje nativní kalendářovou materializaci.','Prospect intake requires native calendar materialization.'],disciplinary_source_requires_native_activation_authority:['Disciplinární zdroj vyžaduje nativní aktivaci.','Disciplinary source requires native activation.'],sporting_owner_drift:['Sportovní stav se změnil mimo Tour.','Sporting state changed outside Tour.']}

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
  const [season,setSeason]=useState(''),[week,setWeek]=useState(''),[slot,setSlot]=useState('1')
  const [points,setPoints]=useState({champion:'100',finalist:'60',semifinal:'30',quarterfinal:'15'})
  const [selected,setSelected]=useState<string[]>([]),[contributions,setContributions]=useState<TourContribution[]|null>(null)
  const [notice,setNotice]=useState<string|null>(null)
  const [player,setPlayer]=useState(''),[playerDetail,setPlayerDetail]=useState<TourPlayer|null>(null)
  const detailRequest=useRef(0),seasonReadRequest=useRef(0),careerReadRequest=useRef(0),intakeReadRequest=useRef(0)
  const [intakeReport,setIntakeReport]=useState<NativeProspectIntakePreflight|null>(null)
  const [birthSportingReport,setBirthSportingReport]=useState<NativeSportingBirthPreflight|null>(null)
  const [historySeason,setHistorySeason]=useState(''),[comparisonSeason,setComparisonSeason]=useState('')
  const [seasonReport,setSeasonReport]=useState<TourSeasonComparison|null>(null)
  const [recordAsOf,setRecordAsOf]=useState(''),[recordStart,setRecordStart]=useState('0'),[recordCountry,setRecordCountry]=useState('')
  const [careerRecords,setCareerRecords]=useState<TourCareerRecords|null>(null)
  const invalidate=()=>{inputs.current++;setReview(null);setConsent(false);setSaveConsent(false);setPlayerDetail(null);detailRequest.current++;setSeasonReport(null);seasonReadRequest.current++;setCareerRecords(null);careerReadRequest.current++;setIntakeReport(null);setBirthSportingReport(null);intakeReadRequest.current++}
  const read=async(signal?:AbortSignal)=>validateTourView(await inspectCalendarTour(runId,branchId,signal),runId,branchId)
  useEffect(()=>{
    const stamp=epoch.current
    const controller=new AbortController()
    let active=true
    const valid=()=>active&&epoch.current===stamp
    setView(null);setError(null);setReview(null);setConsent(false);setSaveConsent(false);setSelected([]);setContributions(null);setNotice(null);setPlayer('');setPlayerDetail(null);detailRequest.current++;setSeasonReport(null);seasonReadRequest.current++;setCareerRecords(null);careerReadRequest.current++;setIntakeReport(null);setBirthSportingReport(null);intakeReadRequest.current++;setBusy(true)
    void read(controller.signal).then(v=>{if(valid()){
      setView(v)
      const clock=v.state?{...v.state.week,calendar:v.run_calendar??v.state.week.calendar}:null
      const first=clock?tourWeekOffset(clock,2):null
      setSeason(first?String(first.season_index+1):'')
      setWeek(first?String(first.week):'')
      setHistorySeason(v.saved_completed_seasons.length?String(v.saved_completed_seasons[v.saved_completed_seasons.length-1]):'')
      setComparisonSeason('')
      setRecordAsOf(v.saved_completed_seasons.length?String(v.saved_completed_seasons[v.saved_completed_seasons.length-1]):'')
      setRecordStart('0');setRecordCountry('')
    }})
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
        const current={...view.state.week,calendar:view.run_calendar??view.state.week.calendar}
        const schedule=scheduleTourEdition(current,Number(season)-1,Number(week))
        if(!schedule)throw Error(cs?'Turnaj musí být platně naplánován alespoň dva týdny dopředu v rámci Runu.':'Edition must be scheduled at least two weeks ahead, inside the Run horizon.')
        const table=Object.fromEntries(Object.entries(points).filter(([k])=>size===8||k!=='quarterfinal').map(([k,v])=>[k,Number(v)]))
        data={edition_id:editionId,name,week:schedule.week,announcement_week:schedule.announcement_week,start_slot:Number(slot),main_entrant_count:size,ranked:true,point_table:table,validity_weeks:current.calendar.weeks_per_year}
      } else if(action==='submit') data={player_ids:selected}
      const command:TourCommand={action,command_id:newCommandId(),edition_id:id,expected_saved_head:view.saved_head_revision_id,expected_checkpoint_fingerprint:view.checkpoint_fingerprint,expected_tour_fingerprint:view.tour_fingerprint,seed:Number(seed),operator_label:'Admin',audit_reason:reason.trim(),data}
      const checked=validateTourPreview(await previewCalendarTour(runId,branchId,command),command,runId,branchId)
      if(!valid())return
      setReview(checked);setConsent(false)
    }catch(e){if(valid()){invalidate();setError(formatApiError(e))}}
    finally{if(epoch.current===stamp&&current.current===scope)setBusy(false)}
  }
  const loadSeasonReport=async()=>{
    if(!view||!view.saved_completed_seasons.includes(Number(historySeason)))return
    const stamp=epoch.current,headAtRequest=view.saved_head_revision_id
    const requestId=++seasonReadRequest.current
    const compared=comparisonSeason===''?null:Number(comparisonSeason)
    setBusy(true);setError(null);setSeasonReport(null)
    try{
      const answer=validateTourSeasonComparison(
        await inspectCalendarTourSeason(runId,branchId,Number(historySeason),compared),
        runId,branchId,headAtRequest,Number(historySeason),compared,
      )
      if(epoch.current!==stamp||current.current!==scope||seasonReadRequest.current!==requestId)return
      setSeasonReport(answer)
    }catch(e){
      if(epoch.current===stamp&&current.current===scope&&seasonReadRequest.current===requestId)setError(formatApiError(e))
    }finally{
      // Input edits revoke the result, but do not start another operation.
      // The completed read must still release busy within its original scope.
      if(epoch.current===stamp&&current.current===scope)setBusy(false)
    }
  }
  const loadCareerRecords=async()=>{
    if(!view||!view.saved_completed_seasons.includes(Number(recordAsOf))
      ||!view.saved_completed_seasons.includes(Number(recordStart))
      ||Number(recordStart)>Number(recordAsOf)
      ||(recordCountry!==''&&!/^[A-Z]{3}$/.test(recordCountry)))return
    const stamp=epoch.current,headAtRequest=view.saved_head_revision_id
    const requestId=++careerReadRequest.current
    const filtered=recordCountry===''?null:recordCountry
    setBusy(true);setError(null);setCareerRecords(null)
    try{
      const answer=validateTourCareerRecords(
        await inspectCalendarTourRecords(runId,branchId,Number(recordAsOf),Number(recordStart),filtered),
        runId,branchId,headAtRequest,Number(recordAsOf),Number(recordStart),filtered,
      )
      if(epoch.current!==stamp||current.current!==scope||careerReadRequest.current!==requestId)return
      setCareerRecords(answer)
    }catch(e){
      if(epoch.current===stamp&&current.current===scope&&careerReadRequest.current===requestId)setError(formatApiError(e))
    }finally{
      if(epoch.current===stamp&&current.current===scope)setBusy(false)
    }
  }
  const loadNativeIntake=async()=>{
    if(!view||!view.checkpoint_fingerprint)return
    const stamp=epoch.current,headAtRequest=view.saved_head_revision_id,checkpoint=view.checkpoint_fingerprint
    const requestId=++intakeReadRequest.current
    setBusy(true);setError(null);setIntakeReport(null);setBirthSportingReport(null)
    try{
      const checked=validateNativeProspectIntake(await inspectNativeTourProspectIntake(runId,branchId),runId,branchId,headAtRequest,checkpoint)
      if(epoch.current!==stamp||current.current!==scope||intakeReadRequest.current!==requestId)return
      setIntakeReport(checked)
    }catch(e){if(epoch.current===stamp&&current.current===scope&&intakeReadRequest.current===requestId)setError(formatApiError(e))}
    finally{if(epoch.current===stamp&&current.current===scope)setBusy(false)}
  }
  const loadNativeBirthSporting=async()=>{
    if(!view?.saved||!view.state||!view.tour_fingerprint||!view.checkpoint_fingerprint
      ||!intakeReport||intakeReport.due_count<1||intakeReport.problems.length>0
      ||intakeReport.saved_head_revision_id!==view.saved_head_revision_id
      ||intakeReport.checkpoint_fingerprint!==view.checkpoint_fingerprint
      ||!/^-?\d+$/.test(seed)||!Number.isSafeInteger(Number(seed)))return
    const stamp=epoch.current,inputsAtRequest=inputs.current
    const requestId=++intakeReadRequest.current
    const request={
      expected_saved_head:view.saved_head_revision_id,
      expected_checkpoint_fingerprint:view.checkpoint_fingerprint,
      expected_tour_fingerprint:view.tour_fingerprint,
      seed:Number(seed),
    }
    setBusy(true);setError(null);setBirthSportingReport(null)
    try {
      const result=validateNativeSportingBirthPreflight(
        await previewCalendarTourNativeBirthSporting(runId,branchId,request),
        runId,branchId,request,
      )
      if(epoch.current!==stamp||current.current!==scope||inputs.current!==inputsAtRequest
        ||intakeReadRequest.current!==requestId)return
      setBirthSportingReport(result)
    }catch(e){
      if(epoch.current===stamp&&current.current===scope&&inputs.current===inputsAtRequest
        &&intakeReadRequest.current===requestId)setError(formatApiError(e))
    }finally{
      if(epoch.current===stamp&&current.current===scope)setBusy(false)
    }
  }
  const names=new Map(view?.players.map(p=>[p.player_id,p.name])??[])
  const ready=Boolean(view&&!busy&&reason.trim()&&/^-?\d+$/.test(seed)&&Number.isSafeInteger(Number(seed))&&(view.saved||view.state))
  const latest=view?.state?.rankings[view.state.rankings.length-1]
  const clock=view?.state?{...view.state.week,calendar:view.run_calendar??view.state.week.calendar}:null
  const plannedEdition=clock?scheduleTourEdition(clock,Number(season)-1,Number(week)):null
  return <section className="panel" aria-label="Configured native Tour" data-active-head={head} data-saved-head={view?.saved_head_revision_id}>
    <h2>{cs?'Tour · Edition a oficiální týden':'Tour · Editions and Official week'}</h2>
    <p>{cs?'Přihlášky, schválení a los lze připravit v jednom Working Draft. Před zápasy, potvrzením výsledků a Week Transition proveďte ruční Save.':'Applications, approval and draw can share one Working Draft. Save manually before matches, result confirmation and Week Transition.'}</p>
    {error&&<p role="alert" className="error">{error}</p>}{notice&&<p role="status">{notice}</p>}
    {!view&&<p>{cs?'Načítání autorit…':'Loading authorities…'}</p>}
    {view&&<>
      <p>{cs?'Stav':'State'}: {view.saved?'Saved':'Working Draft'} · {view.state&&`${cs?'Týden':'Week'} ${view.state.week.week}/${view.state.week.calendar.weeks_per_year}`}</p>
      {view.state&&<section aria-label="Next-week prospect intake preflight">
        <h3>{cs?'Prospect intake – další týden':'Prospect intake – next week'}</h3>
        <p>{cs?'Kontrola ověřeného Saved zdroje; žádná aktivace hráčů.':'Verified Saved source only; no player activation.'}</p>
        <button disabled={busy} onClick={()=>void loadNativeIntake()}>{cs?'Prověřit patnáctileté prospecty':'Check next-week prospects'}</button>
        {intakeReport&&<div aria-label="Verified next-week prospect intake">
          <p>{cs?'Cílový týden':'Target week'}: S{intakeReport.target_week.season_index+1}/W{intakeReport.target_week.week} · {cs?'Připravení':'Ready'}: {intakeReport.due_count} · {cs?'Nesrovnalosti':'Problems'}: {intakeReport.problems.length}</p>
          {intakeReport.due.map(player=><p key={player.player_id}>{player.display_name} · {player.country_code} · <code>{player.player_id}</code></p>)}
          {intakeReport.problems.map(issue=><p key={issue.prospect_id+issue.code}>{issue.prospect_id}: {issue.code}</p>)}
          <p>{cs?'Nativní aktivace je stále zablokovaná do propojení lifecycle, Health a sportovního stavu.':'Native activation stays disabled until lifecycle, Health and sporting state are coupled.'}</p>
          {intakeReport.due_count>0&&intakeReport.problems.length===0&&<>
            <p>{cs?'Sportovní náhled používá seed simulace uvedený níže a ověřená data ze Saved. Nic neukládá.':'Sporting review uses the simulation seed below and verified Saved data. It never writes.'}</p>
            <button disabled={busy||!view.saved||!view.tour_fingerprint||!view.checkpoint_fingerprint
              ||!/^[-]?\d+$/.test(seed)||!Number.isSafeInteger(Number(seed))}
              onClick={()=>void loadNativeBirthSporting()}>{cs?'Prověřit sportovní vývoj narozených hráčů':'Review newborn sporting development'}</button>
          </>}
          {birthSportingReport&&<section aria-label="Verified read-only native sporting review">
            <h4>{cs?'Ověřený sportovní přechod (pouze náhled)':'Verified sporting transition (review only)'}</h4>
            <p>{cs?'Seed':'Seed'}: {birthSportingReport.sporting_week_projection.seed} · {cs?'Hráči':'Players'}: {birthSportingReport.sporting_week_projection.old_population_count} → {birthSportingReport.sporting_week_projection.new_population_count} · {cs?'Aktivní v minulém týdnu':'Played last week'}: {birthSportingReport.sporting_week_projection.played_player_count}</p>
            <p>{cs?'Výsledná sportovní populace':'Resulting sporting population'}: <code>{birthSportingReport.sporting_week_projection.target_players_fingerprint.slice(0,16)}</code></p>
            <p>{cs?'Spojený podpis Health + lifecycle + sporting':'Combined Health + lifecycle + sporting proof'}: <code>{birthSportingReport.sporting_week_projection.signed_admission_week_fingerprint.slice(0,16)}</code></p>
            <p>{cs?'Bez zápisu. Skutečná aktivace nových hráčů zůstává zablokovaná.':'No write. Actual newborn activation remains disabled.'}</p>
          </section>}
        </div>}
      </section>}
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
          <label>{cs?'Sezóna (pořadové číslo)':'Season number'}<input aria-label="Tour Edition season" type="number" min="1" max={clock?.calendar.season_count} value={season} onChange={e=>{setSeason(e.target.value);invalidate()}}/></label>
          <label>{cs?'Týden v sezóně':'Week in season'}<input aria-label="Tour Edition week" type="number" min="1" max={clock?.calendar.weeks_per_year} value={week} onChange={e=>{setWeek(e.target.value);invalidate()}}/></label>
          {plannedEdition?<p>{cs?'Oznámení v':'Announcement at'} S{plannedEdition.announcement_week.season_index+1}/W{plannedEdition.announcement_week.week} · {cs?'Turnaj':'Edition'} S{plannedEdition.week.season_index+1}/W{plannedEdition.week.week}</p>:<p role="status">{cs?'Vyberte termín alespoň dva týdny dopředu a uvnitř horizontu Runu.':'Choose a date at least two weeks ahead within the Run horizon.'}</p>}
          <label>{cs?'První globální slot':'First global slot'}<input aria-label="Tour Edition slot" type="number" value={slot} onChange={e=>{setSlot(e.target.value);invalidate()}}/></label>
          <label>{cs?'Účastníci':'Participants'}<select aria-label="Tour Edition size" value={size} onChange={e=>{setSize(Number(e.target.value));invalidate()}}><option>8</option><option>4</option></select></label>
          {Object.entries(points).filter(([k])=>size===8||k!=='quarterfinal').map(([stage,value])=><label key={stage}>{cs?stageLabels[stage]:stage}<input aria-label={`Tour points ${stage}`} type="number" value={value} onChange={e=>{setPoints({...points,[stage]:e.target.value});invalidate()}}/></label>)}
          <p>{cs?'Platnost bodů':'Point validity'}: {view.state.week.calendar.weeks_per_year} {cs?'týdnů od prvního oficiálního rankingu':'weeks from first Official ranking'}</p>
          <button disabled={!ready||!plannedEdition||!editionId.trim()||!name.trim()} onClick={()=>void perform('create-edition')}>{cs?'Zkontrolovat novou Edition':'Review new Edition'}</button>
        </details>
        {view.state.editions.map(a=>{
          const id=a.edition.edition_id,active=a.edition.week.week===view.state!.week.week&&a.edition.week.season_index===view.state!.week.season_index
          const next: keyof typeof actionLabels=!a.field?'approve':!a.draw?'draw':!a.tournament_fingerprint?'play':'confirm-result'
          return <section key={id} aria-label={`Edition ${id}`}>
            <h3>{a.edition.name} · S{a.edition.week.season_index+1}/W{a.edition.week.week}</h3>
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
        {view.state.week.week===view.state.week.calendar.weeks_per_year&&<section aria-label="Native Season Transition readiness">
          <h3>{cs?'Přechod do další sezóny':'Transition to next season'}</h3>
          <p>{cs?'Závěrečný týden sezóny se dokončí podle uložených pravidel. Ranking nové sezóny využije účinnou sezónní politiku a skutečně odehrané výsledky.':'The final week uses its saved rules. The next season ranking uses its effective policy and actual played results.'}</p>
          {view.season_transition_blockers.length>0&&<ul>{view.season_transition_blockers.map(b=><li key={b}>{b.startsWith('edition_not_terminal:')?b:blockerLabels[b]?.[cs?0:1]??b}</li>)}</ul>}
          <button disabled={!ready||!view.saved||view.season_transition_blockers.length>0} onClick={()=>void perform('season-transition')}>{cs?'Zkontrolovat Season Transition':'Review Season Transition'}</button>
        </section>}
        {view.saved_completed_seasons.length>0&&<section aria-label="Saved native season summaries">
          <h3>{cs?'Uložená historie sezón':'Saved season history'}</h3>
          <p>{cs?'Pouze dokončené sezóny z ověřené Saved Revision. Udělené body nejsou totéž co aktuální Official Ranking.':'Only completed seasons from the verified Saved Revision. Awarded points differ from current Official Ranking points.'}</p>
          <label>{cs?'Sezóna':'Season'}<select aria-label="Signed season" value={historySeason} onChange={e=>{setHistorySeason(e.target.value);setSeasonReport(null);seasonReadRequest.current++}}>
            {view.saved_completed_seasons.map(index=><option key={index} value={index}>S{index+1}</option>)}
          </select></label>
          <label>{cs?'Porovnat s':'Compare with'}<select aria-label="Signed comparison season" value={comparisonSeason} onChange={e=>{setComparisonSeason(e.target.value);setSeasonReport(null);seasonReadRequest.current++}}>
            <option value="">{cs?'Bez porovnání':'No comparison'}</option>
            {view.saved_completed_seasons.filter(index=>index!==Number(historySeason)).map(index=><option key={index} value={index}>S{index+1}</option>)}
          </select></label>
          <button disabled={busy||!historySeason} onClick={()=>void loadSeasonReport()}>{cs?'Načíst přehled sezóny':'Load season summary'}</button>
          {seasonReport&&<div aria-label="Verified season summary">
            <p><strong>{cs?'Sezóna':'Season'} {seasonReport.selected.season_label}</strong> · {seasonReport.selected.completed_edition_count} {cs?'dokončených turnajů':'completed Editions'} · Saved HEAD <code>{seasonReport.saved_head_revision_id}</code></p>
            <table aria-label="Country season comparison"><thead><tr><th>{cs?'Země':'Country'}</th><th>{cs?'Tituly':'Titles'}</th><th>{cs?'Finále':'Finals'}</th><th>{cs?'Udělené body':'Awarded points'}</th>{seasonReport.comparison&&<th>{cs?'Rozdíl titulů / bodů':'Delta titles / points'}</th>}</tr></thead>
              <tbody>{seasonReport.selected.countries.map(row=>{
                const change=seasonReport.country_deltas.find(x=>x.country_code===row.country_code)
                return <tr key={row.country_code}><td>{row.country_code}</td><td>{row.titles}</td><td>{row.finals}</td><td>{row.awarded_points}</td>{seasonReport.comparison&&<td>{change?.titles_delta??0} / {change?.awarded_points_delta??0}</td>}</tr>
              })}</tbody></table>
            {seasonReport.comparison&&<p>{cs?'Srovnání proti sezóně':'Compared with season'} {seasonReport.comparison.season_label}. {cs?'Země přítomné pouze ve srovnávané sezóně':'Countries present only in the comparison season'}: {seasonReport.country_deltas.filter(r=>!seasonReport.selected.countries.some(c=>c.country_code===r.country_code)).map(r=>r.country_code).join(', ')||'—'}</p>}
            <details><summary>{cs?'Turnaje a finalisté':'Editions and finalists'}</summary>
              {seasonReport.selected.editions.map(e=><p key={e.edition_id}>{e.name} · W{e.week}: {e.champion_name} ({e.champion_country}) / {e.finalist_name} ({e.finalist_country})</p>)}
            </details>
            <details><summary>{cs?'Jednotliví hráči':'Individual players'}</summary>
              <table><thead><tr><th>{cs?'Hráč':'Player'}</th><th>{cs?'Země':'Country'}</th><th>{cs?'Tituly':'Titles'}</th><th>{cs?'Body':'Points'}</th></tr></thead><tbody>{seasonReport.selected.players.map(p=><tr key={p.player_id}><td>{p.name}</td><td>{p.country_code}</td><td>{p.titles}</td><td>{p.awarded_points}</td></tr>)}</tbody></table>
            </details>
            <p>{cs?'Poslední ranking publikovaný v sezóně':'Last ranking published within the season'}: W{seasonReport.selected.last_week_published_ranking.week}</p>
          </div>}
        </section>}
        {view.saved_completed_seasons.length>0&&<section aria-label="Signed career records">
          <h3>{cs?'Historické rekordy a rekordmani':'Historical records and holders'}</h3>
          <p>{cs?'Výhradně dokončené a uložené sezóny. Rekordy ze skutečných turnajů, nikoli aktuální body v Official Rankingu. Shoda na čele znamená více rekordmanů.':'Completed Saved seasons only. Real Edition records, not current Official Ranking points. Ties retain all record holders.'}</p>
          <label>{cs?'Konec období':'Period ends at'}<select aria-label="Records as of season" value={recordAsOf} onChange={e=>{setRecordAsOf(e.target.value);if(Number(recordStart)>Number(e.target.value))setRecordStart('0');setCareerRecords(null);careerReadRequest.current++}}>
            {view.saved_completed_seasons.map(i=><option key={i} value={i}>S{i+1}</option>)}
          </select></label>
          <label>{cs?'Začátek období':'Period begins at'}<select aria-label="Records from season" value={recordStart} onChange={e=>{setRecordStart(e.target.value);setCareerRecords(null);careerReadRequest.current++}}>
            {view.saved_completed_seasons.filter(i=>i<=Number(recordAsOf)).map(i=><option key={i} value={i}>S{i+1}</option>)}
          </select></label>
          <label>{cs?'Země (ISO-3, nepovinné)':'Country (ISO-3, optional)'}<input aria-label="Records country" maxLength={3} placeholder="CZE" value={recordCountry} onChange={e=>{setRecordCountry(e.target.value.trim().toUpperCase());setCareerRecords(null);careerReadRequest.current++}}/></label>
          <button disabled={busy||!recordAsOf||!view.saved_completed_seasons.includes(Number(recordStart))||(recordCountry!==''&&!/^[A-Z]{3}$/.test(recordCountry))} onClick={()=>void loadCareerRecords()}>{cs?'Načíst historické rekordy':'Load historical records'}</button>
          {careerRecords&&<div aria-label="Verified career records">
            <p><strong>{cs?'Období':'Period'} S{careerRecords.from_season_index+1}–S{careerRecords.as_of_season_index+1}</strong> · {careerRecords.completed_edition_count} {cs?'dokončených turnajů':'completed Editions'} · {cs?'Filtr':'Filter'} {careerRecords.country_code??(cs?'všechny země':'all countries')} · Saved HEAD <code>{careerRecords.saved_head_revision_id}</code></p>
            {careerRecords.records.map(entry=>{
              const name=entry.metric==='titles'?(cs?'Tituly':'Titles'):entry.metric==='finals'?(cs?'Finálové účasti bez titulu':'Runner-up finishes'):(cs?'Udělené body z turnajů':'Original Edition awarded points')
              return <details key={entry.record_id}>
                <summary>{entry.scope==='player'?(cs?'Hráči':'Players'):(cs?'Země':'Countries')} · {name} · {cs?'Rekord':'Record'}: {entry.value} · {cs?'Rekordmani':'Holders'}: {entry.holders.map(h=>h.label).join(', ')||'—'}</summary>
                <table aria-label={entry.record_id}><thead><tr><th>#</th><th>{cs?'Jméno / země':'Name / country'}</th><th>{cs?'Země':'Country'}</th><th>{cs?'Hodnota':'Value'}</th></tr></thead>
                  <tbody>{entry.leaderboard.map(h=><tr key={h.entity_id}><td>{h.rank}</td><td>{h.label}</td><td>{h.country_code}</td><td>{h[entry.metric]}</td></tr>)}</tbody></table>
                <p>{cs?'Historie rekordmanů – ke konci uložené sezóny':'Record-holder history at each Saved season closure'}</p>
                {entry.holder_history.map(change=><p key={change.season_index}>S{change.season_index+1}: {change.record_value} · {change.holder_labels.join(', ')} · {change.change} · <code>{change.boundary_command_id}</code></p>)}
              </details>
            })}
          </div>}
        </section>}
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
        {review.impact.ranking&&<p>{cs?'Nový týden':'New week'}: {review.impact.target_week?.season_index!==undefined? `${review.impact.target_week.season_index+1}/W${review.impact.target_week.week}`:review.impact.target_week?.week} · {cs?'Klasifikovaní hráči':'Classified players'}: {review.impact.ranking.rows.length} · {cs?'Změnění hráči':'Changed players'}: {review.impact.sporting?.changed_player_count} · {cs?'Změny atributů':'Attribute changes'}: {review.impact.sporting?.attribute_change_count}</p>}
        {review.impact.sporting?.changes&&<details><summary>{cs?'Dopady na hráče':'Player impacts'}</summary><table><thead><tr><th>{cs?'Hráč':'Player'}</th><th>{cs?'Změny atributů':'Attribute changes'}</th><th>Form</th><th>{cs?'Rozehranost':'Sharpness'}</th><th>{cs?'Únava':'Fatigue'}</th></tr></thead><tbody>{review.impact.sporting.changes.map(p=><tr key={p.player_id}><td>{names.get(p.player_id)??p.player_id}</td><td>{p.changed_attributes}</td><td>{p.form_before} → {p.form_after}</td><td>{p.sharpness_before} → {p.sharpness_after}</td><td>{p.fatigue_before} → {p.fatigue_after}</td></tr>)}</tbody></table></details>}
        <label><input aria-label="Confirm Tour command" type="checkbox" checked={consent} onChange={e=>setConsent(e.target.checked)}/>{review.command.action==='season-transition'?(cs?'Výslovně potvrzuji přechod do další sezóny podle těchto uložených vstupů.':'I explicitly confirm the next season using these saved inputs.'):(cs?'Potvrzuji tuto operaci nad zobrazeným vstupem.':'I confirm this operation over the displayed inputs.')}</label>
        <button disabled={busy||!consent} onClick={()=>void perform('commit')}>{cs?'Provést potvrzenou operaci':'Execute confirmed operation'}</button></section>}
      {view.state&&!view.saved&&<><label><input aria-label="Confirm Tour Save" type="checkbox" checked={saveConsent} onChange={e=>setSaveConsent(e.target.checked)}/>{cs?'Uložit společně Tour, sportovní stav a ranking.':'Save Tour, sporting state and ranking together.'}</label><button disabled={busy||!saveConsent} onClick={()=>void perform('save')}>{cs?'Ruční Save Tour':'Manual Tour Save'}</button></>}
    </>}
  </section>
}
