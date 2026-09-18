import { screen, within } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import {
  clearViewerStorage,
  expectNoForbiddenViewerActions,
  renderWithViewerProviders,
  setViewerActiveRunId
} from '../../test/viewerTestUtils'
import { ViewerRunBrowserPage } from './ViewerRunBrowserPage'

const api = vi.hoisted(() => ({
  listRunContainers: vi.fn(),
  ApiError: class ApiError extends Error {
    status: number
    constructor(message: string, status = 500) {
      super(message)
      this.status = status
    }
  }
}))

vi.mock('../../api/client', () => api)

function renderRunBrowser(): void {
  renderWithViewerProviders(<ViewerRunBrowserPage />)
}

function sampleRun(overrides: Record<string, unknown> = {}) {
  return {
    run_id: 'run alpha',
    display_name: 'Run Alpha',
    storage_kind: 'custom_local',
    read_only: false,
    world_id: 'official_fax_world',
    world_package_fingerprint: 'world-fp',
    config_version: 'v1',
    config_fingerprint: 'config-fp',
    global_seed: 42,
    timeline_start_season: 2000,
    timeline_end_season: 2049,
    viewer_branch_id: 'viewer',
    official_branch_id: 'main',
    status: 'ready',
    metadata_json: {},
    mapped_simulation_run_count: 1,
    ...overrides
  }
}

describe('ViewerRunBrowserPage', () => {
  beforeEach(() => {
    clearViewerStorage()
    vi.clearAllMocks()
    api.listRunContainers.mockResolvedValue({ run_containers: [] })
  })

  it('shows no active Product Run when none is selected', async () => {
    renderRunBrowser()
    expect(await screen.findByText('No active Viewer run selected.')).toBeInTheDocument()
  })

  it('shows loading and empty states from the Product Run list API', async () => {
    api.listRunContainers.mockReturnValueOnce(new Promise(() => undefined))
    const first = renderWithViewerProviders(<ViewerRunBrowserPage />)
    expect(screen.getAllByText('Loading available runs…').length).toBeGreaterThan(0)
    first.unmount()

    api.listRunContainers.mockResolvedValueOnce({ run_containers: [] })
    renderRunBrowser()
    expect(await screen.findByText('No Viewer runs are available yet.')).toBeInTheDocument()
  })

  it('renders Product Run metadata and encoded quick links', async () => {
    setViewerActiveRunId('run alpha')
    api.listRunContainers.mockResolvedValue({ run_containers: [sampleRun()] })

    renderRunBrowser()

    expect(await screen.findByRole('heading', { level: 4, name: 'run alpha' })).toBeInTheDocument()
    expect(screen.getByText('Current active Viewer run id:')).toBeInTheDocument()
    const metadata = screen.getByLabelText('Run run alpha metadata')
    for (const [label, value] of [
      ['Product Run ID', 'run alpha'],
      ['Status', 'ready'],
      ['Storage kind', 'custom_local'],
      ['Read-only', 'false'],
      ['World ID', 'official_fax_world'],
      ['Timeline', '2000–2049'],
      ['Official Branch ID', 'main'],
      ['Mapped SimulationRuns', '1']
    ]) {
      expect(within(metadata).getByText(label)).toBeInTheDocument()
      expect(within(metadata).getByText(value)).toBeInTheDocument()
    }

    for (const [label, href] of [
      ['Season calendar', '/viewer/runs/run%20alpha/calendar'],
      ['Rankings', '/viewer/runs/run%20alpha/rankings'],
      ['Race', '/viewer/runs/run%20alpha/race'],
      ['Tournaments', '/viewer/runs/run%20alpha/tournaments'],
      ['Players', '/viewer/runs/run%20alpha/players'],
      ['Countries', '/viewer/runs/run%20alpha/countries'],
      ['History', '/viewer/runs/run%20alpha/history'],
      ['Finals', '/viewer/runs/run%20alpha/finals']
    ]) {
      expect(screen.getByRole('link', { name: label })).toHaveAttribute('href', href)
    }
    expectNoForbiddenViewerActions()
  })

  it('drops malformed Product Run records and never emits unsafe route text', async () => {
    api.listRunContainers.mockResolvedValue({
      run_containers: [
        null,
        7,
        'run-string',
        {},
        { run_id: { value: 'object-run' } },
        { run_id: '' },
        sampleRun({
          run_id: 'safe run',
          status: { bad: true },
          world_id: ['bad'],
          official_branch_id: { bad: true },
          mapped_simulation_run_count: { bad: true }
        })
      ]
    })

    renderRunBrowser()

    expect(await screen.findByRole('heading', { level: 4, name: 'safe run' })).toBeInTheDocument()
    expect(screen.queryByText('object-run')).not.toBeInTheDocument()
    expect(screen.queryByText('run-string')).not.toBeInTheDocument()
    expect(document.body).not.toHaveTextContent('[object Object]')
    const metadata = screen.getByLabelText('Run safe run metadata')
    expect(within(metadata).getAllByText('—').length).toBeGreaterThanOrEqual(4)
    for (const link of screen.getAllByRole('link')) {
      const href = link.getAttribute('href') ?? ''
      expect(href).not.toContain('[object%20Object]')
      expect(href).not.toContain('[object Object]')
      expect(href).not.toMatch(/^\/admin(?:\/|$)/)
    }
    expectNoForbiddenViewerActions()
  })

  it('encodes Product Run ids with slashes, hashes, and spaces', async () => {
    api.listRunContainers.mockResolvedValue({
      run_containers: [{ ...sampleRun(), run_id: 'run/alpha #1' }]
    })

    renderRunBrowser()

    expect(await screen.findByRole('heading', { level: 4, name: 'run/alpha #1' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Season calendar' })).toHaveAttribute(
      'href',
      '/viewer/runs/run%2Falpha%20%231/calendar'
    )
    expectNoForbiddenViewerActions()
  })

  it('shows a safe unavailable state when Product Run listing fails', async () => {
    api.listRunContainers.mockRejectedValue(new Error('run list unavailable'))
    renderRunBrowser()
    expect(await screen.findByText('Run metadata is temporarily unavailable.')).toBeInTheDocument()
    expectNoForbiddenViewerActions()
  })
})
