import { describe, expect, it } from 'vitest'
import { fieldChanges, parseInteger, parsePopulations, parseRating, populationChanges, timezoneAreaChanges, validateTimezoneAreas } from './review'

describe('World Package authoring input boundary', () => {
  it('does not turn empty or non-numeric input into zero', () => {
    expect(() => parseInteger('', 'Population', false, 1)).toThrow('required')
    expect(() => parseInteger('0', 'Population', false, 1)).toThrow('range')
    expect(() => parseInteger('2.5', 'Population', false, 1)).toThrow('whole number')
    expect(() => parseInteger('NaN', 'Population', false, 1)).toThrow('whole number')
    expect(parseInteger('', 'Area', false, 1, undefined, true)).toBeNull()
    expect(parseInteger('123', 'Area', false, 1)).toBe(123)
  })

  it('checks authored population years, duplicates and default year without interpolation', () => {
    expect(() => parsePopulations([{year: '2020', population: ''}], false)).toThrow('required')
    expect(() => parsePopulations([{year: '2020', population: '0'}], false)).toThrow('range')
    expect(() => parsePopulations([{year: '2020', population: '10.1'}], false)).toThrow('whole number')
    expect(() => parsePopulations([{year: '2051', population: '10'}], false)).toThrow('range')
    expect(() => parsePopulations([{year: '1990', population: '10'}], false)).toThrow('2020')
    expect(() => parsePopulations([{year: '2020', population: '100'}, {year: '02020', population: '200'}], false)).toThrow('more than once')
    expect(parsePopulations([{year: '2020', population: '100'}, {year: '1990', population: '30'}], false)).toEqual({'2020': 100, '1990': 30})
  })

  it('validates 1–10 tenths without changing legacy 1–5 precision', () => {
    const v2 = 'country_ratings_1_10.v2'
    const v1 = 'country_ratings_1_5.v1'
    expect(parseRating('7.4', 'Popularity', false, v2)).toBe(7.4)
    expect(() => parseRating('', 'Popularity', false, v2)).toThrow('required')
    expect(() => parseRating('7.44', 'Popularity', false, v2)).toThrow('decimal')
    expect(() => parseRating('11', 'Popularity', false, v2)).toThrow('from 1 to 10')
    expect(parseRating('4.45', 'Popularity', false, v1)).toBe(4.45)
    expect(() => parseRating('6', 'Popularity', false, v1)).toThrow('from 1 to 5')
  })

  it('reports explicit differences including deleted population years', () => {
    expect(fieldChanges({name: 'A', area_km2: 123}, {name: 'B', area_km2: 123}, ['name', 'area_km2']))
      .toEqual([{field:'name', before:'A', after:'B'}])
    expect(populationChanges({'2000': 20, '2020':100}, {'2020':200, '1990':5}))
      .toEqual([
        {field:'1990', before:'—', after:'5'},
        {field:'2000', before:'20', after:'—'},
        {field:'2020', before:'100', after:'200'}
      ])
  })
})


describe('Timezone Area authored circular registry', () => {
  it('assigns zero-based contiguous positions and accepts a one-area ring', () => {
    expect(validateTimezoneAreas([{ code: 'UTC_0', name: 'UTC center' }], false))
      .toEqual([{ code: 'UTC_0', name: 'UTC center', position: 0 }])
    expect(validateTimezoneAreas([{ code: 'W', name: 'West' }, { code: 'E', name: 'East' }], false))
      .toEqual([{code:'W',name:'West',position:0},{code:'E',name:'East',position:1}])
  })
  it('rejects empty, duplicate, malformed and whitespace-padded entries', () => {
    expect(() => validateTimezoneAreas([], false)).toThrow('At least one')
    expect(() => validateTimezoneAreas([{code:'W',name:'West'},{code:'W',name:'Repeat'}], false)).toThrow('Duplicate')
    expect(() => validateTimezoneAreas([{code:' w',name:'West'}], false)).toThrow('uppercase')
    expect(() => validateTimezoneAreas([{code:'w',name:'West'}], false)).toThrow('uppercase')
    expect(() => validateTimezoneAreas([{code:'W',name:'  '}], false)).toThrow('required')
    expect(() => validateTimezoneAreas([{code:'W',name:' West'}], false)).toThrow('surrounding')
  })
  it('shows explicit before→after entries for reorders and removals', () => {
    expect(timezoneAreaChanges(
      [{code:'W',name:'West',position:0},{code:'E',name:'East',position:1}],
      [{code:'E',name:'East',position:0},{code:'W',name:'West',position:1}]
    )).toEqual([
      {field:'Timezone Area 1',before:'W — West',after:'E — East'},
      {field:'Timezone Area 2',before:'E — East',after:'W — West'}
    ])
  })
})
