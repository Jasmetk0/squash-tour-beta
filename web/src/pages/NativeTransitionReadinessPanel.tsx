import {useEffect,useRef,useState} from 'react'
import {inspectCalendarTourTransitionReadiness} from '../api/client'
import type {TourView} from '../api/calendarTour'
import {validateNativeTransitionReadiness,type NativeTransitionReadiness} from '../api/nativeTransitionReadiness'
import {useLanguage} from '../i18n/LanguageContext'
import {formatApiError} from '../utils/apiErrors'

export function NativeTransitionReadinessPanel({view,disabled}:{view:TourView;disabled:boolean}){
  const cs=useLanguage().language==='cs'
  const scope=JSON.stringify([view.run_id,view.branch_id,view.saved_head_revision_id,view.checkpoint_fingerprint,view.tour_fingerprint,view.run_calendar,view.state?.week,disabled])
  const active=useRef(scope),generation=useRef(0),controller=useRef<AbortController|null>(null)
  if(active.current!==scope){active.current=scope;generation.current++}
  const [result,setResult]=useState<{scope:string;token:number;report:NativeTransitionReadiness}|null>(null)
  const [error,setError]=useState<{scope:string;token:number;message:string}|null>(null)
  const [loading,setLoading]=useState<{scope:string;token:number}|null>(null)
  useEffect(()=>{controller.current?.abort();setLoading(null);return()=>{generation.current++;controller.current?.abort()}},[scope])
  const load=async()=>{
    const stamp=++generation.current,c=new AbortController();controller.current?.abort();controller.current=c
    setResult(null);setError(null);setLoading({scope,token:stamp})
    try{
      const raw=await inspectCalendarTourTransitionReadiness(view.run_id,view.branch_id,c.signal)
      if(stamp!==generation.current||active.current!==scope)return
      setResult({scope,token:stamp,report:validateNativeTransitionReadiness(raw,view)})
    }catch(e){if(stamp===generation.current&&active.current===scope&&!c.signal.aborted)setError({scope,token:stamp,message:formatApiError(e)})}
    finally{if(stamp===generation.current&&active.current===scope)setLoading(null)}
  }
  const report=result?.scope===scope&&result.token===generation.current?result.report:null
  return <section aria-label="Verified native transition capability">
    <h4>{cs?'Skutečná připravenost přechodu':'Actual transition readiness'}</h4>
    <p>{cs?'Pouze kontrola. Nic se neodsimuluje ani neuloží. Potom použijte běžnou kontrolu Week/Season Transition a samostatný Save.':'Read-only check. Nothing is simulated or saved. Then use the ordinary Week/Season Transition review and separate Save.'}</p>
    <button disabled={disabled||(loading?.scope===scope&&loading.token===generation.current)} onClick={()=>void load()}>{cs?'Ověřit možnosti přechodu':'Check transition capability'}</button>
    {error?.scope===scope&&error.token===generation.current&&<p role="alert">{error.message}</p>}
    {report&&<div aria-label="Verified transition readiness result">
      <p>{report.can_preview_transition?(cs?'Lze zkontrolovat přechod.':'Transition review is available.'):(cs?'Přechod je blokován.':'Transition is blocked.')} · {cs?'Již přijatí hráči':'Admitted players'}: {report.admitted_population_count}</p>
      {report.target_week?<p>{cs?'Cíl':'Target'}: S{report.target_week.season_index+1}/W{report.target_week.week}</p>:<p>{cs?'Konec horizontu Runu; nejprve jej prodlužte.':'Run horizon exhausted; extend it first.'}</p>}
      {report.due.map(p=><p key={p.player_id}>{cs?'Nový hráč':'New player'}: {p.display_name} · {p.country_code}</p>)}
      {report.blockers.map(b=><p key={b}>{b==='manual_save_required'?(cs?'Nejprve proveďte ruční Save.':'Manual Save is required first.'):b}</p>)}
      {report.target_scope==='native_competition'&&<p>{cs?'Po přijetí hráče a manuálním Save lze připravit novou Edition, přihlášky, los a skutečné zápasy.':'After admission and manual Save, new Editions, Entry, draws and real matches are available.'}</p>}
      {report.target_scope==='native_natural_transitions'&&<p>{cs?'Po narození jsou zatím podporovány jen přirozené přechody. Nové turnaje, přihlášky a zápasy ještě nejsou podporovány.':'After birth, only natural transitions are currently supported. New Editions, Entry and matches are not supported yet.'}</p>}
      <small>HEAD <code>{report.saved_head_revision_id}</code> · <code>{report.readiness_fingerprint}</code></small>
    </div>}
  </section>
}
