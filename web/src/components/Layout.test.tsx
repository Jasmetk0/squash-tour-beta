import { screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { Layout } from './Layout'
import { renderWithRoute } from '../test/testUtils'

describe('Layout run-scoped navigation', () => {
  it('includes all run sub-pages for a selected run', async () => {
    renderWithRoute(<Layout />, '/runs/run-a/finals')

    expect(await screen.findByRole('link', { name: 'Runs' })).toHaveAttribute('href', '/runs')
    expect(await screen.findByRole('link', { name: 'Countries Editor' })).toHaveAttribute('href', '/world/countries')
    expect(await screen.findByRole('link', { name: 'Talent Preview' })).toHaveAttribute('href', '/world/talent-preview')
    expect(await screen.findByRole('link', { name: 'Run Detail' })).toHaveAttribute('href', '/runs/run-a')
    expect(screen.getByRole('link', { name: 'Events' })).toHaveAttribute('href', '/runs/run-a/events')
    expect(screen.getByRole('link', { name: 'Season Calendar' })).toHaveAttribute('href', '/runs/run-a/calendar')
    expect(screen.getByRole('link', { name: 'Activity' })).toHaveAttribute('href', '/runs/run-a/activity')
    expect(screen.getByRole('link', { name: 'Diagnostics' })).toHaveAttribute('href', '/runs/run-a/diagnostics')
    expect(screen.getByRole('link', { name: 'World Tour Finals' })).toHaveAttribute('href', '/runs/run-a/finals')
    expect(screen.getByRole('link', { name: 'Season Rollover' })).toHaveAttribute('href', '/runs/run-a/rollover')
    expect(screen.getByRole('link', { name: 'Bootstrap / Lineage' })).toHaveAttribute('href', '/runs/run-a/bootstrap-lineage')
    expect(screen.getByRole('link', { name: 'Season Chain' })).toHaveAttribute('href', '/runs/run-a/season-chain')
    expect(screen.getByRole('link', { name: 'Ranking Snapshots' })).toHaveAttribute(
      'href',
      '/runs/run-a/snapshots/ranking'
    )
    expect(screen.getByRole('link', { name: 'Race Snapshots' })).toHaveAttribute('href', '/runs/run-a/snapshots/race')
    expect(screen.getByText('Current run context: run-a')).toBeInTheDocument()
  })
})
