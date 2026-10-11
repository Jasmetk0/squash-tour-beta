import { useQuery } from '@tanstack/react-query'

import { getAdminBranchCheckpointSeasonState } from '../api/client'
import { useOptionalAdminTime } from './AdminTimeContext'
import { adminHistoricalSeasonStateQueryKey } from './adminQueryKeys'

export function useAdminViewedSeasonState() {
  const context = useOptionalAdminTime()
  const time = context ?? { runId: '', branchId: null, viewCheckpointId: null, mode: 'present' as const }
  const historical = time.mode === 'checkpoint'
  const query = useQuery({
    queryKey: adminHistoricalSeasonStateQueryKey(time.runId, time.branchId, time.viewCheckpointId),
    queryFn: () => getAdminBranchCheckpointSeasonState(time.runId, time.branchId!, time.viewCheckpointId!),
    enabled: historical && Boolean(time.runId && time.branchId && time.viewCheckpointId),
    retry: false,
  })
  const unavailable = historical && Boolean(query.error && typeof query.error === 'object' && 'status' in query.error && query.error.status === 409)
  const failed = historical && Boolean(query.error) && !unavailable
  return { time: context, historical, query, seasonState: query.data?.season_state ?? null, unavailable, failed }
}
