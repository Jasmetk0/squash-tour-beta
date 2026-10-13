import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { GroupTieResolutionEditor } from './GroupTieResolutionEditor'
import type { GroupStandingsTieState } from '../api/tournamentGroupStandings'

const api = vi.hoisted(() => ({
  resolveAdminGroupStandingsTie: vi.fn(),
  ApiError: class ApiError extends Error {
    status: number
    constructor(message: string, status = 409) { super(message); this.status = status }
  }
}))
vi.mock('../api/client', () => api)

const fingerprint = 'a'.repeat(64)
const caseState: GroupStandingsTieState = {
  schema_version: 'tournament_group_tie_resolution_state.v1',
  run_id: 'r', branch_id: 'b', event_id: 'e',
  unresolved_case_fingerprint: fingerprint,
  unresolved_case: { group_index: 1, reason: 'group_ratio_unresolved', player_ids: ['A','B','C'] },
  resolutions: [],
}

function mount(state: GroupStandingsTieState = caseState, enabled = true) {
  const onResolution = vi.fn().mockResolvedValue(null)
  const queryClient = new QueryClient({defaultOptions:{mutations:{retry:false},queries:{retry:false}}})
  const result = render(<QueryClientProvider client={queryClient}>
    <GroupTieResolutionEditor runId="r" branchId="b" eventId="e"
      tieState={state} enabled={enabled} onResolution={onResolution}/>
  </QueryClientProvider>)
  return {...result, onResolution}
}

describe('Run Admin exact group tie decision', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    api.resolveAdminGroupStandingsTie.mockResolvedValue({authority_fingerprint:'b'.repeat(64)})
  })

  it('requires a deliberate ordering review, audit reason and separate confirmation', async () => {
    const { onResolution } = mount()
    const commit = screen.getByRole('button',{name:'Commit audited group tie decision'})
    expect(commit).toBeDisabled()
    expect(screen.getByRole('list',{name:'Proposed tie order'}).textContent).toContain('ABC')
    fireEvent.click(screen.getByRole('button',{name:'Move A down'}))
    expect(screen.getByRole('list',{name:'Proposed tie order'}).textContent).toMatch(/B.*A.*C/)
    expect(commit).toBeDisabled()
    fireEvent.change(screen.getByLabelText('Admin tie decision reason'), {
      target:{value:'Reviewed tied athletes and approved this exact order.'}
    })
    const approve = screen.getByLabelText('Confirm this exact player order and recorded audit reason')
    fireEvent.click(approve)
    expect(commit).toBeEnabled()
    fireEvent.click(commit)
    await waitFor(() => expect(api.resolveAdminGroupStandingsTie).toHaveBeenCalledTimes(1))
    expect(api.resolveAdminGroupStandingsTie).toHaveBeenCalledWith('r','b','e',
      ['A','B','C'],{
        command_id:expect.any(String),
        case_fingerprint:fingerprint,
        ordered_player_ids:['B','A','C'],
        admin_reason:'Reviewed tied athletes and approved this exact order.',
      })
    await waitFor(() => expect(onResolution).toHaveBeenCalledTimes(1))
  })

  it('changing the reviewed order or reason invalidates prior confirmation', () => {
    mount()
    fireEvent.change(screen.getByLabelText('Admin tie decision reason'),{
      target:{value:'Exact operator audit reason'}
    })
    fireEvent.click(screen.getByLabelText('Confirm this exact player order and recorded audit reason'))
    expect(screen.getByRole('button',{name:'Commit audited group tie decision'})).toBeEnabled()
    fireEvent.click(screen.getByRole('button',{name:'Move B up'}))
    expect(screen.getByRole('button',{name:'Commit audited group tie decision'})).toBeDisabled()
    expect(screen.getByLabelText('Confirm this exact player order and recorded audit reason')).not.toBeChecked()
  })

  it('does not allow an empty reason, missing fingerprint or blocked context', () => {
    const { unmount } = mount()
    fireEvent.change(screen.getByLabelText('Admin tie decision reason'),{
      target:{value:'   '}
    })
    expect(screen.getByLabelText('Confirm this exact player order and recorded audit reason')).toBeDisabled()
    unmount()
    const {unmount:unmount2} = mount({...caseState, unresolved_case_fingerprint:undefined})
    fireEvent.change(screen.getByLabelText('Admin tie decision reason'),{target:{value:'Reviewed evidence'}})
    expect(screen.getByRole('button',{name:'Commit audited group tie decision'})).toBeDisabled()
    unmount2()
    mount(caseState,false)
    expect(screen.getByRole('button',{name:'Move A down'})).toBeDisabled()
    expect(screen.getByRole('button',{name:'Commit audited group tie decision'})).toBeDisabled()
    expect(api.resolveAdminGroupStandingsTie).not.toHaveBeenCalled()
  })

  it('surfaces a stale-case conflict and clears confirmation without persisting a guessed order', async () => {
    api.resolveAdminGroupStandingsTie.mockRejectedValue(new api.ApiError('Case changed',409))
    const {onResolution} = mount()
    fireEvent.change(screen.getByLabelText('Admin tie decision reason'),{target:{value:'Reviewed evidence'}})
    fireEvent.click(screen.getByLabelText('Confirm this exact player order and recorded audit reason'))
    fireEvent.click(screen.getByRole('button',{name:'Commit audited group tie decision'}))
    expect(await screen.findByRole('alert')).toHaveTextContent('Case changed')
    await waitFor(() => expect(onResolution).toHaveBeenCalledOnce())
    expect(screen.getByRole('button',{name:'Commit audited group tie decision'})).toBeDisabled()
  })
})
