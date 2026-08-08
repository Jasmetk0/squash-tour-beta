import { render, screen, within } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it } from 'vitest'

import { AdminNavigation } from './AdminNavigation'

function renderAdminNavigation(runId?: string): void {
  render(
    <MemoryRouter initialEntries={[runId ? `/admin/runs/${runId}/finals` : '/admin']}>
      <AdminNavigation scope={runId ? { kind: 'run', runId } : { kind: 'global' }} />
    </MemoryRouter>
  )
}

describe('AdminNavigation', () => {
  it('renders primary Admin navigation labels and hrefs without a run context', () => {
    renderAdminNavigation()

    const primaryNav = screen.getByRole('navigation', { name: 'Global Admin navigation' })

    expect(within(primaryNav).getByRole('link', { name: 'Dashboard' })).toHaveAttribute('href', '/admin')
    expect(within(primaryNav).getByRole('link', { name: 'World' })).toHaveAttribute('href', '/admin/world')
    expect(within(primaryNav).getByRole('link', { name: 'Players' })).toHaveAttribute('href', '/admin/players')
    expect(within(primaryNav).getByRole('link', { name: 'Tour & Seasons' })).toHaveAttribute('href', '/admin/tour-seasons')
    expect(within(primaryNav).getByRole('link', { name: 'Runs' })).toHaveAttribute('href', '/admin/runs')
    expect(within(primaryNav).getByRole('link', { name: 'Simulate' })).toHaveAttribute('href', '/admin/simulate')
    expect(within(primaryNav).getByRole('link', { name: 'Diagnostics' })).toHaveAttribute('href', '/admin/diagnostics')
    expect(within(primaryNav).getByRole('link', { name: 'Settings' })).toHaveAttribute('href', '/admin/settings')
    expect(screen.queryByRole('navigation', { name: 'Run Admin navigation' })).not.toBeInTheDocument()
    expect(screen.queryByText(/Current run context:/)).not.toBeInTheDocument()
  })

  it('renders run-scoped Admin navigation labels, hrefs, and current run context', () => {
    renderAdminNavigation('run-a')

    const runNav = screen.getByRole('navigation', { name: 'Run Admin navigation' })

    expect(screen.queryByRole('navigation', { name: 'Global Admin navigation' })).not.toBeInTheDocument()
    expect(within(runNav).getByRole('link', { name: 'Back to Global' })).toHaveAttribute('href', '/admin')
    expect(within(runNav).getByRole('link', { name: 'Home' })).toHaveAttribute('href', '/admin/runs/run-a')
    expect(within(runNav).getByRole('link', { name: 'Events' })).toHaveAttribute('href', '/admin/runs/run-a/events')
    expect(within(runNav).getByRole('link', { name: 'Season Calendar' })).toHaveAttribute('href', '/admin/runs/run-a/calendar')
    expect(within(runNav).getByRole('link', { name: 'Activity' })).toHaveAttribute('href', '/admin/runs/run-a/activity')
    expect(within(runNav).getByRole('link', { name: 'Players' })).toHaveAttribute('href', '/admin/runs/run-a/players')
    expect(within(runNav).getByRole('link', { name: 'Nations' })).toHaveAttribute('href', '/admin/runs/run-a/nations')
    expect(within(runNav).getByRole('link', { name: 'Diagnostics' })).toHaveAttribute('href', '/admin/runs/run-a/diagnostics')
    expect(within(runNav).getByRole('link', { name: 'World Generation' })).toHaveAttribute('href', '/admin/runs/run-a/world-generation')
    expect(within(runNav).getByRole('link', { name: 'World Tour Finals' })).toHaveAttribute('href', '/admin/runs/run-a/finals')
    expect(within(runNav).getByRole('link', { name: 'Season Rollover' })).toHaveAttribute('href', '/admin/runs/run-a/rollover')
    expect(within(runNav).getByRole('link', { name: 'Bootstrap / Lineage' })).toHaveAttribute('href', '/admin/runs/run-a/bootstrap-lineage')
    expect(within(runNav).getByRole('link', { name: 'Season Chain' })).toHaveAttribute('href', '/admin/runs/run-a/season-chain')
    expect(within(runNav).getByRole('link', { name: 'Ranking Snapshots' })).toHaveAttribute('href', '/admin/runs/run-a/snapshots/ranking')
    expect(within(runNav).getByRole('link', { name: 'Race Snapshots' })).toHaveAttribute('href', '/admin/runs/run-a/snapshots/race')
    expect(screen.getByText('Current run context: run-a')).toBeInTheDocument()
  })
})
