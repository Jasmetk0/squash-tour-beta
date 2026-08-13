import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, expect, it, vi } from 'vitest'
import { renderWithRoute } from '../test/testUtils'
import { SeasonCategoryPoints } from './SeasonCategoryPoints'

const api = vi.hoisted(() => ({ getSeasonCategoryPoints: vi.fn(), initializeSeasonCategoryPoints: vi.fn(), updateSeasonCategoryPoints: vi.fn() }))
vi.mock('../api/client', () => api)

beforeEach(() => {
  vi.clearAllMocks()
  api.getSeasonCategoryPoints.mockResolvedValue({ season: '2001/02', initialized: true, categories: [{ season: '2001/02', category: 'PLATINUM', ranking_points_table: { champion: 1000, finalist: 650 }, provenance: 'prefilled_from_previous_season', source_season: '2000/01' }] })
  api.updateSeasonCategoryPoints.mockResolvedValue({})
})

it('renders provenance and saves explicit zero while blank stays missing', async () => {
  renderWithRoute(<SeasonCategoryPoints seasonLabelRaw="2001/02" />, '/')
  expect(await screen.findByText(/prefilled_from_previous_season/)).toBeInTheDocument()
  expect(screen.getByText(/2000\/01/)).toBeInTheDocument()
  const champion = screen.getByRole('spinbutton', { name: 'PLATINUM champion' })
  const finalist = screen.getByRole('spinbutton', { name: 'PLATINUM finalist' })
  await userEvent.clear(champion)
  await userEvent.type(champion, '0')
  await userEvent.clear(finalist)
  await userEvent.click(screen.getByRole('button', { name: 'Save PLATINUM' }))
  await waitFor(() => expect(api.updateSeasonCategoryPoints).toHaveBeenCalledWith('2001/02', 'PLATINUM', { champion: 0 }))
})
