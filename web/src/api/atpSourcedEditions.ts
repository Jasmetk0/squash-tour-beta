export type ATPSourcedEditionCatalog={run_id:string;branch_id:string;saved_head_revision_id:string;entries:{
  profile:{schema_version?:string;main_entrants?:number;qualification_entrants?:number;qualifier_spots?:number;occurrence_id:string;name:string;source_start_date:string;source_end_date:string;
    qualification_date_status?:'not_verified'|'verified';
    qualification_date_evidence?:{start_date:string;end_date:string;source_urls:string[];published_dates:string[]};
    group_count:number;group_size:number;ranked:boolean;played_group_win_points:number;
    native_announcement_lead_weeks:number;entrant_selection:'admin_selected_no_automatic_race_or_age'};
  profile_fingerprint:string;
  execution_supported?:boolean;
  execution_blockers?:string[];
  calendar_projection:{run_ordinals?:number[];run_weeks?:{season_index:number;season_week:number}[];source_finish_after_mapped_occupancy?:boolean};
}[]}

/** Treat server responses as untrusted until their Saved scope and shape agree. */
export function validateATPSourcedEditionCatalog(value:ATPSourcedEditionCatalog,run:string,branch:string,head:string):ATPSourcedEditionCatalog {
  const integer=(n:unknown,min:number)=>typeof n==='number'&&Number.isSafeInteger(n)&&n>=min
  const isoDate=(value:unknown):value is string=>{
    if(typeof value!=='string'||!/^\d{4}-\d{2}-\d{2}$/.test(value))return false
    const parsed=new Date(value+'T00:00:00Z')
    return Number.isFinite(parsed.getTime())&&parsed.toISOString().slice(0,10)===value
  }
  if(!value||value.run_id!==run||value.branch_id!==branch||value.saved_head_revision_id!==head||!Array.isArray(value.entries))
    throw Error('ATP source changed. Refresh the Tour.')
  const ids=new Set<string>()
  for(const entry of value.entries){
    const p=entry?.profile,projection=entry?.calendar_projection
    const knockout=p?.schema_version==='atp_squash_knockout_profile.v1'||p?.schema_version==='atp_squash_knockout_profile.v2'
    const evidence=p?.qualification_date_evidence
    if(p?.schema_version!==undefined&&!['atp_squash_group_profile.v1','atp_squash_knockout_profile.v1','atp_squash_knockout_profile.v2'].includes(p.schema_version))
      throw Error('Unsupported Saved ATP sporting profile version')
    if(p?.schema_version==='atp_squash_knockout_profile.v1'&&
      (evidence!==undefined||p.qualification_date_status==='verified'))
      throw Error('Historical ATP profile cannot acquire verified Qualification dates')
    if(p?.schema_version==='atp_squash_knockout_profile.v2'&&(
      p.qualification_date_status!=='verified'||!evidence||
      !isoDate(evidence.start_date)||!isoDate(evidence.end_date)||
      evidence.start_date>evidence.end_date||evidence.start_date>p.source_start_date||evidence.end_date>p.source_end_date||
      !Array.isArray(evidence.source_urls)||evidence.source_urls.length===0||
      !evidence.source_urls.every(url=>typeof url==='string'&&url.startsWith('https://'))||
      !Array.isArray(evidence.published_dates)||evidence.published_dates.length!==evidence.source_urls.length||
      !evidence.published_dates.every(d=>isoDate(d)&&d<=evidence.start_date)))
      throw Error('Invalid Saved ATP Qualification date evidence')
    if(!p||!/^atp_[0-9]{4}_[a-z0-9_]+$/.test(p.occurrence_id)||ids.has(p.occurrence_id)||
      typeof p.name!=='string'||!p.name.trim()||!/^\d{4}-\d{2}-\d{2}$/.test(p.source_start_date)||
      !/^\d{4}-\d{2}-\d{2}$/.test(p.source_end_date)||typeof p.ranked!=='boolean'||
      (knockout?(!integer(p.main_entrants,2)||!integer(p.qualification_entrants,2)||!integer(p.qualifier_spots,1)||entry.execution_supported!==false):
        (!integer(p.group_count,1)||!integer(p.group_size,2)||!integer(p.played_group_win_points,0)||!integer(p.native_announcement_lead_weeks,1)))||
      p.entrant_selection!=='admin_selected_no_automatic_race_or_age'||
      !/^[0-9a-f]{64}$/.test(entry.profile_fingerprint)||!projection||
      (projection.run_weeks!==undefined&&(!Array.isArray(projection.run_weeks)||
        !Array.isArray(projection.run_ordinals)||projection.run_weeks.length!==projection.run_ordinals.length||
        !projection.run_weeks.every(w=>integer(w.season_index,0)&&integer(w.season_week,1))||
        !projection.run_ordinals.every(n=>integer(n,0)))))
      throw Error('Invalid Saved ATP sporting profile catalog')
    ids.add(p.occurrence_id)
  }
  return value
}
