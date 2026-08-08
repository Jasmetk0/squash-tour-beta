export const adminBranchStateQueryKey = (runId: string, branchId: string | null) =>
  ['admin-branch-state', runId, branchId] as const

export const adminBranchHeadQueryKey = (runId: string, branchId: string | null, checkpointId: string | null) =>
  ['admin-branch-head', runId, branchId, checkpointId] as const
