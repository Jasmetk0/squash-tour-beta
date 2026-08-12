import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { renderWithRoute } from '../test/testUtils'
import { SeasonCalendarPreview } from './SeasonCalendarPreview'

const api = vi.hoisted(() => ({ getSeasonCalendar: vi.fn(), updateTournamentEditionRanking: vi.fn() }))
vi.mock('../api/client', () => api)

const rankingEvent = (complete: boolean, status: 'planned' | 'active' = 'planned') => ({
  event_id: 'evt-ranked', season: '2000/2001', season_week: 1, start_season_week: 1,
  event_name: 'Ranked event', category: 'OPEN', host_country: 'ENG', region: 'EUROPE', template_id: 'tpl', status,
  ranking_status: 'ranked' as const, ranking_points_table: complete ? { champion: 10, finalist: 5 } : { champion: 10 },
  required_ranking_point_stages: ['champion', 'finalist'], points_table_complete: complete,
  missing_required_point_stages: complete ? [] : ['finalist']
})
const response = (event: ReturnType<typeof rankingEvent>) => ({ calendar: { events: [event], validation_warnings: [], validation_errors: [] }, summary: { event_count: 1, persisted: true, first_event_week: 1, last_event_week: 1 }, validation_warnings: [] })

describe('Tournament Edition ranking controls', () => {
  beforeEach(() => { vi.clearAllMocks(); api.updateTournamentEditionRanking.mockResolvedValue({}); api.getSeasonCalendar.mockResolvedValue(response(rankingEvent(false))) })

  it('renders missing required fields and repairs the table atomically', async () => {
    api.getSeasonCalendar.mockResolvedValueOnce(response(rankingEvent(false))).mockResolvedValue(response(rankingEvent(true)))
    renderWithRoute(<SeasonCalendarPreview seasonLabelRaw="2000/01" />, '/')
    const finalist = await screen.findByRole('spinbutton', { name: 'Points for finalist' })
    expect(finalist).toHaveValue(null)
    expect(finalist).toHaveAttribute('aria-invalid', 'true')
    await userEvent.type(finalist, '5')
    await userEvent.click(screen.getByRole('button', { name: 'Save ranking configuration' }))
    expect(api.updateTournamentEditionRanking).toHaveBeenCalledWith('2000/01', 'evt-ranked', { ranking_status: 'ranked', ranking_points_table: { champion: 10, finalist: 5 } })
    await waitFor(() => expect(screen.getByText('Points table complete.')).toBeInTheDocument())
  })

  it('saves an Unranked selection only on the atomic save action', async () => {
    renderWithRoute(<SeasonCalendarPreview seasonLabelRaw="2000/01" />, '/')
    await userEvent.selectOptions(await screen.findByRole('combobox', { name: 'Ranking status for Ranked event' }), 'unranked')
    expect(api.updateTournamentEditionRanking).not.toHaveBeenCalled()
    expect(screen.getByText(/awards no MSA points or Best N result/)).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: 'Save ranking configuration' }))
    expect(api.updateTournamentEditionRanking).toHaveBeenCalledWith('2000/01', 'evt-ranked', { ranking_status: 'unranked', ranking_points_table: { champion: 10 } })
  })

  it('disables ranking editing after the Edition is no longer planned', async () => {
    api.getSeasonCalendar.mockResolvedValue(response(rankingEvent(false, 'active')))
    renderWithRoute(<SeasonCalendarPreview seasonLabelRaw="2000/01" />, '/')
    expect(await screen.findByRole('combobox', { name: 'Ranking status for Ranked event' })).toBeDisabled()
    expect(screen.getByRole('spinbutton', { name: 'Points for finalist' })).toBeDisabled()
    expect(screen.getByRole('button', { name: 'Save ranking configuration' })).toBeDisabled()
  })
})

it('normalizes a legacy-shaped event without manufacturing point values', async () => {
  const legacy = { ...rankingEvent(false) } as Record<string, unknown>
  for (const field of ['ranking_status', 'ranking_points_table', 'ranking_configuration_legacy', 'required_ranking_point_stages', 'missing_required_point_stages', 'points_table_complete']) delete legacy[field]
  api.getSeasonCalendar.mockResolvedValue(response(legacy as ReturnType<typeof rankingEvent>))
  renderWithRoute(<SeasonCalendarPreview seasonLabelRaw="2000/01" />, '/')
  expect(await screen.findByRole('combobox', { name: 'Ranking status for Ranked event' })).toHaveValue('ranked')
  expect(screen.queryAllByRole('spinbutton')).toHaveLength(0)
  expect(screen.getByText('Points table complete.')).toBeInTheDocument()
})
