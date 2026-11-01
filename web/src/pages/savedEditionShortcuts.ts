/** Browser-local saved Edition shortcuts, NOT canonical Saved Views or Run data.
 * Links are reconstructed from individually checked identity fields. No stored
 * arbitrary URLs may redirect an Admin outside its current Run/Branch scope.
 */
export const SAVED_EDITION_SHORTCUT_STORAGE_KEY='squash-saved-edition-shortcuts.v1'
export const SAVED_EDITION_SHORTCUT_LIMIT=24

export type SavedEditionShortcutTab='overview'|'entries'|'draw'|'schedule'|'results'|'settings'
const tabs:readonly SavedEditionShortcutTab[]=['overview','entries','draw','schedule','results','settings']
export type SavedEditionShortcut={
  id:string;name:string;runId:string;branchId:string;revisionId:string
  eventId:string;seasonIndex:number;tab:SavedEditionShortcutTab;matchSearch:string
}
type SavedEditionShortcutInput=Omit<SavedEditionShortcut,'id'>

const nonempty=(s:unknown,max:number):s is string=>
  typeof s==='string'&&s.length>0&&s.length<=max&&s.trim()===s&&s.trim().length>0

export function validSavedEditionShortcut(value:unknown):value is SavedEditionShortcut{
  if(!value||typeof value!=='object'||Array.isArray(value))return false
  const p=value as Record<string,unknown>
  return nonempty(p.id,90)&&nonempty(p.name,72)
    &&nonempty(p.runId,180)&&nonempty(p.branchId,180)
    &&nonempty(p.revisionId,180)&&nonempty(p.eventId,180)
    &&typeof p.seasonIndex==='number'&&Number.isSafeInteger(p.seasonIndex)
    &&p.seasonIndex>=0&&p.seasonIndex<50
    &&tabs.includes(p.tab as SavedEditionShortcutTab)
    &&typeof p.matchSearch==='string'&&p.matchSearch.length<=120
    &&(p.tab==='results'||p.matchSearch==='')
}

export function loadSavedEditionShortcuts(raw:string|null):SavedEditionShortcut[]{
  if(!raw||raw.length>20000)return []
  try{
    const parsed:unknown=JSON.parse(raw)
    if(!parsed||typeof parsed!=='object'||Array.isArray(parsed))return []
    const bundle=parsed as Record<string,unknown>
    if(bundle.schema_version!=='saved_edition_shortcuts.v1'||!Array.isArray(bundle.items)
      ||bundle.items.length>SAVED_EDITION_SHORTCUT_LIMIT)return []
    const seen=new Set<string>()
    const items:SavedEditionShortcut[]=[]
    for(const item of bundle.items){
      if(!validSavedEditionShortcut(item)||seen.has(item.id))return []
      seen.add(item.id);items.push(item)
    }
    return items
  }catch{return []}
}

export function serializeSavedEditionShortcuts(items:readonly SavedEditionShortcut[]):string{
  if(items.length>SAVED_EDITION_SHORTCUT_LIMIT||items.some(item=>!validSavedEditionShortcut(item))
    ||new Set(items.map(item=>item.id)).size!==items.length)
    throw Error('Invalid saved Edition shortcut store')
  const value=JSON.stringify({schema_version:'saved_edition_shortcuts.v1',items})
  if(value.length>20000)throw Error('Saved Edition shortcuts exceed local storage allowance')
  return value
}

/** Never render a stored href; always construct a same-Run path. The backend
 * still verifies that this saved revision remains reachable on the Branch. */
export function savedEditionShortcutHref(item:SavedEditionShortcut):string|null{
  if(!validSavedEditionShortcut(item))return null
  const q=new URLSearchParams()
  q.set('branch',item.branchId);q.set('revision',item.revisionId)
  q.set('season',String(item.seasonIndex));q.set('tab',item.tab)
  if(item.tab==='results'&&item.matchSearch)q.set('matchSearch',item.matchSearch)
  return '/admin/runs/'+encodeURIComponent(item.runId)
    +'/tour/calendar/'+encodeURIComponent(item.eventId)+'?'+q.toString()
}

export function createSavedEditionShortcut(
  source:SavedEditionShortcutInput,id:string,
):SavedEditionShortcut{
  const item={...source,id}
  if(!validSavedEditionShortcut(item))throw Error('Invalid Saved Edition shortcut context')
  return item
}

/** Existing same exact view is renamed/moved to front, not duplicated.
 * A different revision or result filter remains a separate explicit bookmark. */
export function upsertSavedEditionShortcut(
  items:readonly SavedEditionShortcut[],next:SavedEditionShortcut,
):SavedEditionShortcut[]{
  if(!validSavedEditionShortcut(next))throw Error('Invalid Saved Edition shortcut')
  const same=(item:SavedEditionShortcut)=>item.runId===next.runId
    &&item.branchId===next.branchId&&item.revisionId===next.revisionId
    &&item.eventId===next.eventId&&item.seasonIndex===next.seasonIndex
    &&item.tab===next.tab&&item.matchSearch===next.matchSearch
  const prior=items.find(same)
  const remaining=items.filter(item=>!same(item)&&item.id!==next.id)
  const updated=[{...next,id:prior?.id??next.id},...remaining]
  if(updated.length>SAVED_EDITION_SHORTCUT_LIMIT)
    throw Error('Maximum number of Saved Edition shortcuts reached')
  // Fails closed on malformed previously stored data; no partial write.
  serializeSavedEditionShortcuts(updated)
  return updated
}

export function scopedSavedEditionShortcuts(
  items:readonly SavedEditionShortcut[],runId:string,branchId:string,
):SavedEditionShortcut[]{
  return items.filter(item=>validSavedEditionShortcut(item)
    &&item.runId===runId&&item.branchId===branchId)
}
