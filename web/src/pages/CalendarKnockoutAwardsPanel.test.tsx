import { act, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { LanguageProvider } from '../i18n/LanguageContext'
import type { CalendarAwardReview, KnockoutInspection } from '../api/calendarOpeningKnockout'
import { CalendarKnockoutAwardsPanel } from './CalendarKnockoutAwardsPanel'

const api = vi.hoisted(() => ({
  reviewCalendarKnockoutAwards: vi.fn(), applyCalendarKnockoutAwards: vi.fn(),
}))
vi.mock('../api/client', () => api)
const applied = vi.fn().mockResolvedValue(undefined)
const view = (head: string): KnockoutInspection => ({
  saved_head_revision_id: head, knockout_fingerprint: 'b'.repeat(64),
  saved: true, run_calendar: { weeks_per_year: 52 },
} as KnockoutInspection)
const review = (head: string): CalendarAwardReview => ({
  run_id: 'r', branch_id: 'b', source_saved_head: head,
  source_knockout_fingerprint: 'b'.repeat(64),
  publication_status: 'prepared_not_official', preview_fingerprint: 'a'.repeat(64),
  first_publication_week: { week: 2, calendar: { weeks_per_year: 52 } },
  awards: ['one', 'two', 'three', 'four'].map(player_id => ({
    player_id, reached_stage: 'semifinal', main_points: 30,
  })),
} as CalendarAwardReview)
function panel(head: string) {
  return <LanguageProvider><CalendarKnockoutAwardsPanel runId="r" branchId="b"
    view={view(head)} onApplied={applied}/></LanguageProvider>
}
function requestReview() {
  fireEvent.change(screen.getByLabelText('Point policy audit reason'), {
    target: { value: 'Reviewed point policy' },
  })
  fireEvent.click(screen.getByRole('button', { name: 'Review prepared point awards' }))
}

describe('prepared point review belongs to one exact Saved source', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    localStorage.setItem('squash-engine-language-v1', 'en')
  })

  it('drops old consent on HEAD change and requires a fresh review and confirmation', async () => {
    api.reviewCalendarKnockoutAwards.mockImplementation(async (_r, _b, proposal) => review(proposal.expected_saved_head))
    api.applyCalendarKnockoutAwards.mockResolvedValue({ fingerprint: 'c'.repeat(64) })
    const mounted = render(panel('head-a'))
    requestReview()
    const consent = await screen.findByLabelText('Confirm preparing points without Official publication.')
    fireEvent.click(consent)
    expect(screen.getByRole('button', { name: 'Apply prepared awards' })).toBeEnabled()
    mounted.rerender(panel('head-b'))
    expect(screen.queryByRole('button', { name: 'Apply prepared awards' })).not.toBeInTheDocument()
    expect(api.applyCalendarKnockoutAwards).not.toHaveBeenCalled()
    fireEvent.click(screen.getByRole('button', { name: 'Review prepared point awards' }))
    await screen.findByRole('button', { name: 'Apply prepared awards' })
    expect(screen.getByRole('button', { name: 'Apply prepared awards' })).toBeDisabled()
    fireEvent.click(screen.getByLabelText('Confirm preparing points without Official publication.'))
    fireEvent.click(screen.getByRole('button', { name: 'Apply prepared awards' }))
    await waitFor(() => expect(api.applyCalendarKnockoutAwards).toHaveBeenCalledTimes(1))
    expect(api.applyCalendarKnockoutAwards.mock.calls[0][2].proposal.expected_saved_head).toBe('head-b')
  })

  it('ignores a late review after switching away and back to the same Saved HEAD', async () => {
    let resolve!: (value: CalendarAwardReview) => void
    api.reviewCalendarKnockoutAwards.mockReturnValue(new Promise(r => { resolve = r }))
    const mounted = render(panel('head-a'))
    requestReview()
    mounted.rerender(panel('head-b'))
    mounted.rerender(panel('head-a'))
    await act(async () => { resolve(review('head-a')) })
    expect(screen.queryByRole('button', { name: 'Apply prepared awards' })).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Review prepared point awards' })).toBeEnabled()
    expect(api.applyCalendarKnockoutAwards).not.toHaveBeenCalled()
  })

  it('does not display an error from a previous Saved source', async () => {
    let reject!: (reason: Error) => void
    api.reviewCalendarKnockoutAwards.mockReturnValue(new Promise((_resolve, r) => { reject = r }))
    const mounted = render(panel('head-a'))
    requestReview()
    mounted.rerender(panel('head-b'))
    await act(async () => { reject(new Error('old source error')) })
    expect(screen.queryByText('old source error')).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Review prepared point awards' })).toBeEnabled()
  })
})
