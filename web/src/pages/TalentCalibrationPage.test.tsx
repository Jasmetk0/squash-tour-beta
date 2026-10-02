import { screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { TalentCalibrationPage } from './TalentCalibrationPage'
import { renderWithRoute } from '../test/testUtils'

const api = vi.hoisted(() => ({ getTalentCalibration: vi.fn() }))
vi.mock('../api/client', () => api)

const stats = { minimum: 110, maximum: 190, mean: 150, p10: 120, p25: 135, p50: 150, p75: 170, p90: 185 }
const names = ['solid_prospect', 'strong_prospect', 'elite_prospect', 'special_prospect', 'generational_talent']
const response = {
  seed: 4, sample_count: 100, quality_policy_id: 'quality-v1', quality_policy_fingerprint: 'qfp',
  sporting_profile_policy_id: 'profile-v1', sporting_profile_policy_fingerprint: 'pfp', current_ovr: stats, potential_ovr: stats,
  bands: names.map((band) => ({ band, configured_rarity_weight: .2, generated_count: 20, generated_share: .2, expected_count: 20,
    generated_minus_expected: 0, current_ovr: stats, potential_ovr: stats,
    development_timing_counts: { 'Early Bloomer': 5, Standard: 10, 'Late Bloomer': 5 },
    potential_histogram: [{ lower: 110, upper: 119, count: 20 }] }))
}

describe('TalentCalibrationPage', () => {
  beforeEach(() => { api.getTalentCalibration.mockReset(); api.getTalentCalibration.mockResolvedValue(response) })
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
  it('shows loading and error states', async () => {
    api.getTalentCalibration.mockRejectedValue(new Error('nope'))
    renderWithRoute(<TalentCalibrationPage />, '/admin/world/talent-calibration')
    expect(screen.getByText(/loading calibration/i)).toBeInTheDocument()
    expect(await screen.findByText(/calibration unavailable/i)).toBeInTheDocument()
  })
})
