export function getFinalsInspectionRoute({
  runId,
  hasQualification,
  hasResult
}: {
  runId: string
  hasQualification: boolean
  hasResult: boolean
}): string {
  // Treat the Run ID as one route segment even if it contains reserved characters.
  const encodedRunId = encodeURIComponent(runId)
  if (hasResult) {
    return `/runs/${encodedRunId}/finals/result`
  }
  if (hasQualification) {
    return `/runs/${encodedRunId}/finals/qualification`
  }
  return `/runs/${encodedRunId}/finals`
}
