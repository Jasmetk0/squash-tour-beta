import { useQuery } from '@tanstack/react-query'
import { createContext, useContext, useEffect, useMemo, useRef, useState, useCallback } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'

import { getRunContainer, listRunBranches } from '../api/client'
import type { RunBranch } from '../api/types'
import { formatApiError } from '../utils/apiErrors'
import { allowConfirmedAdminNavigation, confirmAdminContextChange } from '../navigation/runContextGuard'

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
  const { pathname, search, hash } = useLocation()
  const navigate = useNavigate()
  const acceptedLocation = useRef<{runId: string; href: string} | null>(null)
  const requestedBranchId = new URLSearchParams(search).get('branch')
  const selectionsByRun = useRef(new Map<string, string>())
  const [selection, setSelection] = useState<{ runId: string; branchId: string } | null>(null)
  const currentSelection = useRef<{runId:string; branchId:string}|null>(null)
  currentSelection.current = selection
  const runQuery = useQuery({ queryKey: ['admin-run-container', runId], queryFn: () => getRunContainer(runId), retry: false })
  const branchesQuery = useQuery({ queryKey: ['admin-run-branches', runId], queryFn: () => listRunBranches(runId), retry: false })
  const branches = useMemo(() => validBranches(branchesQuery.data?.run_branches, runId), [branchesQuery.data, runId])
  const viewerBranchId = runQuery.data?.official_branch_id ?? null

  useEffect(() => {
    if (!branchesQuery.isSuccess || runQuery.isLoading) return
    const href = pathname + search + hash
    const requestedIsValid = !requestedBranchId ||
      branches.some(branch => branch.branch_id === requestedBranchId)
    const old = currentSelection.current
    const priorBranchId = old?.runId === runId ? old.branchId : null

    // A rejected deep link must roll the browser address back together with
    // the provider selection. This also covers POP (Back/Forward) navigation:
    // keeping the URL on an unapproved Branch would make reload unsafe.
    if (requestedBranchId && priorBranchId && requestedBranchId !== priorBranchId) {
      if (!confirmAdminContextChange('Branch', runId, requestedBranchId)) {
        const previous = acceptedLocation.current
        if (previous?.runId === runId && previous.href !== href) {
          navigate(previous.href, { replace: true })
        }
        return
      }
    }
    if (!requestedIsValid) {
      // Fail closed. Never silently open Viewer or a remembered Branch when a
      // stale/foreign Branch was explicitly requested.
      selectionsByRun.current.delete(runId)
      currentSelection.current = null
      setSelection(null)
      acceptedLocation.current = { runId, href }
      return
    }
    const remembered = selectionsByRun.current.get(runId)
    const next = requestedBranchId
      ?? (remembered && branches.some(branch => branch.branch_id === remembered) ? remembered : null)
      ?? (viewerBranchId && branches.some(branch => branch.branch_id === viewerBranchId) ? viewerBranchId : null)
      ?? branches[0]?.branch_id
      ?? null
    if (next) selectionsByRun.current.set(runId, next)
    else selectionsByRun.current.delete(runId)
    currentSelection.current = next ? { runId, branchId: next } : null
    acceptedLocation.current = { runId, href }
    setSelection(next ? { runId, branchId: next } : null)
  }, [branches, branchesQuery.isSuccess, runId, runQuery.isLoading, viewerBranchId,
    requestedBranchId, pathname, search, hash, navigate])

  const selectedBranchId = selection?.runId === runId && branches.some(branch => branch.branch_id === selection.branchId)
    ? selection.branchId
    : null
  const selectBranch = useCallback((branchId: string): boolean => {
    if (!branches.some(branch => branch.branch_id === branchId)) return false
    const current = currentSelection.current
    if (current?.runId === runId && current.branchId === branchId) return true
    if (current?.runId === runId && !confirmAdminContextChange('Branch', runId, branchId)) return false
    selectionsByRun.current.set(runId, branchId)
    currentSelection.current = {runId, branchId}
    setSelection({ runId, branchId })
    // A selector change must not leave an older explicit ?branch= in the URL.
    // Preserve all unrelated query parameters and the hash.
    const params = new URLSearchParams(search)
    if (params.has('branch')) {
      params.set('branch', branchId)
      const nextHref = pathname + '?' + params.toString() + hash
      acceptedLocation.current = { runId, href: nextHref }
      allowConfirmedAdminNavigation(nextHref)
      navigate(nextHref, { replace: true })
    }
    return true
  }, [branches, runId, pathname, search, hash, navigate])
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
