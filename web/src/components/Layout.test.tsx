import { fireEvent, screen, within } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { Layout } from './Layout'
import { forbiddenViewerActionLabels, expectNoForbiddenViewerActions } from '../test/viewerTestUtils'
import { renderWithRoute } from '../test/testUtils'

const api = vi.hoisted(() => ({
  listRuns: vi.fn()
}))

vi.mock('../api/client', () => api)

function viewerNav(): HTMLElement {
  return screen.getByTestId('viewer-primary-nav')
}

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

  it('renders Viewer topbar links as Viewer-only links without Admin shell controls in the Viewer nav', async () => {
    renderWithRoute(<Layout />, '/viewer/rankings')

    expect(await screen.findByText('Viewer / MSA Website Mode')).toBeInTheDocument()
    const nav = viewerNav()
    const links = within(nav).getAllByRole('link')
    expect(links.length).toBeGreaterThan(0)
    for (const link of links) {
      const href = link.getAttribute('href') ?? ''
      expect(href).toMatch(/^\/viewer(?:\/|$)/)
      expect(href).not.toMatch(/^\/admin(?:\/|$)/)
    }
    expect(within(nav).queryByText(/Admin|Commissioner|Engine Mode|Engine/i)).not.toBeInTheDocument()
  })

  it('registers Viewer dropdown links as Viewer-only destinations without fake result labels', async () => {
    renderWithRoute(<Layout />, '/viewer/tour')

    expect(await screen.findByText('Viewer / MSA Website Mode')).toBeInTheDocument()
    const nav = viewerNav()
    const dropdownMenus = within(nav).getAllByLabelText(/ menu$/)
    expect(dropdownMenus.length).toBeGreaterThan(0)
    for (const menu of dropdownMenus) {
      for (const link of within(menu).getAllByRole('link')) {
        const href = link.getAttribute('href') ?? ''
        expect(href).toMatch(/^\/viewer(?:\/|$)/)
        expect(href).not.toMatch(/^\/admin(?:\/|$)/)
      }
    }
    expect(within(nav).queryByText(/Winner|Top 100|standings table/i)).not.toBeInTheDocument()
    expect(document.body).not.toHaveTextContent('[object Object]')
  })

  it('keeps Viewer nav free of backend mutation controls while allowing local selectors', async () => {
    renderWithRoute(<Layout />, '/viewer')

    expect(await screen.findByText('Viewer / MSA Website Mode')).toBeInTheDocument()
    const nav = viewerNav()
    expect(within(nav).getByRole('search', { name: 'Viewer search' })).toBeInTheDocument()
    expect(within(nav).queryByLabelText('Viewer active run')).not.toBeInTheDocument()
    expect(within(nav).queryByRole('button', { name: 'Season 2004/05 · W10' })).not.toBeInTheDocument()
    expect(await screen.findByRole('option', { name: /run-b/i })).toHaveAttribute('value', 'run-b')
    fireEvent.change(screen.getByLabelText('Viewer active run'), { target: { value: 'run-b' } })
    expect(localStorage.getItem('beta_engine:viewer_active_run_id')).toBe('run-b')
    expect(screen.getByLabelText('Viewer header context controls')).toBeInTheDocument()
    expectNoForbiddenViewerActions(within(nav))
    for (const label of forbiddenViewerActionLabels) {
      expect(within(nav).queryByRole('button', { name: label })).not.toBeInTheDocument()
      expect(within(nav).queryByRole('link', { name: label })).not.toBeInTheDocument()
    }
  })
})
