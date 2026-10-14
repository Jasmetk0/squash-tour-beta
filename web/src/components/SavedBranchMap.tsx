/** View-only Run Branch lineage. Never infer Saved links from checkpoints or
 * Saved Revision timestamps; every rendered connection is explicit metadata. */
import type {RunBranch} from '../api/types'

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
  runId,branches,selectedBranchId,viewerBranchId,officialBranchId,onSelect
}:Props):JSX.Element{
  const model=buildSavedBranchMap(runId,branches)
  return <section className="saved-branch-map" aria-label="Saved Branch lineage map">
    <h4>Branch map · skutečné větvení</h4>
    <p className="status">Read-only selection / Pouze výběr pro prohlížení. Clicking a Branch
      does not activate it, switch Viewer, create a fork or restore a revision.</p>
    {model.error&&<p role="alert">{model.error}</p>}
    {!model.error&&model.nodes.length===0&&<p role="status">No Run Branches are saved.</p>}
    {!model.error&&<div className="saved-branch-map__lanes" role="list">
      {model.nodes.map(({branch,depth,connection,parentId})=>
        <div key={branch.branch_id} role="listitem" className="saved-branch-map__lane"
          style={{marginLeft:Math.min(depth,18)*25}}>
          <span className="saved-branch-map__connector" aria-hidden="true">
            {depth>0?'↳':'●'}</span>
          <button type="button" className="saved-branch-map__branch"
            aria-label={'View Branch '+branch.display_name}
            aria-pressed={branch.branch_id===selectedBranchId}
            onClick={()=>onSelect(branch.branch_id)}>
            <strong>{branch.display_name}</strong>
            <small><code>{branch.branch_id}</code></small>
            <span className="status">
              {branch.branch_id===viewerBranchId?'Viewer · ':''}
              {branch.branch_id===officialBranchId?'Official · ':''}
              {branch.branch_id===selectedBranchId?'Viewing · ':''}
              {branch.read_only?'Read-only':branch.status}
            </span>
            {connection==='saved_revision'&&<small>Saved fork from{' '}
              <code>{parentId}</code> at <code>{branch.forked_from_saved_revision_id}</code></small>}
            {connection==='checkpoint'&&<small>Legacy checkpoint fork from{' '}
              <code>{parentId}</code> at <code>{branch.forked_from_checkpoint_id}</code>
              {' '}· not a Saved Revision relation</small>}
            {connection==='unresolved'&&<small>Unverified / missing Saved parent relationship
              {branch.forked_from_branch_id&&<> · <code>{branch.forked_from_branch_id}</code></>}</small>}
            {connection==='root'&&<small>Root / no recorded fork parent</small>}
            <small>Saved HEAD: <code>{branch.saved_head_revision_id??'not exposed'}</code></small>
          </button>
        </div>
      )}
    </div>}
  </section>
}
