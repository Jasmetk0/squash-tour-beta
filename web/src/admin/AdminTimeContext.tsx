import { useQuery } from '@tanstack/react-query'
import { createContext, useContext, useMemo, useState } from 'react'

import { getBranchState, listBranchCheckpoints } from '../api/client'
import type { BranchCheckpoint } from '../api/types'
import { useAdminBranch } from './AdminBranchContext'
import { adminBranchCheckpointsQueryKey, adminBranchStateQueryKey } from './adminQueryKeys'
import { formatApiError } from '../utils/apiErrors'

export type AdminTimeContextValue = {
  runId: string
  branchId: string | null
  mode: 'present' | 'checkpoint'
  presentSeason: number | null
  presentWeek: number | null
  presentEventId: string | null
  presentEventSequence: number | null
  headCheckpointId: string | null
  viewSeason: number | null
  viewWeek: number | null
  viewEventId: string | null
  viewEventSequence: number | null
  viewCheckpointId: string | null
  selectedCheckpoint: BranchCheckpoint | null
  checkpoints: BranchCheckpoint[]
  checkpointsLoading: boolean
  checkpointsError: string | null
  selectPresent: () => void
  selectCheckpoint: (checkpointId: string) => void
  isLoading: boolean
  isAvailable: boolean
  error: string | null
  identityMismatch: boolean
}

const AdminTimeContext = createContext<AdminTimeContextValue | null>(null)

export function AdminTimeProvider({ children }: { children: React.ReactNode }): JSX.Element {
  const { runId, selectedBranchId } = useAdminBranch()
  const [selection, setSelection] = useState<{ runId: string; branchId: string; checkpointId: string } | null>(null)
  const stateQuery = useQuery({
    queryKey: adminBranchStateQueryKey(runId, selectedBranchId),
    queryFn: () => getBranchState(selectedBranchId!),
    enabled: Boolean(runId && selectedBranchId),
    retry: false,
  })
  const checkpointsQuery = useQuery({
    queryKey: adminBranchCheckpointsQueryKey(runId, selectedBranchId),
    queryFn: () => listBranchCheckpoints({ run_id: runId, branch_id: selectedBranchId! }),
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
  const checkpoints = useMemo(() => (checkpointsQuery.data?.branch_checkpoints ?? [])
    .filter(checkpoint => checkpoint.run_id === runId && checkpoint.branch_id === selectedBranchId && checkpoint.checkpoint_id.trim() && Number.isFinite(checkpoint.sequence))
    .sort((left, right) => right.sequence - left.sequence), [checkpointsQuery.data, runId, selectedBranchId])
  const selectionMatches = Boolean(selection && selection.runId === runId && selection.branchId === selectedBranchId)
  const selectedCheckpoint = selectionMatches ? checkpoints.find(checkpoint => checkpoint.checkpoint_id === selection!.checkpointId) ?? null : null
  const selectedIdentity = selectionMatches ? selection : null
  const mode = selectedIdentity && selectedIdentity.checkpointId !== validState?.head_checkpoint_id ? 'checkpoint' : 'present'
  const historicalUnavailable = mode === 'checkpoint' && !selectedCheckpoint

  const selectCheckpoint = (checkpointId: string): void => {
    const checkpoint = checkpoints.find(item => item.checkpoint_id === checkpointId)
    if (!checkpoint || !selectedBranchId) return
    if (checkpoint.checkpoint_id === validState?.head_checkpoint_id) { setSelection(null); return }
    setSelection({ runId, branchId: selectedBranchId, checkpointId })
  }

  return <AdminTimeContext.Provider value={{
    runId,
    branchId: selectedBranchId,
    mode,
    presentSeason: validState?.current_season ?? null,
    presentWeek: validState?.current_week ?? null,
    presentEventId: validState?.current_event_id ?? null,
    presentEventSequence: validState?.current_event_sequence ?? null,
    headCheckpointId: validState?.head_checkpoint_id ?? null,
    viewSeason: mode === 'checkpoint' ? selectedCheckpoint?.season ?? null : validState?.current_season ?? null,
    viewWeek: mode === 'checkpoint' ? selectedCheckpoint?.week ?? null : validState?.current_week ?? null,
    viewEventId: mode === 'checkpoint' ? selectedCheckpoint?.event_id ?? null : validState?.current_event_id ?? null,
    viewEventSequence: mode === 'checkpoint' ? selectedCheckpoint?.event_sequence ?? null : validState?.current_event_sequence ?? null,
    viewCheckpointId: mode === 'checkpoint' ? selectedIdentity?.checkpointId ?? null : validState?.head_checkpoint_id ?? null,
    selectedCheckpoint,
    checkpoints,
    checkpointsLoading: Boolean(selectedBranchId && checkpointsQuery.isLoading),
    checkpointsError: checkpointsQuery.error ? formatApiError(checkpointsQuery.error) : historicalUnavailable ? 'The selected historical checkpoint is unavailable.' : null,
    selectPresent: () => setSelection(null),
    selectCheckpoint,
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
