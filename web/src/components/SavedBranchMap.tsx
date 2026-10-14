/** View-only Run Branch lineage. Never infer Saved links from checkpoints or
 * Saved Revision timestamps; every rendered connection is explicit metadata. */
import type {RunBranch} from '../api/types'
import {useLanguage} from '../i18n/LanguageContext'

export type BranchMapNode={
  branch:RunBranch;depth:number;
  parentId:string|null;connection:'saved_revision'|'checkpoint'|'root'|'unresolved'
}
export type BranchMapResult={nodes:BranchMapNode[];error:string|null}

export function buildSavedBranchMap(runId:string,branches:RunBranch[]):BranchMapResult{
  if(!runId||branches.some(b=>b.run_id!==runId||!b.branch_id.trim())||
      new Set(branches.map(b=>b.branch_id)).size!==branches.length)
    return {nodes:[],error:'Branch map Run scope or Branch identity is inconsistent'}
  const byId=new Map(branches.map(b=>[b.branch_id,b]))
  const depth=new Map<string,number>()
  const visiting=new Set<string>()
  function level(id:string):number{
    if(depth.has(id))return depth.get(id)!
    if(visiting.has(id))throw Error('Branch fork lineage contains a cycle')
    const branch=byId.get(id)!
    visiting.add(id)
    const parent=branch.forked_from_branch_id
    const n=parent&&parent!==id&&byId.has(parent)?level(parent)+1:0
    if(parent===id)throw Error('Branch fork lineage points to itself')
    visiting.delete(id);depth.set(id,n)
    return n
  }
  try{
    branches.forEach(b=>level(b.branch_id))
  }catch(e){return {nodes:[],error:e instanceof Error?e.message:String(e)}}
  const byParent=new Map<string,RunBranch[]>()
  const roots:RunBranch[]=[]
  const sort=(a:RunBranch,b:RunBranch)=>a.display_name.localeCompare(b.display_name)||
    a.branch_id.localeCompare(b.branch_id)
  branches.forEach(b=>{
    const parent=b.forked_from_branch_id
    if(parent&&byId.has(parent)){
      const children=byParent.get(parent)??[]
      children.push(b);byParent.set(parent,children)
    } else roots.push(b)
  })
  roots.sort(sort)
  byParent.forEach(children=>children.sort(sort))
  const nodes:BranchMapNode[]=[]
  function walk(b:RunBranch):void{
    const parent=b.forked_from_branch_id
    const hasParent=Boolean(parent&&byId.has(parent))
    const connection:BranchMapNode['connection']=!parent?'root':
      !hasParent?'unresolved':
      b.forked_from_saved_revision_id?'saved_revision':
      b.forked_from_checkpoint_id?'checkpoint':'unresolved'
    nodes.push({branch:b,depth:depth.get(b.branch_id)!,parentId:hasParent?parent:null,connection})
    for(const child of byParent.get(b.branch_id)??[])walk(child)
  }
  roots.forEach(walk)
  if(nodes.length!==branches.length)return {nodes:[],error:'Branch lineage traversal is incomplete'}
  return {nodes,error:null}
}

type Props={
  runId:string;branches:RunBranch[];selectedBranchId:string;
  viewerBranchId:string|null;officialBranchId:string|null;
  onSelect:(branchId:string)=>void
}
export function SavedBranchMap({
  runId,branches,selectedBranchId,onSelect
}:Props):JSX.Element{
  const {language}=useLanguage()
  const L=(cs:string,en:string)=>language==='cs'?cs:en
  const model=buildSavedBranchMap(runId,branches)
  const translatedErrors:Record<string,string>={
    'Branch map Run scope or Branch identity is inconsistent':'Nesouhlasí rozsah Runu nebo identita větví.',
    'Branch fork lineage contains a cycle':'Historie větvení obsahuje cyklus.',
    'Branch fork lineage points to itself':'Větev odkazuje sama na sebe.',
    'Branch lineage traversal is incomplete':'Historii větvení nelze úplně projít.',
  }
  return <section className="saved-branch-map" aria-label={L("Mapa historie větví","Saved Branch lineage map")}>
    <h4>{L('Mapa větví · skutečné návaznosti','Branch map · recorded lineage')}</h4>
    <p className="status">{L(
      'Pouze prohlížení. Výběr větve ji neaktivuje, nepřepíná veřejné zobrazení, nevytváří odbočku ani neobnovuje revizi.',
      'Read-only selection. Choosing a branch does not activate it, change public viewing, create a fork or restore a revision.'
    )}</p>
    {model.error&&<p role="alert">{language==='cs'?translatedErrors[model.error]??model.error:model.error}</p>}
    {!model.error&&model.nodes.length===0&&<p role="status">{L('Nejsou uloženy žádné větve Runu.','No Run Branches are saved.')}</p>}
    {!model.error&&<div className="saved-branch-map__lanes" role="list">
      {model.nodes.map(({branch,depth,connection,parentId})=>
        <div key={branch.branch_id} role="listitem" className="saved-branch-map__lane"
          style={{marginLeft:Math.min(depth,18)*25}}>
          <span className="saved-branch-map__connector" aria-hidden="true">
            {depth>0?'↳':'●'}</span>
          <button type="button" className="saved-branch-map__branch"
            aria-label={L('Zobrazit větev ','View Branch ')+branch.display_name}
            aria-pressed={branch.branch_id===selectedBranchId}
            onClick={()=>onSelect(branch.branch_id)}>
            <strong>{branch.display_name}</strong>
            <small><code>{branch.branch_id}</code></small>
            <span className="status">
              {branch.branch_id===selectedBranchId?L('Prohlížená · ','Viewing · '):''}
              {branch.read_only?L('Jen pro čtení','Read-only'):branch.status}
            </span>
            {connection==='saved_revision'&&<small>{L('Uložená odbočka z','Saved fork from')}{' '}
              <code>{parentId}</code> {L('na revizi','at revision')}{' '}<code>{branch.forked_from_saved_revision_id}</code></small>}
            {connection==='checkpoint'&&<small>{L('Starší odbočka z checkpointu větve','Legacy checkpoint fork from')}{' '}
              <code>{parentId}</code> {L('v','at')}{' '}<code>{branch.forked_from_checkpoint_id}</code>
              {' '}· {L('nejde o vazbu Saved Revision','not a Saved Revision relation')}</small>}
            {connection==='unresolved'&&<small>{L('Neověřená nebo chybějící vazba na uloženého předka','Unverified or missing Saved parent relationship')}
              {branch.forked_from_branch_id&&<> · <code>{branch.forked_from_branch_id}</code></>}</small>}
            {connection==='root'&&<small>{L('Kořenová větev / bez zaznamenaného předka','Root / no recorded fork parent')}</small>}
            <small>{L('Uložený HEAD','Saved HEAD')}: <code>{branch.saved_head_revision_id??L('nezveřejněn','not exposed')}</code></small>
          </button>
        </div>
      )}
    </div>}
  </section>
}
