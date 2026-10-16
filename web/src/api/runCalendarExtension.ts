import type { RunCalendarMetadata } from './runCalendarCreation'

export type CalendarExtensionBranchReview = {
  branch_id: string
  display_name: string
  saved_head_revision_id: string | null
  saved_head_content_hash: string | null
  draft_version: number | null
  blockers: string[]
}

export type CalendarExtensionReview = {
  schema_version: 'run_calendar_extension_review.v1'
  run_id: string
  read_only: true
  save_performed: false
  simulation_started: false
  review_fingerprint: string
  can_save: boolean
  blockers: string[]
  branch_count: number
  branches: CalendarExtensionBranchReview[]
  original_calendar: RunCalendarMetadata
  proposed_calendar: RunCalendarMetadata
  added_seasons: number
  added_weeks: number
  frozen_task_count: number
  sporting_execution_unlocked: false
}

export type CalendarExtensionSaveRequest = {
  command_id: string
  new_season_count: number
  review_fingerprint: string
  explicit_confirmation: true
}

export type CalendarExtensionReceipt = {
  schema_version: 'run_calendar_extension_save.v1'
  run_id: string
  command_id: string
  review_fingerprint: string
  saved: true
  simulation_started: false
  sporting_execution_unlocked: false
  previous_calendar: RunCalendarMetadata
  current_calendar: RunCalendarMetadata
  branch_count: number
  branches: {
    branch_id: string
    previous_saved_head_revision_id: string
    saved_revision_id: string
    saved_revision_content_hash: string
    audit_event_id: string
    draft_version: number
  }[]
}

export function validateCalendarExtensionReview(
  raw: unknown, runId: string, newCount: number
): CalendarExtensionReview {
  const r = raw as CalendarExtensionReview
  if (!r || r.schema_version !== 'run_calendar_extension_review.v1'
    || r.run_id !== runId || r.read_only !== true
    || r.save_performed !== false || r.simulation_started !== false
    || !/^[0-9a-f]{64}$/.test(r.review_fingerprint)
    || typeof r.can_save !== 'boolean'
    || !Array.isArray(r.blockers)
    || !Array.isArray(r.branches)
    || r.branches.length !== r.branch_count
    || r.branches.some(b => !b.branch_id || !Array.isArray(b.blockers))
    || !r.original_calendar || !r.proposed_calendar
    || r.proposed_calendar.season_count !== newCount
    || r.added_seasons !== newCount - r.original_calendar.season_count
    || r.added_seasons <= 0
    || r.added_weeks !== r.added_seasons * r.original_calendar.weeks_per_year
    || r.original_calendar.weeks_per_year !== r.proposed_calendar.weeks_per_year
    || r.original_calendar.start_year !== r.proposed_calendar.start_year
    || r.original_calendar.season_start_year_week !== r.proposed_calendar.season_start_year_week
    || r.sporting_execution_unlocked !== false) {
    throw Error('Invalid reviewed Run calendar extension evidence')
  }
  return r
}

export function validateCalendarExtensionReceipt(
  raw: unknown, runId: string, payload: CalendarExtensionSaveRequest,
): CalendarExtensionReceipt {
  const r = raw as CalendarExtensionReceipt
  if (!r || r.schema_version !== 'run_calendar_extension_save.v1'
    || r.run_id !== runId || r.command_id !== payload.command_id
    || r.review_fingerprint !== payload.review_fingerprint
    || r.saved !== true || r.simulation_started !== false
    || r.sporting_execution_unlocked !== false
    || !r.current_calendar || r.current_calendar.season_count !== payload.new_season_count
    || !Array.isArray(r.branches) || r.branch_count !== r.branches.length
    || r.branches.some(b => !b.saved_revision_id || !b.audit_event_id)) {
    throw Error('Invalid Run calendar extension Save receipt')
  }
  return r
}
