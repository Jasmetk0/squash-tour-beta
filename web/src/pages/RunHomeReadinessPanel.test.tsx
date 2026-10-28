import { fireEvent, render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it, vi } from 'vitest'

import { validateRunHomeReadiness } from '../api/runHomeReadiness'
import type { RunHomeReadiness } from '../api/runHomeReadiness'
import { RunHomeReadinessPanel } from './RunHomeReadinessPanel'
import { runHomeReadinessFixture } from '../test/runHomeReadinessFixture'

const data: RunHomeReadiness = runHomeReadinessFixture()

function mount(locale: 'cs' | 'en' = 'en', values = data, rankingSetupAvailable = false) {
  const refresh = vi.fn()
  render(<MemoryRouter>
    <RunHomeReadinessPanel data={values} runId="run-a" language={locale}
      rankingSetupAvailable={rankingSetupAvailable} refreshing={false} refresh={refresh} />
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
    expect(screen.getByText(/Unsaved changes are not counted in this overview/)).toBeInTheDocument()
    // Only Saved evidence is inspected: direct the user to review pending work first.
    expect(screen.getAllByRole('link', { name: 'Inspect Branch and revision history →' })[0])
      .toHaveAttribute('href', '/admin/runs/run-a/branches')
    const checklist = screen.getByText('Show saved-foundation checks (6) · 3 items needing attention')
    expect(checklist).toBeVisible()
    expect(checklist.closest('details')).not.toHaveAttribute('open')
    fireEvent.click(checklist)
    expect(checklist.closest('details')).toHaveAttribute('open')
    expect(screen.getAllByRole('link', { name: 'Add a Calendar Package →' })[0])
      .toHaveAttribute('href', '/admin/runs/run-a/manage')
    expect(screen.getAllByRole('link', { name: 'Inspect Branch and revision history →' })[0])
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

  it('does not mistake optional Health for a global readiness guarantee', () => {
    mount('en', {
      ...data,
      items: data.items.map(item => ({
        ...item,
        status: item.code === 'health' ? 'optional' as const : 'saved' as const,
        evidence_count: item.code === 'health' || item.code === 'working_draft'
          ? 0 : Math.max(1, item.evidence_count)
      }))
    })
    expect(screen.getByText('Show saved-foundation checks (6)')).toBeVisible()
    expect(screen.getByText(/does not certify all operations/)).toBeVisible()
    fireEvent.click(screen.getByText('Show saved-foundation checks (6)'))
    expect(screen.getByText('Not required here · Health records: 0')).toBeVisible()
    expect(screen.queryByRole('link', { name: /Add a World Package|Inspect Branch and revision history/ })).toBeNull()
  })

  it('prioritizes a genuinely missing Saved foundation after a clean draft, and skips optional entries', () => {
    mount('en', {
      ...data,
      items: data.items.map(item => ({
        ...item,
        status: item.code === 'health' ? 'optional' as const
          : item.code === 'calendar_package' ? 'missing' as const : 'saved' as const,
        evidence_count: item.code === 'health' || item.code === 'calendar_package'
          || item.code === 'working_draft' ? 0 : Math.max(1, item.evidence_count)
      }))
    })
    expect(screen.getByText('Show saved-foundation checks (6) · 1 item needing attention')).toBeVisible()
    expect(screen.getAllByRole('link', { name: 'Add a Calendar Package →' })[0])
      .toHaveAttribute('href', '/admin/runs/run-a/manage')
    expect(screen.queryByText(/Unsaved changes are not counted in this overview/)).toBeNull()
  })

  it('keeps the optional global Test Lab shortcut limited to preparation', () => {
    mount('en', { ...data, phase: 'sporting_history' })
    expect(screen.queryByRole('link', { name: 'Open global Test Lab' })).toBeNull()
  })

  it('uses the Czech plural for five attention items including an unsaved draft', () => {
    mount('cs', {
      ...data,
      items: data.items.map(item => ({
        ...item,
        status: item.code === 'population' ? 'saved' as const
          : item.code === 'working_draft' ? 'unsaved' as const : 'missing' as const,
        evidence_count: item.code === 'population' ? 1000
          : item.code === 'working_draft' ? 1 : 0
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
        rankingSetupAvailable={false} refreshing={false} refresh={vi.fn()} />
    </MemoryRouter>)
    fireEvent.click(screen.getByText('Show saved-foundation checks (6) · 3 items needing attention'))
    expect(screen.getAllByRole('link', { name: 'Inspect Branch and revision history →' })[0])
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

  it('rejects invalid Run clocks rather than displaying a misleading Saved-readiness card', () => {
    const invalidClocks = [
      { ...data.current_calendar, schema_version: 'unknown' },
      { ...data.current_calendar, weeks_per_year: 0 },
      { ...data.current_calendar, season_start_year_week: 0 },
      { ...data.current_calendar, season_start_year_week: 53 },
      { ...data.current_calendar, start_year: -1 },
      { ...data.current_calendar, season_count: 0 },
      { ...data.current_calendar, weeks_per_year: 52.5 },
    ]
    for (const current_calendar of invalidClocks) {
      expect(() => validateRunHomeReadiness({ ...data, current_calendar }, 'run-a', 'branch-a'))
        .toThrow('Invalid Run Home readiness evidence')
    }
  })

  it('rejects contradictory saved and missing foundation counts while allowing pending draft changes', () => {
    const wrongSaved = data.items.map(item => item.code === 'world'
      ? { ...item, evidence_count: 0 } : item)
    const wrongMissing = data.items.map(item => item.code === 'calendar_package'
      ? { ...item, evidence_count: 1 } : item)
    const wrongRanking = data.items.map(item => item.code === 'official_ranking'
      ? { ...item, evidence_count: 2 } : item)
    for (const items of [wrongSaved, wrongMissing, wrongRanking]) {
      expect(() => validateRunHomeReadiness({ ...data, items }, 'run-a', 'branch-a'))
        .toThrow('Invalid Run Home readiness evidence')
    }
    expect(validateRunHomeReadiness(data, 'run-a', 'branch-a')).toEqual(data)
  })

  it('rejects an empty Saved revision identifier even when its hash is well formed', () => {
    expect(() => validateRunHomeReadiness({ ...data, saved_revision_id: ' ' }, 'run-a', 'branch-a'))
      .toThrow('Invalid Run Home readiness evidence')
  })

  it('rejects status combinations that the Saved readiness authority never emits', () => {
    for (const [code, status] of [
      ['world', 'optional'], ['calendar_package', 'candidate_only'],
      ['population', 'unsaved'], ['health', 'candidate_only'],
      ['official_ranking', 'optional'], ['working_draft', 'missing']
    ] as const) {
      const items = data.items.map(item => item.code === code
        ? { ...item, status, evidence_count: 0 } : item)
      expect(() => validateRunHomeReadiness({ ...data, items }, 'run-a', 'branch-a'))
        .toThrow('Invalid Run Home readiness evidence')
    }
  })

  it('routes FAX initial ranking setup to the actual Run Home preparation section', () => {
    mount('en', {
      ...data,
      sporting_calendar_supported_by_legacy_writers: true,
      current_calendar: {
        schema_version: 'run_calendar.v1', weeks_per_year: 61,
        season_start_year_week: 37, start_year: 2000, season_count: 50
      },
      items: data.items.map(item => ({
        ...item,
        status: item.code === 'working_draft' ? 'saved' as const : item.status,
        evidence_count: item.code === 'working_draft' ? 0 : item.evidence_count
      }))
     }, true)
    fireEvent.click(screen.getByText('Show saved-foundation checks (6) · 2 items needing attention'))
    const rankingLink = screen.getByRole('link', { name: 'Open ranking preparation and publication →' })
    expect(rankingLink).toHaveAttribute('href', '/admin/runs/run-a#run-initial-ranking')
    expect(screen.queryByText(/not available for this selected Run, Branch or calendar/)).toBeNull()
  })

  it('routes unsupported calendars to read-only candidate inspection without promising publication', () => {
    mount('en', {
      ...data,
      items: data.items.map(item => ({
        ...item,
        status: item.code === 'working_draft' ? 'saved' as const : item.status,
        evidence_count: item.code === 'working_draft' ? 0 : item.evidence_count
      }))
    })
    fireEvent.click(screen.getByText('Show saved-foundation checks (6) · 2 items needing attention'))
    expect(screen.getByRole('link', { name: 'Inspect ranking candidates →' }))
      .toHaveAttribute('href', '/admin/runs/run-a/branches/branch-a/ranking-candidates')
    expect(screen.getByText(/not available for this selected Run, Branch or calendar/)).toBeVisible()
  })

  it('keeps the next action for an unsaved Working Draft honest about where Save happens', () => {
    mount('cs')
    expect(screen.getByText(/Historie větví sama neukládá Working Draft/)).toBeVisible()
    const branchLinks = screen.getAllByRole('link', { name: 'Prověřit Branch a historii revizí →' })
    expect(branchLinks[0]).toHaveAttribute('href', '/admin/runs/run-a/branches')
    expect(screen.queryByRole('link', { name: 'Zkontrolovat a uložit změny →' })).toBeNull()
  })

  it('falls back to read-only candidates when the FAX Run or selected Branch is not editable', () => {
    mount('en', {
      ...data,
      sporting_calendar_supported_by_legacy_writers: true,
      items: data.items.map(item => ({
        ...item,
        status: item.code === 'working_draft' ? 'saved' as const : item.status,
        evidence_count: item.code === 'working_draft' ? 0 : item.evidence_count
      }))
    }, false)
    fireEvent.click(screen.getByText('Show saved-foundation checks (6) · 2 items needing attention'))
    expect(screen.getByRole('link', { name: 'Inspect ranking candidates →' }))
      .toHaveAttribute('href', '/admin/runs/run-a/branches/branch-a/ranking-candidates')
    expect(screen.queryByRole('link', { name: 'Open ranking preparation and publication →' })).toBeNull()
    expect(screen.getByText(/not available for this selected Run, Branch or calendar/)).toBeVisible()
  })

  it('encodes Run and Branch identities in unsupported ranking candidate inspection links', () => {
    render(<MemoryRouter>
      <RunHomeReadinessPanel data={{ ...data, branch_id: 'br/č 2',
        items: data.items.map(item => ({ ...item,
          status: item.code === 'working_draft' ? 'saved' as const : item.status,
          evidence_count: item.code === 'working_draft' ? 0 : item.evidence_count
        })) }}
        runId="run/č 1" language="cs" rankingSetupAvailable={false}
        refreshing={false} refresh={vi.fn()} />
    </MemoryRouter>)
    fireEvent.click(screen.getByText('Zobrazit kontrolu uložených podkladů (6) · 2 položky k prověření'))
    expect(screen.getByRole('link', { name: 'Prohlédnout kandidáty rankingu →' }))
      .toHaveAttribute('href', '/admin/runs/run%2F%C4%8D%201/branches/br%2F%C4%8D%202/ranking-candidates')
  })
})
