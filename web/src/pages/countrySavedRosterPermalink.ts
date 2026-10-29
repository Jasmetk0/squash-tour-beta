/** Deep links for the exact present-time Saved Country roster.
 * URL state is a view hint only, not authorisation of source or player identity.
 */
export type CountryRosterViewState={
  search:string;status:string;includePrepared:boolean;page:number
}
export const DEFAULT_COUNTRY_ROSTER_VIEW:CountryRosterViewState={
  search:'',status:'',includePrepared:false,page:0,
}
const owned=['spScope','spSearch','spStatus','spPrepared','spPage'] as const
const MAX_PAGE=1_000_000

function safeFilter(v:string|null,max:number):string{
  return v!==null&&v.length<=max&&v===v.trim()?v:''
}

export function readCountryRosterPermalink(
  params:URLSearchParams,scope:string,
):CountryRosterViewState{
  if(params.get('spScope')!==scope)return {...DEFAULT_COUNTRY_ROSTER_VIEW}
  const p=params.get('spPage')
  const n=p&&/^[1-9]\d{0,6}$/.test(p)?Number(p):1
  const page=Number.isSafeInteger(n)&&n>=1&&n<=MAX_PAGE?n-1:0
  return {
    search:safeFilter(params.get('spSearch'),120),
    status:safeFilter(params.get('spStatus'),80),
    includePrepared:params.get('spPrepared')==='1',
    page,
  }
}

/** Preserve World context (year, country filters), replacing only roster-owned keys. */
export function writeCountryRosterPermalink(
  params:URLSearchParams,scope:string,state:CountryRosterViewState,
):URLSearchParams{
  const result=new URLSearchParams(params)
  for(const key of owned)result.delete(key)
  result.set('tab','players')
  result.set('spScope',scope)
  if(state.search)result.set('spSearch',state.search)
  if(state.status)result.set('spStatus',state.status)
  if(state.includePrepared)result.set('spPrepared','1')
  if(state.page>0)result.set('spPage',String(state.page+1))
  return result
}
export function countryRosterReturnPath(
  runId:string,countryCode:string,params:URLSearchParams,
):string{
  return '/admin/runs/'+encodeURIComponent(runId)+'/world/countries/'+
    encodeURIComponent(countryCode)+'?'+params.toString()
}

/** Reject external, cross-Run, non-country, historical and cross-country redirects. */
export function safeCountryRosterReturn(
  value:string|null,runId:string,countryCode:string|null,
  branchId:string|null,savedHead:string|null,
):string|null{
  if(!value||value.length>2500||!runId||!branchId||!savedHead||
    !/^[A-Z]{3}$/.test(countryCode??''))return null
  const exact='/admin/runs/'+encodeURIComponent(runId)+'/world/countries/'+countryCode
  const scope=JSON.stringify([runId,branchId,savedHead,countryCode])
  try {
    const url=new URL(value,'https://country-roster.local')
    if(url.origin!=='https://country-roster.local'||url.username||url.password||
      url.pathname!==exact||!value.startsWith(exact+'?')||
      url.searchParams.get('tab')!=='players'||
      url.searchParams.getAll('spScope').length!==1||
      url.searchParams.get('spScope')!==scope||
      url.searchParams.has('revision')||url.hash)return null
    return url.pathname+url.search
  }catch{return null}
}
