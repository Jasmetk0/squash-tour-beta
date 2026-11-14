import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { FollowStar } from './FollowStar'

// Component contract tests: the API boundary is mocked, not the production HTTP/SQLite stack.
const api = vi.hoisted(() => ({ getRunFollows: vi.fn(), putRunFollow: vi.fn(), deleteRunFollow: vi.fn() }))
vi.mock('../api/client', () => ({
  ...api,
  ApiError: class ApiError extends Error {
    status: number
    constructor(message: string, status = 500) { super(message); this.status = status }
  }
}))
const list = (rows: unknown[]) => ({ schema_version: 'run_follows.v1', run_id: 'run', follows: rows })
function mount(cs = false) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } })
  return render(<QueryClientProvider client={client}><FollowStar runId="run" kind="player" subjectId="P1" cs={cs} /></QueryClientProvider>)
}

describe('FollowStar (component, mocked API)', () => {
  beforeEach(() => Object.values(api).forEach(m => m.mockReset()))

  it('follows an unfollowed player through the Run endpoint', async () => {
    api.getRunFollows.mockResolvedValue(list([]))
    api.putRunFollow.mockResolvedValue(list([{ kind: 'player', subject_id: 'P1', alerts_enabled: true }]))
    mount()
    fireEvent.click(await screen.findByRole('button', { name: /Follow/ }))
    await waitFor(() => expect(api.putRunFollow).toHaveBeenCalledWith('run', 'player', 'P1', true))
  })

  it('shows a followed player as pressed and unfollows (CS)', async () => {
    api.getRunFollows.mockResolvedValue(list([{ kind: 'player', subject_id: 'P1', alerts_enabled: true }]))
    api.deleteRunFollow.mockResolvedValue(list([]))
    mount(true)
    const button = await screen.findByRole('button', { name: /Přestat sledovat/ })
    expect(button).toHaveAttribute('aria-pressed', 'true')
    fireEvent.click(button)
    await waitFor(() => expect(api.deleteRunFollow).toHaveBeenCalledWith('run', 'player', 'P1'))
  })

  it('does not offer a toggle for a response that belongs to another Run', async () => {
    api.getRunFollows.mockResolvedValue({ ...list([]), run_id: 'other' })
    mount()
    expect(await screen.findByText(/Following is unavailable/)).toBeInTheDocument()
    expect(screen.queryByRole('button')).not.toBeInTheDocument()
  })
})
