import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { renderWithRoute } from '../test/testUtils'
import { SeasonCalendarPreview } from './SeasonCalendarPreview'
const api = vi.hoisted(() => ({ getSeasonCalendar: vi.fn(), updateTournamentEditionRanking: vi.fn() }))
vi.mock('../api/client', () => api)
const event = (ranking_status: 'ranked' | 'unranked', complete: boolean) => ({ event_id: `evt-${ranking_status}`, season: '2000/2001', season_week: 1, start_season_week: 1, event_name: `${ranking_status} event`, category: 'OPEN', host_country: 'ENG', region: 'EUROPE', template_id: 'tpl', status: 'planned', ranking_status, ranking_points_table: complete ? { champion: 10, finalist: 5 } : { champion: 10 }, points_table_complete: complete, missing_required_point_stages: complete ? [] : ['finalist'] })
describe('Tournament Edition ranking controls', () => {
  beforeEach(() => { vi.clearAllMocks(); api.updateTournamentEditionRanking.mockResolvedValue({}); api.getSeasonCalendar.mockResolvedValue({ calendar: { events: [event('ranked', false), event('unranked', true)], validation_warnings: [], validation_errors: [] }, summary: { event_count: 2, persisted: true, first_event_week: 1, last_event_week: 1 }, validation_warnings: [] }) })
  it('shows status, Ranked warning/table, and Unranked explanation', async () => { renderWithRoute(<SeasonCalendarPreview seasonLabelRaw="2000/01" />, '/'); expect(await screen.findByText(/Points table incomplete/)).toHaveTextContent('finalist'); expect(screen.getByText(/awards no MSA points or Best N result/)).toBeInTheDocument(); expect(screen.getByText('Effective points table')).toBeInTheDocument() })
  it('lets Admin select status while planned', async () => { renderWithRoute(<SeasonCalendarPreview seasonLabelRaw="2000/01" />, '/'); const select = await screen.findByRole('combobox', { name: 'Ranking status for ranked event' }); await userEvent.selectOptions(select, 'unranked'); expect(api.updateTournamentEditionRanking).toHaveBeenCalledWith('2000/01', 'evt-ranked', { ranking_status: 'unranked', ranking_points_table: { champion: 10 } }) })
})
