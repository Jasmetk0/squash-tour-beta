import {useEffect,useState} from 'react'
import {Link} from 'react-router-dom'
import {
  SAVED_EDITION_SHORTCUT_STORAGE_KEY as KEY,SAVED_EDITION_SHORTCUT_LIMIT,
  createSavedEditionShortcut,loadSavedEditionShortcuts,
  savedEditionShortcutHref,scopedSavedEditionShortcuts,
  serializeSavedEditionShortcuts,upsertSavedEditionShortcut,
  type SavedEditionShortcut,type SavedEditionShortcutTab,
} from '../pages/savedEditionShortcuts'

const labels={
  cs:{
    header:'Připnuté pohledy na uložené turnaje',
    hint:'Pouze místní záložky v tomto prohlížeči. Nejsou součástí Saved Runu, synchronizace ani exportu. Každý odkaz zachovává původní Branch a Saved Revision.',
    input:'Název pohledu',save:'Připnout aktuální pohled',
    open:'Otevřít',remove:'Odebrat',empty:'V této Branch zatím nejsou připnuté pohledy.',
    unavailable:'Místní úložiště prohlížeče není dostupné. Pohled nebyl uložen.',
    limit:'Limit připnutých pohledů byl dosažen.',
    caution:'Starší revize musí být stále dostupná v historii vybrané Branch. Nedostupný nebo cizí zdroj se nenačte.',
  },
  en:{
    header:'Pinned Saved Edition views',
    hint:'Browser-local bookmarks only. Not part of Saved Run data, sync or exports. Every link retains the original Branch and Saved Revision.',
    input:'View name',save:'Pin this view',
    open:'Open',remove:'Remove',empty:'No pinned views on this Branch yet.',
    unavailable:'Browser-local storage is unavailable. The view was not saved.',
    limit:'Pinned view limit reached.',
    caution:'Older revisions must still be reachable in the selected Branch history. Missing or foreign sources cannot be loaded.',
  },
} as const

function read():SavedEditionShortcut[]{
  return loadSavedEditionShortcuts(window.localStorage.getItem(KEY))
}

export function SavedEditionShortcuts({
  runId,branchId,revisionId,seasonIndex,eventId,eventName,tab,matchSearch,cs,
}:{
  runId:string;branchId:string;revisionId:string;seasonIndex:number
  eventId:string;eventName:string;tab:SavedEditionShortcutTab
  matchSearch:string;cs:boolean
}):JSX.Element{
  const t=labels[cs?'cs':'en']
  const [name,setName]=useState(eventName.slice(0,72))
  const [items,setItems]=useState<SavedEditionShortcut[]>(()=>{
    try{return read()}catch{return []}
  })
  const [error,setError]=useState<string|null>(null)
  useEffect(()=>{
    const refresh=(event:StorageEvent)=>{
      if(event.key===KEY||event.key===null){
        try{setItems(read());setError(null)}
        catch{setError(t.unavailable)}
      }
    }
    window.addEventListener('storage',refresh)
    return ()=>window.removeEventListener('storage',refresh)
  },[t.unavailable])
  const scoped=scopedSavedEditionShortcuts(items,runId,branchId)
  const normalizedSearch=tab==='results'?matchSearch:''
  const exists=scoped.some(item=>item.revisionId===revisionId&&item.eventId===eventId
    &&item.seasonIndex===seasonIndex&&item.tab===tab&&item.matchSearch===normalizedSearch)
  const full=items.length>=SAVED_EDITION_SHORTCUT_LIMIT&&!exists
  const commit=(action:(existing:SavedEditionShortcut[])=>SavedEditionShortcut[])=>{
    try{
      const next=action(read())
      window.localStorage.setItem(KEY,serializeSavedEditionShortcuts(next))
      setItems(next);setError(null)
    }catch(e){
      setError(e instanceof Error&&e.message.includes('Maximum number')
        ?t.limit:t.unavailable)
    }
  }
  const save=()=>{
    const title=name.trim()
    if(!title||title.length>72)return
    try{
      const next=createSavedEditionShortcut({
        name:title,runId,branchId,revisionId,seasonIndex,eventId,tab,
        matchSearch:normalizedSearch,
      },'local-'+Date.now().toString(36)+'-'+Math.random().toString(36).slice(2,12))
      commit(previous=>upsertSavedEditionShortcut(previous,next))
    }catch{setError(t.unavailable)}
  }
  const remove=(id:string)=>{
    commit(previous=>previous.filter(item=>
      !(item.id===id&&item.runId===runId&&item.branchId===branchId)))
  }
  return <section className="section-subtle" aria-label={t.header}>
    <h3>{t.header}</h3>
    <p className="status">{t.hint}</p>
    <div className="actions">
      <label>{t.input}{' '}
        <input type="text" value={name} maxLength={72}
          onChange={e=>setName(e.target.value)}/>
      </label>
      <button type="button" disabled={!name.trim()||full} onClick={save}>
        {t.save}
      </button>
    </div>
    {error&&<p role="alert">{error}</p>}
    {full&&<p role="status">{t.limit}</p>}
    {scoped.length===0?<p className="status">{t.empty}</p>:
      <ul>{scoped.map(item=>{
        const href=savedEditionShortcutHref(item)
        return <li key={item.id}>
          <strong>{item.name}</strong>{' · '}
          {item.tab}{item.matchSearch?' · '+item.matchSearch:''}
          {' · '}S{item.seasonIndex+1}
          {' · '}<code>{item.revisionId}</code>
          {' · '}{href?<Link to={href}>{t.open}</Link>:null}
          {' · '}<button type="button" onClick={()=>remove(item.id)}
            aria-label={t.remove+' '+item.name}>{t.remove}</button>
        </li>
      })}</ul>}
    {scoped.length>0&&<p className="status">{t.caution}</p>}
  </section>
}
