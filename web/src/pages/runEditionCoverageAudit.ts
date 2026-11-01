/** Bounded, read-only diagnostic of Entry preparation across one Run-owned
 * Calendar Package. Every Edition uses the existing authoritative GET; no
 * local sporting eligibility calculation, default ranking or Entry writer.
 */
import type { RunBranch, RunPackageStateResponse } from '../api/types'
import type { RunCalendarProjection, RunCalendarEvent } from '../api/runFirstTournament'
import type { EntryTimingInspection } from '../api/runEditionEntryTiming'
import { entryTimingScope, isHash } from '../api/runEditionEntryTiming'

export const ENTRY_COVERAGE_MAX_EDITIONS = 200
export const ENTRY_COVERAGE_CONCURRENCY = 4

export type EntryCoverageState =
  | 'no_plan' | 'missing_ranking' | 'configuration_ready' | 'bound'
  | 'blocked' | 'unsupported' | 'unavailable'

export type EditionCoverageRow = {
  event_id: string
  name: string
  week: number
  status: EntryCoverageState
  can_confirm_configuration: boolean
  ranking_binding_status: string | null
  blockers: { code: string; detail: string }[]
  source_fingerprint: string | null
  error: string | null
}

export type EditionCoverageReport = {
  format: 'run_edition_entry_coverage.v1'
  run_id: string
  branch_id: string
  saved_head_revision_id: string
  calendar_package_id: string
  calendar_fingerprint: string
  package_state_fingerprint: string
  season: string
  row_count: number
  rows: EditionCoverageRow[]
  counts: Record<EntryCoverageState, number>
  complete_reads: boolean
  all_plans_configured: boolean
  automatic_eligibility: 'not_implemented'
  authorizes_execution: false
  automatic_save: false
  evidence_scope: 'current_working_draft'
}

export type EditionCoverageReader = {
  branches: (runId: string) => Promise<{ run_branches: RunBranch[] }>
  packageState: (runId: string, branchId: string) => Promise<RunPackageStateResponse>
  calendar: (runId: string, branchId: string, packageId: string) => Promise<RunCalendarProjection>
  timing: (runId: string, branchId: string, packageId: string, eventId: string) => Promise<EntryTimingInspection>
}

const allStatuses: EntryCoverageState[] = [
  'no_plan','missing_ranking','configuration_ready','bound','blocked','unsupported','unavailable'
]

function requireHead(
  data: { run_branches: RunBranch[] }, runId: string, branchId: string, expected: string,
): void {
  if (!data || !Array.isArray(data.run_branches)) throw Error('Branch inventory is unavailable')
  const ids = new Set<string>()
  let found = false
  for (const b of data.run_branches) {
    if (!b || b.run_id !== runId || typeof b.branch_id !== 'string' || ids.has(b.branch_id))
      throw Error('Branch inventory is foreign or ambiguous')
    ids.add(b.branch_id)
    if (b.branch_id === branchId) {
      found = true
      if (b.saved_head_revision_id !== expected)
        throw Error('Selected Branch Saved HEAD changed; retry the Entry audit')
    }
  }
  if (!found) throw Error('Selected Branch no longer belongs to this Run')
}

function requirePackageState(
  value: RunPackageStateResponse, runId: string, branchId: string,
): string {
  if (!value || value.state?.run_id !== runId || value.state.branch_id !== branchId
      || !isHash(value.fingerprint)) throw Error('Run Package state is missing or foreign')
  return value.fingerprint
}

function validatedEvents(
  value: RunCalendarProjection, runId: string, branchId: string, packageId: string,
  stateHash: string, maxWeek: number
): RunCalendarEvent[] {
  if (!value || value.run_id !== runId || value.branch_id !== branchId
    || value.package_id !== packageId || value.run_package_state_fingerprint !== stateHash
    || !isHash(value.fingerprint) || !isHash(value.content_fingerprint)
    || value.calendar?.season !== value.season
    || !Array.isArray(value.calendar.events) || !Array.isArray(value.calendar.validation_errors)
    || value.calendar.validation_errors.length !== 0)
    throw Error('Calendar projection does not match the current Run-owned Package state')
  const seen = new Set<string>()
  const events = value.calendar.events
  if (events.length > ENTRY_COVERAGE_MAX_EDITIONS)
    throw Error('Too many Editions for one audit; narrow the Calendar Package first')
  for (const e of events) {
    if (!e || typeof e.event_id !== 'string' || !e.event_id.trim()
      || seen.has(e.event_id) || typeof e.event_name !== 'string'
      || !Number.isSafeInteger(e.season_week) || e.season_week < 1
      || e.season_week > maxWeek || String(e.season) !== value.season) {
      throw Error('Calendar contains duplicate, invalid or out-of-clock Editions')
    }
    seen.add(e.event_id)
  }
  return [...events].sort((a,b) => a.season_week - b.season_week
    || a.event_id.localeCompare(b.event_id))
}

