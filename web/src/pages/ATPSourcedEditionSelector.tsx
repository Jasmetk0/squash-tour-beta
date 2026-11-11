import {useRef,useState} from 'react'
import {inspectATPSourcedEditions} from '../api/client'
import type {ATPSourcedEditionCatalog} from '../api/atpSourcedEditions'
import {validateATPSourcedEditionCatalog} from '../api/atpSourcedEditions'
import type {TourWeek} from '../api/calendarTour'
import {scheduleTourEdition} from '../api/nativeTourCalendar'
import {useLanguage} from '../i18n/LanguageContext'
import {formatApiError} from '../utils/apiErrors'

export function ATPSourcedEditionSelector({runId,branchId,head,clock,existing,disabled,onSelect}:{
  runId:string;branchId:string;head:string;clock:TourWeek;existing:string[];disabled:boolean;onSelect:(id:string)=>void;
}) {
  const cs=useLanguage().language==='cs'
  const scope=JSON.stringify([runId,branchId,head,clock]),current=useRef(scope)
  current.current=scope
  const [catalog,setCatalog]=useState<{scope:string;value:ATPSourcedEditionCatalog}|null>(null)
  const [busy,setBusy]=useState(false),[error,setError]=useState<string|null>(null)
  const entries=catalog?.scope===scope?catalog.value.entries:[]
  const load=async()=>{
    const stamp=scope
    setBusy(true);setError(null);setCatalog(null)
    try{
      const value=await inspectATPSourcedEditions(runId,branchId)
      if(current.current!==stamp)return
      setCatalog({scope:stamp,value:validateATPSourcedEditionCatalog(value,runId,branchId,head)})
    }catch(e){if(current.current===stamp)setError(formatApiError(e))}
    finally{setBusy(false)}
  }
  return <section aria-label="Saved ATP sporting profiles">
    <p>{cs?'Načti sportovní formáty z uloženého ATP balíčku. Hráče zatím vybírá Admin; automatická nominace podle Race a věku není zapojena.':'Load sporting formats from the Saved ATP Package. Admin selects entrants; automatic Race and age qualification is not connected.'}</p>
    <button disabled={busy||disabled} onClick={()=>void load()}>{cs?'Načíst ATP turnaje z balíčku':'Load ATP tournaments from Package'}</button>
    {error&&<p role="alert">{error}</p>}
    {entries.map(({profile:p,calendar_projection:projection})=>{
      const target=projection.run_weeks?.[0]
      const knockout=p.schema_version==='atp_squash_knockout_profile.v1'||p.schema_version==='atp_squash_knockout_profile.v2'
      const qualification=p.qualification_date_evidence
      const possible=!knockout&&target&&projection.run_weeks?.length===1&&!projection.source_finish_after_mapped_occupancy&&
        scheduleTourEdition(clock,target.season_index,target.season_week)&&
        (projection.run_ordinals?.[0]??-1)-p.native_announcement_lead_weeks>
          clock.season_index*clock.calendar.weeks_per_year+clock.week-1
      return <div key={p.occurrence_id}>
        <p>{p.name} · {p.source_start_date} – {p.source_end_date}</p>
        {knockout?<p>{cs?'Hlavní pavouk':'Main draw'} {p.main_entrants} · {cs?'Kvalifikace':'Qualification'} {p.qualification_entrants} → {p.qualifier_spots}</p>:
          <p>{p.group_count} × {p.group_size} · {cs?'Body za výhru ve skupině':'Points per group win'} {p.played_group_win_points}</p>}
        {existing.includes(p.occurrence_id)?<p>{cs?'Edition už existuje.':'Edition already exists.'}</p>:
          <button disabled={busy||disabled||!possible} onClick={()=>onSelect(p.occurrence_id)}>{cs?'Zkontrolovat import':'Review import'} {p.name}</button>}
        {knockout&&qualification&&<p>{cs?'Ověřený termín kvalifikace':'Verified Qualification dates'}: {qualification.start_date} – {qualification.end_date}</p>}
        {knockout?<p>{qualification?
          (cs?'Struktura a termín kvalifikace jsou ověřené. Simulace tohoto formátu zatím není dostupná.':'Structure and Qualification dates verified. Simulation of this format is not available yet.'):
          (cs?'Struktura je ověřená. Simulace čeká na ověření termínu kvalifikace a napojení bodovaného pavouku na W52.':'Structure verified. Simulation awaits verified Qualification dates and W52 ranked knockout integration.')}</p>:
          !possible&&<p>{cs?'Termín nebo předchozí oznámení není dostupné v tomto Runu.':'The event or preceding announcement is unavailable in this Run.'}</p>}
      </div>
    })}
  </section>
}
