import { screen, within } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { renderWithRoute } from '../test/testUtils'
import { LabNavigation } from './LabNavigation'

describe('direct Test Lab navigation', () => {
  it('links the other Lab tools without an action or simulated Run mutation', () => {
    renderWithRoute(<LabNavigation active="tournament" />, '/admin/labs/tournament')
    const nav = screen.getByRole('navigation', { name: 'Test Lab navigation' })

    expect(within(nav).getByRole('link', { name: 'Test Lab' })).toHaveAttribute('href', '/admin/labs')
    expect(within(nav).getByRole('link', { name: 'Match Lab' })).toHaveAttribute('href', '/admin/labs/match')
    expect(within(nav).getByRole('link', { name: 'Player Lab' })).toHaveAttribute('href', '/admin/labs/player')
    expect(within(nav).queryByRole('link', { name: 'Tournament Lab' })).not.toBeInTheDocument()
    expect(within(nav).getByText('Tournament Lab')).toHaveAttribute('aria-current', 'page')
  })

  it('marks Player Lab as active without linking to its current page', () => {
    renderWithRoute(<LabNavigation active="player" />, '/admin/labs/player')
    const nav = screen.getByRole('navigation', { name: 'Test Lab navigation' })
    expect(within(nav).getByText('Player Lab')).toHaveAttribute('aria-current', 'page')
    expect(within(nav).getByRole('link', { name: 'Tournament Lab' })).toHaveAttribute('href', '/admin/labs/tournament')
  })
})
