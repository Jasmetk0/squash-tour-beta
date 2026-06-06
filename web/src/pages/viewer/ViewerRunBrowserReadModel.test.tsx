import { screen, within } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { VIEWER_ACTIVE_RUN_STORAGE_KEY } from '../../viewer/activeRun'
import { clearViewerStorage, expectNoForbiddenViewerActions, renderWithViewerProviders, setViewerActiveRunId } from '../../test/viewerTestUtils'
import { ViewerRunBrowserPage } from './ViewerRunBrowserPage'

const api = vi.hoisted(() => ({
  listRuns: vi.fn()
}))

vi.mock('../../api/client', () => api)

function renderRunBrowser(): void {
  renderWithViewerProviders(<ViewerRunBrowserPage />)
}

function runFixture(overrides: Record<string, unknown> = {}) {
  return {
    run_id: 'run alpha',
    season: 2031,
    seed: 42,
    progress: { next_event_index: 3, total_events: 11, completed_event_count: 2 },
    source_type: 'fresh_seed',
    parent_run_id: 'parent-run',
    child_run_count: 1,
    ...overrides
  }
}

describe('ViewerRunBrowserPage read-model polish', () => {
  beforeEach(() => {
    clearViewerStorage()
    vi.clearAllMocks()
    api.listRuns.mockResolvedValue({ runs: [] })
  })

  it('renders successful run cards with conservative metadata and encoded run-scoped links', async () => {
    api.listRuns.mockResolvedValue({
      runs: [runFixture({ run_id: 'run alpha/space #hash' }), runFixture({ run_id: 'run beta', parent_run_id: null, child_run_count: 0 })]
    })

    renderRunBrowser()

    expect(await screen.findByRole('heading', { level: 2, name: 'Run Browser' })).toBeInTheDocument()
    const runCard = await screen.findByLabelText('Run run alpha/space #hash')
    const metadata = within(runCard).getByLabelText('Run run alpha/space #hash metadata')
    for (const [label, value] of [
      ['Run id', 'run alpha/space #hash'],
      ['Season', '2031'],
      ['Seed', '42'],
      ['Source', 'fresh_seed'],
      ['Parent run', 'parent-run'],
      ['Child runs', '1'],
      ['Next event index', '3'],
      ['Total events', '11'],
      ['Completed event count', '2']
    ]) {
      expect(within(metadata).getByText(label)).toBeInTheDocument()
      expect(within(metadata).getByText(value)).toBeInTheDocument()
    }

    const encodedRun = 'run%20alpha%2Fspace%20%23hash'
    expect(within(runCard).getByRole('link', { name: 'Season calendar' })).toHaveAttribute('href', `/viewer/runs/${encodedRun}/calendar`)
    expect(within(runCard).getByRole('link', { name: 'Tournaments' })).toHaveAttribute('href', `/viewer/runs/${encodedRun}/tournaments`)
    expect(within(runCard).getByRole('link', { name: 'Rankings' })).toHaveAttribute('href', `/viewer/runs/${encodedRun}/rankings`)
    expect(within(runCard).getByRole('link', { name: 'Race' })).toHaveAttribute('href', `/viewer/runs/${encodedRun}/race`)
    expect(within(runCard).getByRole('link', { name: 'Players' })).toHaveAttribute('href', `/viewer/runs/${encodedRun}/players`)
    expect(within(runCard).getByRole('link', { name: 'Countries' })).toHaveAttribute('href', `/viewer/runs/${encodedRun}/countries`)
    expect(within(runCard).getByRole('link', { name: 'History' })).toHaveAttribute('href', `/viewer/runs/${encodedRun}/history`)
    expect(within(runCard).getByRole('link', { name: 'Finals' })).toHaveAttribute('href', `/viewer/runs/${encodedRun}/finals`)
    expectNoForbiddenViewerActions()
  })

  it('renders a read-only empty state without forbidden Viewer action labels', async () => {
    renderRunBrowser()

    expect(await screen.findByText('No Viewer runs are available yet.')).toBeInTheDocument()
    expectNoForbiddenViewerActions()
  })

  it('renders a safe unavailable state when the run list API fails', async () => {
    api.listRuns.mockRejectedValue(new Error('run list unavailable'))

    renderRunBrowser()

    expect(await screen.findByText('Run metadata is temporarily unavailable.')).toBeInTheDocument()
    expectNoForbiddenViewerActions()
  })

  it('uses em dash fallbacks for missing optional metadata without throwing', async () => {
    api.listRuns.mockResolvedValue({ runs: [runFixture({ source_type: null, parent_run_id: null, child_run_count: undefined })] })

    renderRunBrowser()

    const metadata = await screen.findByLabelText('Run run alpha metadata')
    expect(within(metadata).getByText('Source')).toBeInTheDocument()
    expect(within(metadata).getByText('Parent run')).toBeInTheDocument()
    expect(within(metadata).getByText('Child runs')).toBeInTheDocument()
    expect(within(metadata).getAllByText('—').length).toBeGreaterThanOrEqual(3)
  })

  it('indicates the active run from existing active-run storage without changing selection semantics', async () => {
    setViewerActiveRunId('run active')
    api.listRuns.mockResolvedValue({ runs: [runFixture({ run_id: 'run active' }), runFixture({ run_id: 'run inactive' })] })

    renderRunBrowser()

    expect(await screen.findByText('Current active Viewer run id:')).toBeInTheDocument()
    expect(await screen.findByLabelText('Run run active')).toHaveTextContent('Active Viewer run')
    expect(screen.getByLabelText('Run run active')).toHaveTextContent('Currently selected for active-run Viewer pages.')
    expect(screen.getByLabelText('Run run inactive')).toHaveTextContent('Available Viewer run')
  })

  it('falls back for unsafe object run-list fields without rendering raw object strings', async () => {
    api.listRuns.mockResolvedValue({
      runs: [
        runFixture({
          source_type: { raw: 'source' },
          parent_run_id: ['parent-run'],
          child_run_count: { count: 2 },
          progress: {
            next_event_index: { raw: 3 },
            total_events: null,
            completed_event_count: ['done']
          }
        })
      ]
    })

    renderRunBrowser()

    const metadata = await screen.findByLabelText('Run run alpha metadata')
    for (const label of ['Source', 'Parent run', 'Child runs', 'Next event index', 'Total events', 'Completed event count']) {
      expect(within(metadata).getByText(label)).toBeInTheDocument()
    }
    expect(within(metadata).getAllByText('—').length).toBeGreaterThanOrEqual(6)
    expect(screen.queryByText('[object Object]')).not.toBeInTheDocument()
    expectNoForbiddenViewerActions()
  })

  it('uses em dash progress fallbacks when a run is missing progress', async () => {
    api.listRuns.mockResolvedValue({ runs: [runFixture({ progress: undefined })] })

    renderRunBrowser()

    const metadata = await screen.findByLabelText('Run run alpha metadata')
    for (const label of ['Next event index', 'Total events', 'Completed event count']) {
      expect(within(metadata).getByText(label)).toBeInTheDocument()
    }
    expect(within(metadata).getAllByText('—').length).toBeGreaterThanOrEqual(3)
  })

  it('does not crash when listRuns returns duplicate run IDs and keeps encoded links', async () => {
    api.listRuns.mockResolvedValue({
      runs: [
        runFixture({ run_id: 'duplicate/run #1', seed: 1 }),
        runFixture({ run_id: 'duplicate/run #1', seed: 2 })
      ]
    })

    renderRunBrowser()

    const cards = await screen.findAllByLabelText('Run duplicate/run #1')
    expect(cards).toHaveLength(2)
    for (const card of cards) {
      expect(within(card).getByRole('link', { name: 'Season calendar' })).toHaveAttribute(
        'href',
        '/viewer/runs/duplicate%2Frun%20%231/calendar'
      )
    }
  })

  it('renders weird primitive run-list values using the existing primitive metadata contract', async () => {
    api.listRuns.mockResolvedValue({
      runs: [
        runFixture({
          source_type: true,
          parent_run_id: false,
          child_run_count: true,
          progress: { next_event_index: false, total_events: 0, completed_event_count: true }
        })
      ]
    })

    renderRunBrowser()

    const metadata = await screen.findByLabelText('Run run alpha metadata')
    for (const [label, value] of [
      ['Source', 'true'],
      ['Parent run', 'false'],
      ['Child runs', 'true'],
      ['Next event index', 'false'],
      ['Total events', '0'],
      ['Completed event count', 'true']
    ]) {
      expect(within(metadata).getByText(label)).toBeInTheDocument()
      expect(within(metadata).getAllByText(value).length).toBeGreaterThan(0)
    }
  })

  it('keeps an active run panel value even when the active run is absent from the run list', async () => {
    setViewerActiveRunId('missing-active-run')
    const setItemSpy = vi.spyOn(Storage.prototype, 'setItem')
    const removeItemSpy = vi.spyOn(Storage.prototype, 'removeItem')
    api.listRuns.mockResolvedValue({ runs: [runFixture({ run_id: 'run alpha' }), runFixture({ run_id: 'run beta' })] })

    renderRunBrowser()

    expect(await screen.findByText('Current active Viewer run id:')).toBeInTheDocument()
    expect(screen.getAllByText('missing-active-run').length).toBeGreaterThan(0)
    expect(await screen.findByLabelText('Run run alpha')).toHaveTextContent('Available Viewer run')
    expect(screen.getByLabelText('Run run beta')).toHaveTextContent('Available Viewer run')
    expect(screen.queryByText('Currently selected for active-run Viewer pages.')).not.toBeInTheDocument()
    expect(localStorage.getItem(VIEWER_ACTIVE_RUN_STORAGE_KEY)).toBe('missing-active-run')
    expect(setItemSpy).not.toHaveBeenCalled()
    expect(removeItemSpy).not.toHaveBeenCalled()
  })

  it('renders safely when storage is unavailable during run browser render', async () => {
    vi.spyOn(Storage.prototype, 'getItem').mockImplementation(() => {
      throw new Error('storage unavailable')
    })
    api.listRuns.mockResolvedValue({ runs: [runFixture()] })

    renderRunBrowser()

    expect(await screen.findByRole('heading', { level: 2, name: 'Run Browser' })).toBeInTheDocument()
    expect(screen.getByText('No active Viewer run selected.')).toBeInTheDocument()
    expect(await screen.findByLabelText('Run run alpha')).toHaveTextContent('Available Viewer run')
    expect(screen.queryByText(/storage unavailable/i)).not.toBeInTheDocument()
  })

})
