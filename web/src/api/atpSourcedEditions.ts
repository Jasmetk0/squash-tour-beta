export type ATPSourcedEditionCatalog={run_id:string;branch_id:string;saved_head_revision_id:string;entries:{
  profile:{schema_version?:string;main_entrants?:number;qualification_entrants?:number;qualifier_spots?:number;occurrence_id:string;name:string;source_start_date:string;source_end_date:string;
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
  if(!value||value.run_id!==run||value.branch_id!==branch||value.saved_head_revision_id!==head||!Array.isArray(value.entries))
    throw Error('ATP source changed. Refresh the Tour.')
  const ids=new Set<string>()
  for(const entry of value.entries){
    const p=entry?.profile,projection=entry?.calendar_projection
    const knockout=p?.schema_version==='atp_squash_knockout_profile.v1'
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
