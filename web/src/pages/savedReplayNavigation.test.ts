import {describe,expect,it} from 'vitest'
import {parseSavedReplayRally} from './savedReplayNavigation'
describe('Saved rally archive navigation target',()=>{
  it('accepts exact one-based positions including pagination boundaries',()=>{
    for(const n of [1,25,26,30,999])expect(parseSavedReplayRally(String(n),999)).toBe(n)
    expect(parseSavedReplayRally('30',30)).toBe(30)
    expect(parseSavedReplayRally('31',30)).toBeNull()
  })
  it('rejects decimals, zero, negative, whitespace and unsafe values without rounding',()=>{
    for(const raw of ['', '0','01','-1',' 1','1 ','+1','2.0','1e1','NaN',
      'Infinity','999999999999999999999999999'])
      expect(parseSavedReplayRally(raw,999)).toBeNull()
    expect(parseSavedReplayRally('1',0)).toBeNull()
    expect(parseSavedReplayRally('1',-5)).toBeNull()
    expect(parseSavedReplayRally('1',1.5)).toBeNull()
    expect(parseSavedReplayRally('1',Number.MAX_SAFE_INTEGER+1)).toBeNull()
  })
})
