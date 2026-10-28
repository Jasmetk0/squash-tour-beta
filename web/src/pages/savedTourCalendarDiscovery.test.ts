import {describe,expect,it} from 'vitest'
import type {SavedTourEvent} from '../api/savedTour'
import {calendarWeeksWithEditions,filterSavedTourEvents,neighboringMatchingWeeks,
  savedCalendarPublication,savedCalendarPlayerOutcome,savedCalendarWeek,
  publishedFinalFinishes} from './savedTourCalendarDiscovery'

function event(id:string,week:number,overrides:Partial<SavedTourEvent>={}):SavedTourEvent{
  return {event_id:id,event_name:id,season:'2002/2003',season_week:week,template_id:'tpl',
    category:'Gold',tour_level:'WORLD',host_country:'CZE',host_city:'Brno',region:'Europe',
    main_draw_size:16,qualification_draw_size:0,seeds_count:4,qualifier_spots:0,
    wild_cards:0,byes:0,ranking_status:'ranked',result_published:false,
    champion_player_id:null,finalist_player_id:null,...overrides}
}
const base={tour:'',category:'',country:'',search:'',publication:'all' as const,
  playerId:'',playerOutcome:'any' as const}

describe('Saved Tour discovery is a pure read-only projection',()=>{
  it('searches event names, IDs, cities and codes without altering original order',()=>{
    const entries=[
      event('a',5,{event_name:'Brněnský Turnaj',result_published:true}),
      event('egyptian-finals',5,{event_name:'Cairo Classic',host_city:'Káhira',host_country:'EGY'}),
      event('a-third',12,{event_name:'Future Open',host_city:null})
    ]
    const original=JSON.stringify(entries)
    for(const term of ['BRNENSKY','brněnský','brno','A']){
      const found=filterSavedTourEvents(entries,{...base,search:term})
      expect(found.some(e=>e.event_id==='a')).toBe(true)
    }
    expect(filterSavedTourEvents(entries,{...base,search:'KAHIRA'}).map(e=>e.event_id)).toEqual(['egyptian-finals'])
    expect(filterSavedTourEvents(entries,{...base,search:'finals'}).map(e=>e.event_id)).toEqual(['egyptian-finals'])
    expect(filterSavedTourEvents(entries,{...base,search:'egy'}).map(e=>e.event_id)).toEqual(['egyptian-finals'])
    expect(filterSavedTourEvents(entries,{...base,search:'  '}).map(e=>e.event_id)).toEqual(['a','egyptian-finals','a-third'])
    expect(JSON.stringify(entries)).toBe(original)
  })

  it('combines exact category/Tour/country and the saved publication flag',()=>{
    const entries=[event('published',5,{result_published:true}),
      event('unpublished',5),event('other-country',8,{host_country:'EGY',result_published:true})]
    expect(filterSavedTourEvents(entries,{...base,country:'CZE',publication:'published'})
      .map(e=>e.event_id)).toEqual(['published'])
    expect(filterSavedTourEvents(entries,{...base,publication:'not-published'})
      .map(e=>e.event_id)).toEqual(['unpublished'])
    expect(filterSavedTourEvents(entries,{...base,tour:'REGIONAL'})).toEqual([])
    expect(filterSavedTourEvents(entries,{...base,category:'Gold'})).toHaveLength(3)
    expect(savedCalendarPublication('invalid')).toBe('all')
    expect(savedCalendarPublication(null)).toBe('all')
    expect(savedCalendarPublication('published')).toBe('published')
  })

  it('finds published champion and finalist evidence by ID, without claiming complete careers',()=>{
    const entries=[
      event('first',5,{result_published:true,champion_player_id:'player-ALPHA',finalist_player_id:'player-beta'}),
      event('second',5,{result_published:true,champion_player_id:'player-beta',finalist_player_id:'player-GAMMA'}),
      event('stale-unpublished',7,{result_published:false,champion_player_id:'player-beta',finalist_player_id:'player-ALPHA'}),
      event('no-outcome',8,{result_published:true,champion_player_id:null,finalist_player_id:null})
    ]
    const original=JSON.stringify(entries)
    expect(filterSavedTourEvents(entries,{...base,playerId:'PLAYER-beta'}).map(e=>e.event_id))
      .toEqual(['first','second'])
    expect(filterSavedTourEvents(entries,{...base,playerId:'player-BETA',playerOutcome:'champion'})
      .map(e=>e.event_id)).toEqual(['second'])
    expect(filterSavedTourEvents(entries,{...base,playerId:'player-BETA',playerOutcome:'finalist'})
      .map(e=>e.event_id)).toEqual(['first'])
    expect(filterSavedTourEvents(entries,{...base,playerId:'player-GAMMA',playerOutcome:'champion'}))
      .toEqual([])
    expect(filterSavedTourEvents(entries,{...base,playerId:' ',playerOutcome:'champion'}))
      .toEqual(entries)
    expect(JSON.stringify(entries)).toBe(original)
    expect(savedCalendarPlayerOutcome('bogus')).toBe('any')
    expect(savedCalendarPlayerOutcome(null)).toBe('any')
    expect(savedCalendarPlayerOutcome('finalist')).toBe('finalist')
  })

  it('counts only documented published wins and runner-ups in supplied Editions',()=>{
    const entries=[
      event('first',5,{result_published:true,champion_player_id:'A',finalist_player_id:'B'}),
      event('second',9,{result_published:true,champion_player_id:'B',finalist_player_id:'A'}),
      event('third',9,{result_published:true,champion_player_id:'A',finalist_player_id:'C'}),
      event('unpublished',11,{result_published:false,champion_player_id:'A',finalist_player_id:'B'}),
      event('malformed',12,{result_published:true,champion_player_id:'D',finalist_player_id:'D'}),
      event('partial',13,{result_published:true,champion_player_id:null,finalist_player_id:'C'})
    ]
    const original=JSON.stringify(entries)
    expect(publishedFinalFinishes(entries)).toEqual([
      {playerId:'A',championFinishes:2,runnerUpFinishes:1},
      {playerId:'B',championFinishes:1,runnerUpFinishes:1},
      {playerId:'C',championFinishes:0,runnerUpFinishes:2}
    ])
    expect(publishedFinalFinishes(entries.slice(0,1))).toEqual([
      {playerId:'A',championFinishes:1,runnerUpFinishes:0},
      {playerId:'B',championFinishes:0,runnerUpFinishes:1}
    ])
    expect(publishedFinalFinishes(entries.slice(3,5))).toEqual([])
    expect(JSON.stringify(entries)).toBe(original)
  })

  it('preserves original week order and simultaneous editions when hiding empty weeks',()=>{
    const entries=[event('b',5),event('a',5),event('c',12)]
    expect(calendarWeeksWithEditions(entries,15,true)).toEqual([5,12])
    expect(calendarWeeksWithEditions(entries,15,false)).toHaveLength(15)
    expect(calendarWeeksWithEditions([],15,true)).toEqual([])
    expect(calendarWeeksWithEditions(entries,0,false)).toEqual([])
    expect(calendarWeeksWithEditions(entries,1.5,false)).toEqual([])
  })

  it('validates strict 1-based week links, including boundaries',()=>{
    expect(savedCalendarWeek(null,61)).toBeNull()
    expect(savedCalendarWeek('1',61)).toBe(1)
    expect(savedCalendarWeek('61',61)).toBe(61)
    for(const raw of ['','0','01','-1','62','1.0','1e1','NaN','99999999999999999999']){
      expect(savedCalendarWeek(raw,61)).toBe('invalid')
    }
    expect(savedCalendarWeek('1',0)).toBe('invalid')
  })
  it('moves to the nearest matching week while preserving empty intervals',()=>{
    const occupied=[2,9,21,61]
    expect(neighboringMatchingWeeks(occupied,null)).toEqual({previous:null,next:null})
    expect(neighboringMatchingWeeks(occupied,1)).toEqual({previous:null,next:2})
    expect(neighboringMatchingWeeks(occupied,9)).toEqual({previous:2,next:21})
    expect(neighboringMatchingWeeks(occupied,16)).toEqual({previous:9,next:21})
    expect(neighboringMatchingWeeks(occupied,61)).toEqual({previous:21,next:null})
    expect(occupied).toEqual([2,9,21,61])
  })
  it('handles absent optional search fields without crashing or inventing entries',()=>{
    const entries=[event('safe-id',4,{event_name:null as unknown as string,host_city:null})]
    expect(filterSavedTourEvents(entries,{...base,search:'safe-id'})).toEqual(entries)
    expect(filterSavedTourEvents(entries,{...base,search:'random'})).toEqual([])
  })
})
