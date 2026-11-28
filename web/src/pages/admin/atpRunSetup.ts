import { verifiedRunCalendar } from '../../api/runEditionEntryTiming'
import type { RunContainer } from '../../api/types'

export const ATP_EARTH_WORLD_ID = 'atp_earth'
export const ATP_CALENDAR_APPLY_PATH = '/admin/packages/atp-tour-calendar-reference'

export type ATPRunSetupTarget = { runId: string; branchId: string }

function exactId(value: unknown): value is string {
  return typeof value === 'string' && value.length > 0 && value.trim() === value
}

export function readATPRunSetupTarget(params: URLSearchParams): ATPRunSetupTarget | null {
  const [runId, ...otherRuns] = params.getAll('run')
  const [branchId, ...otherBranches] = params.getAll('branch')
  return exactId(runId) && exactId(branchId) && !otherRuns.length && !otherBranches.length
    ? { runId, branchId } : null
}

export function atpRunSetupLink(path: string, target: ATPRunSetupTarget): string {
  const params = new URLSearchParams({ run: target.runId, branch: target.branchId })
  return `${path}?${params}`
}

export function hasATPRunSetupCalendar(run: RunContainer): boolean {
  const clock = verifiedRunCalendar(run)
  return clock?.weeks_per_year === 52 && clock.season_start_year_week === 1
}

export function createdATPRunSetupLink(run: RunContainer): string | null {
  if (!hasATPRunSetupCalendar(run) || !exactId(run.viewer_branch_id)) return null
  return atpRunSetupLink(`/admin/packages/world/${ATP_EARTH_WORLD_ID}/apply`, {
    runId: run.run_id,
    branchId: run.viewer_branch_id,
  })
}