function classifiedRow(
  raw: EntryTimingInspection, e: RunCalendarEvent, runId: string, branchId: string,
  packageId: string, expectedHead: string, stateHash: string
): EditionCoverageRow {
  if (!entryTimingScope(raw, runId, branchId, packageId, e.event_id))
    throw Error('Entry timing response has a foreign Run, Branch, Package or Edition')
  if (!Array.isArray(raw.blockers)
    || raw.blockers.some(b => !b || typeof b.code !== 'string'
      || typeof b.detail !== 'string')
    || raw.automatic_eligibility_status !== 'not_implemented')
    throw Error('Entry timing prerequisites or eligibility contract are malformed')
  if (raw.timing === null) {
    if (raw.preflight_status !== 'missing_content')
      throw Error('Missing Entry plan is not an applicable empty state')
    return {
      event_id: e.event_id, name: e.event_name, week: e.season_week,
      status: 'no_plan', can_confirm_configuration: false,
      ranking_binding_status: null, blockers: raw.blockers,
      source_fingerprint: null, error: null
    }
  }
  if (raw.saved_head_revision_id !== expectedHead || raw.state_fingerprint !== stateHash
    || !isHash(raw.preview_fingerprint) || !isHash(raw.edition_fingerprint))
    throw Error('Entry timing inspection refers to a different Saved HEAD or Package state')
  const status: EntryCoverageState = raw.preflight_status === 'unsupported_execution'
    ? 'unsupported' : raw.preflight_status === 'blocked' ? 'blocked'
    : raw.ranking_binding_status === 'bound' ? 'bound'
    : raw.ranking_binding_status === 'ready_for_explicit_confirmation'
      ? 'configuration_ready' : 'missing_ranking'
  return {
    event_id: e.event_id, name: e.event_name, week: e.season_week,
    status, can_confirm_configuration: raw.can_confirm_configuration,
    ranking_binding_status: raw.ranking_binding_status,
    blockers: raw.blockers, source_fingerprint: raw.preview_fingerprint, error: null
  }
}

function errorRow(e: RunCalendarEvent, error: unknown): EditionCoverageRow {
  return {
    event_id: e.event_id, name: e.event_name, week: e.season_week,
    status: 'unavailable', can_confirm_configuration: false,
    ranking_binding_status: null, blockers: [], source_fingerprint: null,
    error: error instanceof Error ? error.message : 'Entry read failed'
  }
}

/** Reads 80 FAX Editions with a fixed four-request upper bound, and then
 * revalidates Package/Calendar/HEAD so changes during the read cannot become
 * a synthetic "green" report. Per-Edition errors remain visible as Unknown.
 */
export async function inspectRunEditionCoverage(
  reader: EditionCoverageReader,
  runId: string, branchId: string, head: string, packageId: string, maxWeek: number,
): Promise<EditionCoverageReport> {
  if (!runId || !branchId || !head || !packageId
    || !Number.isSafeInteger(maxWeek) || maxWeek < 1)
    throw Error('Select a Run, Branch, Saved HEAD and explicit Run calendar')
  const [beforeBranches, beforeState] = await Promise.all([
    reader.branches(runId), reader.packageState(runId, branchId)
  ])
  requireHead(beforeBranches, runId, branchId, head)
  const stateHash = requirePackageState(beforeState, runId, branchId)
  const initialCalendar = await reader.calendar(runId, branchId, packageId)
  const events = validatedEvents(initialCalendar,runId,branchId,packageId,stateHash,maxWeek)
  const rows: EditionCoverageRow[] = new Array(events.length)
  let offset = 0
  const workers = Array.from({ length: Math.min(ENTRY_COVERAGE_CONCURRENCY,events.length) }, async () => {
    while (offset < events.length) {
      const index = offset++
      const event = events[index]
      try {
        rows[index] = classifiedRow(
          await reader.timing(runId,branchId,packageId,event.event_id),
          event,runId,branchId,packageId,head,stateHash
        )
      } catch(e) {
        rows[index] = errorRow(event,e)
      }
    }
  })
  await Promise.all(workers)
  const [afterState, afterCalendar, afterBranches] = await Promise.all([
    reader.packageState(runId,branchId),
    reader.calendar(runId,branchId,packageId),
    reader.branches(runId)
  ])
  requireHead(afterBranches,runId,branchId,head)
  if (requirePackageState(afterState,runId,branchId) !== stateHash
    || afterCalendar.fingerprint !== initialCalendar.fingerprint
    || afterCalendar.content_fingerprint !== initialCalendar.content_fingerprint
    || afterCalendar.run_package_state_fingerprint !== stateHash
    || validatedEvents(afterCalendar,runId,branchId,packageId,stateHash,maxWeek)
       .map(e=>e.event_id).join('\0') !== events.map(e=>e.event_id).join('\0'))
    throw Error('Calendar or Working Draft changed during the Entry audit; retry')
  const counts = Object.fromEntries(allStatuses.map(status => [
    status, rows.filter(r=>r.status===status).length
  ])) as Record<EntryCoverageState,number>
  return {
    format:'run_edition_entry_coverage.v1',run_id:runId,branch_id:branchId,
    saved_head_revision_id:head,calendar_package_id:packageId,
    calendar_fingerprint:initialCalendar.fingerprint,
    package_state_fingerprint:stateHash,season:initialCalendar.season,
    row_count:events.length,rows,counts,
    complete_reads:counts.unavailable===0,
    all_plans_configured:counts.no_plan===0&&counts.unavailable===0,
    automatic_eligibility:'not_implemented',authorizes_execution:false,
    automatic_save:false,evidence_scope:'current_working_draft'
  }
}
