import {screen, within} from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import {beforeEach, describe, expect, it, vi} from 'vitest'
import {renderWithRoute} from '../test/testUtils'
import {InitialPopulationComparisonPanel} from './InitialPopulationComparisonPanel'

const api = vi.hoisted(() => ({listInitialPopulationComparisons: vi.fn(), getInitialPopulationComparison: vi.fn(), runInitialPopulationComparison: vi.fn(), getInitialPopulationPlayers: vi.fn(), initialPopulationExportUrl: vi.fn()}))
vi.mock('../api/client', () => api)
const distribution = {count: 2, minimum: 15, maximum: 30, mean: 22.5, p10: 16.5, p25: 18.75, p50: 22.5, p75: 26.25, p90: 28.5, p95: 29.25, p99: 29.85, histogram: [{lower: 10,upper: 19,count: 1},{lower: 30,upper: 39,count: 1}]}
const variability = {minimum: 22.5, maximum: 22.5, mean: 22.5, standard_deviation: 0}
const summary = {player_count: 2, countries: [{code: 'AAA',name: 'Present',count: 2,share: 1},{code: 'ZZZ',name: 'Zero',count: 0,share: 0}], metrics: {age: distribution, potential_ability: {...distribution,mean: null}}, potential_tiers: {S: 0, A: 2}, tour_registration: {before_entry: null,after_entry: null,reason: 'No authoritative Tour registration history.'}}
const result = {schema_version: 'player_lab_initial_population_comparison.v1', session_id: 'saved-population', fingerprint: 'f'.repeat(64),cached: false,request: {world_ids: ['fifa_earth','atp_earth'],season: '2000/2001',player_count: 2,seeds: [101]},duration_seconds: 1, engine: {commit: 'commit',source_fingerprint: 'hash',uncommitted_source: false},sources: [], interpretation: {},effective_configuration: {},runs: ['fifa_earth','atp_earth'].map(world_id=>({world_id,seed: 101,summary,duration_seconds: .1,gameplay_fingerprint: world_id})),aggregates: ['fifa_earth','atp_earth'].map(world_id=>({world_id,summary,between_seed_countries: {AAA: variability,ZZZ: variability},between_seed_metrics: {age: {mean: variability,p99: variability},potential_ability: {mean: variability,p99: variability}},between_seed_tiers: {S: variability,A: variability}}))}

describe('InitialPopulationComparisonPanel (API boundary component tests)', () => {
  beforeEach(()=>{
    vi.clearAllMocks()
    api.listInitialPopulationComparisons.mockResolvedValue([{session_id: result.session_id,fingerprint: result.fingerprint,request: result.request}])
    api.getInitialPopulationComparison.mockResolvedValue(result)
    api.runInitialPopulationComparison.mockResolvedValue(result)
    api.getInitialPopulationPlayers.mockResolvedValue({session_id: result.session_id,world_id: 'fifa_earth',seed: 101,gameplay_fingerprint: 'fifa_earth',players: []})
    api.initialPopulationExportUrl.mockImplementation((id,format)=>`/saved/${id}/export?format=${format}`)
  })
  it('submits explicit Earth inputs and opens the saved result', async()=>{
    const user = userEvent.setup()
    renderWithRoute(<InitialPopulationComparisonPanel />, '/admin/labs/player')
    await user.clear(screen.getByLabelText('Players per population')); await user.type(screen.getByLabelText('Players per population'),'2')
    await user.clear(screen.getByLabelText('Initial population seeds')); await user.type(screen.getByLabelText('Initial population seeds'),'101')
    await user.click(screen.getByRole('button',{name: 'Generate and save population comparison'}))
    expect(await screen.findByText('Saved initial population results')).toBeVisible()
    expect(api.runInitialPopulationComparison).toHaveBeenCalledWith({world_ids: ['fifa_earth','atp_earth'],season: '2000/01',player_count: 2,seeds: [101]}, expect.anything())
    expect(screen.getByRole('link',{name: 'Export players CSV'})).toHaveAttribute('href','/saved/saved-population/export?format=csv')
  })
  it('reopens from URL without generation, shows missing values and genuine zero counts, and switches seed scope', async()=>{
    const user = userEvent.setup()
    renderWithRoute(<InitialPopulationComparisonPanel />, '/admin/labs/player?population_session=saved-population')
    expect(await screen.findByText('Saved initial population results')).toBeVisible()
    expect(api.runInitialPopulationComparison).not.toHaveBeenCalled()
    expect(screen.getByText(/Tour registration before\/after entry: —/)).toBeVisible()
    const zero = within(screen.getByRole('table',{name: 'Earth population country comparison'})).getByText('ZZZ · Zero').closest('tr')!
    expect(within(zero).getAllByText('0 / 0.00%')).toHaveLength(2)
    const metrics = screen.getByRole('table',{name: 'Pooled population metrics'})
    expect(within(metrics).getAllByText('—').length).toBeGreaterThan(1)
    await user.selectOptions(screen.getByLabelText('Inspect generated population'),'1')
    expect(api.getInitialPopulationPlayers).toHaveBeenLastCalledWith('saved-population','atp_earth',101,'atp_earth')
  })
  it('rejects duplicate worlds before starting production work', async()=>{
    const user = userEvent.setup()
    renderWithRoute(<InitialPopulationComparisonPanel />, '/admin/labs/player')
    await user.selectOptions(screen.getByLabelText('Second World Package'),'fifa_earth')
    await user.click(screen.getByRole('button',{name: 'Generate and save population comparison'}))
    expect(screen.getByRole('alert')).toHaveTextContent('distinct Earth packages')
    expect(api.runInitialPopulationComparison).not.toHaveBeenCalled()
  })
})
