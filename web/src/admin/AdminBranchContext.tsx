import { useQuery } from '@tanstack/react-query'
import { createContext, useContext, useEffect, useMemo, useRef, useState, useCallback } from 'react'
import { useLocation } from 'react-router-dom'

import { getRunContainer, listRunBranches } from '../api/client'
import type { RunBranch } from '../api/types'
import { formatApiError } from '../utils/apiErrors'
import { confirmAdminContextChange } from '../navigation/runContextGuard'

export type AdminBranchContextValue = {
  runId: string
  selectedBranchId: string | null
  selectedBranch: RunBranch | null
  branches: RunBranch[]
  viewerBranchId: string | null
  isLoading: boolean
  error: string | null
  viewerBranchMissing: boolean
  selectBranch: (branchId: string) => boolean
}

const AdminBranchContext = createContext<AdminBranchContextValue | null>(null)

function validBranches(value: unknown, runId: string): RunBranch[] {
  if (!Array.isArray(value)) return []
  return value
    .filter((branch): branch is RunBranch => (
      typeof branch === 'object' && branch !== null
      && (branch as RunBranch).run_id === runId
      && typeof (branch as RunBranch).branch_id === 'string'
      && Boolean((branch as RunBranch).branch_id.trim())
    ))
    .sort((left, right) => left.branch_id < right.branch_id ? -1 : left.branch_id > right.branch_id ? 1 : 0)
}

export function AdminBranchProvider({ runId, children }: { runId: string; children: React.ReactNode }): JSX.Element {
  // This shell context deliberately does not make legacy Run pages branch-aware. Those pages
  // must migrate separately to real BranchState/checkpoint-backed read contracts.
  const { search } = useLocation()
  const requestedBranchId = new URLSearchParams(search).get('branch')
  const selectionsByRun = useRef(new Map<string, string>())
  const [selection, setSelection] = useState<{ runId: string; branchId: string } | null>(null)
  const currentSelection = useRef<{runId:string; branchId:string}|null>(null)
  currentSelection.current = selection
  const deniedLink = useRef<string | null>(null)
  const runQuery = useQuery({ queryKey: ['admin-run-container', runId], queryFn: () => getRunContainer(runId), retry: false })
  const branchesQuery = useQuery({ queryKey: ['admin-run-branches', runId], queryFn: () => listRunBranches(runId), retry: false })
  const branches = useMemo(() => validBranches(branchesQuery.data?.run_branches, runId), [branchesQuery.data, runId])
  const viewerBranchId = runQuery.data?.official_branch_id ?? null

  useEffect(() => {
    if (!branchesQuery.isSuccess || runQuery.isLoading) return
    const remembered = selectionsByRun.current.get(runId)
    // An explicit Runs inventory deep link chooses *only* this Admin Branch.
    // An invalid/stale Branch ID fails closed; never substitute the Viewer Branch.
    if (requestedBranchId && !branches.some(branch => branch.branch_id === requestedBranchId)) {
      selectionsByRun.current.delete(runId)
      setSelection(null)
      return
    }
    const next = (requestedBranchId && branches.some(branch => branch.branch_id === requestedBranchId) ? requestedBranchId : null)
      ?? (remembered && branches.some(branch => branch.branch_id === remembered) ? remembered : null)
      ?? (viewerBranchId && branches.some(branch => branch.branch_id === viewerBranchId) ? viewerBranchId : null)
      ?? branches[0]?.branch_id
      ?? null
    const old = currentSelection.current
    const priorBranchId = old?.runId === runId ? old.branchId : null
    const transitionId = runId + '/' + priorBranchId + '->' + next
    // A direct ?branch=... change after initial selection is a real context
    // transition, even when triggered imperatively by useNavigate.
    if (requestedBranchId && priorBranchId && next !== priorBranchId) {
      if (deniedLink.current === transitionId) return
      if (!confirmAdminContextChange('Branch', runId, next ?? undefined)) {
        deniedLink.current = transitionId
        return
      }
    }
    deniedLink.current = null
    if (next) selectionsByRun.current.set(runId, next)
    else selectionsByRun.current.delete(runId)
    currentSelection.current = next ? {runId, branchId:next} : null
    setSelection(next ? { runId, branchId: next } : null)
  }, [branches, branchesQuery.isSuccess, runId, runQuery.isLoading, viewerBranchId, requestedBranchId])

  const selectedBranchId = selection?.runId === runId && branches.some(branch => branch.branch_id === selection.branchId)
    ? selection.branchId
    : null
  const selectBranch = useCallback((branchId: string): boolean => {
    if (!branches.some(branch => branch.branch_id === branchId)) return false
    const current = currentSelection.current
    if (current?.runId === runId && current.branchId === branchId) return true
    if (current?.runId === runId && !confirmAdminContextChange('Branch', runId, branchId)) return false
    deniedLink.current = null
    selectionsByRun.current.set(runId, branchId)
    currentSelection.current = {runId, branchId}
    setSelection({ runId, branchId })
    return true
  }, [branches, runId])
  const errors = [
    runQuery.error ? `Run metadata unavailable: ${formatApiError(runQuery.error)}` : null,
    branchesQuery.error ? `Branch metadata unavailable: ${formatApiError(branchesQuery.error)}` : null,
  ].filter((error): error is string => Boolean(error))
  const value: AdminBranchContextValue = {
    runId,
    selectedBranchId,
    selectedBranch: branches.find(branch => branch.branch_id === selectedBranchId) ?? null,
    branches,
    viewerBranchId,
    isLoading: runQuery.isLoading || branchesQuery.isLoading,
    error: requestedBranchId && branchesQuery.isSuccess && !branches.some(branch => branch.branch_id === requestedBranchId)
      ? `Requested Admin Branch "${requestedBranchId}" does not belong to this Run.`
      : errors.length ? errors.join('; ') : null,
    viewerBranchMissing: Boolean(viewerBranchId && branchesQuery.isSuccess && !branches.some(branch => branch.branch_id === viewerBranchId)),
    selectBranch,
  }

  return <AdminBranchContext.Provider value={value}>{children}</AdminBranchContext.Provider>
}

export function useAdminBranch(): AdminBranchContextValue {
  const value = useContext(AdminBranchContext)
  if (!value) throw new Error('useAdminBranch must be used within AdminBranchProvider')
  return value
}
