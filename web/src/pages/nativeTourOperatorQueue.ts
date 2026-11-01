import type {TourView, TourEdition} from '../api/calendarTour'

export type NativeTourOperatorStage =
  | 'applications' | 'field' | 'draw' | 'group_tie' | 'play' | 'results' | 'reviewed'
export type NativeTourOperatorPeriod = 'past' | 'current' | 'future'

export type NativeTourOperatorItem = {
  editionId:string
  name:string
  sourceIndex:number
  seasonIndex:number
  week:number
  period:NativeTourOperatorPeriod
  stage:NativeTourOperatorStage
  applications:number
  mainField:number
  matches:number
  results:number
}
export type NativeTourOperatorQueue = {
  source:{runId:string;branchId:string;savedHead:string;workingDraft:boolean}
  current:{seasonIndex:number;week:number}
  items:NativeTourOperatorItem[]
}

const validInteger=(v:unknown,min:number,max:number)=>Number.isSafeInteger(v) && typeof v==='number' && v>=min && v<=max

const stage=(edition:TourEdition,tie:boolean):NativeTourOperatorStage=>{
  if(edition.result_confirmed)return 'reviewed'
  if(tie)return 'group_tie'
  if(edition.tournament_fingerprint)return 'results'
  if(edition.draw)return 'play'
  if(edition.field)return 'draw'
  if(edition.submissions.length>0)return 'field'
  return 'applications'
}

/**
 * Source-exact *read only* index of the existing verified native Tour inspection.
 * A stage is descriptive evidence, NOT a server preflight/permission to execute.
 * Never infer player eligibility, completed Save, global-slot ownership or points.
 */
export function deriveNativeTourOperatorQueue(
  view:TourView,runId:string,branchId:string,
):NativeTourOperatorQueue{
  const now=view?.state?.week
  const max=now?.calendar?.weeks_per_year
  if(view?.schema_version!=='calendar_tour_inspection.v1'
    ||view.run_id!==runId||view.branch_id!==branchId
    ||typeof view.saved_head_revision_id!=='string'||!view.saved_head_revision_id
    ||typeof view.saved!=='boolean'
    ||!now||!validInteger(max,1,100)
    ||!validInteger(now.season_index,0,10000)||!validInteger(now.week,1,max!)
    ||!Array.isArray(view.state?.editions)||!view.edition_evidence
    ||typeof view.edition_evidence!=='object'||Array.isArray(view.edition_evidence))
    throw Error('Native Tour operator queue has no verified Run/Branch/Week source')
  const seen=new Set<string>()
  const items=view.state.editions.map((item,index):NativeTourOperatorItem=>{
    const edition=item?.edition
    const when=edition?.week
    const id=edition?.edition_id
    const evidence=typeof id==='string'?view.edition_evidence[id]:undefined
    if(!item||!edition||typeof id!=='string'||id.length===0||seen.has(id)
      ||typeof edition.name!=='string'||!edition.name.trim()
      ||!when||!validInteger(when.season_index,0,10000)
      ||!validInteger(when.week,1,max!)||!when.calendar
      ||when.calendar.weeks_per_year!==max
      ||!Array.isArray(item.submissions)
      ||item.submissions.some(s=>!s||typeof s.player_id!=='string'||!s.player_id)
      ||!(item.field===null||(item.field
        &&Array.isArray(item.field.direct_main_player_ids)
        &&Array.isArray(item.field.below_qualification_cut_player_ids)))
      ||typeof item.result_confirmed!=='boolean'
      ||(evidence&&(!Array.isArray(evidence.matches)||!Array.isArray(evidence.results))))
      throw Error('Native Tour operator queue contains invalid or duplicate Edition evidence')
    seen.add(id)
    const t=when.season_index*max!+when.week
    const current=now.season_index*max!+now.week
    const period:NativeTourOperatorPeriod=t<current?'past':t===current?'current':'future'
    return{
      editionId:id,name:edition.name,sourceIndex:index,
      seasonIndex:when.season_index,week:when.week,
      period,stage:stage(item,Boolean(view.groups?.[id]?.tie_case)),
      applications:item.submissions.length,
      mainField:item.field?.direct_main_player_ids.length??0,
      matches:evidence?.matches.length??0,
      results:evidence?.results.length??0,
    }
  })
  items.sort((a,b)=>{
    const pa=a.period==='current'?0:a.period==='past'?1:2
    const pb=b.period==='current'?0:b.period==='past'?1:2
    return pa-pb||a.seasonIndex-b.seasonIndex||a.week-b.week
      ||a.editionId.localeCompare(b.editionId)
  })
  return{
    source:{runId,branchId,savedHead:view.saved_head_revision_id,workingDraft:!view.saved},
    current:{seasonIndex:now.season_index,week:now.week},items,
  }
}
