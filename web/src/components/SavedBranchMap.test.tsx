import {describe,expect,it,vi} from 'vitest'
import {render,screen,within} from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import type {RunBranch} from '../api/types'
import {SavedBranchMap,buildSavedBranchMap} from './SavedBranchMap'
const locale=vi.hoisted(()=>({current:'en' as 'en'|'cs'}))
vi.mock('../i18n/LanguageContext',()=>({useLanguage:()=>({language:locale.current})}))

function branch(id:string,source:string|null=null,rev:string|null=null,checkpoint:string|null=null):RunBranch{
  return {run_id:'run-a',branch_id:id,display_name:id,status:'active',
    read_only:false,branch_seed:null,legacy_simulation_run_id:null,
    forked_from_branch_id:source,forked_from_saved_revision_id:rev,
    forked_from_checkpoint_id:checkpoint,saved_head_revision_id:'head-'+id,
    head_checkpoint_id:null,metadata_json:{},is_official:false}
}
describe('Read-only Saved Branch lineage',()=>{
  it('connects only exact recorded saved forks and labels checkpoint-based forks separately',()=>{
    const a=branch('root'),b=branch('fork','root','shared-rev'),c=branch('legacy','root',null,'cp-first')
    const result=buildSavedBranchMap('run-a',[c,b,a])
    expect(result.error).toBeNull()
    expect(result.nodes.map(n=>[n.branch.branch_id,n.depth,n.connection,n.parentId])).toEqual([
      ['root',0,'root',null],['fork',1,'saved_revision','root'],['legacy',1,'checkpoint','root'],
    ])
  })
  it('never fakes missing parent/unknown fork or graph through wrong Run',()=>{
    const missing=buildSavedBranchMap('run-a',[branch('fork','missing','some-rev')])
    expect(missing.nodes).toHaveLength(1)
    expect(missing.nodes[0].connection).toBe('unresolved')
    expect(missing.nodes[0].parentId).toBeNull()
    const empty=buildSavedBranchMap('run-a',[branch('root'),branch('fork','root')])
    expect(empty.nodes[1].connection).toBe('unresolved')
    expect(buildSavedBranchMap('run-a',[branch('same'),branch('same')]).error).toMatch(/identity/)
    expect(buildSavedBranchMap('run-a',[{...branch('x'),run_id:'other'}]).error).toMatch(/scope/)
    expect(buildSavedBranchMap('run-a',[branch('a','b','rev1'),branch('b','a','rev2')]).error)
      .toMatch(/cycle/)
    expect(buildSavedBranchMap('run-a',[branch('a','a','rev1')]).error).toMatch(/itself/)
  })
  it('selects a view branch without activating or restoring any Run state',async()=>{
    locale.current='en'
    const select=vi.fn()
    render(<SavedBranchMap runId="run-a" branches={[branch('root'),branch('fork','root','ancestor')]}
      selectedBranchId="root" viewerBranchId="fork" officialBranchId="root"
      onSelect={select}/>)
    const map=screen.getByLabelText('Saved Branch lineage map')
    expect(within(map).getByText(/Read-only selection/)).toBeInTheDocument()
    const selected=within(map).getByRole('button',{name:'View Branch root'})
    const alternative=within(map).getByRole('button',{name:'View Branch fork'})
    expect(selected).toHaveAttribute('aria-pressed','true')
    expect(alternative).toHaveAttribute('aria-pressed','false')
    expect(alternative).not.toHaveTextContent('Viewer')
    expect(alternative).toHaveTextContent('ancestor')
    expect(selected).not.toHaveTextContent('Official')
    await userEvent.click(alternative)
    expect(select).toHaveBeenCalledOnce()
    expect(select).toHaveBeenCalledWith('fork')
    expect(selected).toHaveAttribute('aria-pressed','true')
  })
  it('has fully Czech map guidance and no privileged badges',()=>{
    locale.current='cs'
    render(<SavedBranchMap runId="run-a" branches={[branch('root'),branch('fork','root','ancestor')]}
      selectedBranchId="root" viewerBranchId="fork" officialBranchId="root" onSelect={vi.fn()}/>)
    const map=screen.getByLabelText('Mapa historie větví')
    expect(within(map).getByText(/Pouze prohlížení/)).toBeInTheDocument()
    expect(within(map).getByRole('button',{name:'Zobrazit větev root'})).toHaveTextContent('Prohlížená')
    expect(map).not.toHaveTextContent('Official')
    expect(map).not.toHaveTextContent('Viewer')
  })
})
