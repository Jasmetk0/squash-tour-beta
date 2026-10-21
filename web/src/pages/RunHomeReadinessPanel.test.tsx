import { fireEvent, render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it, vi } from 'vitest'

import { validateRunHomeReadiness } from '../api/runHomeReadiness'
import type { RunHomeReadiness } from '../api/runHomeReadiness'
import { RunHomeReadinessPanel } from './RunHomeReadinessPanel'

const data: RunHomeReadiness = {
  schema_version: 'run_home_readiness.v1',
  run_id: 'run-a', branch_id: 'branch-a', saved_revision_id: 'revision-a',
  saved_revision_content_hash: 'a'.repeat(64), draft_version: 1,
  source: 'validated_selected_branch_saved_head',
  run_status: 'working', phase: 'preparation',
  current_calendar: { schema_version: 'run_calendar.v1', weeks_per_year: 52,
    season_start_year_week: 35, start_year: 2030, season_count: 3 },
  items: [
    { code: 'world', status: 'saved', evidence_count: 250 },
    { code: 'calendar_package', status: 'missing', evidence_count: 0 },
    { code: 'population', status: 'saved', evidence_count: 1000 },
    { code: 'health', status: 'saved', evidence_count: 1 },
    { code: 'official_ranking', status: 'candidate_only', evidence_count: 0 },
    { code: 'working_draft', status: 'unsaved', evidence_count: 1 }
  ],
  saved_transition_count: 0,
  saved_published_ranking_count: 0,
  active_full_simulation_task_count: 0,
  historical_full_simulation_task_count: 0,
  sporting_calendar_supported_by_legacy_writers: false,
  requires_operation_preflight: true, simulation_started: false,
}

function mount(locale: 'cs' | 'en' = 'en', values = data) {
  const refresh = vi.fn()
  render(<MemoryRouter>
    <RunHomeReadinessPanel data={values} runId="run-a" language={locale}
      refreshing={false} refresh={refresh} />
  </MemoryRouter>)
  return refresh
}

describe('saved Run readiness panel', () => {
  it('keeps the next action visible and collapses the detailed readiness checklist', () => {
    const refresh = mount()
    expect(screen.getByText('This Branch readiness')).toBeInTheDocument()
    expect(screen.getByText(/This calendar is not supported by the legacy FAX simulation path/)).toHaveClass('status')
    expect(screen.getByText('Unsaved changes are not counted in this overview.')).toBeInTheDocument()
    const checklist = screen.getByText('Show saved-foundation checks (6) · 3 items needing attention')
    expect(checklist).toBeVisible()
    expect(screen.queryByRole('link', { name: 'Inspect and Save changes →' })).not.toBeInTheDocument()
    fireEvent.click(checklist)
    expect(screen.getAllByRole('link', { name: 'Add a Calendar Package →' })[0])
      .toHaveAttribute('href', '/admin/runs/run-a/manage')
    expect(screen.getByRole('link', { name: 'Inspect and Save changes →' }))
      .toHaveAttribute('href', '/admin/runs/run-a/branches')
    expect(screen.getByText('Saved transitions:', { exact: false })).not.toBeVisible()
    fireEvent.click(screen.getByText('Technical provenance and limits'))
    expect(screen.getByText('Saved transitions:', { exact: false })).toBeVisible()
    expect(screen.getByText('Selected Branch:', { exact: false })).toHaveTextContent('branch-a')
    expect(screen.getByText('Run calendar:', { exact: false })).toHaveTextContent('52 weeks per season · 3 seasons')
    fireEvent.click(screen.getByRole('button', { name: 'Refresh inspection' }))
    expect(refresh).toHaveBeenCalledTimes(1)
  })

  it('renders Czech with required preflight even for reference FAX', () => {
    mount('cs', {
      ...data,
      sporting_calendar_supported_by_legacy_writers: true,
      current_calendar: { ...data.current_calendar, weeks_per_year: 61,
        season_start_year_week: 37, start_year: 2000, season_count: 50 }
    })
    expect(screen.getByText('Připravenost této Branch')).toBeInTheDocument()
    expect(screen.getByText('Zobrazit kontrolu uložených podkladů (6) · 3 položky k prověření')).toBeVisible()
    expect(screen.getByText(/Před každou operací je stále nutná vlastní kontrola/)).toBeInTheDocument()
    fireEvent.click(screen.getByText('Zobrazit kontrolu uložených podkladů (6) · 3 položky k prověření'))
    expect(screen.getAllByRole('link', { name: 'Doplnit Calendar Package →' })[0])
      .toHaveAttribute('href', '/admin/runs/run-a/manage')
  })

  it('does not suggest missing prerequisites when all saved foundations are satisfied', () => {
    mount('en', {
      ...data,
      items: data.items.map(item => ({ ...item, status: 'saved' as const }))
    })
    expect(screen.getByText('Show saved-foundation checks (6)')).toBeVisible()
    expect(screen.getByText('The selected foundations are saved. Sporting operations still require a separate preflight.')).toBeVisible()
  })

  it('rejects alien and reordered readiness evidence', () => {
    expect(validateRunHomeReadiness(data, 'run-a', 'branch-a')).toEqual(data)
    expect(() => validateRunHomeReadiness(data, 'run-a', 'branch-b')).toThrow()
    expect(() => validateRunHomeReadiness({ ...data, items: [...data.items].reverse() }, 'run-a', 'branch-a')).toThrow()
    expect(() => validateRunHomeReadiness({ ...data, simulation_started: true }, 'run-a', 'branch-a')).toThrow()
  })
})
