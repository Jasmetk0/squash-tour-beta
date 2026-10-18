import { act, fireEvent, render, screen, within } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { LanguageProvider } from '../i18n/LanguageContext'
import { CalendarPopulationSportingPanel } from './CalendarPopulationSportingPanel'
import type { PopulationSportingCheckpoint, PopulationSportingPlayer } from '../api/calendarOpeningKnockout'
const api = vi.hoisted(() => ({ inspectCalendarSportingPlayer: vi.fn(), ApiError: class ApiError extends Error {} }))
vi.mock('../api/client', () => api)
const checkpoint: PopulationSportingCheckpoint = {
  schema_version: 'calendar_sporting_checkpoint.v1', fingerprint: 'a'.repeat(64),
  source_knockout_fingerprint: 'b'.repeat(64), player_count: 5, attribute_count: 57,
  phase: 'opening_week_after_knockout', saved: true, annual_development_applied: false, health_effects_applied: false,
}
const response = (head = 'head', playerId = 'outside'): PopulationSportingPlayer => ({
  schema_version: 'calendar_sporting_checkpoint_player.v1', run_id: 'r', branch_id: 'b',
  saved_head_revision_id: head, checkpoint_fingerprint: checkpoint.fingerprint,
  player: { player_id: playerId, current_form: 100, match_sharpness: 100, long_term_fatigue: 0,
    potential_ovr: 150, attributes: Array.from({ length: 57 }, (_, i) => [`attribute-${i}`, 100]),
  },
})
const panel = (head = 'head') => <LanguageProvider><CalendarPopulationSportingPanel
  runId="r" branchId="b" head={head} checkpoint={checkpoint} playerIds={['outside', 'a', 'b', 'c', 'd']} />
</LanguageProvider>

describe('stored population sporting inspection (HTTP boundary mocked)', () => {
  beforeEach(() => { vi.clearAllMocks(); localStorage.setItem('squash-engine-language-v1', 'en') })
  it('requests an actual stored nonparticipant with exact source, and clears after selecting a different player', async () => {
    api.inspectCalendarSportingPlayer.mockResolvedValue(response())
    render(panel())
    fireEvent.click(screen.getByRole('button', { name: 'Inspect stored sporting record' }))
    const record = await screen.findByLabelText('Population sporting player record')
    expect(within(record).getAllByRole('row')).toHaveLength(58)
    expect(api.inspectCalendarSportingPlayer).toHaveBeenCalledWith('r', 'b', 'outside', 'head', checkpoint.fingerprint)
    fireEvent.change(screen.getByRole('combobox', { name: 'Population player' }), { target: { value: 'a' } })
    expect(screen.queryByLabelText('Population sporting player record')).not.toBeInTheDocument()
  })
  it('ignores an old A to B to A response and permits a fresh request', async () => {
    let resolve!: (v: PopulationSportingPlayer) => void
    api.inspectCalendarSportingPlayer.mockReturnValue(new Promise(r => { resolve = r }))
    const mounted = render(panel('A'))
    fireEvent.click(screen.getByRole('button', { name: 'Inspect stored sporting record' }))
    mounted.rerender(panel('B')); mounted.rerender(panel('A'))
    await act(async () => { resolve(response('A')) })
    expect(screen.queryByLabelText('Population sporting player record')).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Inspect stored sporting record' })).toBeEnabled()
  })
  it.each(['scope', 'fingerprint', 'catalog', 'state'])('rejects %s drift', async fault => {
    const r = response()
    if (fault === 'scope') r.player.player_id = 'foreign'
    if (fault === 'fingerprint') r.checkpoint_fingerprint = 'f'.repeat(64)
    if (fault === 'catalog') r.player.attributes.pop()
    if (fault === 'state') r.player.long_term_fatigue = 101
    api.inspectCalendarSportingPlayer.mockResolvedValue(r)
    render(panel())
    fireEvent.click(screen.getByRole('button', { name: 'Inspect stored sporting record' }))
    expect(await screen.findByRole('alert')).toBeVisible()
    expect(screen.queryByLabelText('Population sporting player record')).not.toBeInTheDocument()
  })
})
