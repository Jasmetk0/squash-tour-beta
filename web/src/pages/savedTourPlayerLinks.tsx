/** Shared, read-only player links across immutable Saved Tour screens. */
import {Link} from 'react-router-dom'
import {savedSeasonFinalLookupHref} from './savedTourCalendarDiscovery'

type ProfileProps={runId:string;playerId:string;showCurrent:boolean}
/** The caller must validate exact Run/Branch/Revision and only allow a current HEAD. */
export function SavedPlayerProfileLink({runId,playerId,showCurrent}:ProfileProps):JSX.Element{
  return showCurrent?<Link to={'/admin/runs/'+encodeURIComponent(runId)+
    '/people/'+encodeURIComponent(playerId)+'?tab=career'}>{playerId}</Link>:<>{playerId}</>
}

type FinalLookupProps={
  runId:string;branch:string;revision:string;season:number
  playerId:string;params:URLSearchParams;cs:boolean
}
/** An archived final lookup is distinct from navigating to a current player career. */
export function SavedFinalLookupLink({
  runId,branch,revision,season,playerId,params,cs
}:FinalLookupProps):JSX.Element{
  return <Link to={savedSeasonFinalLookupHref(
    runId,branch,revision,season,playerId,params
  )} aria-label={(cs?'Dohledat publikovaná finále hráče ':'Find published finals for ')+playerId}>
    {playerId}</Link>
}
