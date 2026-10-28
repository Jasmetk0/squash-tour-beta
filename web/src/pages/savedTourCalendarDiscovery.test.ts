import {describe,expect,it} from 'vitest'
import type {SavedTourEvent} from '../api/savedTour'
import {calendarWeeksWithEditions,filterSavedTourEvents,savedCalendarPublication} from './savedTourCalendarDiscovery'

function event(id:string,week:number,overrides:Partial<SavedTourEvent>={}):SavedTourEvent{
  return {event_id:id,event_name:id,season:'2002/2003',season_week:week,template_id:'tpl',
    category:'Gold',tour_level:'WORLD',host_country:'CZE',host_city:'Brno',region:'Europe',
    main_draw_size:16,qualification_draw_size:0,seeds_count:4,qualifier_spots:0,
    wild_cards:0,byes:0,ranking_status:'ranked',result_published:false,
    champion_player_id:null,finalist_player_id:null,...overrides}
}
const base={tour:'',category:'',country:'',search:'',publication:'all' as const}

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

  it('preserves original week order and simultaneous editions when hiding empty weeks',()=>{
    const entries=[event('b',5),event('a',5),event('c',12)]
    expect(calendarWeeksWithEditions(entries,15,true)).toEqual([5,12])
    expect(calendarWeeksWithEditions(entries,15,false)).toHaveLength(15)
    expect(calendarWeeksWithEditions([],15,true)).toEqual([])
    expect(calendarWeeksWithEditions(entries,0,false)).toEqual([])
    expect(calendarWeeksWithEditions(entries,1.5,false)).toEqual([])
  })

  it('handles absent optional search fields without crashing or inventing entries',()=>{
    const entries=[event('safe-id',4,{event_name:null as unknown as string,host_city:null})]
    expect(filterSavedTourEvents(entries,{...base,search:'safe-id'})).toEqual(entries)
    expect(filterSavedTourEvents(entries,{...base,search:'random'})).toEqual([])
  })
})
