import {fireEvent,render,screen,within} from '@testing-library/react'
import {MemoryRouter} from 'react-router-dom'
import {afterEach,beforeEach,describe,expect,it,vi} from 'vitest'
import {SavedEditionShortcuts} from './SavedEditionShortcuts'
import {
  SAVED_EDITION_SHORTCUT_STORAGE_KEY as KEY,
  createSavedEditionShortcut,loadSavedEditionShortcuts,serializeSavedEditionShortcuts,
  type SavedEditionShortcutTab,
} from '../pages/savedEditionShortcuts'

const props={
  runId:'run-a',branchId:'branch-a',revisionId:'rev-old',seasonIndex:2,
  eventId:'event-x',eventName:'Brno Open',tab:'results' as SavedEditionShortcutTab,
  matchSearch:'P1',cs:false,
}
function mount(changes:Partial<typeof props>={}){
  return render(<MemoryRouter><SavedEditionShortcuts {...props} {...changes}/></MemoryRouter>)
}
const saved=(changes:Record<string,unknown>={})=>createSavedEditionShortcut({
  name:'Saved result',runId:props.runId,branchId:props.branchId,
  revisionId:props.revisionId,seasonIndex:props.seasonIndex,eventId:props.eventId,
  tab:'results',matchSearch:'P1',...changes,
},'previous-1')

