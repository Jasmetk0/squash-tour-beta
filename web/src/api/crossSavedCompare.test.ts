import {afterEach,describe,it,expect,vi} from 'vitest'
import {compareCrossSavedRevisions} from './crossSavedCompare'
afterEach(()=>vi.unstubAllGlobals())
describe('Read-only cross Saved comparison transport',()=>{
  it('encodes all six independent sources in one GET',async()=>{
    const fetcher=vi.fn().mockResolvedValue(new Response(JSON.stringify({components:[]})))
    vi.stubGlobal('fetch',fetcher)
    await compareCrossSavedRevisions('run/a','branch?b','rev#c','run d','branch/e','rev&f')
    const [url,init]=fetcher.mock.calls[0]
    const parsed=new URL(url)
    expect(parsed.pathname).toBe('/admin/cross-run-compare')
    expect([...parsed.searchParams.values()]).toEqual(['run/a','branch?b','rev#c','run d','branch/e','rev&f'])
    expect(init.method).toBe('GET');expect(init.body).toBeUndefined()
    expect(fetcher).toHaveBeenCalledTimes(1)
  })
  it('preserves source-validation conflicts without retry or writes',async()=>{
    const fetcher=vi.fn().mockResolvedValue(new Response('broken Saved source',{status:409}))
    vi.stubGlobal('fetch',fetcher)
    await expect(compareCrossSavedRevisions('a','b','c','d','e','f')).rejects.toMatchObject({status:409,message:'broken Saved source'})
    expect(fetcher).toHaveBeenCalledTimes(1)
  })
})
