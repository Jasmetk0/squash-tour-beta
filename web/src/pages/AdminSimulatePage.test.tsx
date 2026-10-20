import { render, screen, within } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it } from 'vitest'
import { LanguageProvider } from '../i18n/LanguageContext'
import { AdminSimulatePage } from './AdminSimulatePage'

describe('global simulation launcher', () => {
  beforeEach(() => localStorage.clear())

  it.each([
    { language: 'cs', title: 'Simulace', runs: 'Otevřít Runy', tasks: 'Centrum simulací', slot: 'Další slot', day: 'Další zápasový den', season: 'Další sezona', caveat: /Dostupnost každého příkazu/ },
    { language: 'en', title: 'Simulate', runs: 'Open Runs', tasks: 'Simulation Task Center', slot: 'Next Slot', day: 'Next Match Day', season: 'Next Season', caveat: /Each command is checked/ }
  ])('shows truthful scopes and explicit destinations in $language', ({ language, title, runs, tasks, slot, day, season, caveat }) => {
    localStorage.setItem('squash-engine-language-v1', language)
    localStorage.setItem('beta_engine:last_run_id', 'remembered-run')
    localStorage.setItem('beta_engine:viewer_active_product_run_id', 'viewer-run')
    render(<MemoryRouter><LanguageProvider><AdminSimulatePage /></LanguageProvider></MemoryRouter>)

    expect(screen.getByRole('heading', { name: title })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: runs })).toHaveAttribute('href', '/admin/runs')
    expect(screen.getByRole('link', { name: tasks })).toHaveAttribute('href', '/admin/operations')
    const scopes = within(screen.getByRole('list'))
    expect(scopes.getAllByRole('listitem')).toHaveLength(8)
    for (const label of [slot, day, season, 'Full Simulation']) expect(scopes.getByText(label)).toBeInTheDocument()
    expect(screen.getByText(caveat)).toBeInTheDocument()
    expect(screen.queryByRole('button')).not.toBeInTheDocument()
    expect(screen.queryByRole('combobox')).not.toBeInTheDocument()
    expect(screen.queryByRole('table')).not.toBeInTheDocument()
    expect(screen.queryByText(/remembered-run|viewer-run/)).not.toBeInTheDocument()
    expect(localStorage.getItem('beta_engine:last_run_id')).toBe('remembered-run')
    expect(localStorage.getItem('beta_engine:viewer_active_product_run_id')).toBe('viewer-run')
  })
})
