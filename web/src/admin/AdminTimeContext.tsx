import { useQuery } from '@tanstack/react-query'
import { createContext, useContext } from 'react'

import { getBranchState } from '../api/client'
import { useAdminBranch } from './AdminBranchContext'
import { adminBranchStateQueryKey } from './adminQueryKeys'
import { formatApiError } from '../utils/apiErrors'

export type AdminTimeContextValue = {
  runId: string
  branchId: string | null
  mode: 'present'
  currentSeason: number | null
  currentWeek: number | null
  currentEventId: string | null
  currentEventSequence: number | null
  headCheckpointId: string | null
  isLoading: boolean
  isAvailable: boolean
  error: string | null
  identityMismatch: boolean
}

const AdminTimeContext = createContext<AdminTimeContextValue | null>(null)

export function AdminTimeProvider({ children }: { children: React.ReactNode }): JSX.Element {
  const { runId, selectedBranchId } = useAdminBranch()
  const stateQuery = useQuery({
    queryKey: adminBranchStateQueryKey(runId, selectedBranchId),
    queryFn: () => getBranchState(selectedBranchId!),
    enabled: Boolean(runId && selectedBranchId),
    retry: false,
  })
  const validState = stateQuery.data?.run_id === runId && stateQuery.data.branch_id === selectedBranchId
    ? stateQuery.data
    : null
  const identityMismatch = Boolean(stateQuery.data && !validState)
  const error = identityMismatch
    ? 'Branch State identity does not match the Active Admin Run and Branch.'
    : stateQuery.error
      ? formatApiError(stateQuery.error)
      : null

  return <AdminTimeContext.Provider value={{
    runId,
    branchId: selectedBranchId,
    mode: 'present',
    currentSeason: validState?.current_season ?? null,
    currentWeek: validState?.current_week ?? null,
    currentEventId: validState?.current_event_id ?? null,
    currentEventSequence: validState?.current_event_sequence ?? null,
    headCheckpointId: validState?.head_checkpoint_id ?? null,
    isLoading: Boolean(selectedBranchId && stateQuery.isLoading),
    isAvailable: Boolean(validState),
    error,
    identityMismatch,
  }}>{children}</AdminTimeContext.Provider>
}

export function useAdminTime(): AdminTimeContextValue {
  const value = useContext(AdminTimeContext)
  if (!value) throw new Error('useAdminTime must be used within AdminTimeProvider')
  return value
}
