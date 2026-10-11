import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'

import {
  GeneratedPlayerReviewInspector, summariseGeneratedPlayers
} from './GeneratedPlayerReviewInspector'
import type { RunInitialWorldPlayer } from '../api/runInitialWorldSetup'

const players: RunInitialWorldPlayer[] = [
  {player_id:'p-5',name:'Eli',country_code:'CZE',age_years_at_season_start:22,current_ability:70,potential_ability:82,potential_tier:'B',career_stage:'developing'},
  {player_id:'p-1',name:'Adam',country_code:'USA',age_years_at_season_start:15,current_ability:50,potential_ability:93,potential_tier:'S',career_stage:'junior'},
  {player_id:'p-3',name:'Bob',country_code:'CZE',age_years_at_season_start:35,current_ability:69,potential_ability:82,potential_tier:'B',career_stage:'late_career'},
  {player_id:'p-4',name:'Dan',country_code:'FRA',age_years_at_season_start:29,current_ability:80,potential_ability:92,potential_tier:'A',career_stage:'prime'},
  {player_id:'p-2',name:'Chris',country_code:'SVK',age_years_at_season_start:45,current_ability:62,potential_ability:78,potential_tier:'C',career_stage:'late_career'},
  {player_id:'p-6',name:'Fran',country_code:'GER',age_years_at_season_start:18,current_ability:75,potential_ability:88,potential_tier:'A',career_stage:'developing'},
  {player_id:'p-7',name:'Gus',country_code:'POL',age_years_at_season_start:20,current_ability:63,potential_ability:77,potential_tier:'C',career_stage:'developing'},
  {player_id:'p-8',name:'Hugo',country_code:'HUN',age_years_at_season_start:28,current_ability:66,potential_ability:78,potential_tier:'C',career_stage:'prime'}
]

describe('immutable generated cohort inspection',()=>{
  it('summarises the actual entire first-week cohort with exact deterministic counts',()=>{
    const original=JSON.stringify(players)
    const s=summariseGeneratedPlayers(players)
    expect(s.total).toBe(8)
    expect(s.countries).toEqual([
      {label:'CZE',count:2},
      {label:'FRA',count:1},{label:'GER',count:1},{label:'HUN',count:1},
      {label:'POL',count:1},{label:'SVK',count:1},{label:'USA',count:1}
    ])
    expect(s.ageGroups.map(x=>x.count)).toEqual([1,3,2,0,2])
    expect(s.potentialTiers).toEqual([
      {label:'C',count:3},{label:'A',count:2},
      {label:'B',count:2},{label:'S',count:1}
    ])
    expect(s.averageAge).toBe(26.5)
    expect(s.averageCurrentAbility).toBe(66.9)
    expect(s.averagePotentialAbility).toBe(83.8)
    expect(s.ageMinimum).toBe(15)
    expect(s.ageMaximum).toBe(45)
    expect(JSON.stringify(players)).toBe(original)
  })
  it('handles an empty batch transparently without fabricated averages',()=>{
    expect(summariseGeneratedPlayers([])).toMatchObject({
      total:0,countries:[],potentialTiers:[],ageMinimum:null,
      ageMaximum:null,averageAge:null,averageCurrentAbility:null
    })
  })
  it('shows compact full-cohort statistics and every row by default',()=>{
    render(<GeneratedPlayerReviewInspector players={players}/>)
    expect(screen.getByRole('region',{name:'Complete generated player preview'})).toBeInTheDocument()
    expect(screen.getByRole('status')).toHaveTextContent('Showing 8 / 8')
    expect(screen.getByText('26.5')).toBeInTheDocument()
    const table=screen.getByRole('region',{name:'Complete generated player preview'})
    expect(within(table).getAllByRole('row')).toHaveLength(9)
    expect(screen.getByText(/Statistics always use the entire verified preview/)).toBeInTheDocument()
    expect(screen.getByText(/not canonical 0–200 OVR/)).toBeInTheDocument()
  })
  it('filters display rows only, without changing source array or full-cohort metrics',async()=>{
    const before=JSON.stringify(players)
    render(<GeneratedPlayerReviewInspector players={players}/>)
    const table=screen.getByRole('region',{name:'Complete generated player preview'})
    await userEvent.selectOptions(screen.getByRole('combobox',{name:'Filter generated player country'}),'CZE')
    expect(screen.getByRole('status')).toHaveTextContent('Showing 2 / 8')
    expect(within(table).getAllByRole('row')).toHaveLength(3)
    expect(screen.getByText('26.5')).toBeInTheDocument()
    await userEvent.selectOptions(screen.getByRole('combobox',{name:'Filter generated player potential'}),'B')
    expect(screen.getByRole('status')).toHaveTextContent('Showing 2 / 8')
    await userEvent.type(screen.getByRole('textbox',{name:'Search generated player preview'}),'eli')
    expect(screen.getByRole('status')).toHaveTextContent('Showing 1 / 8')
    await userEvent.clear(screen.getByRole('textbox',{name:'Search generated player preview'}))
    await userEvent.type(screen.getByRole('textbox',{name:'Search generated player preview'}),'p-3')
    expect(screen.getByRole('status')).toHaveTextContent('Showing 1 / 8')
    expect(JSON.stringify(players)).toBe(before)
    await userEvent.click(screen.getByRole('button',{name:'Clear display filters'}))
    expect(screen.getByRole('status')).toHaveTextContent('Showing 8 / 8')
    expect(within(table).getAllByRole('row')).toHaveLength(9)
  })
  it('shows no match explicitly, without mutating the authoritative cohort',async()=>{
    render(<GeneratedPlayerReviewInspector players={players}/>)
    await userEvent.type(screen.getByRole('textbox',{name:'Search generated player preview'}),'not-a-player')
    expect(screen.getByRole('status')).toHaveTextContent('Showing 0 / 8')
    expect(screen.getByText(/No preview player matches/)).toBeInTheDocument()
    expect(screen.getByText('26.5')).toBeInTheDocument()
  })
  it('exposes remaining country bars and sorts read-only by ability',async()=>{
    render(<GeneratedPlayerReviewInspector players={players}/>)
    const countries=screen.getByRole('region',{name:'Country breakdown'})
    expect(within(countries).getByRole('button',{name:'All countries (7)'})).toBeInTheDocument()
    await userEvent.click(within(countries).getByRole('button',{name:'All countries (7)'}))
    expect(within(countries).getByText('USA')).toBeInTheDocument()
    const table=screen.getByRole('region',{name:'Complete generated player preview'})
    await userEvent.selectOptions(screen.getByRole('combobox',{name:'Sort generated player preview'}),'current')
    const rows=within(table).getAllByRole('row')
    expect(within(rows[1]).getByText('Dan')).toBeInTheDocument()
    expect(within(rows[8]).getByText('Adam')).toBeInTheDocument()
  })
})
