import { fireEvent, render, screen, within } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it } from 'vitest'
import { AdminNavigation } from './AdminNavigation'
import { LanguageProvider } from '../i18n/LanguageContext'

function renderNav(pathname: string): void {
  const run = pathname.match(/^\/admin\/runs\/([^/]+)/)
  render(<MemoryRouter initialEntries={[pathname]}><LanguageProvider>
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
    expect(within(nav).getByRole('link', { name: 'World Tour Finals' })).toHaveAttribute('href', '/admin/runs/run-a/finals')
    expect(screen.getByRole('navigation', { name: 'Run management navigation' })).toHaveTextContent('Správa Runu')
    fireEvent.click(screen.getByRole('button', { name: 'Sbalit navigaci' }))
    expect(screen.getByRole('button', { name: 'Rozbalit navigaci' })).toBeInTheDocument()
  })
})
