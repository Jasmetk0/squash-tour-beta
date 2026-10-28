/** Exact numeric jump guard for a read-only, paginated Saved rally archive. */
export function parseSavedReplayRally(raw:string,total:number):number|null{
  if(!Number.isSafeInteger(total)||total<1||!/^[1-9]\d*$/.test(raw))return null
  const value=Number(raw)
  return Number.isSafeInteger(value)&&value<=total?value:null
}
