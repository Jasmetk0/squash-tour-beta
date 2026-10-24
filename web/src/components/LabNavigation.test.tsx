import { screen, within } from '@testing-library/react'
import { beforeEach, describe, expect, it } from 'vitest'
import { LanguageProvider } from '../i18n/LanguageContext'

import { renderWithRoute } from '../test/testUtils'
import { LabNavigation } from './LabNavigation'

describe('direct Test Lab navigation', () => {
  beforeEach(() => localStorage.setItem('squash-engine-language-v1', 'en'))
  it('links the other Lab tools without an action or simulated Run mutation', () => {
    renderWithRoute(<LanguageProvider><LabNavigation active="tournament" /></LanguageProvider>, '/admin/labs/tournament')
    const nav = screen.getByRole('navigation', { name: 'Test Lab navigation' })

    expect(within(nav).getByRole('link', { name: 'Test Lab' })).toHaveAttribute('href', '/admin/labs')
    expect(within(nav).getByRole('link', { name: 'Match Lab' })).toHaveAttribute('href', '/admin/labs/match')
    expect(within(nav).getByRole('link', { name: 'Player Lab' })).toHaveAttribute('href', '/admin/labs/player')
    expect(within(nav).queryByRole('link', { name: 'Tournament Lab' })).not.toBeInTheDocument()
    expect(within(nav).getByText('Tournament Lab').closest('[aria-current]')).toHaveAttribute('aria-current', 'page')
  })

  it('marks Player Lab as active without linking to its current page', () => {
    renderWithRoute(<LanguageProvider><LabNavigation active="player" /></LanguageProvider>, '/admin/labs/player')
    const nav = screen.getByRole('navigation', { name: 'Test Lab navigation' })
    expect(within(nav).getByText('Player Lab').closest('[aria-current]')).toHaveAttribute('aria-current', 'page')
    expect(within(nav).getByRole('link', { name: 'Tournament Lab' })).toHaveAttribute('href', '/admin/labs/tournament')
  })
  it('renders Czech navigation and identifies the active Lab without executing anything', () => {
    localStorage.setItem('squash-engine-language-v1', 'cs')
    renderWithRoute(<LanguageProvider><LabNavigation active="match" /></LanguageProvider>, '/admin/labs/match')
    const nav = screen.getByRole('navigation', { name: 'Navigace Test Labů' })
    expect(within(nav).getByText('Laboratoř zápasů').closest('[aria-current]')).toHaveAttribute('aria-current', 'page')
    expect(within(nav).getByRole('link', { name: 'Laboratoř turnajů' })).toHaveAttribute('href', '/admin/labs/tournament')
    expect(within(nav).getByRole('link', { name: 'Rozcestník Labů' })).toHaveAttribute('href', '/admin/labs')
  })
})
