import {describe,it,expect} from 'vitest'
import {selectedBuilderSeason} from './seasonBuilderDeepLink'
const seasons=[{label:'2000/01'},{label:'2001/02'},{label:'2049/50'}]
describe('read-only canonical Season Builder deep link',()=>{
 it('selects precisely an existing authorable target season',()=>{
  expect(selectedBuilderSeason('2001/02',seasons)).toBe('2001/02')
  expect(selectedBuilderSeason('2049/50',seasons)).toBe('2049/50')
 })
 it.each([null,'','2002/03','1999/00','2050/51','2001/2002','2001/03','2001/02/evil','2001/02%00'])('rejects unsupported or forged season %s',(input)=>{
  expect(selectedBuilderSeason(input,seasons)).toBeNull()
 })
})
