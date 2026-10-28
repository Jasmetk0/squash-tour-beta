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
    expect(screen.getByRole('link', { name: 'Open global Test Lab' }))
      .toHaveAttribute('href', '/admin/labs')
    expect(screen.getByText(/This calendar is not supported by the legacy FAX simulation path/)).toHaveClass('status')
    expect(screen.getByText('Unsaved changes are not counted in this overview.')).toBeInTheDocument()
    // Only Saved evidence is inspected: direct the user to review pending work first.
    expect(screen.getAllByRole('link', { name: 'Inspect and Save changes →' })[0])
      .toHaveAttribute('href', '/admin/runs/run-a/branches')
    const checklist = screen.getByText('Show saved-foundation checks (6) · 3 items needing attention')
    expect(checklist).toBeVisible()
    expect(checklist.closest('details')).not.toHaveAttribute('open')
    fireEvent.click(checklist)
    expect(checklist.closest('details')).toHaveAttribute('open')
    expect(screen.getAllByRole('link', { name: 'Add a Calendar Package →' })[0])
      .toHaveAttribute('href', '/admin/runs/run-a/manage')
    expect(screen.getAllByRole('link', { name: 'Inspect and Save changes →' })[0])
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
    expect(screen.getByRole('link', { name: 'Otevřít globální Test Lab' }))
      .toHaveAttribute('href', '/admin/labs')
    expect(screen.getByText('Zobrazit kontrolu uložených podkladů (6) · 3 položky k prověření')).toBeVisible()
    expect(screen.getByText(/Před každou operací je stále nutná vlastní kontrola/)).toBeInTheDocument()
    fireEvent.click(screen.getByText('Zobrazit kontrolu uložených podkladů (6) · 3 položky k prověření'))
    expect(screen.getAllByRole('link', { name: 'Doplnit Calendar Package →' })[0])
      .toHaveAttribute('href', '/admin/runs/run-a/manage')
  })

  it('does not suggest missing prerequisites when all saved foundations are satisfied', () => {
    mount('en', {
      ...data,
      items: data.items.map(item => ({ ...item, status: 'saved' as const,
        evidence_count: item.code === 'working_draft' ? 0 : Math.max(1, item.evidence_count) }))
    })
    expect(screen.getByText('Show saved-foundation checks (6)')).toBeVisible()
    fireEvent.click(screen.getByText('Show saved-foundation checks (6)'))
    expect(screen.getByText('Clean Working Draft · Pending changes: 0')).toBeVisible()
    expect(screen.getByText('This saved-foundation inspection has no further action. It does not certify all operations; each requires its own preflight.')).toBeVisible()
  })

  it('rejects alien and reordered readiness evidence', () => {
    expect(validateRunHomeReadiness(data, 'run-a', 'branch-a')).toEqual(data)
    expect(() => validateRunHomeReadiness(data, 'run-a', 'branch-b')).toThrow()
    expect(() => validateRunHomeReadiness({ ...data, items: [...data.items].reverse() }, 'run-a', 'branch-a')).toThrow()
    expect(() => validateRunHomeReadiness({ ...data, simulation_started: true }, 'run-a', 'branch-a')).toThrow()
  })

  it('does not mistake optional foundations for completed saved content', () => {
    mount('en', {
      ...data,
      items: data.items.map(item => ({ ...item, status: 'optional' as const }))
    })
    expect(screen.getByText('Show saved-foundation checks (6)')).toBeVisible()
    expect(screen.getByText(/does not certify all operations/)).toBeVisible()
    expect(screen.queryByRole('link', { name: /Add a World Package|Inspect and Save changes/ })).toBeNull()
  })

  it('prioritizes a genuinely missing Saved foundation after a clean draft, and skips optional entries', () => {
    mount('en', {
      ...data,
      items: data.items.map(item => ({
        ...item,
        status: item.code === 'world' ? 'optional' as const
          : item.code === 'calendar_package' ? 'missing' as const : 'saved' as const
      }))
    })
    expect(screen.getByText('Show saved-foundation checks (6) · 1 item needing attention')).toBeVisible()
    expect(screen.getAllByRole('link', { name: 'Add a Calendar Package →' })[0])
      .toHaveAttribute('href', '/admin/runs/run-a/manage')
    expect(screen.queryByText('Unsaved changes are not counted in this overview.')).toBeNull()
  })

  it('keeps the optional global Test Lab shortcut limited to preparation', () => {
    mount('en', { ...data, phase: 'sporting_history' })
    expect(screen.queryByRole('link', { name: 'Open global Test Lab' })).toBeNull()
  })

  it('uses the Czech plural for five missing saved foundations', () => {
    mount('cs', {
      ...data,
      items: data.items.map(item => ({
        ...item,
        status: item.code === 'working_draft' ? 'saved' as const : 'missing' as const
      }))
    })
    expect(screen.getByText('Zobrazit kontrolu uložených podkladů (6) · 5 položek k prověření'))
      .toBeVisible()
  })

  it('explains distinct Saved entity counts, initial cohort and published ranking in English', () => {
    mount('en')
    fireEvent.click(screen.getByText('Show saved-foundation checks (6) · 3 items needing attention'))
    expect(screen.getByText('Saved · World entities: 250')).toBeVisible()
    expect(screen.getByText('Missing · Calendar entities: 0')).toBeVisible()
    expect(screen.getByText('Saved · Initial-population players: 1000')).toBeVisible()
    expect(screen.getByText('Saved · Health records: 1')).toBeVisible()
    expect(screen.getByText('Candidate only · Ranking publications: 0')).toBeVisible()
    expect(screen.getByText('Unsaved · Pending changes: 1')).toBeVisible()
    expect(screen.getByText(/Counts Calendar Package entities.*not the Run week-count configuration/)).toBeVisible()
    expect(screen.getByText(/Counts only saved initial-population players, not every player/)).toBeVisible()
    expect(screen.getByText(/Counts actually saved ranking publications; candidate rankings are not publications/)).toBeVisible()
    expect(screen.getByText(/Candidate data is not published authority/)).toBeVisible()
    expect(screen.getByText(/Counts this Branch Working Draft changes; other unfinished editors/)).toBeVisible()
  })

  it('explains the meaning of missing, optional and saved evidence without claiming global blockers', () => {
    mount('en', {
      ...data,
      items: data.items.map(item => ({
        ...item,
        status: item.code === 'health' ? 'optional' as const
          : item.code === 'working_draft' ? 'saved' as const : 'missing' as const,
        evidence_count: 0
      }))
    })
    fireEvent.click(screen.getByText('Show saved-foundation checks (6) · 4 items needing attention'))
    expect(screen.getByText('Not required here · Health records: 0')).toBeVisible()
    expect(screen.getByText(/This check does not require this foundation here; another operation may/)).toBeVisible()
    expect(screen.getAllByText(/No matching evidence in this Saved Revision/)).toHaveLength(4)
    expect(screen.getByText(/Counts Saved Health records, not match-specific medical clearance/)).toBeVisible()
    expect(screen.getByText('Clean Working Draft · Pending changes: 0')).toBeVisible()
    expect(screen.getByText(/This Working Draft has no pending changes/)).toBeVisible()
  })

  it('provides Czech interpretation without claiming that a ranking candidate is published', () => {
    mount('cs')
    fireEvent.click(screen.getByText('Zobrazit kontrolu uložených podkladů (6) · 3 položky k prověření'))
    expect(screen.getByText('Pouze návrh · Publikace rankingu: 0')).toBeVisible()
    expect(screen.getByText('Neuloženo · Nevyřízené změny: 1')).toBeVisible()
    expect(screen.getByText(/kandidátní pořadí není publikované/)).toBeVisible()
    expect(screen.getByText(/změny dosud nejsou součástí Saved Revision/)).toBeVisible()
    expect(screen.getByText(/Jde jen o uloženou počáteční populaci/)).toBeVisible()
    expect(screen.getByText(/nikoliv nastavení počtu týdnů Runu/)).toBeVisible()
  })

  it('keeps read-only repair links scoped to the encoded selected Run ID', () => {
    render(<MemoryRouter>
      <RunHomeReadinessPanel data={data} runId="run/č 1" language="en"
        refreshing={false} refresh={vi.fn()} />
    </MemoryRouter>)
    fireEvent.click(screen.getByText('Show saved-foundation checks (6) · 3 items needing attention'))
    expect(screen.getAllByRole('link', { name: 'Inspect and Save changes →' })[0])
      .toHaveAttribute('href', '/admin/runs/run%2F%C4%8D%201/branches')
    expect(screen.getAllByRole('link', { name: 'Add a Calendar Package →' })[0])
      .toHaveAttribute('href', '/admin/runs/run%2F%C4%8D%201/manage')
    expect(screen.getByRole('link', { name: 'Open global Test Lab' }))
      .toHaveAttribute('href', '/admin/labs')
  })

  it('distinguishes a clean Czech Working Draft from saved sporting data', () => {
    mount('cs', {
      ...data,
      items: data.items.map(item => ({
        ...item,
        status: item.code === 'working_draft' ? 'saved' as const : item.status,
        evidence_count: item.code === 'working_draft' ? 0 : item.evidence_count
      }))
    })
    fireEvent.click(screen.getByText('Zobrazit kontrolu uložených podkladů (6) · 2 položky k prověření'))
    expect(screen.getByText('Čistý Working Draft · Nevyřízené změny: 0')).toBeVisible()
    expect(screen.getByText(/Tento Working Draft nemá čekající změny/)).toBeVisible()
  })
})
