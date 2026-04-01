export function getFinalsInspectionRoute({
  runId,
  hasQualification,
  hasResult
}: {
  runId: string
  hasQualification: boolean
  hasResult: boolean
}): string {
  if (hasResult) {
    return `/runs/${runId}/finals/result`
  }
  if (hasQualification) {
    return `/runs/${runId}/finals/qualification`
  }
  return `/runs/${runId}/finals`
}
