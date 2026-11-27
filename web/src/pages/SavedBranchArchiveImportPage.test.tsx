import {act,fireEvent,render,screen} from '@testing-library/react'
import {MemoryRouter} from 'react-router-dom'
import {beforeEach,describe,expect,it,vi} from 'vitest'
import {SavedBranchArchiveImportPage} from './SavedBranchArchiveImportPage'

const mocks=vi.hoisted(()=>({
  previewSavedBranchImport:vi.fn(),confirmSavedBranchImport:vi.fn(),
  ArchiveRestoreRejected:class extends Error {
    constructor(message:string,readonly status:number,readonly code:string) { super(message) }
  }
}))
vi.mock('../api/runBranchArchiveImportPreview',()=>({
  ...mocks,MAX_IMPORT_ARCHIVE_BYTES:128*1024*1024
}))
vi.mock('../i18n/LanguageContext',()=>({useLanguage:()=>({language:'en'})}))
const answer={
  run_id:'run',display_name:'Portable Run',selected_branch_id:'main',
  viewer_branch_id:'main',selected_head_revision_id:'revision',
  archive_digest:'ab'.repeat(32),archive_size_bytes:3,
  branches:[{branch_id:'main'}],history:[{revision_id:'revision'}],
  audit_event_count:2,checkpoint_count:1,
  unresolved_package_references:[],omitted_areas:['working_drafts'],
  conflicts:[],can_restore:true
}
const mount=()=>render(<MemoryRouter><SavedBranchArchiveImportPage/></MemoryRouter>)
const select=(name='world.sqbranch')=>{
  const file=new File(['abc'],name)
  fireEvent.change(screen.getByLabelText('Select an archive up to 128 MiB'),{
    target:{files:[file]}
  })
  return file
}
describe('Admin archive preview and restore',()=>{
  beforeEach(()=>{
    vi.resetAllMocks()
    mocks.previewSavedBranchImport.mockResolvedValue(answer)
    mocks.confirmSavedBranchImport.mockResolvedValue(undefined)
  })
  it('never contacts the backend before explicit preview or restores before consent',async()=>{
    mount()
    expect(screen.getByRole('button',{name:'Validate archive and conflicts'})).toBeDisabled()
    expect(mocks.previewSavedBranchImport).not.toHaveBeenCalled()
    select()
    expect(mocks.previewSavedBranchImport).not.toHaveBeenCalled()
    fireEvent.click(screen.getByRole('button',{name:'Validate archive and conflicts'}))
    expect(await screen.findByText(/currently has no target identity conflicts/)).toBeInTheDocument()
    expect(screen.getByText(/Original Run/)).toBeInTheDocument()
    expect(screen.getByText(/Portable Run/)).toBeInTheDocument()
    expect(screen.getByRole('button',{name:'Restore Run'})).toBeDisabled()
    expect(mocks.confirmSavedBranchImport).not.toHaveBeenCalled()
    expect(mocks.previewSavedBranchImport).toHaveBeenCalledTimes(1)
  })
  it('shows the actual blocking target conflicts without enabling restore',async()=>{
    mocks.previewSavedBranchImport.mockResolvedValueOnce({
      ...answer,can_restore:false,conflicts:[
        {code:'run_name_exists',identity:'Portable Run',area:'run_containers'}
      ]
    })
    mount()
    select()
    fireEvent.click(screen.getByRole('button',{name:'Validate archive and conflicts'}))
    expect(await screen.findByRole('alert')).toHaveTextContent('Restore is blocked')
    expect(screen.getByText(/run_name_exists/)).toBeInTheDocument()
    expect(screen.queryByRole('button',{name:/confirm|restore/i})).not.toBeInTheDocument()
  })
  it('rejects invalid files before any request',()=>{
    mount()
    select('foreign.json')
    expect(screen.getByRole('alert')).toHaveTextContent('Select a valid')
    expect(screen.getByRole('button',{name:'Validate archive and conflicts'})).toBeDisabled()
    expect(mocks.previewSavedBranchImport).not.toHaveBeenCalled()
  })
  it('invalidates a reviewed preview when another file is selected',async()=>{
    mount()
    select()
    fireEvent.click(screen.getByRole('button',{name:'Validate archive and conflicts'}))
    expect(await screen.findByText(/currently has no target identity conflicts/)).toBeInTheDocument()
    select('replacement.sqbranch')
    expect(screen.queryByText(/currently has no target identity conflicts/)).not.toBeInTheDocument()
    expect(mocks.previewSavedBranchImport).toHaveBeenCalledTimes(1)
  })
  it('ignores delayed preview replies after explicit cancellation',async()=>{
    let resolve!: (value:typeof answer)=>void
    mocks.previewSavedBranchImport.mockImplementationOnce(()=>new Promise<typeof answer>(r=>{resolve=r}))
    mount()
    select()
    fireEvent.click(screen.getByRole('button',{name:'Validate archive and conflicts'}))
    expect(screen.getByRole('status')).toHaveTextContent('Verifying exact SHA-256')
    fireEvent.click(screen.getByRole('button',{name:'Clear review'}))
    await act(async()=>{resolve(answer)})
    expect(screen.queryByText(/currently has no target identity conflicts/)).not.toBeInTheDocument()
    expect(screen.getByRole('button',{name:'Validate archive and conflicts'})).toBeDisabled()
  })
  it('never presents partial data when backend validation fails',async()=>{
    mocks.previewSavedBranchImport.mockRejectedValueOnce(new Error('Saved owner invalid'))
    mount()
    select()
    fireEvent.click(screen.getByRole('button',{name:'Validate archive and conflicts'}))
    expect(await screen.findByRole('alert')).toHaveTextContent('Saved owner invalid')
    expect(screen.queryByText(/currently has no target identity conflicts/)).not.toBeInTheDocument()
  })
  const giveConsent = () => {
    fireEvent.change(screen.getByLabelText('Operator name'),{target:{value:'Admin'}})
    fireEvent.change(screen.getByLabelText('Restore reason'),{target:{value:'Recovery test'}})
    fireEvent.click(screen.getByRole('checkbox',{name:/I confirm restoration/}))
  }
  it('uses one immutable command for uncertain outcomes and links only after the verified receipt',async()=>{
    mocks.confirmSavedBranchImport.mockRejectedValueOnce(new Error('Connection lost'))
    mount()
    const file = select()
    fireEvent.click(screen.getByRole('button',{name:'Validate archive and conflicts'}))
    await screen.findByRole('button',{name:'Restore Run'})
    giveConsent()
    fireEvent.click(screen.getByRole('button',{name:'Restore Run'}))
    const retry = await screen.findByRole('button',{name:'Retry the same restore'})
    expect(screen.getByLabelText('Restore reason')).toBeDisabled()
    expect(screen.getByLabelText('Select an archive up to 128 MiB')).toBeDisabled()
    expect(screen.queryByRole('link',{name:'Open restored Run'})).not.toBeInTheDocument()
    fireEvent.click(retry)
    expect(await screen.findByRole('link',{name:'Open restored Run'})).toHaveAttribute('href','/admin/runs/run')
    expect(mocks.confirmSavedBranchImport).toHaveBeenCalledTimes(2)
    expect(mocks.confirmSavedBranchImport.mock.calls[1].slice(0,3))
      .toEqual([file,answer,mocks.confirmSavedBranchImport.mock.calls[0][2]])
  })
  it('requires fresh review and new consent after a stale target preview',async()=>{
    mocks.confirmSavedBranchImport.mockRejectedValueOnce(new mocks.ArchiveRestoreRejected(
      'Target changed',409,'stale_import_preview'
    ))
    mount()
    select()
    const review = screen.getByRole('button',{name:'Validate archive and conflicts'})
    fireEvent.click(review)
    await screen.findByRole('button',{name:'Restore Run'})
    giveConsent()
    fireEvent.click(screen.getByRole('button',{name:'Restore Run'}))
    expect(await screen.findByRole('alert')).toHaveTextContent('Review the archive again')
    expect(screen.queryByRole('button',{name:'Restore Run'})).not.toBeInTheDocument()
    fireEvent.click(review)
    expect(await screen.findByRole('button',{name:'Restore Run'})).toBeDisabled()
    expect(mocks.confirmSavedBranchImport).toHaveBeenCalledTimes(1)
  })
})
