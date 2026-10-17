import { act, fireEvent, render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { LanguageProvider } from '../i18n/LanguageContext'
import { CalendarCanonicalInputsPanel } from './CalendarCanonicalInputsPanel'
import type { CanonicalKnockoutPreview, CanonicalKnockoutSource } from '../api/calendarOpeningKnockout'
const api = vi.hoisted(() => ({ previewCalendarCanonicalKnockout: vi.fn() }))
vi.mock('../api/client', () => api)
const entrants = ['a', 'b', 'c', 'd'], world = 'b'.repeat(64)
const source = (): CanonicalKnockoutSource => ({
  schema_version: 'calendar_canonical_match_source.v1', source_initial_world_fingerprint: world,
  annual_development_applied: false,
  players: entrants.map(player_id => ({ player: { player_id, name: player_id } })),
  records: entrants.map(player_id => ({ player_id, potential_ovr: 150,
    attributes: Array.from({ length: 57 }, (_, i) => [`attribute-${i}`, 100] as [string, number]),
  })),
})
const response = (head: string): CanonicalKnockoutPreview => ({
  schema_version: 'calendar_canonical_knockout_preview.v1', run_id: 'r', branch_id: 'b',
  saved_head_revision_id: head, fingerprint: 'c'.repeat(64), source: source(),
})
const panel = (head = 'head', frozen?: CanonicalKnockoutSource) => <LanguageProvider>
  <CalendarCanonicalInputsPanel runId="r" branchId="b" head={head} world={world} entrants={entrants} source={frozen}/>
</LanguageProvider>

describe('read-only canonical input preview (HTTP boundary mocked)', () => {
  beforeEach(() => { vi.clearAllMocks(); localStorage.setItem('squash-engine-language-v1', 'en') })
  it('previews 57 attributes and drops them when Saved HEAD changes', async () => {
    api.previewCalendarCanonicalKnockout.mockResolvedValue(response('head'))
    const mounted = render(panel())
    fireEvent.click(screen.getByRole('button', { name: 'Preview 57 attributes' }))
    fireEvent.click(await screen.findByText('57 attributes · a'))
    expect(screen.getByRole('table', { name: 'Attributes a' }).querySelectorAll('tbody tr')).toHaveLength(57)
    expect(api.previewCalendarCanonicalKnockout).toHaveBeenCalledWith('r', 'b', {
      expected_saved_head: 'head', expected_initial_world_fingerprint: world, entrant_ids: entrants,
    })
    mounted.rerender(panel('new-head'))
    expect(screen.queryByText('57 attributes · a')).not.toBeInTheDocument()
  })
  it('ignores late responses after A to B to A', async () => {
    let resolve!: (v: CanonicalKnockoutPreview) => void
    api.previewCalendarCanonicalKnockout.mockReturnValue(new Promise(r => { resolve = r }))
    const mounted = render(panel('A'))
    fireEvent.click(screen.getByRole('button', { name: 'Preview 57 attributes' }))
    mounted.rerender(panel('B')); mounted.rerender(panel('A'))
    await act(async () => { resolve(response('A')) })
    expect(screen.queryByText('57 attributes · a')).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Preview 57 attributes' })).toBeEnabled()
  })
  it('shows frozen played source without requesting a new profile', () => {
    render(panel('head', source()))
    expect(screen.getByText('Frozen attributes used when played.')).toBeVisible()
    expect(screen.queryByRole('button', { name: 'Preview 57 attributes' })).not.toBeInTheDocument()
    fireEvent.click(screen.getByText('57 attributes · a'))
    expect(screen.getByRole('table', { name: 'Attributes a' })).toBeVisible()
    expect(api.previewCalendarCanonicalKnockout).not.toHaveBeenCalled()
  })
})
