import { useQuery } from '@tanstack/react-query'
import { getViewerOfficialRunContext, ApiError } from '../api/client'

export function useViewerOfficialRunContext(productRunId: string | null) {
  return useQuery({
    queryKey: ['viewer-official-run-context', productRunId],
    queryFn: () => getViewerOfficialRunContext(productRunId as string),
    enabled: Boolean(productRunId?.trim()),
    retry: (count, error) => !(error instanceof ApiError && (error.status === 404 || error.status === 409)) && count < 1,
    refetchOnWindowFocus: true,
    refetchInterval: 60_000
  })
}
