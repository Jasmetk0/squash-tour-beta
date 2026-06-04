import { screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { Layout } from './Layout'
import { renderWithRoute } from '../test/testUtils'

const api = vi.hoisted(() => ({
  listRuns: vi.fn()
}))

vi.mock('../api/client', () => api)

describe('Layout mode navigation', () => {
  beforeEach(() => {
    localStorage.clear()
    vi.clearAllMocks()
    api.listRuns.mockResolvedValue({
      runs: [
        {
          run_id: 'run-a',
          season: 2030,
          seed: 9,
          progress: { next_event_index: 0, total_events: 4, completed_event_count: 0 },
          source_type: 'fresh_seed',
          parent_run_id: null,
          child_run_count: 0
        },
        {
          run_id: 'run-b',
          season: 2031,
          seed: 11,
          progress: { next_event_index: 1, total_events: 5, completed_event_count: 1 },
          source_type: 'fresh_seed',
          parent_run_id: null,
          child_run_count: 0
        }
      ]
    })
  })

  it('keeps Admin / Engine mode navigation and run-scoped admin links stable', async () => {
    renderWithRoute(<Layout />, '/admin/runs/run-a/finals')

    expect(await screen.findByText('Admin / Engine Mode')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Viewer / MSA' })).toHaveAttribute('href', '/viewer')
    expect(screen.getByRole('link', { name: 'Admin / Engine' })).toHaveAttribute('href', '/admin/runs/run-a/finals')
    expect(screen.getByRole('link', { name: 'World' })).toHaveAttribute('href', '/admin/world')
    expect(screen.getByRole('link', { name: 'Tour & Seasons' })).toHaveAttribute('href', '/admin/tour-seasons')
    expect(screen.getByRole('link', { name: 'Simulate' })).toHaveAttribute('href', '/admin/simulate')
    expect(screen.getByRole('link', { name: 'Runs' })).toHaveAttribute('href', '/admin/runs')
    expect(screen.getByRole('link', { name: 'Run Detail' })).toHaveAttribute('href', '/admin/runs/run-a')
    expect(screen.getByRole('link', { name: 'Events' })).toHaveAttribute('href', '/admin/runs/run-a/events')
    expect(screen.getByRole('link', { name: 'Season Calendar' })).toHaveAttribute('href', '/admin/runs/run-a/calendar')
    expect(screen.getAllByRole('link', { name: 'Diagnostics' })[1]).toHaveAttribute('href', '/admin/runs/run-a/diagnostics')
    expect(screen.getByRole('link', { name: 'World Generation' })).toHaveAttribute('href', '/admin/runs/run-a/world-generation')
    expect(screen.getByRole('link', { name: 'Ranking Snapshots' })).toHaveAttribute('href', '/admin/runs/run-a/snapshots/ranking')
    expect(screen.getByRole('link', { name: 'Race Snapshots' })).toHaveAttribute('href', '/admin/runs/run-a/snapshots/race')
    expect(screen.getByText('Current run context: run-a')).toBeInTheDocument()
  })

  it('shows one Viewer primary nav in Viewer mode', async () => {
    renderWithRoute(<Layout />, '/viewer/runs/run-a/rankings')

    expect(await screen.findByText('Viewer / MSA Website Mode')).toBeInTheDocument()
    expect(screen.getAllByTestId('viewer-primary-nav')).toHaveLength(1)
  })
})
