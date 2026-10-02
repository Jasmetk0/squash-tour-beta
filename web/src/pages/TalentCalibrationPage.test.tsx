import { screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { TalentCalibrationPage } from './TalentCalibrationPage'
import { renderWithRoute } from '../test/testUtils'

const api = vi.hoisted(() => ({ getTalentCalibration: vi.fn(), compareTalentCalibration: vi.fn(), compareTalentCalibrationMultiSeed: vi.fn() }))
vi.mock('../api/client', () => api)

const stats = { minimum: 110, maximum: 190, mean: 150, p10: 120, p25: 135, p50: 150, p75: 170, p90: 185 }
const names = ['solid_prospect', 'strong_prospect', 'elite_prospect', 'special_prospect', 'generational_talent']
const response = {
  seed: 4, sample_count: 100, quality_policy_id: 'quality-v1', quality_policy_fingerprint: 'qfp',
  sporting_profile_policy_id: 'profile-v1', sporting_profile_policy_fingerprint: 'pfp', baseline_potential_min: 110, baseline_potential_max: 190, current_ovr: stats, potential_ovr: stats,
  bands: names.map((band) => ({ band, configured_rarity_weight: .2, generated_count: 20, generated_share: .2, expected_count: 20,
    generated_minus_expected: 0, current_ovr: stats, potential_ovr: stats,
    development_timing_counts: { 'Early Bloomer': 5, Standard: 10, 'Late Bloomer': 5 },
    potential_histogram: [{ lower: 110, upper: 119, count: 20 }] }))
}


const comparison = {
  seed: 4, sample_count: 100, baseline_policy_id: 'profile-v1', baseline_policy_fingerprint: 'pfp',
  candidate_sandbox_configuration_fingerprint: 'cfp', quality_policy_id: 'quality-v1', quality_policy_fingerprint: 'qfp',
  global_comparison: { baseline_potential_ovr: stats, candidate_potential_ovr: stats, delta: { minimum: 0, maximum: 0, mean: 0, p10: 0, p50: 0, p90: 0, increased: 0, unchanged: 100, decreased: 0 } },
  bands: names.map((band, index) => ({ band, generated_count: index === 4 ? 0 : 25, configured_rarity_weight: .2,
    candidate_range: { potential_min: 110, potential_max: 190 }, baseline_potential_ovr: index === 4 ? { minimum: null, maximum: null, mean: null, p10: null, p25: null, p50: null, p75: null, p90: null } : stats,
    candidate_potential_ovr: index === 4 ? { minimum: null, maximum: null, mean: null, p10: null, p25: null, p50: null, p75: null, p90: null } : stats,
    delta: { minimum: index === 4 ? null : 0, maximum: index === 4 ? null : 0, mean: index === 4 ? null : 0, p10: index === 4 ? null : 0, p50: index === 4 ? null : 0, p90: index === 4 ? null : 0, increased: 0, unchanged: index === 4 ? 0 : 25, decreased: 0 },
    baseline_histogram: [{ lower: 110, upper: 119, count: index === 4 ? 0 : 25 }], candidate_histogram: [{ lower: 110, upper: 119, count: index === 4 ? 0 : 25 }] })),
  adjacent_overlaps: names.slice(0, 4).map((band, index) => ({ lower_band: band, upper_band: names[index + 1], baseline: index === 3 ? null : 1, candidate: index === 3 ? null : 1 }))
}
const variability = { minimum: 1, maximum: 2, mean: 1.5, standard_deviation: .5 }
const multi = {
  seed_start: 100, seed_count: 2, sample_count_per_seed: 50, total_sample_count: 100, seeds: [100, 101],
  quality_policy_id: 'quality-v1', quality_policy_fingerprint: 'qfp', baseline_policy_id: 'profile-v1', baseline_policy_fingerprint: 'pfp', candidate_sandbox_configuration_fingerprint: 'multi-cfp',
  pooled_global_comparison: comparison.global_comparison, pooled_bands: comparison.bands,
  band_robustness: names.map((band, index) => ({ band, total_generated_samples: index === 4 ? 1 : 25, seeds_with_samples: index === 4 ? 1 : 2, seeds_without_samples: index === 4 ? 1 : 0, candidate_median: index === 4 ? { minimum: null, maximum: null, mean: null, standard_deviation: null } : variability, candidate_mean: variability, generated_count: variability })),
  overlap_robustness: names.slice(0, 4).map((band, index) => ({ lower_band: band, upper_band: names[index + 1], baseline_pooled: 1, candidate_pooled: index === 3 ? null : 1, baseline_per_seed: variability, candidate_per_seed: index === 3 ? { minimum: null, maximum: null, mean: null, standard_deviation: null } : variability, missing_seed_count: index === 3 ? 2 : 0 })),
  per_seed: [100, 101].map((seed) => ({ seed, total_samples: 50, generated_counts: { solid_prospect: 20, strong_prospect: 15, elite_prospect: 10, special_prospect: 5, generational_talent: 0 }, baseline_potential_median: 150, candidate_potential_median: 151, median_delta: 1, adjacent_candidate_overlaps: {} }))
}

describe('TalentCalibrationPage', () => {
  beforeEach(() => { api.getTalentCalibration.mockReset(); api.compareTalentCalibration.mockReset(); api.compareTalentCalibrationMultiSeed.mockReset(); api.getTalentCalibration.mockResolvedValue(response); api.compareTalentCalibration.mockResolvedValue(comparison); api.compareTalentCalibrationMultiSeed.mockResolvedValue(multi) })
  it('renders diagnostic evidence and recalculates with controls', async () => {
    const user = userEvent.setup()
    renderWithRoute(<TalentCalibrationPage />, '/admin/world/talent-calibration')
    expect(screen.getByText(/diagnostic only/i)).toBeInTheDocument()
    const table = await screen.findByRole('table', { name: 'Quality band comparison' })
    for (const label of ['Solid Prospect', 'Strong Prospect', 'Elite Prospect', 'Special Prospect', 'Generational Talent']) {
      expect(within(table).getByRole('rowheader', { name: label })).toBeInTheDocument()
    }
    expect(within(table).getAllByText('150.0').length).toBeGreaterThan(0)

    const currentOvrTable = screen.getByRole('table', { name: 'Current OVR by quality band' })
    expect(within(currentOvrTable).getByRole('rowheader', { name: 'Elite Prospect' })).toBeInTheDocument()
    expect(within(currentOvrTable).getAllByText('150.0').length).toBeGreaterThan(0)
    await user.clear(screen.getByLabelText('Seed')); await user.type(screen.getByLabelText('Seed'), '99')
    await user.clear(screen.getByLabelText('Sample count')); await user.type(screen.getByLabelText('Sample count'), '321')
    await user.click(screen.getByRole('button', { name: 'Run calibration' }))
    expect(api.getTalentCalibration).toHaveBeenLastCalledWith({ seed: 99, sample_count: 321 })
  })

  it('edits, compares, resets, and renders sandbox diagnostics safely', async () => {
    const user = userEvent.setup()
    renderWithRoute(<TalentCalibrationPage />, '/admin/world/talent-calibration')
    expect(await screen.findByText(/experimental only/i)).toBeInTheDocument()
    const controls = screen.getByRole('table', { name: 'Candidate potential ranges' })
    expect(within(controls).getAllByRole('rowheader')).toHaveLength(5)
    const solidMin = within(controls).getByLabelText('Solid Prospect Potential Min')
    expect(solidMin).toHaveValue(110)
    await user.clear(solidMin); await user.type(solidMin, '120')
    await user.click(screen.getByRole('button', { name: 'Compare candidate' }))
    expect(api.compareTalentCalibration.mock.calls[0][0]).toEqual({ seed: 0, sample_count: 5000, candidate_ranges: { solid_prospect: { potential_min: 120, potential_max: 190 }, strong_prospect: { potential_min: 110, potential_max: 190 }, elite_prospect: { potential_min: 110, potential_max: 190 }, special_prospect: { potential_min: 110, potential_max: 190 }, generational_talent: { potential_min: 110, potential_max: 190 } } })
    expect(await screen.findByRole('table', { name: 'Candidate comparison' })).toBeInTheDocument()
    const globalTable = screen.getByRole('table', { name: 'Global candidate comparison' })
    expect(within(globalTable).getByText('100')).toBeInTheDocument()
    expect(screen.getByText('No generated samples for this seed/sample size')).toBeInTheDocument()
    expect(screen.getByRole('table', { name: 'Adjacent-band overlap' })).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Reset to baseline' }))
    expect(solidMin).toHaveValue(110)

    await user.clear(screen.getByLabelText('Seed'))
    await user.type(screen.getByLabelText('Seed'), '12')
    await user.click(screen.getByRole('button', { name: 'Run calibration' }))
    expect(screen.queryByRole('table', { name: 'Global candidate comparison' })).not.toBeInTheDocument()
    for (const forbidden of ['Save', 'Apply', 'Publish']) expect(screen.queryByRole('button', { name: forbidden })).not.toBeInTheDocument()
  })

  it('shows loading and error states', async () => {
    api.getTalentCalibration.mockRejectedValue(new Error('nope'))
    renderWithRoute(<TalentCalibrationPage />, '/admin/world/talent-calibration')
    expect(screen.getByText(/loading calibration/i)).toBeInTheDocument()
    expect(await screen.findByText(/calibration unavailable/i)).toBeInTheDocument()
  })

  it('runs multi-seed robustness with shared candidate controls and clears stale results', async () => {
    const user = userEvent.setup()
    renderWithRoute(<TalentCalibrationPage />, '/admin/world/talent-calibration')
    await screen.findByRole('table', { name: 'Candidate potential ranges' })
    expect(screen.getByLabelText('Number of seeds')).toHaveAttribute('max', '100')
    await user.clear(screen.getByLabelText('Number of seeds')); await user.type(screen.getByLabelText('Number of seeds'), '2')
    await user.clear(screen.getByLabelText('Samples per seed')); await user.type(screen.getByLabelText('Samples per seed'), '50')
    await user.click(screen.getByRole('button', { name: 'Run multi-seed analysis' }))
    expect(api.compareTalentCalibrationMultiSeed.mock.calls[0][0]).toEqual(expect.objectContaining({ seed_start: 100, seed_count: 2, sample_count_per_seed: 50 }))
    expect(api.compareTalentCalibrationMultiSeed.mock.calls[0][0].candidate_ranges).toEqual(expect.objectContaining({ solid_prospect: { potential_min: 110, potential_max: 190 } }))
    const bands = await screen.findByRole('table', { name: 'Band robustness' })
    expect(within(bands).getAllByRole('rowheader')).toHaveLength(5)
    expect(within(bands).getByRole('rowheader', { name: 'Generational Talent' })).toBeInTheDocument()
    expect(screen.getByText('Seeds with Generational evidence')).toBeInTheDocument()
    expect(screen.getByRole('table', { name: 'Overlap robustness' })).toBeInTheDocument()
    expect(within(screen.getByRole('table', { name: 'Per-seed results' })).getAllByRole('rowheader')).toHaveLength(2)
    expect(screen.getAllByText('—').length).toBeGreaterThan(0)
    await user.clear(screen.getByLabelText('Starting seed')); await user.type(screen.getByLabelText('Starting seed'), '200')
    expect(screen.queryByRole('table', { name: 'Band robustness' })).not.toBeInTheDocument()
  })
})
