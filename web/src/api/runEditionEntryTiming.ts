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
function isValidRunCalendarMetadata(value: unknown): value is RunCalendarMetadata {
  if (!value || typeof value !== 'object' || Array.isArray(value)) return false
  const c = value as Record<string, unknown>
  return Object.keys(c).sort().join(',') ===
    ['schema_version', 'weeks_per_year', 'season_start_year_week', 'start_year', 'season_count'].sort().join(',') &&
    c.schema_version === 'run_calendar.v1' &&
    Number.isSafeInteger(c.weeks_per_year) && (c.weeks_per_year as number) >= 1 &&
    Number.isSafeInteger(c.season_start_year_week) &&
    (c.season_start_year_week as number) >= 1 &&
    (c.season_start_year_week as number) <= (c.weeks_per_year as number) &&
    Number.isSafeInteger(c.start_year) && (c.start_year as number) >= 0 &&
    Number.isSafeInteger(c.season_count) && (c.season_count as number) >= 1
}

export function verifiedRunCalendar(run: RunContainer | null | undefined): RunCalendarMetadata | null {
  if (!run || !run.metadata_json || !Object.prototype.hasOwnProperty.call(run.metadata_json, 'run_calendar')) return null
  const value = run.metadata_json.run_calendar
  return isValidRunCalendarMetadata(value) ? value : null
}

export function sameClock(a: RunCalendarMetadata, b: RunCalendarMetadata): boolean {
  return a.schema_version === b.schema_version && a.weeks_per_year === b.weeks_per_year &&
    a.season_start_year_week === b.season_start_year_week &&
    a.start_year === b.start_year && a.season_count === b.season_count
}
export function sameWeek(a: EntryWeek | null, b: EntryWeek | null): boolean {
  return a === null || b === null ? a === b :
    a.season_index === b.season_index && a.week === b.week && sameClock(a.calendar, b.calendar)
}
export function sameTiming(a: EditionEntryTiming | null, b: EditionEntryTiming | null): boolean {
  return a === null || b === null ? a === b :
    a.schema_version === b.schema_version &&
    sameWeek(a.main_open, b.main_open) &&
    a.main_duration_weeks === b.main_duration_weeks &&
    a.qualification_duration_weeks === b.qualification_duration_weeks &&
    sameWeek(a.final_commitment, b.final_commitment) &&
    sameWeek(a.ranking_publication_override, b.ranking_publication_override)
}
export function weekInClock(position: EntryWeek | null, clock: RunCalendarMetadata): boolean {
  return position !== null &&
    sameClock(position.calendar, clock) &&
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
/** Check network DTOs before passing nested timing/window values to React. */
function validTiming(value: EditionEntryTiming | null | undefined): value is EditionEntryTiming {
  if (!value || !isValidRunCalendarMetadata(value.main_open?.calendar) ||
    value.schema_version !== 'edition_entry_timing.v1') return false
  const clock = value.main_open.calendar
  const optionalWeek = (week: EntryWeek | null | undefined) =>
    week === null || (week !== undefined && validWeek(week, clock))
  return validWeek(value.main_open, clock) &&
    Number.isSafeInteger(value.main_duration_weeks) && value.main_duration_weeks > 0 &&
    Number.isSafeInteger(value.qualification_duration_weeks) && value.qualification_duration_weeks > 0 &&
    optionalWeek(value.final_commitment) && optionalWeek(value.ranking_publication_override)
}

function validWeek(value: EntryWeek | null | undefined, clock: RunCalendarMetadata): boolean {
  return Boolean(value && typeof value === 'object' &&
    isValidRunCalendarMetadata(value.calendar) && weekInClock(value, clock))
}

export function validEntryTimingInspection(
  value: EntryTimingInspection, run: string, branch: string, pkg: string, edition: string
): boolean {
  if (!entryTimingScope(value, run, branch, pkg, edition) ||
    !Array.isArray(value.blockers) ||
    !value.blockers.every(b => b != null && typeof b.code === 'string' && typeof b.detail === 'string') ||
    value.automatic_eligibility_status !== 'not_implemented') return false
  if (value.timing === null) return value.preflight_status === 'missing_content'
  const data = value as EntryTimingPreview
  if (!validTiming(data.timing) || !data.resolved || typeof data.resolved !== 'object') return false
  const clock = data.timing.main_open.calendar
  const nullableWeek = (week: EntryWeek | null | undefined) =>
    week === null || (week !== undefined && validWeek(week, clock))
  return data.schema_version === 'run_edition_entry_timing_preview.v1' &&
    data.configuration_state === 'working_draft' &&
    Number.isSafeInteger(data.draft_version) && data.draft_version >= 0 &&
    typeof data.saved_head_revision_id === 'string' &&
    isHash(data.preview_fingerprint) && isHash(data.state_fingerprint) &&
    isHash(data.edition_fingerprint) &&
    validWeek(data.resolved.main_open, clock) &&
    sameWeek(data.resolved.main_open, data.timing.main_open) &&
    validWeek(data.resolved.main_close, clock) &&
    validWeek(data.resolved.qualification_open, clock) &&
    validWeek(data.resolved.qualification_close, clock) &&
    validWeek(data.resolved.final_commitment, clock) &&
    nullableWeek(data.resolved.default_ranking_completed_week) &&
    nullableWeek(data.resolved.ranking_publication_week) &&
    nullableWeek(data.current_week) &&
    (data.before === null || validTiming(data.before)) &&
    (data.ranking_snapshot_fingerprint === null || isHash(data.ranking_snapshot_fingerprint)) &&
    (data.ranking_authority_fingerprint === null || isHash(data.ranking_authority_fingerprint)) &&
    ['missing_prerequisite', 'ready_for_explicit_confirmation', 'bound'].includes(data.ranking_binding_status) &&
    ['missing_content', 'blocked', 'ready', 'unsupported_execution'].includes(data.preflight_status) &&
    ['after_main_closing_minus_one', 'explicit_publication_override'].includes(data.resolved.ranking_source) &&
    typeof data.can_confirm_configuration === 'boolean'
}
