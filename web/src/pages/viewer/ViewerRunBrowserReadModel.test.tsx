import { screen, within } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { VIEWER_ACTIVE_PRODUCT_RUN_STORAGE_KEY } from '../../viewer/activeProductRun'
import {
  clearViewerStorage,
  expectNoForbiddenViewerActions,
  renderWithViewerProviders,
  setViewerActiveProductRunId
} from '../../test/viewerTestUtils'
import { ViewerRunBrowserPage } from './ViewerRunBrowserPage'

const api = vi.hoisted(() => ({
  listRunContainers: vi.fn()
}))

vi.mock('../../api/client', () => api)

function renderRunBrowser(): void {
  renderWithViewerProviders(<ViewerRunBrowserPage />)
}

function runFixture(overrides: Record<string, unknown> = {}) {
  return {
    run_id: 'run alpha',
    display_name: 'Run Alpha',
    storage_kind: 'custom_local',
    read_only: false,
    world_id: 'fax-world',
    world_package_fingerprint: 'world-fp',
    config_version: 'v1',
    config_fingerprint: 'config-fp',
    global_seed: 42,
    timeline_start_season: 2000,
    timeline_end_season: 2049,
    viewer_branch_id: 'viewer',
    official_branch_id: 'official',
    status: 'ready',
    metadata_json: {},
    mapped_simulation_run_count: 2,
    ...overrides
  }
}

describe('ViewerRunBrowserPage Product Run read model', () => {
  beforeEach(() => {
    clearViewerStorage()
    vi.clearAllMocks()
    api.listRunContainers.mockResolvedValue({ run_containers: [] })
  })

  it('renders Product Run cards with conservative metadata and encoded links', async () => {
    api.listRunContainers.mockResolvedValue({
      run_containers: [
        runFixture({ run_id: 'run alpha/space #hash' }),
        runFixture({ run_id: 'run beta', official_branch_id: null, mapped_simulation_run_count: 0 })
      ]
    })

    renderRunBrowser()

    const runCard = await screen.findByLabelText('Run run alpha/space #hash')
    const metadata = within(runCard).getByLabelText('Run run alpha/space #hash metadata')
    for (const [label, value] of [
      ['Product Run ID', 'run alpha/space #hash'],
      ['Status', 'ready'],
      ['Storage kind', 'custom_local'],
      ['Read-only', 'false'],
      ['World ID', 'fax-world'],
      ['Timeline', '2000–2049'],
      ['Official Branch ID', 'official'],
      ['Mapped SimulationRuns', '2']
    ]) {
      expect(within(metadata).getByText(label)).toBeInTheDocument()
      expect(within(metadata).getByText(value)).toBeInTheDocument()
    }
    const encodedRun = 'run%20alpha%2Fspace%20%23hash'
    for (const [label, suffix] of [
      ['Season calendar', 'calendar'],
      ['Tournaments', 'tournaments'],
      ['Rankings', 'rankings'],
      ['Race', 'race'],
      ['Players', 'players'],
      ['Countries', 'countries'],
      ['History', 'history'],
      ['Finals', 'finals']
    ]) {
      expect(within(runCard).getByRole('link', { name: label })).toHaveAttribute(
        'href',
        `/viewer/runs/${encodedRun}/${suffix}`
      )
    }
    expectNoForbiddenViewerActions()
  })

  it('uses safe fallbacks for optional or malformed Product Run metadata', async () => {
    api.listRunContainers.mockResolvedValue({
      run_containers: [
        runFixture({
          status: '',
          storage_kind: { bad: true },
          world_id: null,
          timeline_start_season: undefined,
          timeline_end_season: undefined,
          official_branch_id: null,
          mapped_simulation_run_count: { bad: true }
        })
      ]
    })

    renderRunBrowser()

    const metadata = await screen.findByLabelText('Run run alpha metadata')
    expect(within(metadata).getAllByText('—').length).toBeGreaterThanOrEqual(6)
    expect(screen.queryByText('[object Object]')).not.toBeInTheDocument()
    expectNoForbiddenViewerActions()
  })

  it('marks only the active Product Run without mutating storage', async () => {
    setViewerActiveProductRunId('run active')
    const setItemSpy = vi.spyOn(Storage.prototype, 'setItem')
    const removeItemSpy = vi.spyOn(Storage.prototype, 'removeItem')
    api.listRunContainers.mockResolvedValue({
      run_containers: [
        runFixture({ run_id: 'run active' }),
        runFixture({ run_id: 'run inactive' })
      ]
    })

    renderRunBrowser()

    expect(await screen.findByText('Current active Viewer run id:')).toBeInTheDocument()
    expect(await screen.findByLabelText('Run run active')).toHaveTextContent('Active Viewer run')
    expect(screen.getByLabelText('Run run inactive')).toHaveTextContent('Available Viewer run')
    expect(localStorage.getItem(VIEWER_ACTIVE_PRODUCT_RUN_STORAGE_KEY)).toBe('run active')
    expect(setItemSpy).not.toHaveBeenCalled()
    expect(removeItemSpy).not.toHaveBeenCalled()
  })

  it('keeps duplicate Product Run IDs render-safe and links encoded', async () => {
    api.listRunContainers.mockResolvedValue({
      run_containers: [
        runFixture({ run_id: 'duplicate/run #1', global_seed: 1 }),
        runFixture({ run_id: 'duplicate/run #1', global_seed: 2 })
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

  it('keeps an active Product Run panel even when the run is absent from the list', async () => {
    setViewerActiveProductRunId('missing-active-run')
    api.listRunContainers.mockResolvedValue({
      run_containers: [runFixture({ run_id: 'run alpha' }), runFixture({ run_id: 'run beta' })]
    })

    renderRunBrowser()

    expect(await screen.findByText('Current active Viewer run id:')).toBeInTheDocument()
    expect(screen.getAllByText('missing-active-run').length).toBeGreaterThan(0)
    expect(await screen.findByLabelText('Run run alpha')).toHaveTextContent('Available Viewer run')
    expect(screen.queryByText('Currently selected for active-run Viewer pages.')).not.toBeInTheDocument()
    expectNoForbiddenViewerActions()
  })
})
