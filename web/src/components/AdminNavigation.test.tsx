import { fireEvent, render, screen, within } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it } from 'vitest'
import { AdminNavigation } from './AdminNavigation'
import { LanguageProvider } from '../i18n/LanguageContext'

function renderNav(pathname: string): ReturnType<typeof render> {
  const run = pathname.match(/^\/admin\/runs\/([^/]+)/)
  return render(<MemoryRouter initialEntries={[pathname]}><LanguageProvider>
    <AdminNavigation scope={run ? { kind: 'run', runId: run[1] } : { kind: 'global' }} />
  </LanguageProvider></MemoryRouter>)
}

describe('pre-alpha navigation sidebar', () => {
  beforeEach(() => localStorage.clear())
  it('keeps only global Home, Runs, Packages and Test Lab above bottom settings', () => {
    renderNav('/admin')
    const nav = screen.getByRole('navigation', { name: 'Global Admin navigation' })
    expect(within(nav).getAllByRole('link').map(link => link.getAttribute('href'))).toEqual([
      '/admin', '/admin/runs', '/admin/packages', '/admin/labs'
    ])
    expect(screen.getByRole('navigation', { name: 'Application settings navigation' })).toHaveTextContent('Nastavení aplikace')
  })
  it('retains run context and nested active categories, allowing submenu expansion', () => {
    renderNav('/admin/runs/run-a/finals')
    const nav = screen.getByRole('navigation', { name: 'Run Admin navigation' })
    expect(within(nav).getByRole('link', { name: 'Tour' })).toHaveClass('active')
    expect(within(nav).getByRole('link', { name: 'Finálový turnaj' })).toHaveAttribute('href', '/admin/runs/run-a/finals')
    expect(screen.getByRole('navigation', { name: 'Run management navigation' })).toHaveTextContent('Správa Runu')
    fireEvent.click(screen.getByRole('button', { name: 'Sbalit navigaci' }))
    expect(screen.getByRole('button', { name: 'Rozbalit navigaci' })).toBeInTheDocument()
  })
  it('persists collapse and pin choices across remounts', () => {
    const { unmount } = renderNav('/admin')
    fireEvent.click(screen.getByRole('button', { name: 'Odepnout navigaci' }))
    fireEvent.click(screen.getByRole('button', { name: 'Sbalit navigaci' }))
    expect(localStorage.getItem('squash-engine-sidebar-collapsed-v1')).toBe('true')
    expect(localStorage.getItem('squash-engine-sidebar-pinned-v1')).toBe('false')
    unmount()
    renderNav('/admin')
    expect(screen.getByRole('button', { name: 'Rozbalit navigaci' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Připnout navigaci' })).toBeInTheDocument()
  })

  it('activates Players for canonical player profiles and match replay, with English submenu labels', () => {
    localStorage.setItem('squash-engine-language-v1', 'en')
    renderNav('/admin/runs/run-a/people/player-a/matches/event-a/match-a')
    const nav = screen.getByRole('navigation', { name: 'Run Admin navigation' })
    expect(within(nav).getByRole('link', { name: 'Players' })).toHaveClass('active')
    expect(within(nav).getByRole('link', { name: 'Player list' })).toHaveAttribute('href', '/admin/runs/run-a/players')
  })
})
