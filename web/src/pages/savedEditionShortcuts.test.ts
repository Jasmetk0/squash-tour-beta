import {describe,expect,it} from 'vitest'
import {
  createSavedEditionShortcut,loadSavedEditionShortcuts,savedEditionShortcutHref,
  scopedSavedEditionShortcuts,serializeSavedEditionShortcuts,
  upsertSavedEditionShortcut,SAVED_EDITION_SHORTCUT_LIMIT,
  type SavedEditionShortcut,
} from './savedEditionShortcuts'

const example=(mod:Partial<SavedEditionShortcut>={}):SavedEditionShortcut=>({
  id:'local-id-1',name:'Saved Brno results',runId:'run-a',branchId:'main-branch',
  revisionId:'rev-older',eventId:'Brno Finals',seasonIndex:2,
  tab:'results',matchSearch:'P-ALPHA',...mod,
})

describe('local source-pinned Saved Edition bookmarks',()=>{
  it('reconstructs a same-Run internal link from exact Run/Branch/revision/season and filter',()=>{
    const original=example()
    const href=savedEditionShortcutHref(original)
    expect(href).toContain('/admin/runs/run-a/tour/calendar/Brno%20Finals?')
    const query=new URL(href!,'https://test.invalid').searchParams
    expect(Object.fromEntries(query)).toEqual({
      branch:'main-branch',revision:'rev-older',season:'2',
      tab:'results',matchSearch:'P-ALPHA',
    })
    expect(savedEditionShortcutHref(example({tab:'draw',matchSearch:''})))
      .not.toContain('matchSearch')
  })
  it('safely encodes arbitrary URL metacharacters without accepting a stored redirect',()=>{
    const item=example({
      runId:'other/run?mode=evil',branchId:'branch?#',
      revisionId:'rev&branch=foreign',eventId:'../match?fake=1',
      matchSearch:'x&revision=impostor',
    })
    const href=savedEditionShortcutHref(item)!
    expect(href.startsWith('/admin/runs/other%2Frun%3Fmode%3Devil/tour/calendar/'))
      .toBe(true)
    expect(href).toContain('..%2Fmatch%3Ffake%3D1')
    const q=new URL(href,'https://test.invalid').searchParams
    expect(q.get('revision')).toBe('rev&branch=foreign')
    expect(q.getAll('revision')).toEqual(['rev&branch=foreign'])
    expect(q.get('matchSearch')).toBe('x&revision=impostor')
  })
  it('fails closed for forged or corrupted IDs, schema, duplicate entries and oversized text',()=>{
    const good=example()
    for(const bad of [
      {...good,runId:''},{...good,runId:' run '},{...good,branchId:null},
      {...good,revisionId:''},{...good,tab:'live'},
      {...good,seasonIndex:50},{...good,seasonIndex:-1},
      {...good,seasonIndex:1.3},{...good,seasonIndex:'2'},
      {...good,matchSearch:'x'.repeat(121)},
      {...good,tab:'draw',matchSearch:'unrelated search'},
      {...good,name:'x'.repeat(73)},
    ]){
      expect(savedEditionShortcutHref(bad as SavedEditionShortcut)).toBeNull()
    }
    for(const bad of [
      'not-json','[]','{}',JSON.stringify({schema_version:'other.v1',items:[good]}),
      JSON.stringify({schema_version:'saved_edition_shortcuts.v1',items:[good,good]}),
      JSON.stringify({schema_version:'saved_edition_shortcuts.v1',items:[{...good,id:'x',seasonIndex:50}]}),
      JSON.stringify({schema_version:'saved_edition_shortcuts.v1',items:new Array(25).fill(good)}),
      'x'.repeat(20001),
    ])expect(loadSavedEditionShortcuts(bad)).toEqual([])
  })
  it('roundtrips 24 verified entries without data expansion or rewriting source',()=>{
    const items=Array.from({length:SAVED_EDITION_SHORTCUT_LIMIT},(_,i)=>
      example({id:'id-'+i,revisionId:'revision-'+i,tab:'overview',matchSearch:''}))
    const original=JSON.stringify(items)
    const serialized=serializeSavedEditionShortcuts(items)
    expect(loadSavedEditionShortcuts(serialized)).toEqual(items)
    expect(JSON.stringify(items)).toBe(original)
    expect(()=>serializeSavedEditionShortcuts([...items,example({id:'extra'})])).toThrow()
    expect(()=>serializeSavedEditionShortcuts([example(),example()])).toThrow()
  })
  it('keeps same historical view unique on rename; distinct revision/filter remains independent',()=>{
    const first=example()
    const rename=example({id:'new-id',name:'Renamed'})
    let next=upsertSavedEditionShortcut([first],rename)
    expect(next).toEqual([{...rename,id:first.id}])
    next=upsertSavedEditionShortcut(next,example({
      id:'other-head',revisionId:'rev-newer',name:'Different Saved head'
    }))
    next=upsertSavedEditionShortcut(next,example({
      id:'different-search',matchSearch:'P-BETA'
    }))
    expect(next.map(x=>x.id)).toEqual(['different-search','other-head','local-id-1'])
    expect(next[2].revisionId).toBe('rev-older')
  })
  it('never silently evicts a previously saved view when 24 entries are full',()=>{
    const items=Array.from({length:24},(_,i)=>example({
      id:'slot-'+i,revisionId:'rev-'+i,tab:'overview',matchSearch:''
    }))
    expect(()=>upsertSavedEditionShortcut(items,example({id:'new-full'})))
      .toThrow('Maximum number')
    const renamed=upsertSavedEditionShortcut(items,example({
      id:'rename-full',revisionId:'rev-3',tab:'overview',matchSearch:'',name:'Renamed'
    }))
    expect(renamed).toHaveLength(24)
    expect(renamed[0]).toMatchObject({id:'slot-3',name:'Renamed'})
  })
  it('scope isolates each Run/Branch but permits explicitly linked old saved revisions',()=>{
    const local=example()
    const old=example({id:'old-rev',revisionId:'older-still'})
    const foreignBranch=example({id:'foreign-branch',branchId:'other-branch'})
    const foreignRun=example({id:'foreign-run',runId:'run-b'})
    const items=[local,old,foreignBranch,foreignRun]
    expect(scopedSavedEditionShortcuts(items,'run-a','main-branch'))
      .toEqual([local,old])
    expect(scopedSavedEditionShortcuts(items,'run-b','main-branch'))
      .toEqual([foreignRun])
    expect(scopedSavedEditionShortcuts(items,'run-a','branch-unselected'))
      .toEqual([])
  })
  it('allows only exact canonical tab/season and nonblank labels',()=>{
    expect(()=>createSavedEditionShortcut({
      name:' ',runId:'run',branchId:'branch',revisionId:'rev',
      eventId:'event',seasonIndex:0,tab:'overview',matchSearch:'',
    },'new')).toThrow()
    const value=createSavedEditionShortcut({
      name:'Final in W5',runId:'run',branchId:'branch',revisionId:'rev',
      eventId:'event',seasonIndex:0,tab:'overview',matchSearch:'',
    },'new')
    expect(value.name).toBe('Final in W5')
    expect(savedEditionShortcutHref(value)).toContain('season=0')
  })
})
