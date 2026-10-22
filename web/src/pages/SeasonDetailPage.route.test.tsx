import { render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { describe, expect, it, vi } from 'vitest'

import { AdminSeasonDetailPage } from './SeasonDetailPage'

vi.mock('./SelectedSeasonWorkspace', () => ({
  SelectedSeasonWorkspace: ({ selectedSeasonRaw }: { selectedSeasonRaw: string }) =>
    <p data-testid="selected-season">{selectedSeasonRaw}</p>,
}))
vi.mock('./SeasonCalendarPreview', () => ({
  SeasonCalendarPreview: () => <p>Mock calendar</p>,
}))
vi.mock('./SeasonRankingPointsPreview', () => ({
  SeasonRankingPointsPreview: () => <p>Mock ranking</p>,
}))
vi.mock('./SeasonHealthPreview', () => ({
  SeasonHealthPreview: () => <p>Mock health</p>,
}))

function mount(url: string) {
  render(
    <MemoryRouter initialEntries={[url]}>
      <Routes><Route path="/admin/seasons/detail/:seasonLabel" element={<AdminSeasonDetailPage />} /></Routes>
    </MemoryRouter>
  )
}

describe('Concrete season route parameter interpretation', () => {
  it('uses the already decoded React Router season parameter', () => {
    mount('/admin/seasons/detail/2000%2F01')
    expect(screen.getByTestId('selected-season')).toHaveTextContent('2000/01')
    expect(screen.getByRole('link', { name: '/admin/seasons/detail/2000%2F01' }))
      .toHaveAttribute('href', '/admin/seasons/detail/2000%2F01')
  })

  it('does not crash on a safely encoded literal percent in an invalid label', () => {
    mount('/admin/seasons/detail/2000%25')
    expect(screen.getByRole('heading', { name: 'Concrete Season' })).toBeInTheDocument()
    expect(screen.getByTestId('selected-season')).toHaveTextContent('2000%')
    expect(screen.queryByRole('heading', { name: 'Canonical route' })).not.toBeInTheDocument()
  })

})
