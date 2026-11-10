import { describe, expect, it } from 'vitest'
import {
  ATP_REFERENCE_SETUP_ID, reviewedATPReference, validATPCatalog
} from './atpReferencePackages'
import type { ATPReferenceCatalog, ATPReferencePreview } from './atpReferencePackages'

const hash=(char:string)=>char.repeat(64)
const catalog:ATPReferenceCatalog={
  package_id:ATP_REFERENCE_SETUP_ID,
  package_type:'Setup',
  source_version:1,
  source_fingerprint:hash('a'),
  reference_span:{from:1990,to:2026},
  provisional_years:[2026],
  usage:'source_reference_only_no_playable_calendar',
  children:[
    {package_type:'Category',package_id:'atp_tour_1990_2026_category',
      source_version:1,source_fingerprint:hash('b'),entity_count:11},
    {package_type:'Series',package_id:'atp_tour_1990_2026_series',
      source_version:1,source_fingerprint:hash('c'),entity_count:164}
  ]
}
const preview:ATPReferencePreview={
  run_id:'run/1',branch_id:'branch/2',saved_head_revision_id:'r0',
  draft_version:0,current_state_fingerprint:null,preview_fingerprint:hash('d'),
  document_identity:{package_id:ATP_REFERENCE_SETUP_ID,package_type:'Setup',
    source_version:1,source_fingerprint:hash('a')},
  additions:['atp_tour_1990_2026_category/atp_250'],
  unchanged:[],updates:[],not_included:[],unresolved:[],
  automatically_resolvable:[],invalid:[],conflicts:[]
}
describe('ATP reference manifest and exact Run review boundaries',()=>{
  it('accepts the one fixed, server-sourced historical Setup',()=>{
    expect(validATPCatalog(catalog)).toBe(true)
    expect(reviewedATPReference(catalog,preview,'run/1','branch/2')).toBe(true)
  })
  it('rejects fabricated sources, swapped child types, non-historical spans and source drift',()=>{
    expect(validATPCatalog({...catalog,package_id:'made-up'})).toBe(false)
    expect(validATPCatalog({...catalog,source_fingerprint:'not-a-fingerprint'})).toBe(false)
    expect(validATPCatalog({...catalog,reference_span:{from:1980,to:2026}})).toBe(false)
    expect(validATPCatalog({...catalog,provisional_years:[]})).toBe(false)
    expect(validATPCatalog({...catalog,children:[...catalog.children].reverse()})).toBe(false)
    expect(validATPCatalog({...catalog,children:[{...catalog.children[0],entity_count:0},catalog.children[1]]})).toBe(false)
    expect(reviewedATPReference(catalog,{
      ...preview,document_identity:{...preview.document_identity,source_fingerprint:hash('b')}
    },'run/1','branch/2')).toBe(false)
  })
  it('rejects wrong Run/Branch, malformed preview and source-identity replay',()=>{
    expect(reviewedATPReference(catalog,preview,'other','branch/2')).toBe(false)
    expect(reviewedATPReference(catalog,preview,'run/1','other')).toBe(false)
    expect(reviewedATPReference(catalog,{...preview,preview_fingerprint:'bad'},'run/1','branch/2')).toBe(false)
    expect(reviewedATPReference(catalog,{...preview,draft_version:-1},'run/1','branch/2')).toBe(false)
    expect(reviewedATPReference(catalog,{
      ...preview,document_identity:{...preview.document_identity,package_type:'Category' as 'Setup'}
    },'run/1','branch/2')).toBe(false)
    expect(reviewedATPReference(catalog,{
      ...preview,current_state_fingerprint:'malformed'
    },'run/1','branch/2')).toBe(false)
    expect(reviewedATPReference(catalog,{
      ...preview,conflicts:'forged' as unknown as string[]
    },'run/1','branch/2')).toBe(false)
  })
})
