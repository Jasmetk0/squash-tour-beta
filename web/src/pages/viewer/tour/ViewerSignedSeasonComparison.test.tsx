import { fireEvent, screen, within } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { LanguageProvider } from '../../../i18n/LanguageContext'
import { renderWithViewerProviders } from '../../../test/viewerTestUtils'
import { ViewerSignedSeasonComparison } from './ViewerSignedSeasonComparison'
import { signedSeasonListFixture, signedSeasonComparisonFixture } from './viewerSignedSeasonFixture'

const api = vi.hoisted(() => ({ getViewerOfficialRunContext: vi.fn() }))
const seasons = vi.hoisted(() => ({ listViewerSignedSeasons: vi.fn(), readViewerSignedSeason: vi.fn() }))
vi.mock('../../../api/client', () => api)
vi.mock('../../../api/viewerSignedSeason', () => seasons)

function renderPanel() {
  renderWithViewerProviders(<LanguageProvider>
    <ViewerSignedSeasonComparison runId="run alpha" />
  </LanguageProvider>)
}

describe('Viewer signed seasons UI (mocked public GETs only)', () => {
  beforeEach(() => {
    localStorage.setItem('squash-engine-language-v1', 'en')
    vi.clearAllMocks()
    api.getViewerOfficialRunContext.mockResolvedValue({
      product_run_id: 'run alpha', official_branch_id: 'branch-tour'
    })
    seasons.listViewerSignedSeasons.mockResolvedValue(signedSeasonListFixture())
    seasons.readViewerSignedSeason.mockImplementation(async (_run, _index, compare) =>
      signedSeasonComparisonFixture(compare !== null))
  })

  it('does not call a season report until explicit choice and then shows signed rows', async () => {
    renderPanel()
    expect(await screen.findByRole('button', { name: 'Show report' })).toBeInTheDocument()
    expect(seasons.readViewerSignedSeason).not.toHaveBeenCalled()
    fireEvent.click(screen.getByRole('button', { name: 'Show report' }))
    expect(await screen.findByText('Season summary: 2001/02')).toBeInTheDocument()
    expect(screen.getByText('rev-20')).toBeInTheDocument()
    const section = screen.getByRole('article', { name: 'Season summary' })
    expect(within(section).getByRole('table', { name: 'Season editions' })).toBeInTheDocument()
    expect(within(section).getByRole('table', { name: 'Country statistics' })).toBeInTheDocument()
    expect(within(section).getByRole('table', { name: 'Published end-of-season ranking' })).toBeInTheDocument()
    expect(within(section).getAllByRole('link', { name: 'Player One' })[0]).toHaveAttribute(
      'href', '/viewer/runs/run%20alpha/players/p1/career'
    )
    expect(seasons.readViewerSignedSeason).toHaveBeenCalledWith('run alpha', 1, null, expect.anything())
    expect(screen.queryByRole('button', { name: /Save|Simulate|Publish/i })).not.toBeInTheDocument()
  })

  it('compares exactly two closed seasons and displays source-verified national deltas', async () => {
    renderPanel()
    await screen.findByRole('button', { name: 'Show report' })
    fireEvent.change(screen.getByLabelText('Comparison season'), { target: { value: '0' } })
    expect(seasons.readViewerSignedSeason).not.toHaveBeenCalled()
    fireEvent.click(screen.getByRole('button', { name: 'Show report' }))
    expect(await screen.findByText('2001/02 ↔ 2000/01')).toBeInTheDocument()
    expect(seasons.readViewerSignedSeason).toHaveBeenCalledWith('run alpha', 1, 0, expect.anything())
    const delta = screen.getByRole('table', { name: 'Change versus comparison season' })
    expect(within(delta).getByText('-40')).toBeInTheDocument()
  })

  it('rejects a comparison from another Saved revision, without showing any statistics', async () => {
    seasons.readViewerSignedSeason.mockResolvedValue({
      ...signedSeasonComparisonFixture(), saved_head_revision_id: 'foreign'
    })
    renderPanel()
    await screen.findByRole('button', { name: 'Show report' })
    fireEvent.click(screen.getByRole('button', { name: 'Show report' }))
    expect(await screen.findByText(/Historical source failed Run/)).toBeInTheDocument()
    expect(screen.queryByText('Season summary: 2001/02')).not.toBeInTheDocument()
  })

  it('refuses foreign Viewer Branch before any signed data read', async () => {
    api.getViewerOfficialRunContext.mockResolvedValue({
      product_run_id: 'other', official_branch_id: 'branch-tour'
    })
    renderPanel()
    expect(await screen.findByText(/Historical source failed Run/)).toBeInTheDocument()
    expect(seasons.listViewerSignedSeasons).not.toHaveBeenCalled()
  })

  it('does not fabricate a season after a legitimate 409 for no signed closure', async () => {
    seasons.listViewerSignedSeasons.mockRejectedValue(new Error('HTTP 409'))
    renderPanel()
    expect(await screen.findByText(/Signed seasons unavailable/)).toBeInTheDocument()
    expect(seasons.readViewerSignedSeason).not.toHaveBeenCalled()
  })
})
