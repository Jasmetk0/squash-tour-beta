import { act, fireEvent, render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { RunCalendarExtensionInspection } from './RunCalendarExtensionInspection'

const api = vi.hoisted(() => ({
  reviewRunCalendarExtension: vi.fn(), saveRunCalendarExtension: vi.fn()
}))
vi.mock('../api/client', () => api)
vi.mock('../utils/apiErrors', () => ({ formatApiError: (error: unknown) => String(error) }))

const calendar = (n: number) => ({
  schema_version: 'run_calendar.v1', start_year: 2030,
  weeks_per_year: 52, season_start_year_week: 1, season_count: n
})
const evidence = (n: number, ready = true) => ({
  schema_version: 'run_calendar_extension_review.v1', run_id: 'r',
  review_fingerprint: 'a'.repeat(64),
  original_calendar: calendar(3), proposed_calendar: calendar(n),
  branch_count: 2, branches: [
    { branch_id: 'a', display_name: 'Main', saved_head_revision_id: 'old-a', blockers: [] },
    { branch_id: 'b', display_name: 'Other', saved_head_revision_id: 'old-b', blockers: ready ? [] : ['dirty'] }
  ], frozen_task_count: 1, added_weeks: (n - 3) * 52, added_seasons: n - 3,
  can_save: ready, blockers: ready ? [] : ['dirty']
})
const receipt = {
  schema_version: 'run_calendar_extension_save.v1', run_id: 'r',
  command_id: 'saved-id', review_fingerprint: 'a'.repeat(64),
  previous_calendar: calendar(3), current_calendar: calendar(4),
  saved: true, branch_count: 2, branches: [
    { branch_id: 'a', saved_revision_id: 'new-a' },
    { branch_id: 'b', saved_revision_id: 'new-b' }
  ]
}
function mount(language: 'cs' | 'en' = 'en') {
  const props = { runId: 'r', branchId: 'a', currentCount: 3, language }
  const view = render(<RunCalendarExtensionInspection {...props} />)
  return { ...view, switchBranch: () =>
    view.rerender(<RunCalendarExtensionInspection {...props} branchId="b" />) }
}

describe('Run horizon extension reviewed Save', () => {
  beforeEach(() => vi.clearAllMocks())

  it('rejects stale review after changing proposed count', async () => {
    let finish!: (v: unknown) => void
    api.reviewRunCalendarExtension.mockReturnValue(
      new Promise(resolve => { finish = resolve })
    )
    mount()
    fireEvent.click(screen.getByRole('button', { name: 'Review all Branches' }))
    fireEvent.change(screen.getByRole('spinbutton'), { target: { value: '5' } })
    await act(async () => finish(evidence(4)))
    expect(screen.queryByText('Main', { exact: true })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Confirm & Save entire Run' })).not.toBeInTheDocument()
    expect(api.saveRunCalendarExtension).not.toHaveBeenCalled()
  })

  it('discards an old Branch review, without dropping the new review', async () => {
    let reject!: (v: unknown) => void
    api.reviewRunCalendarExtension.mockReturnValueOnce(
      new Promise((_resolve, fail) => { reject = fail })
    )
    const view = mount()
    fireEvent.click(screen.getByRole('button', { name: 'Review all Branches' }))
    view.switchBranch()
    api.reviewRunCalendarExtension.mockResolvedValueOnce(evidence(4))
    fireEvent.click(screen.getByRole('button', { name: 'Review all Branches' }))
    await act(async () => reject(Error('former branch')))
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
    expect(await screen.findByText('Main', { exact: true })).toBeInTheDocument()
  })

  it('requires an all-Branch-ready review and explicit confirmation before Save', async () => {
    api.reviewRunCalendarExtension.mockResolvedValueOnce(evidence(4, false))
      .mockResolvedValueOnce(evidence(4))
    api.saveRunCalendarExtension.mockImplementation(async (_runId, input) => ({
      ...receipt, command_id: input.command_id
    }))
    mount('en')
    fireEvent.click(screen.getByRole('button', { name: 'Review all Branches' }))
    expect(await screen.findByText('Save blocked:', { exact: false })).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Confirm & Save entire Run' })).not.toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Review all Branches' }))
    const save = await screen.findByRole('button', { name: 'Confirm & Save entire Run' })
    expect(save).toBeDisabled()
    fireEvent.click(screen.getByRole('checkbox'))
    expect(save).toBeEnabled()
    fireEvent.click(save)
    expect(await screen.findByText('Run horizon saved successfully')).toBeInTheDocument()
    expect(api.saveRunCalendarExtension).toHaveBeenCalledTimes(1)
    const [runId, command] = api.saveRunCalendarExtension.mock.calls[0]
    expect(runId).toBe('r')
    expect(command).toEqual({
      command_id: expect.any(String),
      new_season_count: 4,
      review_fingerprint: 'a'.repeat(64), explicit_confirmation: true,
    })
    expect(screen.getByText('No simulation was started.')).toBeInTheDocument()
  })

  it('offers a Czech review and Save flow', async () => {
    api.reviewRunCalendarExtension.mockResolvedValue(evidence(4))
    mount('cs')
    fireEvent.click(screen.getByRole('button', { name: 'Zkontrolovat všechny Branches' }))
    expect(await screen.findByText('Main', { exact: true })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Potvrdit a uložit celý Run' })).toBeDisabled()
  })
})
