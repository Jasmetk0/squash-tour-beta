import { describe, expect, it } from 'vitest'
import type { WorldPackage } from '../../api/types'
import { catalogFromWorlds, inCategory } from './packageCatalog'

function world(id:string,count:number):WorldPackage {
  return {
    world_id:id,name:'World '+id,description:'Source',type:'official',status:'active',
    source:'built_in',editable:false,deletable:false,archivable:false,
    version:'1',fingerprint:'abc',country_count:count,continent_count:1,
    region_count:1,travel_region_count:0,timezone_area_count:0,used_by_run_count:null,
    validation_status:'unknown',storage:{} as WorldPackage['storage']
  }
}
describe('source-backed Package classification',()=>{
  it('keeps the same World identity once in All but includes actual Country content category',()=>{
    const items=catalogFromWorlds([world('fifa',3),world('fifa',3),world('empty',0)])
    expect(items.map(item=>item.key)).toEqual(['world:fifa','world:empty'])
    expect(inCategory(items,'all')).toHaveLength(2)
    expect(inCategory(items,'world')).toHaveLength(2)
    expect(inCategory(items,'countries')).toHaveLength(1)
    expect(inCategory(items,'countries')[0].key).toBe('world:fifa')
    expect(inCategory(items,'hybrid')).toHaveLength(0)
    expect(inCategory(items,'players')).toHaveLength(0)
    expect(inCategory(items,'category')).toHaveLength(0)
    expect(inCategory(items,'calendar')).toHaveLength(0)
  })
})