describe('Pinned local Saved Edition views',()=>{
  beforeEach(()=>{vi.restoreAllMocks();window.localStorage.clear()})
  afterEach(()=>{vi.restoreAllMocks();window.localStorage.clear()})

  it('does not write on render, saves only a user-chosen verified exact view',()=>{
    const storage=vi.spyOn(Storage.prototype,'setItem')
    mount()
    expect(storage).not.toHaveBeenCalled()
    const region=screen.getByRole('region',{name:'Pinned Saved Edition views'})
    expect(within(region).getByText(/Browser-local bookmarks only/)).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button',{name:'Pin this view'}))
    expect(storage).toHaveBeenCalledTimes(1)
    const found=loadSavedEditionShortcuts(window.localStorage.getItem(KEY))
    expect(found).toHaveLength(1)
    expect(found[0]).toMatchObject({
      name:'Brno Open',runId:'run-a',branchId:'branch-a',
      revisionId:'rev-old',seasonIndex:2,eventId:'event-x',
      tab:'results',matchSearch:'P1',
    })
    const url=screen.getByRole('link',{name:'Open'})
    expect(url.getAttribute('href')).toContain('revision=rev-old')
    expect(url.getAttribute('href')).toContain('matchSearch=P1')
    expect(url.getAttribute('href')).toContain('season=2')
  })

  it('persists across remount, renames identical view and removes on explicit click',()=>{
    const first=mount()
    fireEvent.click(screen.getByRole('button',{name:'Pin this view'}))
    first.unmount()
    const again=mount()
    expect(screen.getByRole('link',{name:'Open'})).toBeInTheDocument()
    fireEvent.change(screen.getByRole('textbox',{name:'View name'}),{
      target:{value:'Critical final'},
    })
    fireEvent.click(screen.getByRole('button',{name:'Pin this view'}))
    const items=loadSavedEditionShortcuts(window.localStorage.getItem(KEY))
    expect(items).toHaveLength(1)
    expect(items[0].name).toBe('Critical final')
    expect(screen.getByText('Critical final')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button',{name:'Remove Critical final'}))
    expect(loadSavedEditionShortcuts(window.localStorage.getItem(KEY))).toEqual([])
    expect(screen.queryByRole('link',{name:'Open'})).not.toBeInTheDocument()
    again.unmount()
  })

  it('never shows foreign Branch/Run bookmarks but allows old revisions on same Branch',()=>{
    const current=saved()
    const older=saved({id:'ignored',name:'Older',revisionId:'rev-historic'})
    const foreign=saved({name:'Other Branch',branchId:'branch-b'})
    const otherRun=saved({name:'Other Run',runId:'run-b'})
    const values=[current,{...older,id:'old-id'},{...foreign,id:'different-branch'},
      {...otherRun,id:'other-run'}]
    window.localStorage.setItem(KEY,serializeSavedEditionShortcuts(values))
    mount()
    expect(screen.getAllByRole('link',{name:'Open'})).toHaveLength(2)
    const oldLink=screen.getAllByRole('link',{name:'Open'}).find(link=>
      link.getAttribute('href')?.includes('revision=rev-historic'))
    expect(oldLink).toBeDefined()
    expect(screen.queryByText('Other Branch')).not.toBeInTheDocument()
    expect(screen.queryByText('Other Run')).not.toBeInTheDocument()
    expect(screen.getByText(/Older revisions must still be reachable/)).toBeInTheDocument()
  })

  it('edits only the exact local view, never an unrelated source or season',()=>{
    const old=saved({name:'Earlier revision',revisionId:'rev-prior'})
    window.localStorage.setItem(KEY,serializeSavedEditionShortcuts([old]))
    mount()
    fireEvent.click(screen.getByRole('button',{name:'Pin this view'}))
    const items=loadSavedEditionShortcuts(window.localStorage.getItem(KEY))
    expect(items.map(x=>x.revisionId)).toEqual(['rev-old','rev-prior'])
  })

  it('fails closed on unavailable storage instead of falsely confirming a save',()=>{
    vi.spyOn(Storage.prototype,'setItem').mockImplementation(()=>{throw new Error('quota')})
    mount()
    fireEvent.click(screen.getByRole('button',{name:'Pin this view'}))
    expect(screen.getByRole('alert')).toHaveTextContent(/storage is unavailable/)
    expect(screen.queryByRole('link',{name:'Open'})).not.toBeInTheDocument()
  })

  it('detects storage events from another tab without adding new network or game actions',()=>{
    mount()
    window.localStorage.setItem(KEY,serializeSavedEditionShortcuts([saved()]))
    fireEvent(window,new StorageEvent('storage',{key:KEY}))
    expect(screen.getByRole('link',{name:'Open'})).toBeInTheDocument()
    window.localStorage.removeItem(KEY)
    fireEvent(window,new StorageEvent('storage',{key:KEY}))
    expect(screen.queryByRole('link',{name:'Open'})).not.toBeInTheDocument()
  })

  it('uses Czech texts and no implicit navigation or backend persistence',()=>{
    mount({cs:true,tab:'draw',matchSearch:''})
    expect(screen.getByRole('region',{name:'Připnuté pohledy na uložené turnaje'}))
      .toBeInTheDocument()
    expect(screen.getByRole('button',{name:'Připnout aktuální pohled'})).toBeEnabled()
    fireEvent.click(screen.getByRole('button',{name:'Připnout aktuální pohled'}))
    expect(screen.getByRole('link',{name:'Otevřít'})).toHaveAttribute(
      'href',expect.stringContaining('tab=draw'))
    expect(screen.getByRole('link',{name:'Otevřít'}).getAttribute('href'))
      .not.toContain('matchSearch')
    expect(screen.getByText(/Pouze místní záložky/)).toBeInTheDocument()
  })

  it('never drops older bookmarks to make room for a 25th',()=>{
    const values=Array.from({length:24},(_,index)=>createSavedEditionShortcut({
      name:'History '+index,runId:'run-a',branchId:'branch-a',
      revisionId:'revision-'+index,seasonIndex:2,eventId:'event-x',
      tab:'overview',matchSearch:'',
    },'bookmark-'+index))
    window.localStorage.setItem(KEY,serializeSavedEditionShortcuts(values))
    mount()
    expect(screen.getByRole('button',{name:'Pin this view'})).toBeDisabled()
    expect(screen.getByText('Pinned view limit reached.')).toBeInTheDocument()
    expect(loadSavedEditionShortcuts(window.localStorage.getItem(KEY))).toEqual(values)
  })
})
