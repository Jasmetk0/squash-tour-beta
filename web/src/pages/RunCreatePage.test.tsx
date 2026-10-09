import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { RunCreatePage } from './RunCreatePage'
import { renderWithRoute } from '../test/testUtils'

const navigate = vi.fn()
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual<typeof import('react-router-dom')>('react-router-dom')
  return { ...actual, useNavigate: () => navigate }
})
const api = vi.hoisted(() => ({ createEmptyRunContainer: vi.fn() }))
vi.mock('../api/client', () => api)

describe('canonical Product Run creation', () => {
  beforeEach(() => {
    localStorage.clear()
    vi.clearAllMocks()
    api.createEmptyRunContainer.mockResolvedValue({
      run_id: 'new-run-1', display_name: 'My test Run',
      storage_kind: 'custom_local', read_only: false,
      official_branch_id: 'timeline-1', status: 'active'
    })
  })

  it('creates an isolated empty Product Run using only its display name and opens the saved identity', async () => {
    renderWithRoute(<RunCreatePage />, '/admin/runs/new')
    expect(screen.queryByLabelText('Seed')).not.toBeInTheDocument()
    expect(screen.queryByLabelText('World Package')).not.toBeInTheDocument()
    expect(screen.getByText(/own Timeline 1, initial Saved Revision/)).toBeInTheDocument()

    await userEvent.type(screen.getByLabelText('Unique Run name'), ' My test Run ')
    await userEvent.click(screen.getByRole('button', { name: 'Create isolated Run' }))
    await waitFor(() => expect(api.createEmptyRunContainer).toHaveBeenCalledWith('My test Run'))
    await waitFor(() => expect(navigate).toHaveBeenCalledWith('/admin/runs/new-run-1'))
    expect(localStorage.getItem('beta_engine:last_run_id')).toBe('new-run-1')
  })

  it('rejects a duplicate name without navigating or recording a guessed Run ID', async () => {
    api.createEmptyRunContainer.mockRejectedValueOnce(new Error('Display name already exists'))
    renderWithRoute(<RunCreatePage />, '/admin/runs/new')
    await userEvent.type(screen.getByLabelText('Unique Run name'), 'My test Run')
    await userEvent.click(screen.getByRole('button', { name: 'Create isolated Run' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('Display name already exists')
    expect(navigate).not.toHaveBeenCalled()
    expect(localStorage.getItem('beta_engine:last_run_id')).toBeNull()
  })

  it('fails closed if the create response does not match the requested Run name', async () => {
    api.createEmptyRunContainer.mockResolvedValueOnce({
      run_id: 'other-run', display_name: 'Somebody else', storage_kind: 'custom_local', read_only: false
    })
    renderWithRoute(<RunCreatePage />, '/admin/runs/new')
    await userEvent.type(screen.getByLabelText('Unique Run name'), 'My test Run')
    await userEvent.click(screen.getByRole('button', { name: 'Create isolated Run' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('unexpected Run identity')
    expect(navigate).not.toHaveBeenCalled()
  })
})
