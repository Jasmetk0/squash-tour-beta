import {afterEach,beforeEach,describe,expect,it,vi} from 'vitest'
import {
  assertSavedBranchImportPreview, previewSavedBranchImport, MAX_IMPORT_ARCHIVE_BYTES
} from './runBranchArchiveImportPreview'

const digest = 'ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad'
const preview = {
  schema_version:'run_branch_archive_preview.v1',
  scope:'custom_selected_saved_branch_with_dependency_history',
  archive_digest:digest, archive_size_bytes:3,
  format:'run_branch_archive.v1', minimum_engine:'engine+archive.v1',
  run_id:'run', display_name:'Portable world', selected_branch_id:'branch',
  selected_head_revision_id:'head', viewer_branch_id:'branch',
  run_activation_revision_id:'head',
  branches:[{branch_id:'branch',display_name:'Main',role:'selected',
    forked_from_branch_id:null,forked_from_saved_revision_id:null,
    saved_head_revision_id:'head'}],
  history:[{revision_id:'head',original_owner_branch_id:'branch',sequence:1,
    parent_revision_id:null,content_hash_algorithm:'sha256',
    content_hash:'cd'.repeat(32),payload_schema_version:'run_saved_revision_v1'}],
  included_components:[], selected_head_components:[],
  unresolved_package_references:[], continuation:'read only',
  audit_event_count:0,checkpoint_count:0,
  omitted_branch_ids:[],omitted_areas:['working_drafts'],
  preview_fingerprint:'ef'.repeat(32),can_restore:true,conflicts:[]
}
const fetchMock=vi.fn()
const file=()=>{
  const value=new File(['abc'],'world.sqbranch')
  Object.defineProperty(value,'arrayBuffer',{value:async()=>new Uint8Array([97,98,99]).buffer})
  return value
}
describe('Saved Branch import read-only preview contract',()=>{
  beforeEach(()=>{
    fetchMock.mockReset()
    vi.stubGlobal('fetch',fetchMock)
    vi.stubGlobal('crypto',{subtle:{digest:vi.fn(async(_alg:string,_value:ArrayBuffer)=>
      Uint8Array.from(digest.match(/../g)!.map(x=>Number.parseInt(x,16))).buffer)}})
  })
  afterEach(()=>vi.unstubAllGlobals())

  it('accepts only a complete, file-bound, consistent backend review',()=>{
    expect(assertSavedBranchImportPreview(preview,3,digest)).toEqual(preview)
    expect(assertSavedBranchImportPreview({
      ...preview,conflicts:[{code:'run_name_exists',identity:'Portable world'}],
      can_restore:false
    },3,digest).can_restore).toBe(false)
    for(const forged of [
      {...preview,archive_size_bytes:4}, {...preview,archive_digest:'ab'.repeat(32)},
      {...preview,preview_fingerprint:'not-a-hash'},
      {...preview,can_restore:true,conflicts:[{code:'collision',identity:'run'}]},
      {...preview,can_restore:false,conflicts:[]},
      {...preview,conflicts:[{code:'collision',identity:''}],can_restore:false},
      {...preview,branches:[{...preview.branches[0],saved_head_revision_id:'other'}]}
    ]) expect(()=>assertSavedBranchImportPreview(forged,3,digest)).toThrow()
  })

  it('sends only a bounded raw-file preview POST; never calls confirm or Save',async()=>{
    fetchMock.mockResolvedValueOnce(new Response(JSON.stringify(preview),{
      status:200,headers:{'Content-Type':'application/json'}
    }))
    const result=await previewSavedBranchImport(file())
    expect(result).toEqual(preview)
    expect(fetchMock).toHaveBeenCalledTimes(1)
    const [url,init]=fetchMock.mock.calls[0] as [string,RequestInit]
    expect(url).toContain('/admin/run-archives/import/preview')
    expect(url).not.toContain('/confirm')
    expect(init.method).toBe('POST')
    expect(init.body).toBeInstanceOf(File)
    expect(init.headers).toEqual({'Content-Type':'application/octet-stream'})
  })

  it('rejects invalid filename and size before any hashing or network request',async()=>{
    const bad=new File(['abc'],'wrong.json')
    await expect(previewSavedBranchImport(bad)).rejects.toThrow(/sqbranch/)
    await expect(previewSavedBranchImport(new File([],'empty.sqbranch'))).rejects.toThrow()
    const tooLarge=file()
    Object.defineProperty(tooLarge,'size',{value:MAX_IMPORT_ARCHIVE_BYTES+1})
    await expect(previewSavedBranchImport(tooLarge)).rejects.toThrow()
    expect(fetchMock).not.toHaveBeenCalled()
  })

  it('rejects a foreign/changed preview after POST without offering restore authority',async()=>{
    fetchMock.mockResolvedValueOnce(new Response(JSON.stringify({
      ...preview,run_id:'foreign',archive_digest:'ab'.repeat(32)
    }),{status:200,headers:{'Content-Type':'application/json'}}))
    await expect(previewSavedBranchImport(file())).rejects.toThrow(/selected file/)
    expect(fetchMock).toHaveBeenCalledTimes(1)
  })

  it('checks cancellation after hashing before starting a potentially expensive validation',async()=>{
    const controller=new AbortController()
    controller.abort()
    await expect(previewSavedBranchImport(file(),controller.signal)).rejects.toMatchObject({name:'AbortError'})
    expect(fetchMock).not.toHaveBeenCalled()
  })

  it('rejects non-JSON success and declared oversized response bodies',async()=>{
    fetchMock.mockResolvedValueOnce(new Response(JSON.stringify(preview),{
      status:200,headers:{'Content-Type':'text/html'}
    }))
    await expect(previewSavedBranchImport(file())).rejects.toThrow(/non-JSON/)
    const cancelled=vi.fn()
    fetchMock.mockResolvedValueOnce(new Response(new ReadableStream({cancel:cancelled}),{
      status:200,headers:{'Content-Type':'application/json','Content-Length':String(MAX_IMPORT_ARCHIVE_BYTES+1)}
    }))
    await expect(previewSavedBranchImport(file())).rejects.toThrow(/size limit/)
    expect(cancelled).toHaveBeenCalledOnce()
  })

  it('surfaces a bounded target collision response without any automatic retry',async()=>{
    fetchMock.mockResolvedValueOnce(new Response(JSON.stringify({
      detail:{code:'identity_conflict',message:'Run name already exists'}
    }),{status:409,headers:{'Content-Type':'application/json'}}))
    await expect(previewSavedBranchImport(file())).rejects.toThrow(/Run name already exists/)
    expect(fetchMock).toHaveBeenCalledTimes(1)
  })
})
