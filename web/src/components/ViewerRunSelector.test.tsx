import { fireEvent, screen, within } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { ViewerRunSelector } from './ViewerRunSelector'
import { VIEWER_ACTIVE_RUN_STORAGE_KEY } from '../viewer/activeRun'
import { expectNoForbiddenViewerActions, renderWithViewerProviders } from '../test/viewerTestUtils'

const api = vi.hoisted(() => ({
  listRuns: vi.fn()
}))

vi.mock('../api/client', () => api)

function renderSelector(): void {
  renderWithViewerProviders(<ViewerRunSelector />)
}

function expectViewerOnlyLinks(): void {
  for (const link of screen.queryAllByRole('link')) {
    const href = link.getAttribute('href') ?? ''
    expect(href).toMatch(/^\/viewer(?:\/|$)/)
    expect(href).not.toMatch(/^\/admin(?:\/|$)/)
    expect(href).not.toContain('[object Object]')
    expect(href).not.toContain('[object%20Object]')
  }
}

describe('ViewerRunSelector runtime safety', () => {
  beforeEach(() => {
    localStorage.clear()
    vi.clearAllMocks()
    api.listRuns.mockResolvedValue({ runs: [] })
  })

  it('renders empty behavior conservatively without fake run records, object output, or mutation controls', async () => {
    renderSelector()

    expect(await screen.findByText('No runs are available yet.')).toBeInTheDocument()
    expect(screen.getByRole('option', { name: 'No runs available' })).toHaveAttribute('value', '')
    expect(screen.getByRole('link', { name: 'Browse all runs' })).toHaveAttribute('href', '/viewer/runs')
    expect(screen.queryByText(/run-a|run alpha|Champion|Winner|Standings/i)).not.toBeInTheDocument()
    expect(document.body).not.toHaveTextContent('[object Object]')
    expectViewerOnlyLinks()
    expectNoForbiddenViewerActions()
  })

  it('renders error behavior conservatively without fake run records, object output, or Admin links', async () => {
    api.listRuns.mockRejectedValue(new Error('run index outage'))

    renderSelector()

    expect(await screen.findByText('Run list is unavailable.')).toBeInTheDocument()
    expect(screen.getByRole('option', { name: 'No runs available' })).toHaveAttribute('value', '')
    expect(screen.queryByText(/run index outage/i)).not.toBeInTheDocument()
    expect(document.body).not.toHaveTextContent('[object Object]')
    expectViewerOnlyLinks()
    expectNoForbiddenViewerActions()
  })

  it('drops malformed run list entries and prevents object-valued run ids from options or links', async () => {
    api.listRuns.mockResolvedValue({
      runs: [
        null,
        5,
        'run-string',
        {},
        { run_id: { value: 'object-run' }, season: { value: 2031 }, seed: { value: 7 } },
        { run_id: '', season: 2031, seed: 1 },
        { run_id: 'safe run', season: { value: 2032 }, seed: ['bad'] }
      ]
    })

    renderSelector()

    const safeOption = await screen.findByRole('option', { name: 'safe run — season —, seed —' })
    expect(safeOption).toHaveAttribute('value', 'safe run')
    expect(screen.queryByText('object-run')).not.toBeInTheDocument()
    expect(screen.queryByText('run-string')).not.toBeInTheDocument()
    expect(document.body).not.toHaveTextContent('[object Object]')
    for (const option of screen.getAllByRole('option')) {
      expect(option).not.toHaveAttribute('value', '[object Object]')
      expect(option.textContent ?? '').not.toContain('[object Object]')
    }
    expectViewerOnlyLinks()
    expectNoForbiddenViewerActions()
  })

  it('stores encoded-slash/hash/space run ids only in local Viewer active-run state and keeps browser link Viewer-only', async () => {
    api.listRuns.mockResolvedValue({
      runs: [{ run_id: 'run/alpha #1', season: 2035, seed: 12 }]
    })

    renderSelector()

    const option = await screen.findByRole('option', { name: 'run/alpha #1 — season 2035, seed 12' })
    expect(option).toHaveAttribute('value', 'run/alpha #1')
    const select = screen.getByLabelText('Available runs')
    fireEvent.change(select, { target: { value: 'run/alpha #1' } })
    fireEvent.click(screen.getByRole('button', { name: 'Set active run' }))

    expect(localStorage.getItem(VIEWER_ACTIVE_RUN_STORAGE_KEY)).toBe('run/alpha #1')
    expect(await screen.findByText('run/alpha #1')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Browse all runs' })).toHaveAttribute('href', '/viewer/runs')
    expect(document.body).not.toHaveTextContent('[object Object]')
    expectViewerOnlyLinks()
    expectNoForbiddenViewerActions()
    expect(api.listRuns).toHaveBeenCalledTimes(1)
  })
})
