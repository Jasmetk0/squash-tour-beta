import { fireEvent, render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { LanguageProvider, useLanguage } from '../i18n/LanguageContext'
import { AdminDiagnosticsPage } from './AdminDiagnosticsPage'

const storage = vi.hoisted(() => ({ lastRunId: null as string | null }))
vi.mock('../viewer/activeRun', () => ({
  readLastRunId: () => storage.lastRunId,
}))

function LanguageSwitch(): JSX.Element {
  const { setLanguage } = useLanguage()
  return (
    <>
      <button type="button" onClick={() => setLanguage('cs')}>CS</button>
      <button type="button" onClick={() => setLanguage('en')}>EN</button>
    </>
  )
}

function mount() {
  render(
    <MemoryRouter>
      <LanguageProvider>
        <LanguageSwitch />
        <AdminDiagnosticsPage />
      </LanguageProvider>
    </MemoryRouter>,
  )
}

describe('AdminDiagnosticsPage launcher', () => {
  beforeEach(() => {
    storage.lastRunId = null
    localStorage.setItem('squash-engine-language-v1', 'cs')
  })

  it('renders Czech diagnostics copy and keeps available vs planned separation', () => {
    mount()
    expect(screen.getByText(/ne souhrnné diagnostické prověření/)).toBeInTheDocument()
    expect(screen.getByText('Zobrazeno 6 z 6 diagnostických oblastí')).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Vyváženost světa' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Validace kalendáře' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Zdraví runu' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Invalidovaná data' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Narativní zámky' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Audit / upozornění' })).toBeInTheDocument()
    expect(screen.getByText(/místo předpokladu W01–W61/)).toBeInTheDocument()

    const filter = screen.getByRole('combobox', { name: 'Zobrazit sekce diagnostiky' })
    fireEvent.change(filter, { target: { value: 'available' } })
    expect(screen.getByText('Zobrazeno 3 z 6 diagnostických oblastí')).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Vyváženost světa' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Zdraví runu' })).toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: 'Narativní zámky' })).not.toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: 'Invalidovaná data' })).not.toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Talent Preview' })).toHaveAttribute('href', '/admin/world/talent-preview')

    fireEvent.change(filter, { target: { value: 'planned' } })
    expect(screen.getByText('Zobrazeno 3 z 6 diagnostických oblastí')).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Invalidovaná data' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Narativní zámky' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Audit / upozornění' })).toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: 'Vyváženost světa' })).not.toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: 'Zdraví runu' })).not.toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Otevřít runy' })).toHaveAttribute('href', '/admin/runs')

    fireEvent.change(filter, { target: { value: 'all' } })
    expect(screen.getByText('Zobrazeno 6 z 6 diagnostických oblastí')).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Validace kalendáře' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Audit / upozornění' })).toBeInTheDocument()
  })

  it('switches to English without resetting the selected diagnostics filter', () => {
    mount()
    const filter = screen.getByRole('combobox', { name: 'Zobrazit sekce diagnostiky' })
    fireEvent.change(filter, { target: { value: 'planned' } })

    fireEvent.click(screen.getByRole('button', { name: 'EN' }))
    expect(screen.getByRole('combobox', { name: 'Show diagnostics sections' })).toHaveValue('planned')
    expect(screen.getByText('Showing 3 of 6 diagnostic areas')).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Invalidated Data' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Narrative Locks' })).toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: 'World Balance' })).not.toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Current vs planned' })).toBeInTheDocument()
  })

  it('does not invent a last Run link when there is no remembered Run', () => {
    mount()
    expect(screen.getByRole('link', { name: 'Otevřít runy' })).toHaveAttribute('href', '/admin/runs')
    expect(screen.queryByRole('link', { name: /run diagnostics|diagnostiku posledního runu|diagnostika posledního runu/i })).not.toBeInTheDocument()
  })

  it('escapes the trimmed last Run ID as one route segment in both diagnostic shortcuts and keeps raw ID', () => {
    storage.lastRunId = '  saved A/B?x  '
    mount()
    const path = '/admin/runs/saved%20A%2FB%3Fx/diagnostics'
    expect(screen.getByRole('link', { name: 'Otevřít diagnostiku posledního runu (saved A/B?x)' })).toHaveAttribute('href', path)
    expect(screen.getByRole('link', { name: 'Diagnostika posledního runu' })).toHaveAttribute('href', path)

    fireEvent.click(screen.getByRole('button', { name: 'EN' }))
    expect(screen.getByRole('link', { name: 'Open last run diagnostics (saved A/B?x)' })).toHaveAttribute('href', path)
    expect(screen.getByRole('link', { name: 'Last run diagnostics' })).toHaveAttribute('href', path)
  })

  it('treats a whitespace-only remembered Run ID as absent', () => {
    storage.lastRunId = '   '
    mount()
    expect(screen.queryByRole('link', { name: /run diagnostics|diagnostiku posledního runu|diagnostika posledního runu/i })).not.toBeInTheDocument()
  })
})
