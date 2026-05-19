import { screen } from '@testing-library/react'
import { beforeEach, describe, expect, it } from 'vitest'

import { Layout } from './Layout'
import { renderWithRoute } from '../test/testUtils'

describe('Layout mode navigation', () => {
  beforeEach(() => {
    localStorage.clear()
  })
  it('shows Admin / Engine mode navigation and run-scoped admin links', async () => {
    renderWithRoute(<Layout />, '/admin/runs/run-a/finals')

    expect(await screen.findByText('Admin / Engine Mode')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Viewer / MSA' })).toHaveAttribute('href', '/viewer')
    expect(screen.getByRole('link', { name: 'Admin / Engine' })).toHaveAttribute('href', '/admin')
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

  it('shows Viewer / MSA mode navigation and read-oriented run links', async () => {
    renderWithRoute(<Layout />, '/viewer/runs/run-a/rankings')

    expect(await screen.findByText('Viewer / MSA Website Mode')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Home' })).toHaveAttribute('href', '/viewer')
    expect(screen.getAllByRole('link', { name: 'Rankings' })[0]).toHaveAttribute('href', '/viewer/rankings')
    expect(screen.getAllByRole('link', { name: 'Tournaments' })[0]).toHaveAttribute('href', '/viewer/tournaments')
    expect(screen.getByRole('link', { name: 'Records' })).toHaveAttribute('href', '/viewer/records')
    expect(screen.getByRole('navigation', { name: 'Run navigation' })).toBeInTheDocument()
    expect(screen.getAllByRole('link', { name: 'Rankings' })[1]).toHaveAttribute('href', '/viewer/runs/run-a/rankings')
    expect(screen.getByRole('link', { name: 'Race' })).toHaveAttribute('href', '/viewer/runs/run-a/race')
    expect(screen.getAllByRole('link', { name: 'Tournaments' })[1]).toHaveAttribute('href', '/viewer/runs/run-a/tournaments')
    expect(screen.getAllByRole('link', { name: 'History' })[0]).toHaveAttribute('href', '/viewer/history')
    expect(screen.getAllByRole('link', { name: 'History' })[1]).toHaveAttribute('href', '/viewer/runs/run-a/history')
  })

  it('shows the active Viewer run indicator and quick links on Viewer top-level routes', async () => {
    localStorage.setItem('beta_engine:viewer_active_run_id', 'viewer-run-a')

    renderWithRoute(<Layout />, '/viewer')

    expect(await screen.findByText('Viewer / MSA Website Mode')).toBeInTheDocument()
    expect(screen.getByLabelText('Viewer active run')).toHaveTextContent('Viewing run: viewer-run-a')
    expect(screen.getByRole('navigation', { name: 'Viewer active run quick links' })).toBeInTheDocument()
    expect(screen.getAllByRole('link', { name: 'Rankings' }).some((link) => link.getAttribute('href') === '/viewer/runs/viewer-run-a/rankings')).toBe(true)
    expect(screen.getAllByRole('link', { name: 'Tournaments' }).some((link) => link.getAttribute('href') === '/viewer/runs/viewer-run-a/tournaments')).toBe(true)
    expect(screen.getAllByRole('link', { name: 'Players' }).some((link) => link.getAttribute('href') === '/viewer/runs/viewer-run-a/players')).toBe(true)
    expect(screen.getAllByRole('link', { name: 'Countries' }).some((link) => link.getAttribute('href') === '/viewer/runs/viewer-run-a/countries')).toBe(true)
    expect(screen.getAllByRole('link', { name: 'History' }).some((link) => link.getAttribute('href') === '/viewer/runs/viewer-run-a/history')).toBe(true)
  })

  it('shows no selected Viewer run message on Viewer top-level routes', async () => {
    renderWithRoute(<Layout />, '/viewer')

    expect(await screen.findByText('Viewer / MSA Website Mode')).toBeInTheDocument()
    expect(screen.getByText(/No Viewer run selected/i)).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Select a run' })).toHaveAttribute('href', '/viewer')
  })

})
