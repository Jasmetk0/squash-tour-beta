import {act,fireEvent,render,screen} from '@testing-library/react'
import {MemoryRouter} from 'react-router-dom'
import {beforeEach,describe,expect,it,vi} from 'vitest'
import {SavedBranchArchiveImportPage} from './SavedBranchArchiveImportPage'

const mocks=vi.hoisted(()=>({previewSavedBranchImport:vi.fn()}))
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
describe('Admin Saved Branch import read-only review',()=>{
  beforeEach(()=>{vi.clearAllMocks();mocks.previewSavedBranchImport.mockResolvedValue(answer)})
  it('never contacts the backend before an explicit preview or offers a restore action',async()=>{
    mount()
    expect(screen.getByText(/preview-only/)).toBeInTheDocument()
    expect(screen.getByRole('button',{name:'Validate archive and conflicts'})).toBeDisabled()
    expect(mocks.previewSavedBranchImport).not.toHaveBeenCalled()
    select()
    expect(mocks.previewSavedBranchImport).not.toHaveBeenCalled()
    fireEvent.click(screen.getByRole('button',{name:'Validate archive and conflicts'}))
    expect(await screen.findByText(/currently has no target identity conflicts/)).toBeInTheDocument()
    expect(screen.getByText(/Original Run/)).toBeInTheDocument()
    expect(screen.getByText(/Portable Run/)).toBeInTheDocument()
    expect(screen.queryByRole('button',{name:/restore|confirm|import now/i})).not.toBeInTheDocument()
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
})
