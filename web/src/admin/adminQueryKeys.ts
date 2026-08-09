export const adminBranchStateQueryKey = (runId: string, branchId: string | null) =>
  ['admin-branch-state', runId, branchId] as const

export const adminBranchCheckpointsQueryKey = (runId: string, branchId: string | null) =>
  ['admin-branch-checkpoints', runId, branchId] as const

export const adminBranchHeadQueryKey = (runId: string, branchId: string | null, checkpointId: string | null) =>
  ['admin-branch-head', runId, branchId, checkpointId] as const

export const adminHistoricalSeasonStateQueryKey = (runId: string, branchId: string | null, checkpointId: string | null) =>
  ['admin-historical-season-state', runId, branchId, checkpointId] as const
