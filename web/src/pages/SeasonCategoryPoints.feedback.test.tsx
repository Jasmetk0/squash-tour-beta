import { fireEvent, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { renderWithRoute } from '../test/testUtils'

import { SeasonCategoryPoints } from './SeasonCategoryPoints'

const api = vi.hoisted(() => ({
  getSeasonCategoryPoints: vi.fn(),
  initializeSeasonCategoryPoints: vi.fn(),
  updateSeasonCategoryPoints: vi.fn(),
}))
vi.mock('../api/client', async importOriginal => ({ ...(await importOriginal<object>()), ...api }))

const table = {
  season: '2000/01',
  category: 'DIAMOND',
  provenance: 'explicit',
  source_season: null,
  ranking_points_table: { champion: 100, finalist: 60 },
}

describe('Season Category Points mutation and failure feedback', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    api.getSeasonCategoryPoints.mockResolvedValue({
      season: '2000/01', initialized: true, categories: [table],
    })
    api.initializeSeasonCategoryPoints.mockResolvedValue({ initialized: true })
    api.updateSeasonCategoryPoints.mockResolvedValue({ saved: true })
  })

  it('shows the backend load error without pretending it has initialized the season', async () => {
    api.getSeasonCategoryPoints.mockRejectedValue(new Error('category backend unavailable'))
    renderWithRoute(<SeasonCategoryPoints seasonLabelRaw="2000/01" />, '/')
    expect(await screen.findByRole('alert')).toHaveTextContent('Could not load category points: category backend unavailable')
    expect(screen.queryByRole('button', { name: /Initialize Season Category Points/ })).not.toBeInTheDocument()
    expect(api.initializeSeasonCategoryPoints).not.toHaveBeenCalled()
  })

  it('keeps the initialize action available after a failed attempt with visible error', async () => {
    api.getSeasonCategoryPoints.mockResolvedValue({ initialized: false, categories: [] })
    api.initializeSeasonCategoryPoints.mockRejectedValue(new Error('already initialized in another session'))
    renderWithRoute(<SeasonCategoryPoints seasonLabelRaw="2000/01" />, '/')
    const button = await screen.findByRole('button', { name: 'Initialize Season Category Points' })
    fireEvent.click(button)
    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Could not initialize category points: already initialized in another session'
    )
    expect(button).toBeEnabled()
    expect(api.initializeSeasonCategoryPoints).toHaveBeenCalledTimes(1)
  })

  it('reports save failure, retains entered values and allows a successful retry', async () => {
    api.updateSeasonCategoryPoints.mockRejectedValueOnce(new Error('conflict during save'))
    renderWithRoute(<SeasonCategoryPoints seasonLabelRaw="2000/01" />, '/')
    const points = await screen.findByRole('spinbutton', { name: 'DIAMOND champion' })
    await waitFor(() => expect(points).toHaveValue(100))
    fireEvent.change(points, { target: { value: '120' } })
    fireEvent.click(screen.getByRole('button', { name: 'Save DIAMOND' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('Could not save DIAMOND points: conflict during save')
    expect(points).toHaveValue(120)
    expect(api.updateSeasonCategoryPoints).toHaveBeenCalledWith('2000/01', 'DIAMOND', {
      champion: 120, finalist: 60
    })
    fireEvent.click(screen.getByRole('button', { name: 'Save DIAMOND' }))
    expect(await screen.findByRole('status')).toHaveTextContent('Saved DIAMOND points.')
    expect(api.updateSeasonCategoryPoints).toHaveBeenCalledTimes(2)
  })

  it('does not attempt an initialization or save without a selected season', () => {
    renderWithRoute(<SeasonCategoryPoints seasonLabelRaw={null} />, '/')
    expect(screen.queryByText('Season Category Points')).not.toBeInTheDocument()
    expect(api.getSeasonCategoryPoints).not.toHaveBeenCalled()
  })
})
