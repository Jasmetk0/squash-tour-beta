import { screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { LanguageProvider } from '../../../i18n/LanguageContext'
import {
  clearViewerStorage, expectNoForbiddenViewerActions,
  renderWithViewerProviders, setViewerActiveRunId
} from '../../../test/viewerTestUtils'
import { ViewerRecordsPage } from './ViewerRecordsPage'

const api = vi.hoisted(() => ({
  getViewerRunCalendar: vi.fn(),
  getViewerTournamentHistory: vi.fn(),
  listViewerOfficialRankingHistory: vi.fn(),
  getViewerFinalsRace: vi.fn(),
  getViewerOfficialRunContext: vi.fn()
}))
const signed = vi.hoisted(() => ({ getViewerSignedTourRecords: vi.fn() }))
vi.mock('../../../api/client', () => api)
vi.mock('../../../api/viewerSignedTourRecords', () => signed)

function renderRecords(): void {
  renderWithViewerProviders(<LanguageProvider><ViewerRecordsPage /></LanguageProvider>)
}

function mockCanonicalViewerSources(): void {
  api.getViewerOfficialRunContext.mockResolvedValue({
    product_run_id: 'record run', official_branch_id: 'viewer-a'
  })
  api.getViewerRunCalendar.mockResolvedValue({
    viewer_branch_id: 'viewer-a', season_count: 2, event_count: 2,
    seasons: [{ events: [{ event_id: 'EVT-2', status: 'planned' }] }]
  })
  api.getViewerTournamentHistory.mockResolvedValue({
    viewer_branch_id: 'viewer-a', tournaments: [
      { event_id: 'EVT-2', event_name: 'British Open', result_published: true }
    ]
  })
  api.listViewerOfficialRankingHistory.mockResolvedValue({
    viewer_branch_id: 'viewer-a', publication_count: 1,
    publications: [{ season_index: 34, week: 20, week_ordinal: 22 }]
  })
  api.getViewerFinalsRace.mockResolvedValue({
    viewer_branch_id: 'viewer-a', publications: []
  })
  signed.getViewerSignedTourRecords.mockRejectedValue(new Error('No signed native season'))
}

describe('ViewerRecordsPage', () => {
  beforeEach(() => {
    clearViewerStorage()
    localStorage.setItem('squash-engine-language-v1', 'en')
    vi.clearAllMocks()
    mockCanonicalViewerSources()
  })

  it('renders the no-active-run landing and never reads a signed record without a Run', () => {
    renderRecords()
    expect(screen.getByRole('heading', { level: 2, name: 'Records' })).toBeInTheDocument()
    expect(screen.getByText('Record book destination prepared for statistics, milestones, and historical achievements.')).toBeInTheDocument()
    expect(screen.getByText('No Product Run is selected yet.')).toBeInTheDocument()
    expect(signed.getViewerSignedTourRecords).not.toHaveBeenCalled()
    expectNoForbiddenViewerActions()
  })

  it('keeps Saved metadata and deferred links while adding optional signed records', async () => {
    setViewerActiveRunId('record run')
    renderRecords()

    expect(await screen.findByRole('link', { name: 'British Open' })).toHaveAttribute(
      'href', '/viewer/runs/record%20run/tournaments/EVT-2'
    )
    expect(screen.getByText('Records Overview')).toBeInTheDocument()
    expect(screen.getByText('record run')).toBeInTheDocument()
    expect(screen.getByText('Viewer Branch')).toBeInTheDocument()
    expect(screen.getByText('Saved Calendar events')).toBeInTheDocument()
    expect(screen.getByText('Official Ranking publications')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Season 34 W20 · #22' })).toHaveAttribute(
      'href', '/viewer/runs/record%20run/rankings/22'
    )
    expect(await screen.findByRole('heading', { name: 'Records from completed seasons' })).toBeInTheDocument()

    const deferredText = screen.getByRole('list', { name: 'Deferred record groups' }).textContent ?? ''
    expect(deferredText.indexOf('Title Leaders')).toBeLessThan(deferredText.indexOf('Weeks at No.1'))
    expect(deferredText.indexOf('Weeks at No.1')).toBeLessThan(deferredText.indexOf('Streaks'))
    expect(deferredText.indexOf('Streaks')).toBeLessThan(deferredText.indexOf('Biggest Upsets'))
    expect(deferredText.indexOf('Biggest Upsets')).toBeLessThan(deferredText.indexOf('Best Seasons'))
    expect(screen.getByRole('link', { name: 'Open active run tournaments' })).toHaveAttribute(
      'href', '/viewer/runs/record%20run/tournaments'
    )
    expectNoForbiddenViewerActions()
  })
})
