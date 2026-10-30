import type { RunCalendarMetadata } from './runCalendarCreation'
import type { RunContainer } from './types'

/** These DTOs reflect the merged #1675 contract; no frontend sporting calculation. */
export type EntryWeek = {
  calendar: RunCalendarMetadata
  season_index: number
  week: number
}
export type EditionEntryTiming = {
  schema_version: 'edition_entry_timing.v1'
  main_open: EntryWeek
  main_duration_weeks: number
  qualification_duration_weeks: number
  final_commitment: EntryWeek | null
  ranking_publication_override: EntryWeek | null
}
export type EntryTimingBlocker = { code: string; detail: string }
export type EntryTimingMissing = {
  run_id: string
  branch_id: string
  package_id: string
  event_id: string
  timing: null
  preflight_status: 'missing_content'
  blockers: EntryTimingBlocker[]
  automatic_eligibility_status: 'not_implemented'
}
export type EntryTimingPreview = {
  schema_version: 'run_edition_entry_timing_preview.v1'
  run_id: string
  branch_id: string
  package_id: string
  event_id: string
  saved_head_revision_id: string
  draft_version: number
  state_fingerprint: string
  edition_fingerprint: string
  timing: EditionEntryTiming
  before: EditionEntryTiming | null
  resolved: {
    main_open: EntryWeek
    main_close: EntryWeek
    qualification_open: EntryWeek
    qualification_close: EntryWeek
    final_commitment: EntryWeek
    default_ranking_completed_week: EntryWeek | null
    ranking_publication_week: EntryWeek | null
    ranking_source: 'explicit_publication_override' | 'after_main_closing_minus_one'
  }
  current_week: EntryWeek | null
  current_window: 'not_open' | 'main' | 'qualification' | 'all_entries_closed' | null
  ranking_snapshot_fingerprint: string | null
  ranking_authority_fingerprint: string | null
  ranking_will_be_bound: boolean
  ranking_binding_status: 'missing_prerequisite' | 'ready_for_explicit_confirmation' | 'bound'
  configuration_state: 'working_draft'
  timing_and_ranking_ready: boolean
  preflight_status: 'unsupported_execution' | 'blocked' | 'missing_content' | 'ready'
  automatic_eligibility_status: 'not_implemented'
  can_confirm_configuration: boolean
  blockers: EntryTimingBlocker[]
  preview_fingerprint: string
}
export type EntryTimingInspection = EntryTimingMissing | EntryTimingPreview
export type EntryTimingConfirmPayload = {
  timing: EditionEntryTiming
  command_id: string
  expected_preview_fingerprint: string
  operator_label: string
  audit_reason: string
}
export type EntryTimingReceipt = {
  command_id: string
  request_fingerprint: string
  request: { kind: 'run_edition_entry_timing.v1'; run_id: string; branch_id: string; package_id: string; event_id: string; timing: EditionEntryTiming; expected_preview_fingerprint: string; operator_label: string; audit_reason: string }
  preview: EntryTimingPreview
  draft_version: number
  state_fingerprint: string
  state: { run_id: string; branch_id: string; [key: string]: unknown }
  ranking_authority_fingerprint: string | null
  already_applied: boolean
  receipt_fingerprint: string
}

export const isHash = (value: unknown): value is string =>
  typeof value === 'string' && /^[0-9a-f]{64}$/.test(value)

/** Never synthesize a FAX/61 calendar when persisted metadata is missing or corrupt. */
export function verifiedRunCalendar(run: RunContainer | null | undefined): RunCalendarMetadata | null {
  if (!run || !run.metadata_json || !Object.prototype.hasOwnProperty.call(run.metadata_json, 'run_calendar')) return null
  const value = run.metadata_json.run_calendar
  if (!value || typeof value !== 'object' || Array.isArray(value)) return null
  const c = value as Record<string, unknown>
  if (Object.keys(c).sort().join(',') !==
    ['schema_version', 'weeks_per_year', 'season_start_year_week', 'start_year', 'season_count'].sort().join(',') ||
    c.schema_version !== 'run_calendar.v1' ||
    !Number.isSafeInteger(c.weeks_per_year) || (c.weeks_per_year as number) < 1 ||
    !Number.isSafeInteger(c.season_start_year_week) ||
    (c.season_start_year_week as number) < 1 || (c.season_start_year_week as number) > (c.weeks_per_year as number) ||
    !Number.isSafeInteger(c.start_year) || (c.start_year as number) < 0 ||
    !Number.isSafeInteger(c.season_count) || (c.season_count as number) < 1) return null
  return c as RunCalendarMetadata
}

export function weekInClock(position: EntryWeek | null, clock: RunCalendarMetadata): boolean {
  return position !== null &&
    JSON.stringify(position.calendar) === JSON.stringify(clock) &&
    Number.isSafeInteger(position.season_index) &&
    position.season_index >= 0 && position.season_index < clock.season_count &&
    Number.isSafeInteger(position.week) && position.week >= 1 && position.week <= clock.weeks_per_year
}

export function entryTimingScope(
  value: { run_id: string; branch_id: string; package_id: string; event_id: string },
  run: string, branch: string, pkg: string, edition: string
): boolean {
  return value?.run_id === run && value.branch_id === branch &&
    value.package_id === pkg && value.event_id === edition
}
export function validEntryTimingInspection(
  value: EntryTimingInspection, run: string, branch: string, pkg: string, edition: string
): boolean {
  if (!entryTimingScope(value, run, branch, pkg, edition) ||
    !Array.isArray(value.blockers) || value.automatic_eligibility_status !== 'not_implemented') return false
  if (value.timing === null) return value.preflight_status === 'missing_content'
  return value.schema_version === 'run_edition_entry_timing_preview.v1' &&
    value.configuration_state === 'working_draft' &&
    isHash(value.preview_fingerprint) && isHash(value.state_fingerprint) &&
    isHash(value.edition_fingerprint) &&
    typeof value.can_confirm_configuration === 'boolean'
}
