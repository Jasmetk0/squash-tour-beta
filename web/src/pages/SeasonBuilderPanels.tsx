import { Link } from 'react-router-dom'

import type {
  SeasonBuilderApplyCommandContractRequest,
  SeasonBuilderApplyCommandContractResponse,
  SeasonBuilderApplyCreateOnlyCommandResponse,
  SeasonBuilderApplyCreateOnlyReadinessResponse,
  SeasonBuilderDryRunBuildRequest,
  SeasonBuilderDryRunBuildResponse,
  SeasonBuilderPreflightRequest,
  SeasonBuilderPreflightResponse,
  SeasonCalendarBuildResponse,
  SeasonCalendarValidationResponse,
  SeasonCalendarValidationIssueCodeRegistryResponse,
  SeasonRegistryEntry,
  SeasonTemplateSlotValidationIssueCodeRegistryResponse,
  SeasonTemplateSlotConflictCodeRegistryResponse,
  SeasonTemplateSlotConflictPreview,
  SeasonTemplateSlotConflictReportResponse,
  SeasonTemplateSlotValidationPreview,
  SeasonTemplateSlotValidationResponse,
  SeasonTemplateSummary,
  TourSeasonsValidationResponse
} from '../api/types'
import { safeToLongSeasonLabel } from '../utils/seasonLabels'
import { formatApiError } from '../utils/apiErrors'

export type SourceType = 'season_template' | 'blank_calendar_planned' | 'another_season_planned' | 'custom_slot_planned'

export const SOURCE_TYPE_OPTIONS: Array<{ value: SourceType; label: string }> = [
  { value: 'season_template', label: 'Season template' },
  { value: 'blank_calendar_planned', label: 'Blank calendar (planned)' },
  { value: 'another_season_planned', label: 'Another season (planned)' },
  { value: 'custom_slot_planned', label: 'Custom slot (planned)' }
]

export type TemplatePreview = {
  slotsWithinSw61: boolean
  qualificationSlotsCount: number
  earliestSlot: number | null
  latestSlot: number | null
}

function formatOptionalList(values?: string[]): string {
  if (!values || values.length === 0) return '—'
  return values.join(', ')
}


export type TemplateValidationStatus = 'OK' | 'Info' | 'Warning'

export type TemplateValidationItem = {
  area: string
  status: TemplateValidationStatus
  message: string
}

export type BuildPolicyStatus = 'OK' | 'Info' | 'Warning' | 'BlockedUntilExplicitChoice'

export type BuildPolicyItem = {
  area: string
  status: BuildPolicyStatus
  message: string
}

export type PreflightSummaryStatus = 'OK' | 'Info' | 'Warning' | 'Blocked'

export type PreflightSummaryItem = {
  area: string
  status: PreflightSummaryStatus
  message: string
}

export type SourceTargetDiffStatus = 'OK' | 'Info' | 'Warning' | 'Blocked'

export type SourceTargetDiffItem = {
  area: string
  status: SourceTargetDiffStatus
  source: string
  target: string
  message: string
}

export type BackendPreflightContractItem = {
  area: string
  required: string
  reason: string
}

export type FutureBuildCommandContractItem = {
  area: string
  required: string
  reason: string
}

export type FutureCommandReadinessStatus = 'OK' | 'Missing' | 'Blocked' | 'Info'

export type FutureCommandReadinessItem = {
  area: string
  status: FutureCommandReadinessStatus
  message: string
}

export type DisabledDryRunReadinessStatus = 'OK' | 'Info' | 'Blocked' | 'Missing'

export type DisabledDryRunReadinessItem = {
  area: string
  status: DisabledDryRunReadinessStatus
  message: string
}

export type ApplyCommandReadinessStatus = 'OK' | 'Info' | 'Blocked' | 'Missing'

export type ApplyCommandReadinessItem = {
  area: string
  status: ApplyCommandReadinessStatus
  message: string
}
export type CreateOnlyApplyGuardSummaryItem = {
  key: string
  label: string
  passed: boolean
  detail?: string
}

type BuildSourceTargetDiffDetailItemsArgs = {
  selectedTargetSeason: SeasonRegistryEntry | null
  selectedSourceType: SourceType
  selectedTemplate: SeasonTemplateSummary | null
  selectedTemplatePreview: TemplatePreview | null
  targetCalendarData: SeasonCalendarBuildResponse | undefined
  targetCalendarExists: boolean | null
}

export function buildSourceTargetDiffDetailItems({
  selectedTargetSeason,
  selectedSourceType,
  selectedTemplate,
  selectedTemplatePreview,
  targetCalendarData,
  targetCalendarExists
}: BuildSourceTargetDiffDetailItemsArgs): SourceTargetDiffItem[] {
  const sourceTypeLabel = SOURCE_TYPE_OPTIONS.find((option) => option.value === selectedSourceType)?.label ?? selectedSourceType
  const targetSeasonLabel = selectedTargetSeason?.label ?? 'No target selected'
  const templateSlotCount = selectedTemplate ? (selectedTemplate.slot_count ?? selectedTemplate.slots.length) : null
  const targetSummary = targetCalendarData?.summary
  const sourceRange = selectedTemplatePreview?.earliestSlot !== null && selectedTemplatePreview?.earliestSlot !== undefined &&
    selectedTemplatePreview?.latestSlot !== null && selectedTemplatePreview?.latestSlot !== undefined
    ? `SW${selectedTemplatePreview.earliestSlot}–SW${selectedTemplatePreview.latestSlot}`
    : 'Unknown'
  const targetRange = targetSummary?.first_event_week !== null && targetSummary?.first_event_week !== undefined &&
    targetSummary?.last_event_week !== null && targetSummary?.last_event_week !== undefined
    ? `SW${targetSummary.first_event_week}–SW${targetSummary.last_event_week}`
    : 'Unknown'

  const items: SourceTargetDiffItem[] = [
    selectedSourceType === 'season_template'
      ? {
          area: 'Source executability',
          status: 'OK',
          source: sourceTypeLabel,
          target: targetSeasonLabel,
          message: 'Season template source can be inspected locally.'
        }
      : {
          area: 'Source executability',
          status: 'Blocked',
          source: sourceTypeLabel,
          target: targetSeasonLabel,
          message: 'Planned source type cannot produce a concrete diff yet.'
        }
  ]

  const sourceWeekCount = selectedTemplate?.week_count
  const targetWeekCount = selectedTargetSeason?.week_count
  items.push(
    sourceWeekCount !== undefined && targetWeekCount !== undefined
      ? sourceWeekCount === targetWeekCount
        ? {
            area: 'Week count',
            status: 'OK',
            source: String(sourceWeekCount),
            target: String(targetWeekCount),
            message: 'Target and template week counts match.'
          }
        : {
            area: 'Week count',
            status: 'Warning',
            source: String(sourceWeekCount),
            target: String(targetWeekCount),
            message: 'Target and template week counts differ.'
          }
      : {
          area: 'Week count',
          status: 'Info',
          source: sourceWeekCount === undefined ? 'Unknown' : String(sourceWeekCount),
          target: targetWeekCount === undefined ? 'Unknown' : String(targetWeekCount),
          message: 'Week count comparison is unavailable from current local data.'
        }
  )

  items.push({
    area: 'Template slot count vs target event count',
    status: 'Info',
    source: templateSlotCount === null ? 'Unknown' : String(templateSlotCount),
    target: targetSummary?.event_count === undefined ? 'Unknown' : String(targetSummary.event_count),
    message: 'Slot count and existing event count are structural indicators only; they are not a final diff.'
  })

  items.push({
    area: 'Source slot range vs target event range',
    status: sourceRange !== 'Unknown' && targetRange !== 'Unknown' ? 'OK' : 'Info',
    source: sourceRange,
    target: targetRange,
    message: 'Range comparison is structural only and does not represent a concrete event-by-event diff.'
  })

  items.push(
    targetCalendarExists === true
      ? {
          area: 'Calendar conflict state',
          status: 'Warning',
          source: 'Selected source',
          target: 'Existing target calendar',
          message: 'Existing target calendar requires future authoritative backend diff before any overwrite/merge command.'
        }
      : targetCalendarExists === false
        ? {
            area: 'Calendar conflict state',
            status: 'OK',
            source: 'Selected source',
            target: 'Empty target calendar',
            message: 'Empty target has no existing concrete events to compare locally, but future backend validation is still required.'
          }
        : {
            area: 'Calendar conflict state',
            status: 'Info',
            source: 'Selected source',
            target: 'Unavailable target state',
            message: 'Target calendar state is unavailable, so conflict state cannot be determined.'
          }
  )

  items.push({
    area: 'Validation authority',
    status: 'Info',
    source: 'Local UI',
    target: 'Backend preflight',
    message: 'Local diff detail is advisory only and must not replace authoritative backend validation.'
  })

  return items
}

type BuildSourceTargetPreflightSummaryItemsArgs = {
  selectedTargetSeason: SeasonRegistryEntry | null
  selectedSourceType: SourceType
  selectedTemplate: SeasonTemplateSummary | null
  selectedTemplatePreview: TemplatePreview | null
  targetCalendarExists: boolean | null
}

export function buildSourceTargetPreflightSummaryItems({
  selectedTargetSeason,
  selectedSourceType,
  selectedTemplate,
  selectedTemplatePreview,
  targetCalendarExists
}: BuildSourceTargetPreflightSummaryItemsArgs): PreflightSummaryItem[] {
  const items: PreflightSummaryItem[] = [
    selectedTargetSeason
      ? { area: 'Target selection', status: 'OK', message: 'Target season selected.' }
      : { area: 'Target selection', status: 'Warning', message: 'Target season is not selected.' }
  ]

  items.push(
    targetCalendarExists === true
      ? { area: 'Target calendar state', status: 'Warning', message: 'Existing calendar detected.' }
      : targetCalendarExists === false
        ? { area: 'Target calendar state', status: 'OK', message: 'No existing calendar detected.' }
        : { area: 'Target calendar state', status: 'Info', message: 'Target calendar state is unknown/unavailable/loading.' }
  )

  const plannedSourceTypeSelected = selectedSourceType !== 'season_template'
  items.push(
    plannedSourceTypeSelected
      ? { area: 'Source type', status: 'Blocked', message: 'Planned source type selected; this source type is not executable yet.' }
      : { area: 'Source type', status: 'OK', message: 'Season template source selected.' }
  )

  if (plannedSourceTypeSelected) {
    items.push({ area: 'Source template', status: 'Blocked', message: 'Source template selection is not executable for planned source types yet.' })
  } else {
    items.push(
      selectedTemplate
        ? { area: 'Source template', status: 'OK', message: 'Template selected for preview.' }
        : { area: 'Source template', status: 'Warning', message: 'Template is required for season template source preview.' }
    )
  }

  if (selectedTargetSeason && selectedTemplate) {
    items.push(
      selectedTargetSeason.week_count === selectedTemplate.week_count
        ? { area: 'Week count compatibility', status: 'OK', message: 'Target and template week_count match.' }
        : { area: 'Week count compatibility', status: 'Warning', message: `Target week_count (${selectedTargetSeason.week_count}) does not match template week_count (${selectedTemplate.week_count}).` }
    )
  } else {
    items.push({ area: 'Week count compatibility', status: 'Info', message: 'Week count compatibility cannot be determined from current local data.' })
  }

  if (selectedTemplatePreview) {
    items.push(
      selectedTemplatePreview.slotsWithinSw61
        ? { area: 'Slot range', status: 'OK', message: 'Template preview indicates slots are within SW1–SW61.' }
        : { area: 'Slot range', status: 'Warning', message: 'Template preview indicates one or more slots are outside SW1–SW61.' }
    )
  } else {
    items.push({ area: 'Slot range', status: 'Info', message: 'Slot range status is unavailable from current local data.' })
  }

  items.push(
    targetCalendarExists === true
      ? { area: 'Overwrite/merge policy', status: 'Blocked', message: 'Existing target calendar requires explicit audited overwrite/merge choice before any future build.' }
      : targetCalendarExists === false
        ? { area: 'Overwrite/merge policy', status: 'OK', message: 'Empty target calendar detected; future creation would still require an explicit audited backend command.' }
        : { area: 'Overwrite/merge policy', status: 'Info', message: 'Target calendar state is unavailable, so no safe future build policy can be finalized.' }
  )

  items.push({ area: 'Next safe step', status: 'Info', message: 'Review read-only diff and backend validation before any future command.' })

  return items
}

export function buildBackendPreflightContractItems(): BackendPreflightContractItem[] {
  return [
    {
      area: 'Request target season',
      required: 'target_season_label',
      reason: 'Backend must know the concrete season that would be inspected before any future build command.'
    },
    {
      area: 'Request source type',
      required: 'source_type',
      reason: 'Backend must distinguish season template, copied season, blank calendar, and custom-slot workflows.'
    },
    {
      area: 'Request source reference',
      required: 'source_template_id or future source identifier',
      reason: 'Backend must resolve the selected source deterministically before comparing it to the target.'
    },
    {
      area: 'Existing calendar policy',
      required: 'overwrite_policy',
      reason: 'Existing target calendars must never be overwritten silently.'
    },
    {
      area: 'Audit identity',
      required: 'requested_by / admin actor',
      reason: 'Future preflight/build workflows must be attributable and reviewable.'
    },
    {
      area: 'Determinism metadata',
      required: 'seed / version / template hash',
      reason: 'Future build output must be reproducible and comparable.'
    },
    {
      area: 'Response blocking status',
      required: 'can_build: false until authoritative validation passes',
      reason: 'UI must never infer build readiness from local-only checks.'
    },
    {
      area: 'Response diff summary',
      required: 'authoritative_diff_summary',
      reason: 'Backend must provide event-level conflicts, additions, replacements, and validation errors.'
    },
    {
      area: 'Response warnings/errors',
      required: 'validation_warnings and validation_errors',
      reason: 'Backend must separate advisory warnings from blocking errors.'
    },
    {
      area: 'Response audit preview',
      required: 'audit_preview',
      reason: 'Admin must see what would be recorded before any future mutation command.'
    }
  ]
}

export function buildOverwriteMergePolicyItems(targetCalendarExists: boolean | null): BuildPolicyItem[] {
  const targetCalendarStateItem: BuildPolicyItem =
    targetCalendarExists === true
      ? { area: 'Target calendar state', status: 'Warning', message: 'Existing calendar detected.' }
      : targetCalendarExists === false
        ? { area: 'Target calendar state', status: 'OK', message: 'No existing calendar detected.' }
        : { area: 'Target calendar state', status: 'Info', message: 'Existing calendar state is unknown/unavailable.' }

  const mergePolicyItem: BuildPolicyItem =
    targetCalendarExists === true
      ? { area: 'Merge policy', status: 'BlockedUntilExplicitChoice', message: 'Merge/replace choice must be explicit and audited before any future command.' }
      : targetCalendarExists === false
        ? { area: 'Merge policy', status: 'Info', message: 'Merge policy is not needed for an empty target, but future command still requires audit.' }
        : { area: 'Merge policy', status: 'Info', message: 'Policy cannot be resolved until calendar state is known.' }

  return [
    targetCalendarStateItem,
    { area: 'Silent overwrite policy', status: 'BlockedUntilExplicitChoice', message: 'Silent overwrite must never be allowed.' },
    mergePolicyItem,
    { area: 'Audit policy', status: 'Info', message: 'Future build command must be explicit, audited, and reviewable.' }
  ]
}

export function buildTemplateValidationItems(template: SeasonTemplateSummary | null): TemplateValidationItem[] {
  if (!template) {
    return [{ area: 'Template selected', status: 'Warning', message: 'No template selected.' }]
  }

  const items: TemplateValidationItem[] = [{ area: 'Template selected', status: 'OK', message: 'Template selected.' }]

  const slots = template.slots
  if (!slots.length) {
    items.push({ area: 'Slot count', status: 'Warning', message: 'Template has no slots.' })
  } else if (template.slot_count !== slots.length) {
    items.push({ area: 'Slot count', status: 'Warning', message: `Template slot_count (${template.slot_count}) differs from payload slots length (${slots.length}).` })
  } else if (template.slot_count > 0) {
    items.push({ area: 'Slot count', status: 'OK', message: 'Template slot count and payload slot list are aligned.' })
  } else {
    items.push({ area: 'Slot count', status: 'Warning', message: 'Template has no slots.' })
  }

  const slotIdCounts = new Map<string, number>()
  for (const slot of slots) {
    slotIdCounts.set(slot.slot_id, (slotIdCounts.get(slot.slot_id) ?? 0) + 1)
  }
  const duplicateSlotIds = [...slotIdCounts.entries()].filter(([, count]) => count > 1).map(([slotId]) => slotId)
  items.push(
    duplicateSlotIds.length
      ? { area: 'Duplicate slot IDs', status: 'Warning', message: `Duplicate slot IDs detected: ${duplicateSlotIds.join(', ')}` }
      : { area: 'Duplicate slot IDs', status: 'OK', message: 'No duplicate slot IDs detected.' }
  )

  const outOfRangeCount = slots.filter((slot) => slot.season_week_start < 1 || slot.season_week_start > 61 || slot.season_week_end < 1 || slot.season_week_end > 61).length
  const endBeforeStartCount = slots.filter((slot) => slot.season_week_end < slot.season_week_start).length
  if (outOfRangeCount > 0) {
    items.push({ area: 'Week ranges', status: 'Warning', message: `${outOfRangeCount} slot(s) have week values outside SW1–SW61.` })
  }
  if (endBeforeStartCount > 0) {
    items.push({ area: 'Week ranges', status: 'Warning', message: `${endBeforeStartCount} slot(s) have season_week_end before season_week_start.` })
  }
  if (!outOfRangeCount && !endBeforeStartCount) {
    items.push({ area: 'Week ranges', status: 'OK', message: 'All slot week ranges are within SW1–SW61 and have valid start/end order.' })
  }

  let missingIdentityFieldCount = 0
  for (const slot of slots) {
    if (!slot.tournament_name?.trim()) missingIdentityFieldCount += 1
    if (!slot.category?.trim()) missingIdentityFieldCount += 1
    if (!slot.host_country?.trim()) missingIdentityFieldCount += 1
    if (!slot.region?.trim()) missingIdentityFieldCount += 1
    if (!slot.source_template_id?.trim()) missingIdentityFieldCount += 1
  }
  items.push(
    missingIdentityFieldCount > 0
      ? { area: 'Missing key fields', status: 'Warning', message: `Missing required slot identity fields: ${missingIdentityFieldCount}` }
      : { area: 'Missing key fields', status: 'OK', message: 'Required slot identity fields are populated.' }
  )

  const qualificationSlotsCount = slots.filter((slot) => slot.has_qualification).length
  items.push({ area: 'Qualification slots', status: 'Info', message: `Qualification slots: ${qualificationSlotsCount}` })

  return items
}

export type DiffPreviewStatus = 'OK' | 'Info' | 'Warning' | 'Planned'

export type DiffPreviewItem = {
  area: string
  status: DiffPreviewStatus
  message: string
}

export function renderPreviewValue(value: string | number | null | undefined): string {
  if (value === null || value === undefined) return '—'
  if (typeof value === 'string' && value.trim() === '') return '—'
  return String(value)
}

export function buildDiffPreviewItems(
  selectedTargetSeason: SeasonRegistryEntry | null,
  selectedSourceType: SourceType,
  selectedTemplate: SeasonTemplateSummary | null,
  selectedTemplatePreview: TemplatePreview | null,
  targetCalendarExists: boolean | null
): DiffPreviewItem[] {
  const items: DiffPreviewItem[] = [
    selectedTargetSeason
      ? { area: 'Target season', status: 'OK', message: 'Target season selected.' }
      : { area: 'Target season', status: 'Warning', message: 'No target season selected.' }
  ]

  if (selectedSourceType === 'season_template') {
    items.push({ area: 'Source type', status: 'OK', message: 'Season template source selected.' })
    items.push(
      selectedTemplate
        ? { area: 'Source template', status: 'OK', message: 'Template selected.' }
        : { area: 'Source template', status: 'Warning', message: 'No template selected.' }
    )

    if (selectedTargetSeason && selectedTemplate) {
      items.push(
        selectedTemplate.week_count === selectedTargetSeason.week_count
          ? { area: 'Template week count', status: 'OK', message: 'Template week count matches target season week count.' }
          : { area: 'Template week count', status: 'Warning', message: `Template week count (${selectedTemplate.week_count}) does not match target season week count (${selectedTargetSeason.week_count}).` }
      )
    } else {
      items.push({ area: 'Template week count', status: 'Info', message: 'Template or target season week count data is not fully available.' })
    }

    if (selectedTemplate) {
      items.push(
        selectedTemplate.slot_count > 0
          ? { area: 'Template slots', status: 'OK', message: 'Template has at least one slot.' }
          : { area: 'Template slots', status: 'Warning', message: 'Template has no slots.' }
      )
    } else {
      items.push({ area: 'Template slots', status: 'Info', message: 'Template slot data is not available.' })
    }

    if (selectedTemplatePreview) {
      items.push(
        selectedTemplatePreview.slotsWithinSw61
          ? { area: 'Slot week range', status: 'OK', message: 'Template slots are within SW1–SW61.' }
          : { area: 'Slot week range', status: 'Warning', message: 'Template has one or more slots outside SW1–SW61.' }
      )
    } else {
      items.push({ area: 'Slot week range', status: 'Info', message: 'Slot week range data is not available.' })
    }
  } else {
    items.push({ area: 'Source type', status: 'Planned', message: 'Source type is planned and not executable yet.' })
    items.push({ area: 'Source template', status: 'Planned', message: 'Source template selection is not active for this planned source type.' })
    items.push({ area: 'Template week count', status: 'Planned', message: 'Template week count comparison is pending an executable source workflow.' })
    items.push({ area: 'Template slots', status: 'Planned', message: 'Template slot checks are pending an executable source workflow.' })
    items.push({ area: 'Slot week range', status: 'Planned', message: 'Slot week range checks are pending an executable source workflow.' })
  }

  items.push(
    targetCalendarExists === true
      ? {
          area: 'Existing target calendar',
          status: 'Warning',
          message: 'Existing calendar detected; future build workflow must require explicit overwrite/merge choice.'
        }
      : targetCalendarExists === false
        ? { area: 'Existing target calendar', status: 'OK', message: 'No existing calendar detected from read-only preview.' }
        : { area: 'Existing target calendar', status: 'Info', message: 'Existing calendar state unavailable from read-only preview.' }
  )

  items.push(
    { area: 'Existing calendar conflict detection', status: 'Planned', message: 'Planned; no concrete season calendar conflict diff is performed on this page.' },
    { area: 'Missing/extra slot comparison', status: 'Planned', message: 'Planned; missing/extra slot compare is not implemented on this page.' },
    { area: 'Category mismatch comparison', status: 'Planned', message: 'Planned; category-level diff checks are not implemented on this page.' },
    { area: 'Host/region travel conflict checks', status: 'Planned', message: 'Planned; host/region travel conflict checks are not implemented on this page.' },
    { area: 'Apply/replace action plan', status: 'Planned', message: 'Planned; apply/replace actions are intentionally not executable from this page.' }
  )

  return items
}

type TargetCalendarStatusPanelProps = {
  selectedTargetSeasonLabel: string
  query: {
    isLoading: boolean
    error: unknown
    data: SeasonCalendarBuildResponse | undefined
  }
}

export function TargetCalendarStatusPanel({ selectedTargetSeasonLabel, query }: TargetCalendarStatusPanelProps): JSX.Element {
  const { isLoading, error, data } = query
  const calendar = data?.calendar
  const summary = data?.summary
  const validationWarningsCount = data?.validation_warnings.length ?? 0
  const validationErrorsCount = data?.validation_errors.length ?? 0

  return (
    <>
      <p>Read-only inspection of the currently selected target season calendar.</p>
      {!selectedTargetSeasonLabel ? <p className="status">Select a target season to inspect existing calendar state.</p> : null}
      {selectedTargetSeasonLabel && isLoading ? <p className="status">Loading target calendar preview…</p> : null}
      {selectedTargetSeasonLabel && error ? <p className="error">Target calendar preview unavailable.</p> : null}
      {selectedTargetSeasonLabel && !isLoading && !error ? (
        calendar ? (
          <ul className="dashboard-help-list">
            <li>Calendar exists: Yes</li>
            <li>Persisted: {summary?.persisted === undefined ? '—' : summary.persisted ? 'Yes' : 'No'}</li>
            <li>Event count: {summary?.event_count ?? 0}</li>
            <li>First event week: {summary?.first_event_week ?? '—'}</li>
            <li>Last event week: {summary?.last_event_week ?? '—'}</li>
            <li>Validation warnings count: {validationWarningsCount}</li>
            <li>Validation errors count: {validationErrorsCount}</li>
          </ul>
        ) : (
          <ul className="dashboard-help-list">
            <li>Calendar exists: No</li>
            <li>Persisted: —</li>
            <li>Event count: {summary?.event_count ?? 0}</li>
            <li>First event week: {summary?.first_event_week ?? '—'}</li>
            <li>Last event week: {summary?.last_event_week ?? '—'}</li>
            <li>Validation warnings count: {validationWarningsCount}</li>
            <li>Validation errors count: {validationErrorsCount}</li>
          </ul>
        )
      ) : null}
      {selectedTargetSeasonLabel && !isLoading && !error && !calendar ? <p>No existing calendar found for selected target season.</p> : null}
    </>
  )
}

type BuildPolicyPreviewPanelProps = {
  targetCalendarExists: boolean | null
}

export function BuildPolicyPreviewPanel({ targetCalendarExists }: BuildPolicyPreviewPanelProps): JSX.Element {
  const items = buildOverwriteMergePolicyItems(targetCalendarExists)
  return (
    <>
      <p>Read-only policy preview. No overwrite, merge, or build action is available on this page.</p>
      <table className="table">
        <thead>
          <tr>
            <th>Area</th>
            <th>Status</th>
            <th>Message</th>
          </tr>
        </thead>
        <tbody>
          {items.map((item) => (
            <tr key={item.area}>
              <td>{item.area}</td>
              <td>{item.status}</td>
              <td>{item.message}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <p>Future implementation must require an explicit audited backend command before modifying any season calendar.</p>
    </>
  )
}

type OverwritePolicySelection = 'none' | 'merge_preview' | 'overwrite_preview'

type OverwriteMergePolicySelectorPanelProps = {
  selectedOverwritePolicy: OverwritePolicySelection
  setSelectedOverwritePolicy: (value: OverwritePolicySelection) => void
  targetCalendarExists: boolean | null
}

export function OverwriteMergePolicySelectorPanel({
  selectedOverwritePolicy,
  setSelectedOverwritePolicy,
  targetCalendarExists
}: OverwriteMergePolicySelectorPanelProps): JSX.Element {
  return (
    <>
      <p>Read-only preflight input. This selector only changes the backend preflight payload and does not execute merge or overwrite.</p>
      <label>
        Future policy preview
        <select
          aria-label="Future policy preview"
          value={selectedOverwritePolicy}
          onChange={(event) => setSelectedOverwritePolicy(event.target.value as OverwritePolicySelection)}
        >
          <option value="none">No policy selected</option>
          <option value="merge_preview">Merge policy preview</option>
          <option value="overwrite_preview">Overwrite policy preview</option>
        </select>
      </label>
      {targetCalendarExists === true ? (
        <p>Existing target calendar detected. Backend preflight will require an explicit future policy before any future build can be considered.</p>
      ) : null}
      {targetCalendarExists === false ? (
        <p>No existing target calendar detected. Policy selection is optional for this read-only preview.</p>
      ) : null}
      {targetCalendarExists === null ? (
        <p>Target calendar state is unknown, so this selector is only an advisory preview input.</p>
      ) : null}
      <p>Changing this selector re-runs read-only backend preflight only. It does not mutate any calendar.</p>
    </>
  )
}

export function SourceTargetPreflightSummaryPanel({ items }: { items: PreflightSummaryItem[] }): JSX.Element {
  return (
    <>
      <p>Read-only local summary. This is not an authoritative backend preflight and does not enable build actions.</p>
      <table>
        <thead>
          <tr>
            <th scope="col">Area</th>
            <th scope="col">Status</th>
            <th scope="col">Message</th>
          </tr>
        </thead>
        <tbody>
          {items.map((item) => (
            <tr key={`${item.area}:${item.message}`}>
              <td>{item.area}</td>
              <td>{item.status}</td>
              <td>{item.message}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <p>No build, overwrite, merge, or apply command is available from this page.</p>
    </>
  )
}

type BuilderSelectionPanelProps = {
  selectedTargetSeasonLabel: string
  setSelectedTargetSeasonLabel: (value: string) => void
  selectedSourceType: SourceType
  setSelectedSourceType: (value: SourceType) => void
  selectedTemplateId: string
  setSelectedTemplateId: (value: string) => void
  seasons: SeasonRegistryEntry[]
  templates: SeasonTemplateSummary[]
}

export function BuilderSelectionPanel(props: BuilderSelectionPanelProps): JSX.Element {
  const {
    selectedTargetSeasonLabel,
    setSelectedTargetSeasonLabel,
    selectedSourceType,
    setSelectedSourceType,
    selectedTemplateId,
    setSelectedTemplateId,
    seasons,
    templates
  } = props

  return (
    <>
      <div className="dashboard-grid">
        <label>
          Target season
          <select aria-label="Target season select" value={selectedTargetSeasonLabel} onChange={(event) => setSelectedTargetSeasonLabel(event.target.value)}>
            {seasons.map((season) => <option key={season.label} value={season.label}>{season.label}</option>)}
          </select>
        </label>
        <label>
          Source type
          <select aria-label="Source type select" value={selectedSourceType} onChange={(event) => setSelectedSourceType(event.target.value as SourceType)}>
            {SOURCE_TYPE_OPTIONS.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}
          </select>
        </label>
        <label>
          Season template
          <select
            aria-label="Season template select"
            value={selectedTemplateId}
            disabled={selectedSourceType !== 'season_template' || !templates.length}
            onChange={(event) => setSelectedTemplateId(event.target.value)}
          >
            {templates.map((template) => <option key={template.template_id} value={template.template_id}>{template.name}</option>)}
          </select>
        </label>
      </div>
      {selectedSourceType !== 'season_template' ? <p>This source type is planned and not executable yet.</p> : null}
    </>
  )
}

type SelectionPreviewPanelProps = {
  selectedTargetSeason: SeasonRegistryEntry | null
  selectedSourceType: SourceType
  selectedTemplate: SeasonTemplateSummary | null
  selectedTemplatePreview: TemplatePreview | null
}

export function SelectionPreviewPanel({ selectedTargetSeason, selectedSourceType, selectedTemplate, selectedTemplatePreview }: SelectionPreviewPanelProps): JSX.Element {
  const targetLegacyLabel = selectedTargetSeason ? safeToLongSeasonLabel(selectedTargetSeason.label) : null
  return (
    <>
      {selectedTargetSeason ? (
        <ul className="dashboard-help-list">
          <li>Target compact label: {selectedTargetSeason.label}</li>
          {targetLegacyLabel ? <li>Target legacy label: {targetLegacyLabel}</li> : null}
          <li>Target start year: {selectedTargetSeason.season_start_year}</li>
          <li>Target season index: {selectedTargetSeason.season_index}</li>
          <li>Target registry status: {selectedTargetSeason.status}</li>
          <li>Target week count: {selectedTargetSeason.week_count}</li>
          <li>Target season week range: SW{selectedTargetSeason.season_week_start}–SW{selectedTargetSeason.season_week_end}</li>
          <li>Target year week range: YW{selectedTargetSeason.year_week_start}–YW{selectedTargetSeason.year_week_end}</li>
          <li><Link to={`/admin/seasons/detail/${encodeURIComponent(selectedTargetSeason.label)}`}>Open target season detail</Link></li>
          <li><Link to={`/admin/seasons?season=${encodeURIComponent(selectedTargetSeason.label)}`}>Open selected season in Seasons workspace</Link></li>
          <li><Link to="/admin/tour-seasons/season-registry">Open Season Registry</Link></li>
        </ul>
      ) : <p>No target season available for preview.</p>}

      {selectedSourceType === 'season_template' ? (
        selectedTemplate && selectedTemplatePreview ? (
          <>
            <ul className="dashboard-help-list">
              <li>Template name: {selectedTemplate.name}</li>
              <li>Template ID: {selectedTemplate.template_id}</li>
              <li>Slot count: {selectedTemplate.slot_count}</li>
              <li>Week count: {selectedTemplate.week_count}</li>
              <li>Status: {selectedTemplate.status}</li>
              <li>Slots within SW1–SW61: {selectedTemplatePreview.slotsWithinSw61 ? 'OK' : 'Warning'}</li>
              <li>Qualification slots count: {selectedTemplatePreview.qualificationSlotsCount}</li>
              <li>Earliest slot: {selectedTemplatePreview.earliestSlot === null ? '—' : `SW${selectedTemplatePreview.earliestSlot}`}</li>
              <li>Latest slot: {selectedTemplatePreview.latestSlot === null ? '—' : `SW${selectedTemplatePreview.latestSlot}`}</li>
              <li><Link to={`/admin/tour-seasons/season-templates/${selectedTemplate.template_id}`}>Open template detail</Link></li>
            </ul>
            <h4>Selected template slot preview</h4>
            <table>
              <thead>
                <tr>
                  <th scope="col">Slot</th>
                  <th scope="col">Week block</th>
                  <th scope="col">Tournament</th>
                  <th scope="col">Category</th>
                  <th scope="col">Host</th>
                  <th scope="col">Region</th>
                  <th scope="col">Qualification</th>
                  <th scope="col">Source template</th>
                  <th scope="col">Notes</th>
                </tr>
              </thead>
              <tbody>
                {selectedTemplate.slots.slice(0, 10).map((slot) => {
                  const weekBlock = slot.season_week_start === slot.season_week_end
                    ? `SW${slot.season_week_start}`
                    : `SW${slot.season_week_start}–SW${slot.season_week_end}`
                  return (
                    <tr key={slot.slot_id}>
                      <td>{renderPreviewValue(slot.slot_id)}</td>
                      <td>{weekBlock}</td>
                      <td>{renderPreviewValue(slot.tournament_name)}</td>
                      <td>{renderPreviewValue(slot.category)}</td>
                      <td>{renderPreviewValue(slot.host_country)}</td>
                      <td>{renderPreviewValue(slot.region)}</td>
                      <td>{slot.has_qualification ? 'Yes' : 'No'}</td>
                      <td>{renderPreviewValue(slot.source_template_id)}</td>
                      <td>{renderPreviewValue(slot.notes)}</td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
            <p>Showing first 10 slots only. Full template detail remains available on the Season Template detail page.</p>
          </>
        ) : <p>No season template available for preview.</p>
      ) : <p>Preview only. This source type has no executable workflow yet.</p>}
    </>
  )
}


export function TemplateValidationSummaryPanel({ selectedTemplate }: { selectedTemplate: SeasonTemplateSummary | null }): JSX.Element {
  const items = buildTemplateValidationItems(selectedTemplate)

  return (
    <>
      <p>Local read-only validation derived from the selected template payload. Not an authoritative build gate.</p>
      <table>
        <thead>
          <tr>
            <th scope="col">Area</th>
            <th scope="col">Status</th>
            <th scope="col">Message</th>
          </tr>
        </thead>
        <tbody>
          {items.map((item) => (
            <tr key={`${item.area}:${item.message}`}>
              <td>{item.area}</td>
              <td>{item.status}</td>
              <td>{item.message}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </>
  )
}

type SeasonTemplateSlotValidationPanelProps = {
  queryEnabled: boolean
  query: {
    isLoading: boolean
    isFetching: boolean
    error: unknown
    data?: SeasonTemplateSlotValidationResponse
  }
  issueCodeRegistryData?: SeasonTemplateSlotValidationIssueCodeRegistryResponse
}

export function SeasonTemplateSlotValidationPanel({ queryEnabled, query, issueCodeRegistryData }: SeasonTemplateSlotValidationPanelProps): JSX.Element {
  if (!queryEnabled) {
    return <p>Select a template to view read-only slot validation.</p>
  }
  if (query.isLoading) {
    return <p>Loading selected template slot validation…</p>
  }
  if (query.error) {
    return <p>Template slot validation request failed: {formatApiError(query.error)}</p>
  }
  if (!query.data) {
    return <p>No template slot validation data returned.</p>
  }

  const { data } = query
  const interpretation = data.summary.status === 'errors'
    ? 'Template slot validation has blocking errors.'
    : data.summary.status === 'warnings'
      ? 'Template slot validation has warnings but no blocking errors.'
      : 'Template slot validation is clean.'
  const visibleIssues = data.issues.slice(0, 10)
  const hiddenCount = Math.max(0, data.issues.length - visibleIssues.length)
  const metadataByCode = new Map((issueCodeRegistryData?.codes ?? []).map((item) => [item.code, item]))

  return (
    <>
      <p>Read-only selected template slot validation. No mutation path is available in this panel.</p>
      {query.isFetching ? <p>Refreshing template slot validation…</p> : null}
      <ul className="dashboard-help-list">
        <li>Template slot validation template_id: {data.template_id}</li>
        <li>Template slot validation template_exists: {String(data.template_exists)}</li>
        <li>Template slot validation read_only: {String(data.read_only)}</li>
        <li>Template slot validation message: {data.message}</li>
        <li>{interpretation}</li>
        <li>Template slot validation status: {data.summary.status}</li>
        <li>Template slot validation errors: {data.summary.error_count}</li>
        <li>Template slot validation warnings: {data.summary.warning_count}</li>
        <li>Template slot validation issue count: {data.summary.issue_count}</li>
        <li>Template slot count: {data.summary.slot_count}</li>
        <li>Template slot week count: {data.summary.week_count ?? '—'}</li>
        <li>Template slot first week: {data.summary.first_week ?? '—'}</li>
        <li>Template slot last week: {data.summary.last_week ?? '—'}</li>
      </ul>
      <table>
        <thead>
          <tr>
            <th scope="col">Severity</th>
            <th scope="col">Code</th>
            <th scope="col">Registry title</th>
            <th scope="col">Slot ID</th>
            <th scope="col">Message</th>
            <th scope="col">Registry description</th>
          </tr>
        </thead>
        <tbody>
          {visibleIssues.map((issue) => {
            const metadata = metadataByCode.get(issue.code)
            const registryTitle = metadata?.title ?? 'Unknown template slot issue code'
            const registryDescription = metadata?.description ?? 'No registry metadata available for this template slot issue code.'
            return (
              <tr key={`${issue.code}:${issue.slot_id ?? 'none'}:${issue.message}`}>
                <td>{issue.severity}</td>
                <td>{issue.code}</td>
                <td>{metadata?.field ? `${registryTitle} (${metadata.field})` : registryTitle}</td>
                <td>{issue.slot_id ?? '—'}</td>
                <td>{issue.message}</td>
                <td>{registryDescription}</td>
              </tr>
            )
          })}
        </tbody>
      </table>
      {hiddenCount > 0 ? <p>{hiddenCount} additional issue(s) hidden. Showing first 10 only.</p> : null}
    </>
  )
}


type SeasonTemplateSlotConflictPanelProps = {
  queryEnabled: boolean
  conflictCodeRegistryData?: SeasonTemplateSlotConflictCodeRegistryResponse
  query: {
    isLoading: boolean
    isFetching: boolean
    error: unknown
    data?: SeasonTemplateSlotConflictReportResponse
  }
}

export function SeasonTemplateSlotConflictPanel({ queryEnabled, query, conflictCodeRegistryData }: SeasonTemplateSlotConflictPanelProps): JSX.Element {
  if (!queryEnabled) return <p>Select a template to view read-only slot conflict analysis.</p>
  if (query.isLoading) return <p>Loading selected template slot conflict analysis…</p>
  if (query.error) return <p>{formatApiError(query.error)}</p>
  if (!query.data) return <p>No selected template slot conflict report is available.</p>

  const { data } = query
  const interpretation = data.summary.status === 'warnings'
    ? 'Template slot conflict analysis has schedule warnings.'
    : data.summary.status === 'info'
      ? 'Template slot conflict analysis has informational findings only.'
      : 'Template slot conflict analysis is clean.'
  const visibleConflicts = data.conflicts.slice(0, 10)
  const hiddenCount = Math.max(0, data.conflicts.length - visibleConflicts.length)
  const metadataByCode = new Map((conflictCodeRegistryData?.codes ?? []).map((metadata) => [metadata.code, metadata]))

  return (
    <>
      <p>Read-only selected template slot conflict analysis. No mutation path is available in this panel.</p>
      {query.isFetching ? <p>Refreshing selected template slot conflict analysis…</p> : null}
      <ul className="dashboard-help-list">
        <li>Selected template slot conflict template_id: {data.template_id}</li>
        <li>Selected template slot conflict template_exists: {String(data.template_exists)}</li>
        <li>Selected template slot conflict read_only: {String(data.read_only)}</li>
        <li>Selected template slot conflict message: {data.message}</li>
        <li>{interpretation}</li>
        <li>Selected template slot conflict status: {data.summary.status}</li>
        <li>Selected template slot conflict warning count: {data.summary.warning_count}</li>
        <li>Selected template slot conflict info count: {data.summary.info_count}</li>
        <li>Selected template slot conflict conflict count: {data.summary.conflict_count}</li>
        <li>Selected template slot conflict slot count: {data.summary.slot_count}</li>
        <li>Selected template slot conflict occupied week count: {data.summary.occupied_week_count}</li>
        <li>Selected template slot conflict busiest week: {data.summary.busiest_week ?? '—'}</li>
        <li>Selected template slot conflict busiest week slot count: {data.summary.busiest_week_slot_count ?? '—'}</li>
      </ul>
      {visibleConflicts.length === 0 ? <p>No template slot conflicts reported.</p> : (
        <table>
          <thead><tr><th>severity</th><th>code</th><th>registry title</th><th>season week</th><th>slot IDs</th><th>categories</th><th>tour levels</th><th>host countries</th><th>description</th><th>registry description</th></tr></thead>
          <tbody>
            {visibleConflicts.map((conflict, index) => {
              const metadata = metadataByCode.get(conflict.code)
              const registryTitle = metadata?.title ?? 'Unknown template slot conflict code'
              const registryDescription = metadata?.description ?? 'No registry metadata available for this template slot conflict code.'
              return <tr key={`${conflict.code}:${conflict.season_week ?? 'none'}:${index}`}>
                <td>{conflict.severity}</td><td>{conflict.code}</td><td>{registryTitle}</td><td>{conflict.season_week ?? '—'}</td>
                <td>{formatOptionalList(conflict.slot_ids)}</td>
                <td>{formatOptionalList(conflict.categories)}</td>
                <td>{formatOptionalList(conflict.tour_levels)}</td>
                <td>{formatOptionalList(conflict.host_countries)}</td>
                <td>{conflict.message}</td>
                <td>{registryDescription}</td>
              </tr>
            })}
          </tbody>
        </table>
      )}
      {hiddenCount > 0 ? <p>{hiddenCount} additional template slot conflicts hidden.</p> : null}
    </>
  )
}

type TemplateSlotConflictCodeRegistryPanelProps = {
  data?: SeasonTemplateSlotConflictCodeRegistryResponse
  isLoading: boolean
  error: unknown
}

export function TemplateSlotConflictCodeRegistryPanel({ data, isLoading, error }: TemplateSlotConflictCodeRegistryPanelProps): JSX.Element {
  if (isLoading) return <p>Loading template slot conflict code registry…</p>
  if (error) return <p>{formatApiError(error)}</p>
  if (!data) return <p>No template slot conflict code registry is available.</p>
  return <>
    <p>Read-only template slot conflict code registry.</p>
    <p>Template slot conflict code count: {data.code_count}</p>
    <p>Template slot conflict registry message: {data.message}</p>
    {data.codes.length === 0 ? <p>No template slot conflict codes registered.</p> : (
      <table>
        <thead><tr><th>severity</th><th>code</th><th>title</th><th>description</th></tr></thead>
        <tbody>{data.codes.map((item) => <tr key={item.code}><td>{item.severity}</td><td>{item.code}</td><td>{item.title}</td><td>{item.description}</td></tr>)}</tbody>
      </table>
    )}
  </>
}

export function extractBracketedIssueCodes(messages: string[]): string[] {
  const seen = new Set<string>()
  const extracted: string[] = []
  for (const message of messages) {
    const match = message.match(/^\[([a-z0-9_]+)\]/)
    if (!match) continue
    const code = match[1]
    if (seen.has(code)) continue
    seen.add(code)
    extracted.push(code)
  }
  return extracted
}

export function readTemplateSlotPreviewIssueCodes(preview: SeasonTemplateSlotValidationPreview | null | undefined | unknown): string[] {
  return readTemplateSlotPreviewCodeArrayField(preview, 'issue_codes')
}

function readTemplateSlotPreviewCodeArrayField(
  preview: unknown,
  field: 'issue_codes' | 'error_codes' | 'warning_codes'
): string[] {
  if (!preview || typeof preview !== 'object') return []
  const rawCodes = (preview as Record<string, unknown>)[field]
  if (!Array.isArray(rawCodes) || rawCodes.length === 0) return []
  const seen = new Set<string>()
  const codes: string[] = []
  for (const rawCode of rawCodes) {
    if (typeof rawCode !== 'string') continue
    const normalizedCode = rawCode.trim()
    if (!normalizedCode || seen.has(normalizedCode)) continue
    seen.add(normalizedCode)
    codes.push(normalizedCode)
  }
  return codes
}

export function hasUsableTemplateSlotPreview(preview: SeasonTemplateSlotValidationPreview | null | undefined): boolean {
  return readTemplateSlotPreviewIssueCodes(preview).length > 0
}

function normalizePreviewScalar(preview: unknown, field: string): string {
  if (!preview || typeof preview !== 'object') return 'n/a'
  const value = (preview as Record<string, unknown>)[field]
  if (typeof value === 'string') {
    const trimmed = value.trim()
    if (!trimmed) return 'n/a'
    if (field === 'status') {
      const normalizedStatus = trimmed.toLowerCase()
      return normalizedStatus === 'clean' || normalizedStatus === 'warnings' || normalizedStatus === 'errors' ? normalizedStatus : 'n/a'
    }
    return trimmed
  }
  if (typeof value === 'number' && Number.isFinite(value)) return field === 'status' ? 'n/a' : String(value)
  if (typeof value === 'boolean') return value ? 'true' : 'false'
  return 'n/a'
}

function normalizeTemplateSlotPreviewCodes(preview: unknown, field: 'issue_codes' | 'error_codes' | 'warning_codes'): string {
  const normalized = readTemplateSlotPreviewCodeArrayField(preview, field)
  return normalized.length > 0 ? normalized.join(', ') : 'none'
}

function readPreviewCodeArrayField(
  preview: unknown,
  field: string
): string[] {
  if (!preview || typeof preview !== 'object') return []
  const rawCodes = (preview as Record<string, unknown>)[field]
  if (!Array.isArray(rawCodes) || rawCodes.length === 0) return []
  const seen = new Set<string>()
  const codes: string[] = []
  for (const rawCode of rawCodes) {
    if (typeof rawCode !== 'string') continue
    const normalizedCode = rawCode.trim()
    if (!normalizedCode || seen.has(normalizedCode)) continue
    seen.add(normalizedCode)
    codes.push(normalizedCode)
  }
  return codes
}

function normalizeConflictPreviewCodes(preview: unknown, field: 'conflict_codes' | 'warning_codes' | 'info_codes'): string {
  const normalized = readPreviewCodeArrayField(preview, field)
  return normalized.length > 0 ? normalized.join(', ') : 'none'
}

function hasTemplateSlotValidationPreview(preview: unknown): boolean {
  if (!preview || typeof preview !== 'object') return false
  return Object.keys(preview as Record<string, unknown>).length > 0
}

function normalizeConflictPreviewScalar(preview: unknown, field: string): string {
  if (!preview || typeof preview !== 'object') return 'n/a'
  const value = (preview as Record<string, unknown>)[field]
  if (field === 'template_exists' || field === 'read_only') {
    return typeof value === 'boolean' ? (value ? 'true' : 'false') : 'n/a'
  }
  if (field === 'warning_count' || field === 'info_count' || field === 'conflict_count' || field === 'busiest_week' || field === 'busiest_week_slot_count') {
    return typeof value === 'number' && Number.isFinite(value) ? String(value) : 'n/a'
  }
  if (typeof value === 'string') {
    const trimmed = value.trim()
    if (!trimmed) return 'n/a'
    if (field === 'status') {
      const normalizedStatus = trimmed.toLowerCase()
      return normalizedStatus === 'clean' || normalizedStatus === 'warnings' || normalizedStatus === 'info' ? normalizedStatus : 'n/a'
    }
    return trimmed
  }
  if (typeof value === 'number' && Number.isFinite(value)) return field === 'status' ? 'n/a' : String(value)
  if (typeof value === 'boolean') return value ? 'true' : 'false'
  return 'n/a'
}

function hasTemplateSlotConflictPreview(preview: unknown): boolean {
  if (!preview || typeof preview !== 'object') return false
  return Object.keys(preview as Record<string, unknown>).length > 0
}

function normalizeStringArrayDisplay(value: unknown): string {
  if (!Array.isArray(value) || value.length === 0) return 'none'
  const seen = new Set<string>()
  const normalized: string[] = []
  for (const item of value) {
    if (typeof item !== 'string') continue
    const trimmed = item.trim()
    if (!trimmed || seen.has(trimmed)) continue
    seen.add(trimmed)
    normalized.push(trimmed)
  }
  return normalized.length > 0 ? normalized.join(', ') : 'none'
}

export function readCandidateIdentitySummary(dryRunResultPreview: unknown): Record<string, string> | null {
  if (!dryRunResultPreview || typeof dryRunResultPreview !== 'object') return null
  const summary = (dryRunResultPreview as Record<string, unknown>).candidate_identity_summary
  if (!summary || typeof summary !== 'object') return null
  const record = summary as Record<string, unknown>
  return {
    candidateCount: normalizeFiniteNumberDisplay(record.candidate_count),
    candidateIds: normalizeStringArrayDisplay(record.candidate_ids),
    candidateIdentityKeys: normalizeStringArrayDisplay(record.candidate_identity_keys),
    duplicateCandidateIds: normalizeStringArrayDisplay(record.duplicate_candidate_ids),
    duplicateCandidateIdentityKeys: normalizeStringArrayDisplay(record.duplicate_candidate_identity_keys),
    readOnly: normalizeBooleanDisplay(record.read_only),
    mutationPermitted: normalizeBooleanDisplay(record.mutation_permitted),
    message: normalizeNonEmptyStringDisplay(record.message)
  }
}

export function readCandidateIdentityContract(dryRunResultPreview: unknown): Record<string, string> | null {
  if (!dryRunResultPreview || typeof dryRunResultPreview !== 'object') return null
  const contract = (dryRunResultPreview as Record<string, unknown>).candidate_identity_contract
  if (!contract || typeof contract !== 'object') return null
  const record = contract as Record<string, unknown>
  return {
    identitySource: normalizeNonEmptyStringDisplay(record.identity_source),
    idStrategy: normalizeNonEmptyStringDisplay(record.id_strategy),
    keyStrategy: normalizeNonEmptyStringDisplay(record.key_strategy),
    keyComponents: normalizeStringArrayDisplay(record.key_components),
    candidateCount: normalizeFiniteNumberDisplay(record.candidate_count),
    hasDuplicateCandidateIds: normalizeBooleanDisplay(record.has_duplicate_candidate_ids),
    hasDuplicateCandidateIdentityKeys: normalizeBooleanDisplay(record.has_duplicate_candidate_identity_keys),
    safeForFutureReference: normalizeBooleanDisplay(record.safe_for_future_reference),
    readOnly: normalizeBooleanDisplay(record.read_only),
    mutationPermitted: normalizeBooleanDisplay(record.mutation_permitted),
    message: normalizeNonEmptyStringDisplay(record.message)
  }
}

export function CandidateIdentitySummaryPanel({ dryRunResultPreview }: { dryRunResultPreview?: unknown }): JSX.Element {
  const summary = readCandidateIdentitySummary(dryRunResultPreview)
  if (!summary) return <p>Candidate identity summary is not available.</p>
  return (
    <>
      <p>Candidate identity summary</p>
      <p>Candidate identity candidate count: {summary.candidateCount}</p>
      <p>Candidate identity candidate IDs: {summary.candidateIds}</p>
      <p>Candidate identity keys: {summary.candidateIdentityKeys}</p>
      <p>Candidate identity duplicate candidate IDs: {summary.duplicateCandidateIds}</p>
      <p>Candidate identity duplicate keys: {summary.duplicateCandidateIdentityKeys}</p>
      <p>Candidate identity read-only: {summary.readOnly}</p>
      <p>Candidate identity mutation permitted: {summary.mutationPermitted}</p>
      <p>Candidate identity message: {summary.message}</p>
    </>
  )
}

export function CandidateIdentityContractPanel({ dryRunResultPreview }: { dryRunResultPreview?: unknown }): JSX.Element {
  const contract = readCandidateIdentityContract(dryRunResultPreview)
  if (!contract) return <p>Candidate identity contract is not available.</p>
  return (
    <>
      <p>Candidate identity contract</p>
      <p>Candidate identity source: {contract.identitySource}</p>
      <p>Candidate identity ID strategy: {contract.idStrategy}</p>
      <p>Candidate identity key strategy: {contract.keyStrategy}</p>
      <p>Candidate identity key components: {contract.keyComponents}</p>
      <p>Candidate identity contract candidate count: {contract.candidateCount}</p>
      <p>Candidate identity has duplicate candidate IDs: {contract.hasDuplicateCandidateIds}</p>
      <p>Candidate identity has duplicate keys: {contract.hasDuplicateCandidateIdentityKeys}</p>
      <p>Candidate identity safe for future reference: {contract.safeForFutureReference}</p>
      <p>Candidate identity contract read-only: {contract.readOnly}</p>
      <p>Candidate identity contract mutation permitted: {contract.mutationPermitted}</p>
      <p>Candidate identity contract message: {contract.message}</p>
    </>
  )
}

export function TemplateSlotValidationPreviewSummaryPanel({
  titlePrefix,
  preview
}: {
  titlePrefix: string
  preview?: SeasonTemplateSlotValidationPreview | null
}): JSX.Element {
  if (!hasTemplateSlotValidationPreview(preview)) {
    return <p>{titlePrefix} template slot validation preview is not available.</p>
  }

  const readOnlyValue = (() => {
    if (!preview || typeof preview !== 'object') return 'n/a'
    const raw = (preview as Record<string, unknown>).read_only
    return typeof raw === 'boolean' ? (raw ? 'true' : 'false') : 'n/a'
  })()

  return (
    <>
      <p>{titlePrefix} template slot validation preview</p>
      <p>{titlePrefix} template slot validation template ID: {normalizePreviewScalar(preview, 'template_id')}</p>
      <p>{titlePrefix} template slot validation template exists: {normalizePreviewScalar(preview, 'template_exists')}</p>
      <p>{titlePrefix} template slot validation read-only: {readOnlyValue}</p>
      <p>{titlePrefix} template slot validation status: {normalizePreviewScalar(preview, 'status')}</p>
      <p>{titlePrefix} template slot validation error count: {normalizePreviewScalar(preview, 'error_count')}</p>
      <p>{titlePrefix} template slot validation warning count: {normalizePreviewScalar(preview, 'warning_count')}</p>
      <p>{titlePrefix} template slot validation issue count: {normalizePreviewScalar(preview, 'issue_count')}</p>
      <p>{titlePrefix} template slot validation issue codes: {normalizeTemplateSlotPreviewCodes(preview, 'issue_codes')}</p>
      <p>{titlePrefix} template slot validation error codes: {normalizeTemplateSlotPreviewCodes(preview, 'error_codes')}</p>
      <p>{titlePrefix} template slot validation warning codes: {normalizeTemplateSlotPreviewCodes(preview, 'warning_codes')}</p>
    </>
  )
}

export function TemplateSlotConflictPreviewSummaryPanel({
  titlePrefix,
  preview
}: {
  titlePrefix: string
  preview?: SeasonTemplateSlotConflictPreview | null
}): JSX.Element {
  if (!hasTemplateSlotConflictPreview(preview)) {
    return <p>{titlePrefix} template slot conflict preview is not available.</p>
  }

  return (
    <>
      <p>{titlePrefix} template slot conflict preview</p>
      <p>{titlePrefix} template slot conflict template ID: {normalizeConflictPreviewScalar(preview, 'template_id')}</p>
      <p>{titlePrefix} template slot conflict template exists: {normalizeConflictPreviewScalar(preview, 'template_exists')}</p>
      <p>{titlePrefix} template slot conflict read-only: {normalizeConflictPreviewScalar(preview, 'read_only')}</p>
      <p>{titlePrefix} template slot conflict status: {normalizeConflictPreviewScalar(preview, 'status')}</p>
      <p>{titlePrefix} template slot conflict warning count: {normalizeConflictPreviewScalar(preview, 'warning_count')}</p>
      <p>{titlePrefix} template slot conflict info count: {normalizeConflictPreviewScalar(preview, 'info_count')}</p>
      <p>{titlePrefix} template slot conflict conflict count: {normalizeConflictPreviewScalar(preview, 'conflict_count')}</p>
      <p>{titlePrefix} template slot conflict conflict codes: {normalizeConflictPreviewCodes(preview, 'conflict_codes')}</p>
      <p>{titlePrefix} template slot conflict warning codes: {normalizeConflictPreviewCodes(preview, 'warning_codes')}</p>
      <p>{titlePrefix} template slot conflict info codes: {normalizeConflictPreviewCodes(preview, 'info_codes')}</p>
      <p>{titlePrefix} template slot conflict busiest week: {normalizeConflictPreviewScalar(preview, 'busiest_week')}</p>
      <p>{titlePrefix} template slot conflict busiest week slot count: {normalizeConflictPreviewScalar(preview, 'busiest_week_slot_count')}</p>
    </>
  )
}


export type DryRunTemplateConflictSummaryDisplay = {
  available: string
  readOnly: string
  nonBlocking: string
  status: string
  warningCount: string
  infoCount: string
  conflictCount: string
  conflictCodes: string
  busiestWeek: string
  busiestWeekSlotCount: string
  source: string
  message: string
}

function normalizeBooleanDisplay(value: unknown): string {
  return typeof value === 'boolean' ? (value ? 'true' : 'false') : 'n/a'
}

function normalizeFiniteNumberDisplay(value: unknown): string {
  return typeof value === 'number' && Number.isFinite(value) ? String(value) : 'n/a'
}

function normalizeNonEmptyStringDisplay(value: unknown): string {
  return typeof value === 'string' && value.trim() ? value.trim() : 'n/a'
}

function normalizeConflictSummaryStatus(value: unknown): string {
  if (typeof value !== 'string') return 'n/a'
  const normalized = value.trim().toLowerCase()
  return normalized === 'clean' || normalized === 'warnings' || normalized === 'info' ? normalized : 'n/a'
}

function normalizeConflictCodesDisplay(value: unknown): string {
  if (!Array.isArray(value) || value.length === 0) return 'none'
  const seen = new Set<string>()
  const codes: string[] = []
  for (const rawCode of value) {
    if (typeof rawCode !== 'string') continue
    const code = rawCode.trim()
    if (!code || seen.has(code)) continue
    seen.add(code)
    codes.push(code)
  }
  return codes.length ? codes.join(', ') : 'none'
}

function readTemplateConflictSummary(summaryContainer: unknown): DryRunTemplateConflictSummaryDisplay | null {
  if (!summaryContainer || typeof summaryContainer !== 'object') return null
  const summary = (summaryContainer as Record<string, unknown>).template_conflict_summary
  if (!summary || typeof summary !== 'object') return null
  const summaryRecord = summary as Record<string, unknown>

  return {
    available: normalizeBooleanDisplay(summaryRecord.available),
    readOnly: normalizeBooleanDisplay(summaryRecord.read_only),
    nonBlocking: normalizeBooleanDisplay(summaryRecord.non_blocking),
    status: normalizeConflictSummaryStatus(summaryRecord.status),
    warningCount: normalizeFiniteNumberDisplay(summaryRecord.warning_count),
    infoCount: normalizeFiniteNumberDisplay(summaryRecord.info_count),
    conflictCount: normalizeFiniteNumberDisplay(summaryRecord.conflict_count),
    conflictCodes: normalizeConflictCodesDisplay(summaryRecord.conflict_codes),
    busiestWeek: normalizeFiniteNumberDisplay(summaryRecord.busiest_week),
    busiestWeekSlotCount: normalizeFiniteNumberDisplay(summaryRecord.busiest_week_slot_count),
    source: normalizeNonEmptyStringDisplay(summaryRecord.source),
    message: normalizeNonEmptyStringDisplay(summaryRecord.message)
  }
}

export function readDryRunTemplateConflictSummary(dryRunResultPreview: unknown): DryRunTemplateConflictSummaryDisplay | null {
  return readTemplateConflictSummary(dryRunResultPreview)
}

export function readPreflightTemplateConflictSummary(authoritativeDiffSummary: unknown): DryRunTemplateConflictSummaryDisplay | null {
  return readTemplateConflictSummary(authoritativeDiffSummary)
}

type TemplateConflictSummaryPanelProps = {
  labelPrefix: 'Preflight' | 'Dry-run'
  unavailableText: string
  summary: DryRunTemplateConflictSummaryDisplay | null
}

function TemplateConflictSummaryPanel({
  labelPrefix,
  unavailableText,
  summary
}: TemplateConflictSummaryPanelProps): JSX.Element {
  if (!summary) return <p>{unavailableText}</p>

  return (
    <>
      <p>{labelPrefix} template conflict summary</p>
      <p>{labelPrefix} template conflict diagnostics available: {summary.available}</p>
      <p>{labelPrefix} template conflict diagnostics read-only: {summary.readOnly}</p>
      <p>{labelPrefix} template conflict diagnostics non-blocking: {summary.nonBlocking}</p>
      <p>{labelPrefix} template conflict status: {summary.status}</p>
      <p>{labelPrefix} template conflict warning count: {summary.warningCount}</p>
      <p>{labelPrefix} template conflict info count: {summary.infoCount}</p>
      <p>{labelPrefix} template conflict conflict count: {summary.conflictCount}</p>
      <p>{labelPrefix} template conflict conflict codes: {summary.conflictCodes}</p>
      <p>{labelPrefix} template conflict busiest week: {summary.busiestWeek}</p>
      <p>{labelPrefix} template conflict busiest week slot count: {summary.busiestWeekSlotCount}</p>
      <p>{labelPrefix} template conflict source: {summary.source}</p>
      <p>{labelPrefix} template conflict message: {summary.message}</p>
    </>
  )
}

export function PreflightTemplateConflictSummaryPanel({ authoritativeDiffSummary }: { authoritativeDiffSummary?: unknown }): JSX.Element {
  const summary = readPreflightTemplateConflictSummary(authoritativeDiffSummary)
  return (
    <TemplateConflictSummaryPanel
      labelPrefix="Preflight"
      unavailableText="Preflight template conflict summary is not available."
      summary={summary}
    />
  )
}

export function DryRunTemplateConflictSummaryPanel({ dryRunResultPreview }: { dryRunResultPreview?: unknown }): JSX.Element {
  const summary = readDryRunTemplateConflictSummary(dryRunResultPreview)
  return (
    <TemplateConflictSummaryPanel
      labelPrefix="Dry-run"
      unavailableText="Dry-run template conflict summary is not available."
      summary={summary}
    />
  )
}

function readTemplateSlotPreviewSummaryField(preview: SeasonTemplateSlotValidationPreview | null | undefined, field: 'status' | 'issue_count'): string {
  return normalizePreviewScalar(preview, field)
}

export function readTemplateSlotConflictPreviewCodes(preview: SeasonTemplateSlotConflictPreview | null | undefined | unknown): string[] {
  if (!preview || typeof preview !== 'object') return []
  const rawCodes = (preview as Record<string, unknown>).conflict_codes
  if (!Array.isArray(rawCodes) || rawCodes.length === 0) return []
  const seen = new Set<string>()
  const normalizedCodes: string[] = []
  for (const rawCode of rawCodes) {
    if (typeof rawCode !== 'string') continue
    const normalizedCode = rawCode.trim()
    if (!normalizedCode || seen.has(normalizedCode)) continue
    seen.add(normalizedCode)
    normalizedCodes.push(normalizedCode)
  }
  return normalizedCodes
}

export function readTemplateSlotConflictPreviewSummaryField(
  preview: SeasonTemplateSlotConflictPreview | null | undefined,
  field: 'status' | 'conflict_count'
): string {
  if (!preview || typeof preview !== 'object') return 'n/a'
  const value = (preview as Record<string, unknown>)[field]
  if (field === 'status') {
    if (typeof value !== 'string') return 'n/a'
    const normalizedStatus = value.trim().toLowerCase()
    return normalizedStatus === 'clean' || normalizedStatus === 'warnings' || normalizedStatus === 'info' ? normalizedStatus : 'n/a'
  }
  return typeof value === 'number' && Number.isFinite(value) ? String(value) : 'n/a'
}

export function extractConflictCodesFromReport(report: SeasonTemplateSlotConflictReportResponse | null | undefined): string[] {
  if (!report) return []
  const seen = new Set<string>()
  const codes: string[] = []
  for (const conflict of report.conflicts) {
    const code = conflict.code.trim()
    if (!code || seen.has(code)) continue
    seen.add(code)
    codes.push(code)
  }
  return codes
}

type TemplateConflictDiagnosticsOverviewDisplay = {
  selectedReportAvailable: 'available' | 'unavailable' | 'n/a'
  selectedStatus: 'clean' | 'warnings' | 'info' | 'n/a'
  selectedConflictCount: string
  preflightPreviewAvailable: 'available' | 'unavailable' | 'n/a'
  preflightSummaryAvailable: 'available' | 'unavailable' | 'n/a'
  preflightStatus: 'clean' | 'warnings' | 'info' | 'n/a'
  preflightConflictCount: string
  dryRunPreviewAvailable: 'available' | 'unavailable' | 'n/a'
  dryRunSummaryAvailable: 'available' | 'unavailable' | 'n/a'
  dryRunStatus: 'clean' | 'warnings' | 'info' | 'n/a'
  dryRunConflictCount: string
  mutationBehavior: string
  blockingBehavior: string
}

function toAvailableString(value: unknown): 'available' | 'unavailable' | 'n/a' {
  if (typeof value !== 'boolean') return 'n/a'
  return value ? 'available' : 'unavailable'
}

function toConflictStatus(value: unknown): 'clean' | 'warnings' | 'info' | 'n/a' {
  if (typeof value !== 'string') return 'n/a'
  const normalized = value.trim().toLowerCase()
  return normalized === 'clean' || normalized === 'warnings' || normalized === 'info' ? normalized : 'n/a'
}

function toCountString(value: unknown): string {
  return typeof value === 'number' && Number.isFinite(value) ? String(value) : 'n/a'
}

function toNonEmptyStringOrNa(value: unknown): string {
  if (typeof value !== 'string') return 'n/a'
  const normalized = value.trim()
  return normalized.length > 0 ? normalized : 'n/a'
}

export function readTemplateConflictDiagnosticsOverview(overview: unknown): TemplateConflictDiagnosticsOverviewDisplay | null {
  if (!overview || typeof overview !== 'object') return null
  const record = overview as Record<string, unknown>
  return {
    selectedReportAvailable: toAvailableString(record.selected_report_available),
    selectedStatus: toConflictStatus(record.selected_status),
    selectedConflictCount: toCountString(record.selected_conflict_count),
    preflightPreviewAvailable: toAvailableString(record.preflight_preview_available),
    preflightSummaryAvailable: toAvailableString(record.preflight_summary_available),
    preflightStatus: toConflictStatus(record.preflight_status),
    preflightConflictCount: toCountString(record.preflight_conflict_count),
    dryRunPreviewAvailable: toAvailableString(record.dry_run_preview_available),
    dryRunSummaryAvailable: toAvailableString(record.dry_run_summary_available),
    dryRunStatus: toConflictStatus(record.dry_run_status),
    dryRunConflictCount: toCountString(record.dry_run_conflict_count),
    mutationBehavior: toNonEmptyStringOrNa(record.mutation_behavior),
    blockingBehavior: toNonEmptyStringOrNa(record.blocking_behavior)
  }
}

function readSelectedConflictOverviewDisplay(
  selectedConflictReport?: SeasonTemplateSlotConflictReportResponse
): {
  selectedAvailable: 'available' | 'unavailable'
  selectedStatus: 'clean' | 'warnings' | 'info' | 'n/a'
  selectedConflictCount: string
} {
  const selectedOverviewRaw = selectedConflictReport?.template_conflict_diagnostics_overview
  const selectedOverview = readTemplateConflictDiagnosticsOverview(selectedOverviewRaw)
  const selectedAvailable = selectedOverview && typeof selectedOverviewRaw?.selected_report_available === 'boolean'
    ? (selectedOverviewRaw.selected_report_available ? 'available' : 'unavailable')
    : (selectedConflictReport ? 'available' : 'unavailable')
  const selectedStatus = selectedOverview && selectedOverview.selectedStatus !== 'n/a'
    ? selectedOverview.selectedStatus
    : (selectedConflictReport?.summary?.status ?? 'n/a')
  const selectedConflictCount = selectedOverview && selectedOverview.selectedConflictCount !== 'n/a'
    ? selectedOverview.selectedConflictCount
    : (typeof selectedConflictReport?.summary?.conflict_count === 'number'
      ? String(selectedConflictReport.summary.conflict_count)
      : 'n/a')
  return { selectedAvailable, selectedStatus, selectedConflictCount }
}

type TemplateConflictDiagnosticsOverviewPanelProps = {
  selectedConflictReport?: SeasonTemplateSlotConflictReportResponse
  preflightResult?: SeasonBuilderPreflightResponse
  dryRunResult?: SeasonBuilderDryRunBuildResponse
}

export function TemplateConflictDiagnosticsOverviewPanel({
  selectedConflictReport,
  preflightResult,
  dryRunResult
}: TemplateConflictDiagnosticsOverviewPanelProps): JSX.Element {
  const { selectedAvailable, selectedStatus, selectedConflictCount } = readSelectedConflictOverviewDisplay(selectedConflictReport)

  const preflightPreview = preflightResult?.template_slot_conflict_preview
  const preflightSummary = readPreflightTemplateConflictSummary(preflightResult?.authoritative_diff_summary)
  const preflightOverview = readTemplateConflictDiagnosticsOverview(preflightResult?.template_conflict_diagnostics_overview)
  const preflightPreviewAvailable = preflightOverview && preflightOverview.preflightPreviewAvailable !== 'n/a'
    ? preflightOverview.preflightPreviewAvailable
    : (preflightResult ? (preflightPreview ? 'available' : 'unavailable') : 'unavailable')
  const preflightSummaryAvailable = preflightOverview && preflightOverview.preflightSummaryAvailable !== 'n/a'
    ? preflightOverview.preflightSummaryAvailable
    : (preflightResult ? (preflightSummary ? 'available' : 'unavailable') : 'unavailable')
  const preflightStatus = preflightOverview && preflightOverview.preflightStatus !== 'n/a'
    ? preflightOverview.preflightStatus
    : (preflightSummary?.status ?? readTemplateSlotConflictPreviewSummaryField(preflightPreview, 'status'))
  const preflightConflictCount = preflightOverview && preflightOverview.preflightConflictCount !== 'n/a'
    ? preflightOverview.preflightConflictCount
    : (preflightSummary?.conflictCount ?? readTemplateSlotConflictPreviewSummaryField(preflightPreview, 'conflict_count'))

  const dryRunPreview = dryRunResult?.template_slot_conflict_preview
  const dryRunSummary = readDryRunTemplateConflictSummary(dryRunResult?.dry_run_result_preview)
  const dryRunOverview = readTemplateConflictDiagnosticsOverview(dryRunResult?.template_conflict_diagnostics_overview)
  const dryRunPreviewAvailable = dryRunOverview && dryRunOverview.dryRunPreviewAvailable !== 'n/a'
    ? dryRunOverview.dryRunPreviewAvailable
    : (dryRunResult ? (dryRunPreview ? 'available' : 'unavailable') : 'unavailable')
  const dryRunSummaryAvailable = dryRunOverview && dryRunOverview.dryRunSummaryAvailable !== 'n/a'
    ? dryRunOverview.dryRunSummaryAvailable
    : (dryRunResult ? (dryRunSummary ? 'available' : 'unavailable') : 'unavailable')
  const dryRunStatus = dryRunOverview && dryRunOverview.dryRunStatus !== 'n/a'
    ? dryRunOverview.dryRunStatus
    : (dryRunSummary?.status ?? readTemplateSlotConflictPreviewSummaryField(dryRunPreview, 'status'))
  const dryRunConflictCount = dryRunOverview && dryRunOverview.dryRunConflictCount !== 'n/a'
    ? dryRunOverview.dryRunConflictCount
    : (dryRunSummary?.conflictCount ?? readTemplateSlotConflictPreviewSummaryField(dryRunPreview, 'conflict_count'))
  const mutationBehavior = dryRunOverview && dryRunOverview.mutationBehavior !== 'n/a'
    ? dryRunOverview.mutationBehavior
    : (preflightOverview && preflightOverview.mutationBehavior !== 'n/a' ? preflightOverview.mutationBehavior : 'unavailable')
  const blockingBehaviorRaw = dryRunOverview && dryRunOverview.blockingBehavior !== 'n/a'
    ? dryRunOverview.blockingBehavior
    : (preflightOverview && preflightOverview.blockingBehavior !== 'n/a' ? preflightOverview.blockingBehavior : 'non_blocking')
  const blockingBehavior = blockingBehaviorRaw.split('_').join('-')

  return (
    <>
      <p>Read-only template conflict diagnostics overview.</p>
      <p>Selected conflict report: {selectedAvailable ? 'available' : 'unavailable'}</p>
      <p>Selected conflict status: {selectedAvailable ? selectedStatus : 'n/a'}</p>
      <p>Selected conflict count: {selectedAvailable ? selectedConflictCount : 'n/a'}</p>
      <p>Preflight conflict preview: {preflightPreviewAvailable}</p>
      <p>Preflight conflict summary: {preflightSummaryAvailable}</p>
      <p>Preflight conflict status: {preflightResult ? preflightStatus : 'n/a'}</p>
      <p>Preflight conflict count: {preflightResult ? preflightConflictCount : 'n/a'}</p>
      <p>Dry-run conflict preview: {dryRunPreviewAvailable}</p>
      <p>Dry-run conflict summary: {dryRunSummaryAvailable}</p>
      <p>Dry-run conflict status: {dryRunResult ? dryRunStatus : 'n/a'}</p>
      <p>Dry-run conflict count: {dryRunResult ? dryRunConflictCount : 'n/a'}</p>
      <p>Conflict diagnostics mutation behavior: {mutationBehavior}</p>
      <p>Conflict diagnostics blocking behavior: {blockingBehavior}</p>
    </>
  )
}

type TemplateSlotValidationPreflightConsistencyPanelProps = {
  slotValidationData?: SeasonTemplateSlotValidationResponse
  preflightResult?: SeasonBuilderPreflightResponse
  dryRunResult?: SeasonBuilderDryRunBuildResponse
}

export function TemplateSlotValidationPreflightConsistencyPanel({
  slotValidationData,
  preflightResult,
  dryRunResult
}: TemplateSlotValidationPreflightConsistencyPanelProps): JSX.Element {
  if (!slotValidationData) {
    return <p>No structured template slot validation data to compare yet.</p>
  }

  const structuredCodes = Array.from(new Set(slotValidationData.issues.map((issue) => issue.code)))
  const preflightPreviewCodes = readTemplateSlotPreviewIssueCodes(preflightResult?.template_slot_validation_preview)
  const preflightUsesStructuredPreview = hasUsableTemplateSlotPreview(preflightResult?.template_slot_validation_preview)
  const preflightCodes = preflightResult
    ? (preflightUsesStructuredPreview ? preflightPreviewCodes : extractBracketedIssueCodes([...preflightResult.validation_warnings, ...preflightResult.validation_errors]))
    : []
  const dryRunPreviewCodes = readTemplateSlotPreviewIssueCodes(dryRunResult?.template_slot_validation_preview)
  const dryRunUsesStructuredPreview = hasUsableTemplateSlotPreview(dryRunResult?.template_slot_validation_preview)
  const dryRunCodes = dryRunResult
    ? (dryRunUsesStructuredPreview ? dryRunPreviewCodes : extractBracketedIssueCodes([...dryRunResult.validation_warnings, ...dryRunResult.validation_errors]))
    : []

  const preflightMissingCodes = structuredCodes.filter((code) => !preflightCodes.includes(code))
  const dryRunMissingCodes = structuredCodes.filter((code) => !dryRunCodes.includes(code))

  return (
    <>
      <p>Read-only consistency check between structured template slot validation and builder diagnostics.</p>
      <h4>Structured template slot issue codes</h4>
      {structuredCodes.length > 0 ? <ul>{structuredCodes.map((code) => <li key={`structured:${code}`}>{code}</li>)}</ul> : <p>No structured template slot issue codes returned.</p>}
      <h4>Preflight diagnostics issue codes</h4>
      {preflightResult ? <p>Preflight diagnostics issue codes source: {preflightUsesStructuredPreview ? 'structured preview' : 'bracketed validation messages'}</p> : null}
      {preflightResult ? <p>Preflight template slot preview status: {readTemplateSlotPreviewSummaryField(preflightResult.template_slot_validation_preview, 'status')}</p> : null}
      {preflightResult ? <p>Preflight template slot preview issue count: {readTemplateSlotPreviewSummaryField(preflightResult.template_slot_validation_preview, 'issue_count')}</p> : null}
      {preflightResult ? (
        preflightCodes.length > 0 ? <ul>{preflightCodes.map((code) => <li key={`preflight:${code}`}>{code}</li>)}</ul> : <p>No preflight issue codes extracted from diagnostics.</p>
      ) : <p>No builder preflight result to compare yet.</p>}
      {preflightResult ? (
        <>
          <p>{preflightMissingCodes.length === 0 ? 'All structured template slot issue codes are represented in preflight diagnostics.' : 'Some structured template slot issue codes are missing from preflight diagnostics.'}</p>
          {preflightMissingCodes.length > 0 ? <ul>{preflightMissingCodes.map((code) => <li key={`preflight-missing:${code}`}>{code}</li>)}</ul> : null}
        </>
      ) : null}

      <h4>Dry-run diagnostics issue codes</h4>
      {dryRunResult ? <p>Dry-run diagnostics issue codes source: {dryRunUsesStructuredPreview ? 'structured preview' : 'bracketed validation messages'}</p> : null}
      {dryRunResult ? <p>Dry-run template slot preview status: {readTemplateSlotPreviewSummaryField(dryRunResult.template_slot_validation_preview, 'status')}</p> : null}
      {dryRunResult ? <p>Dry-run template slot preview issue count: {readTemplateSlotPreviewSummaryField(dryRunResult.template_slot_validation_preview, 'issue_count')}</p> : null}
      {dryRunResult ? (
        dryRunCodes.length > 0 ? <ul>{dryRunCodes.map((code) => <li key={`dry-run:${code}`}>{code}</li>)}</ul> : <p>No dry-run issue codes extracted from diagnostics.</p>
      ) : <p>No dry-run result to compare yet.</p>}
      {dryRunResult ? (
        <>
          <p>{dryRunMissingCodes.length === 0 ? 'All structured template slot issue codes are represented in dry-run diagnostics.' : 'Some structured template slot issue codes are missing from dry-run diagnostics.'}</p>
          {dryRunMissingCodes.length > 0 ? <ul>{dryRunMissingCodes.map((code) => <li key={`dry-run-missing:${code}`}>{code}</li>)}</ul> : null}
        </>
      ) : null}
    </>
  )
}

type TemplateSlotConflictPreflightConsistencyPanelProps = {
  slotConflictData?: SeasonTemplateSlotConflictReportResponse
  preflightResult?: SeasonBuilderPreflightResponse
  dryRunResult?: SeasonBuilderDryRunBuildResponse
}

export function TemplateSlotConflictPreflightConsistencyPanel({
  slotConflictData,
  preflightResult,
  dryRunResult
}: TemplateSlotConflictPreflightConsistencyPanelProps): JSX.Element {
  if (!slotConflictData) {
    return <p>No structured template slot conflict data to compare yet.</p>
  }
  const structuredCodes = extractConflictCodesFromReport(slotConflictData)
  const preflightPreview = preflightResult?.template_slot_conflict_preview
  const preflightCodes = readTemplateSlotConflictPreviewCodes(preflightPreview)
  const dryRunPreview = dryRunResult?.template_slot_conflict_preview
  const dryRunCodes = readTemplateSlotConflictPreviewCodes(dryRunPreview)
  const preflightMissingCodes = structuredCodes.filter((code) => !preflightCodes.includes(code))
  const dryRunMissingCodes = structuredCodes.filter((code) => !dryRunCodes.includes(code))

  return (
    <>
      <p>Read-only consistency check between selected template slot conflict report and builder conflict previews.</p>
      <p>Structured template slot conflict codes: {structuredCodes.length > 0 ? structuredCodes.join(', ') : 'none'}</p>
      <p>Preflight conflict preview codes: {preflightCodes.length > 0 ? preflightCodes.join(', ') : 'none'}</p>
      {preflightResult ? (
        preflightPreview ? (
          <p>{preflightMissingCodes.length === 0 ? 'All structured template slot conflict codes are represented in preflight preview.' : `Preflight conflict preview is missing structured conflict codes: ${preflightMissingCodes.join(', ')}`}</p>
        ) : (
          <p>Preflight conflict preview is not available.</p>
        )
      ) : (
        <p>No preflight result to compare yet.</p>
      )}
      {preflightResult ? <p>Preflight template slot conflict preview status: {readTemplateSlotConflictPreviewSummaryField(preflightPreview, 'status')}</p> : null}
      {preflightResult ? <p>Preflight template slot conflict preview conflict count: {readTemplateSlotConflictPreviewSummaryField(preflightPreview, 'conflict_count')}</p> : null}

      <p>Dry-run conflict preview codes: {dryRunCodes.length > 0 ? dryRunCodes.join(', ') : 'none'}</p>
      {dryRunResult ? (
        dryRunPreview ? (
          <p>{dryRunMissingCodes.length === 0 ? 'All structured template slot conflict codes are represented in dry-run preview.' : `Dry-run conflict preview is missing structured conflict codes: ${dryRunMissingCodes.join(', ')}`}</p>
        ) : (
          <p>Dry-run conflict preview is not available.</p>
        )
      ) : (
        <p>No dry-run result to compare yet.</p>
      )}
      {dryRunResult ? <p>Dry-run template slot conflict preview status: {readTemplateSlotConflictPreviewSummaryField(dryRunPreview, 'status')}</p> : null}
      {dryRunResult ? <p>Dry-run template slot conflict preview conflict count: {readTemplateSlotConflictPreviewSummaryField(dryRunPreview, 'conflict_count')}</p> : null}
    </>
  )
}

export function DiffPreviewSkeletonPanel({ items }: { items: DiffPreviewItem[] }): JSX.Element {
  return (
    <>
      <p>This is a structural preview of future compare/apply checks. It does not inspect or modify an existing concrete season calendar.</p>
      <table>
        <thead>
          <tr>
            <th scope="col">Area</th>
            <th scope="col">Status</th>
            <th scope="col">Message</th>
          </tr>
        </thead>
        <tbody>
          {items.map((item) => (
            <tr key={`${item.area}:${item.message}`}>
              <td>{item.area}</td>
              <td>{item.status}</td>
              <td>{item.message}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <p>No diff/apply command is executed from this page.</p>
    </>
  )
}

export function SourceTargetDiffDetailPanel({ items }: { items: SourceTargetDiffItem[] }): JSX.Element {
  return (
    <>
      <p>Local structural diff preview only. This is not an authoritative backend diff and does not enable apply actions.</p>
      <table>
        <thead>
          <tr>
            <th scope="col">Area</th>
            <th scope="col">Status</th>
            <th scope="col">Source</th>
            <th scope="col">Target</th>
            <th scope="col">Message</th>
          </tr>
        </thead>
        <tbody>
          {items.map((item) => (
            <tr key={`${item.area}:${item.message}`}>
              <td>{item.area}</td>
              <td>{item.status}</td>
              <td>{item.source}</td>
              <td>{item.target}</td>
              <td>{item.message}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <p>No diff, build, merge, overwrite, or apply command is executed from this page.</p>
    </>
  )
}

type BackendPreflightResultPanelProps = {
  queryEnabled: boolean
  requestPayload: SeasonBuilderPreflightRequest
  query: {
    isLoading: boolean
    error: unknown
    data: SeasonBuilderPreflightResponse | undefined
  }
}

export function BackendPreflightResultPanel({ queryEnabled, requestPayload, query }: BackendPreflightResultPanelProps): JSX.Element {
  if (!queryEnabled) {
    return (
      <>
        <p>Authoritative read-only backend preflight result. This endpoint does not build, merge, overwrite, or apply anything.</p>
        <p>Backend preflight is waiting for target season and executable source selection.</p>
        <p>Even when backend preflight succeeds, build actions remain unavailable in this phase.</p>
      </>
    )
  }

  if (query.isLoading) {
    return (
      <>
        <p>Authoritative read-only backend preflight result. This endpoint does not build, merge, overwrite, or apply anything.</p>
        <p>Loading backend preflight…</p>
      </>
    )
  }

  if (query.error) {
    return (
      <>
        <p>Authoritative read-only backend preflight result. This endpoint does not build, merge, overwrite, or apply anything.</p>
        <p className="error">Backend preflight failed: {formatApiError(query.error)}</p>
        <p>Even when backend preflight succeeds, build actions remain unavailable in this phase.</p>
      </>
    )
  }

  const data = query.data
  if (!data) return <p>Backend preflight is waiting for target season and executable source selection.</p>

  const auditPreview = data.audit_preview ?? {}
  const diffSummary = data.authoritative_diff_summary ?? {}
  const stringifyUnknown = (value: unknown): string => {
    if (value === null || value === undefined) return '—'
    if (typeof value === 'string') return value
    if (typeof value === 'number' || typeof value === 'boolean') return String(value)
    try {
      return JSON.stringify(value)
    } catch {
      return String(value)
    }
  }
  const getRecordValue = (record: Record<string, unknown>, key: string): unknown => record[key]
  const formatNullableBoolean = (value: unknown): string => {
    if (typeof value === 'boolean') return value ? 'Yes' : 'No'
    return '—'
  }
  const formatRangeFromRecord = (value: unknown): { firstWeek: string; lastWeek: string } => {
    if (!value || typeof value !== 'object') return { firstWeek: '—', lastWeek: '—' }
    const rangeRecord = value as Record<string, unknown>
    return {
      firstWeek: stringifyUnknown(rangeRecord.first_week),
      lastWeek: stringifyUnknown(rangeRecord.last_week)
    }
  }
  const sourceRange = formatRangeFromRecord(getRecordValue(diffSummary, 'source_range'))
  const targetRange = formatRangeFromRecord(getRecordValue(diffSummary, 'target_range'))
  const structuralComparisonRaw = getRecordValue(diffSummary, 'structural_comparison')
  const structuralComparison = structuralComparisonRaw && typeof structuralComparisonRaw === 'object'
    ? structuralComparisonRaw as Record<string, unknown>
    : null
  const blockingReasonsRaw = getRecordValue(diffSummary, 'blocking_reasons')
  const blockingReasons = Array.isArray(blockingReasonsRaw) ? blockingReasonsRaw : []
  const advisoryNotesRaw = getRecordValue(diffSummary, 'advisory_notes')
  const advisoryNotes = Array.isArray(advisoryNotesRaw) ? advisoryNotesRaw : []
  const policyPreviewInterpretation = requestPayload.overwrite_policy === null
    ? 'No overwrite/merge policy is selected for this read-only preflight.'
    : requestPayload.overwrite_policy === 'merge_preview'
      ? 'Merge policy preview is selected. This only changes backend preflight analysis and does not execute a merge.'
      : requestPayload.overwrite_policy === 'overwrite_preview'
        ? 'Overwrite policy preview is selected. This only changes backend preflight analysis and does not execute an overwrite.'
        : 'Unsupported policy value is being previewed by the backend preflight.'

  return (
    <>
      <p>Authoritative read-only backend preflight result. This endpoint does not build, merge, overwrite, or apply anything.</p>
      <h4>Status: Blocked in this phase</h4>
      <p>Backend preflight completed, but build actions remain disabled because can_build is false.</p>
      {data.validation_errors.length > 0 ? <p>Blocking validation errors are present.</p> : null}
      {data.validation_warnings.length > 0 ? <p>Advisory validation warnings are present.</p> : null}
      {auditPreview.mutation_permitted === false ? <p>Mutation permitted: false</p> : null}
      <table>
        <thead><tr><th scope="col">Field</th><th scope="col">Value</th></tr></thead>
        <tbody>
          <tr><td>can_build</td><td><strong>{String(data.can_build)}</strong></td></tr>
          <tr><td>target_season_label</td><td>{data.target_season_label}</td></tr>
          <tr><td>source_type</td><td>{data.source_type}</td></tr>
          <tr><td>source_template_id</td><td>{data.source_template_id ?? '—'}</td></tr>
          <tr><td>preflight_fingerprint</td><td>{data.preflight_fingerprint ?? 'Unavailable'}</td></tr>
          <tr><td>reviewed_diff_id</td><td>{data.reviewed_diff_id ?? 'Unavailable'}</td></tr>
          <tr><td>target_calendar_exists</td><td>{String(data.target_calendar_exists)}</td></tr>
          <tr><td>target_event_count</td><td>{String(data.target_event_count)}</td></tr>
          <tr><td>source_resolved</td><td>{String(data.source_resolved)}</td></tr>
          <tr><td>validation_warnings count</td><td>{data.validation_warnings.length}</td></tr>
          <tr><td>validation_errors count</td><td>{data.validation_errors.length}</td></tr>
        </tbody>
      </table>
      <h4>Backend preflight request payload</h4>
      <p>This is the exact read-only payload sent to the backend preflight endpoint.</p>
      <table>
        <thead><tr><th scope="col">Field</th><th scope="col">Value</th></tr></thead>
        <tbody>
          <tr><td>target_season_label</td><td>{requestPayload.target_season_label}</td></tr>
          <tr><td>source_type</td><td>{requestPayload.source_type}</td></tr>
          <tr><td>source_template_id</td><td>{requestPayload.source_template_id ?? '—'}</td></tr>
          <tr><td>overwrite_policy</td><td>{requestPayload.overwrite_policy ?? '—'}</td></tr>
          <tr><td>requested_by</td><td>{requestPayload.requested_by ?? '—'}</td></tr>
        </tbody>
      </table>
      <h4>Policy preview interpretation</h4>
      <p>{policyPreviewInterpretation}</p>
      <p>Policy preview never enables build actions in this phase.</p>
      <h4>Validation warnings</h4>
      {data.validation_warnings.length ? <ul>{data.validation_warnings.map((w)=><li key={w}>{w}</li>)}</ul> : <p>No validation warnings returned.</p>}
      <h4>Validation errors</h4>
      {data.validation_errors.length ? <ul>{data.validation_errors.map((e)=><li key={e}>{e}</li>)}</ul> : <p>No validation errors returned.</p>}
      <h4>Authoritative diff summary</h4>
      <h5>Authoritative diff status</h5>
      <table>
        <thead><tr><th scope="col">Field</th><th scope="col">Value</th></tr></thead>
        <tbody>
          <tr><td>status</td><td>{stringifyUnknown(getRecordValue(diffSummary, 'status'))}</td></tr>
          <tr><td>can_build</td><td>{formatNullableBoolean(getRecordValue(diffSummary, 'can_build'))}</td></tr>
          <tr><td>source_type</td><td>{stringifyUnknown(getRecordValue(diffSummary, 'source_type'))}</td></tr>
          <tr><td>source_resolved</td><td>{formatNullableBoolean(getRecordValue(diffSummary, 'source_resolved'))}</td></tr>
          <tr><td>week_count_compatible</td><td>{formatNullableBoolean(getRecordValue(diffSummary, 'week_count_compatible'))}</td></tr>
        </tbody>
      </table>
      <h5>Source vs target structural summary</h5>
      <table>
        <thead><tr><th scope="col">Field</th><th scope="col">Value</th></tr></thead>
        <tbody>
          <tr><td>source_slot_count</td><td>{stringifyUnknown(getRecordValue(diffSummary, 'source_slot_count'))}</td></tr>
          <tr><td>source_week_count</td><td>{stringifyUnknown(getRecordValue(diffSummary, 'source_week_count'))}</td></tr>
          <tr><td>target_week_count</td><td>{stringifyUnknown(getRecordValue(diffSummary, 'target_week_count'))}</td></tr>
          <tr><td>target_calendar_exists</td><td>{formatNullableBoolean(getRecordValue(diffSummary, 'target_calendar_exists'))}</td></tr>
          <tr><td>target_event_count</td><td>{stringifyUnknown(getRecordValue(diffSummary, 'target_event_count'))}</td></tr>
        </tbody>
      </table>
      <h5>Source and target ranges</h5>
      <table>
        <thead><tr><th scope="col">Field</th><th scope="col">Value</th></tr></thead>
        <tbody>
          <tr><td>source_range first_week</td><td>{sourceRange.firstWeek}</td></tr>
          <tr><td>source_range last_week</td><td>{sourceRange.lastWeek}</td></tr>
          <tr><td>target_range first_week</td><td>{targetRange.firstWeek}</td></tr>
          <tr><td>target_range last_week</td><td>{targetRange.lastWeek}</td></tr>
        </tbody>
      </table>
      <h5>Structural comparison</h5>
      {structuralComparison ? (
        <table>
          <thead><tr><th scope="col">Field</th><th scope="col">Value</th></tr></thead>
          <tbody>
            <tr><td>planned_source_slots</td><td>{stringifyUnknown(getRecordValue(structuralComparison, 'planned_source_slots'))}</td></tr>
            <tr><td>existing_target_events</td><td>{stringifyUnknown(getRecordValue(structuralComparison, 'existing_target_events'))}</td></tr>
            <tr><td>target_is_empty</td><td>{formatNullableBoolean(getRecordValue(structuralComparison, 'target_is_empty'))}</td></tr>
            <tr><td>requires_overwrite_or_merge_policy</td><td>{formatNullableBoolean(getRecordValue(structuralComparison, 'requires_overwrite_or_merge_policy'))}</td></tr>
          </tbody>
        </table>
      ) : <p>No structural comparison returned.</p>}
      <h5>Blocking reasons</h5>
      {blockingReasons.length > 0
        ? <ul>{blockingReasons.map((reason, idx) => <li key={`blocking-${idx}`}>{stringifyUnknown(reason)}</li>)}</ul>
        : <p>No backend blocking reasons returned.</p>}
      <h5>Advisory notes</h5>
      {advisoryNotes.length > 0
        ? (
          <>
            <p>Backend advisory notes returned for this policy/source combination.</p>
            <ul>{advisoryNotes.map((note, idx) => <li key={`advisory-${idx}`}>{stringifyUnknown(note)}</li>)}</ul>
          </>
        )
        : <p>No backend advisory notes returned.</p>}
      <h5>Raw authoritative diff summary JSON</h5>
      <pre>{JSON.stringify(data.authoritative_diff_summary, null, 2)}</pre>
      <h4>Audit preview</h4>
      <table>
        <thead><tr><th scope="col">Field</th><th scope="col">Value</th></tr></thead>
        <tbody>
          <tr><td>action</td><td>{String(auditPreview.action ?? '—')}</td></tr>
          <tr><td>requested_by</td><td>{String(auditPreview.requested_by ?? '—')}</td></tr>
          <tr><td>target_season_label</td><td>{String(auditPreview.target_season_label ?? '—')}</td></tr>
          <tr><td>source_type</td><td>{String(auditPreview.source_type ?? '—')}</td></tr>
          <tr><td>source_template_id</td><td>{String(auditPreview.source_template_id ?? '—')}</td></tr>
          <tr><td>overwrite_policy</td><td>{String(auditPreview.overwrite_policy ?? '—')}</td></tr>
          <tr><td>read_only</td><td>{String(auditPreview.read_only ?? '—')}</td></tr>
          <tr><td>mutation_permitted</td><td>{String(auditPreview.mutation_permitted ?? '—')}</td></tr>
        </tbody>
      </table>
      <pre>{JSON.stringify(data.audit_preview, null, 2)}</pre>
      <p>Even when backend preflight succeeds, build actions remain unavailable in this phase.</p>
    </>
  )
}

export function BackendPreflightContractPreviewPanel({ items }: { items: BackendPreflightContractItem[] }): JSX.Element {
  return (
    <>
      <p>Read-only design preview. No backend preflight endpoint is called from this page.</p>
      <table>
        <thead>
          <tr>
            <th scope="col">Area</th>
            <th scope="col">Required future field</th>
            <th scope="col">Reason</th>
          </tr>
        </thead>
        <tbody>
          {items.map((item) => (
            <tr key={`${item.area}:${item.required}`}>
              <td>{item.area}</td>
              <td>{item.required}</td>
              <td>{item.reason}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <p>Future implementation must add an authoritative backend preflight before any build, merge, overwrite, or apply command can exist.</p>
    </>
  )
}

export function buildFutureBuildCommandContractItems(): FutureBuildCommandContractItem[] {
  return [
    { area: 'Target season', required: 'target_season_label', reason: 'Build command must identify one concrete target season.' },
    { area: 'Source type', required: 'source_type', reason: 'Build command must distinguish template/copy/blank/custom workflows.' },
    { area: 'Source reference', required: 'source_template_id or future source identifier', reason: 'Build command must resolve its source deterministically.' },
    { area: 'Policy', required: 'overwrite_policy', reason: 'Existing calendars must never be changed without explicit merge/overwrite intent.' },
    { area: 'Backend preflight fingerprint', required: 'preflight_fingerprint', reason: 'Future build command must prove it is based on a reviewed backend preflight result.' },
    { area: 'Audit actor', required: 'requested_by / admin actor', reason: 'Every future mutation must be attributable.' },
    { area: 'Audit reason', required: 'audit_reason', reason: 'Admin must explain why a build/merge/overwrite is being performed.' },
    { area: 'Determinism', required: 'seed / template_version / config_hash', reason: 'Future build output must be reproducible.' },
    { area: 'Confirmation phrase', required: 'explicit_confirmation', reason: 'Dangerous operations must require explicit confirmation, especially overwrite.' },
    { area: 'Dry-run result reference', required: 'reviewed_diff_id or dry_run_result_id', reason: 'Build command must reference an already reviewed authoritative diff.' },
    { area: 'Mutation scope', required: 'mutation_scope', reason: 'Future implementation must distinguish create-only, merge, overwrite, and repair scopes.' }
  ]
}

type FutureBuildCommandContractPanelProps = {
  items: FutureBuildCommandContractItem[]
  currentPreflightPayload?: SeasonBuilderPreflightRequest
  currentPreflightResult?: SeasonBuilderPreflightResponse
}

export function FutureBuildCommandContractPanel({ items, currentPreflightPayload, currentPreflightResult }: FutureBuildCommandContractPanelProps): JSX.Element {
  const auditPreview = currentPreflightResult?.audit_preview as Record<string, unknown> | undefined
  const mutationPermittedValue = typeof auditPreview?.mutation_permitted === 'boolean'
    ? String(auditPreview.mutation_permitted)
    : 'Unavailable'
  return (
    <>
      <p>Read-only contract preview. No build command exists on this page.</p>
      <table>
        <thead>
          <tr>
            <th scope="col">Area</th>
            <th scope="col">Required future field</th>
            <th scope="col">Reason</th>
          </tr>
        </thead>
        <tbody>
          {items.map((item) => (
            <tr key={`${item.area}:${item.required}`}>
              <td>{item.area}</td>
              <td>{item.required}</td>
              <td>{item.reason}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <h4>Current preflight signals</h4>
      <table>
        <thead><tr><th scope="col">Signal</th><th scope="col">Value</th></tr></thead>
        <tbody>
          <tr><td>target_season_label</td><td>{currentPreflightPayload?.target_season_label ?? 'Unavailable'}</td></tr>
          <tr><td>source_type</td><td>{currentPreflightPayload?.source_type ?? 'Unavailable'}</td></tr>
          <tr><td>source_template_id</td><td>{currentPreflightPayload?.source_template_id ?? 'Unavailable'}</td></tr>
          <tr><td>overwrite_policy</td><td>{currentPreflightPayload?.overwrite_policy ?? 'Unavailable'}</td></tr>
          <tr><td>preflight_fingerprint</td><td>{currentPreflightResult?.preflight_fingerprint ?? 'Unavailable'}</td></tr>
          <tr><td>reviewed_diff_id</td><td>{currentPreflightResult?.reviewed_diff_id ?? 'Unavailable'}</td></tr>
          <tr><td>can_build</td><td>{currentPreflightResult ? String(currentPreflightResult.can_build) : 'Unavailable'}</td></tr>
          <tr><td>source_resolved</td><td>{currentPreflightResult ? String(currentPreflightResult.source_resolved) : 'Unavailable'}</td></tr>
          <tr><td>validation_errors count</td><td>{currentPreflightResult ? String(currentPreflightResult.validation_errors.length) : 'Unavailable'}</td></tr>
          <tr><td>validation_warnings count</td><td>{currentPreflightResult ? String(currentPreflightResult.validation_warnings.length) : 'Unavailable'}</td></tr>
          <tr><td>mutation_permitted</td><td>{mutationPermittedValue}</td></tr>
        </tbody>
      </table>
      <p>Future build implementation must require a reviewed backend preflight, explicit audit metadata, and a separate audited command.</p>
    </>
  )
}

type BuildFutureCommandReadinessItemsArgs = {
  currentPreflightPayload?: SeasonBuilderPreflightRequest
  currentPreflightResult?: SeasonBuilderPreflightResponse
}

export function buildFutureCommandReadinessItems({
  currentPreflightPayload,
  currentPreflightResult
}: BuildFutureCommandReadinessItemsArgs): FutureCommandReadinessItem[] {
  const validationErrorCount = currentPreflightResult?.validation_errors.length
  const validationWarningCount = currentPreflightResult?.validation_warnings.length
  const sourceType = currentPreflightPayload?.source_type
  const sourceTemplateId = currentPreflightPayload?.source_template_id

  return [
    currentPreflightPayload?.target_season_label
      ? { area: 'Target season', status: 'OK', message: `Selected target season: ${currentPreflightPayload.target_season_label}.` }
      : { area: 'Target season', status: 'Missing', message: 'Target season is not selected yet.' },
    sourceType
      ? sourceType !== 'season_template' || Boolean(sourceTemplateId)
        ? { area: 'Source reference', status: 'OK', message: sourceType === 'season_template' ? `Season template source selected: ${sourceTemplateId}.` : `Planned source selected: ${sourceType}.` }
        : { area: 'Source reference', status: 'Missing', message: 'Season template source is selected but source_template_id is missing.' }
      : { area: 'Source reference', status: 'Missing', message: 'Source type is not selected yet.' },
    currentPreflightPayload?.overwrite_policy
      ? { area: 'Policy input', status: 'OK', message: `Overwrite/merge policy selected: ${currentPreflightPayload.overwrite_policy}.` }
      : { area: 'Policy input', status: 'Info', message: 'No overwrite/merge policy selected; acceptable for empty target preview but existing calendars require explicit future policy.' },
    currentPreflightResult?.preflight_fingerprint
      ? { area: 'Preflight fingerprint', status: 'OK', message: 'Backend preflight fingerprint is available.' }
      : { area: 'Preflight fingerprint', status: 'Missing', message: 'Backend preflight fingerprint is not available yet.' },
    currentPreflightResult?.reviewed_diff_id
      ? { area: 'Reviewed diff identity', status: 'OK', message: 'Reviewed diff identity is available.' }
      : { area: 'Reviewed diff identity', status: 'Missing', message: 'Reviewed diff identity is not available yet.' },
    currentPreflightResult
      ? currentPreflightResult.source_resolved
        ? { area: 'Source resolved', status: 'OK', message: 'Source resolved is true.' }
        : { area: 'Source resolved', status: 'Blocked', message: 'Source resolved is false.' }
      : { area: 'Source resolved', status: 'Missing', message: 'Source resolution is unavailable until preflight result is returned.' },
    typeof validationErrorCount === 'number'
      ? validationErrorCount === 0
        ? { area: 'Validation errors', status: 'OK', message: `Validation errors count: ${validationErrorCount}.` }
        : { area: 'Validation errors', status: 'Blocked', message: `Validation errors count: ${validationErrorCount}.` }
      : { area: 'Validation errors', status: 'Missing', message: 'Validation errors count is unavailable until preflight result is returned.' },
    typeof validationWarningCount === 'number'
      ? validationWarningCount === 0
        ? { area: 'Validation warnings', status: 'OK', message: `Validation warnings count: ${validationWarningCount}.` }
        : { area: 'Validation warnings', status: 'Info', message: `Validation warnings count: ${validationWarningCount}.` }
      : { area: 'Validation warnings', status: 'Missing', message: 'Validation warnings count is unavailable until preflight result is returned.' },
    { area: 'Mutation permission', status: 'Blocked', message: 'mutation_permitted is false; this page cannot mutate calendars.' },
    currentPreflightResult
      ? currentPreflightResult.can_build === false
        ? { area: 'can_build flag', status: 'Blocked', message: 'can_build is false; future command remains unavailable.' }
        : { area: 'can_build flag', status: 'Info', message: `can_build is ${String(currentPreflightResult.can_build)}.` }
      : { area: 'can_build flag', status: 'Missing', message: 'can_build is unavailable until preflight result is returned.' },
    { area: 'Command implementation', status: 'Blocked', message: 'No build command exists on this page.' }
  ]
}

export function FutureCommandReadinessChecklistPanel({ items }: { items: FutureCommandReadinessItem[] }): JSX.Element {
  return (
    <>
      <p>Read-only checklist. This summarizes future command prerequisites but does not enable any command.</p>
      <table>
        <thead>
          <tr>
            <th scope="col">Area</th>
            <th scope="col">Status</th>
            <th scope="col">Message</th>
          </tr>
        </thead>
        <tbody>
          {items.map((item) => (
            <tr key={`${item.area}:${item.status}`}>
              <td>{item.area}</td>
              <td>{item.status}</td>
              <td>{item.message}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <p>Readiness remains blocked until a separate audited backend command is implemented.</p>
    </>
  )
}

export function buildDisabledDryRunReadinessItems({
  requestPayload,
  response
}: {
  requestPayload?: SeasonBuilderDryRunBuildRequest
  response?: SeasonBuilderDryRunBuildResponse
}): DisabledDryRunReadinessItem[] {
  const warningCount = response?.validation_warnings.length
  const errorCount = response?.validation_errors.length
  return [
    response
      ? { area: 'Contract endpoint', status: 'OK', message: 'Disabled dry-run contract endpoint returned a response.' }
      : { area: 'Contract endpoint', status: 'Missing', message: 'Disabled dry-run contract endpoint has not returned a response yet.' },
    response
      ? response.enabled === false && response.can_execute === false
        ? { area: 'Execution flag', status: 'Blocked', message: 'Execution is disabled in this phase.' }
        : { area: 'Execution flag', status: 'Info', message: 'Execution is disabled in this phase.' }
      : { area: 'Execution flag', status: 'Info', message: 'Execution is disabled in this phase.' },
    response
      ? response.can_mutate === false
        ? { area: 'Mutation flag', status: 'Blocked', message: 'can_mutate is false; no calendar mutation is permitted.' }
        : { area: 'Mutation flag', status: 'Info', message: 'can_mutate is false; no calendar mutation is permitted.' }
      : { area: 'Mutation flag', status: 'Info', message: 'can_mutate is false; no calendar mutation is permitted.' },
    requestPayload?.preflight_fingerprint && requestPayload.reviewed_diff_id
      ? { area: 'Preflight identity', status: 'OK', message: 'Preflight fingerprint and reviewed diff identity are present.' }
      : { area: 'Preflight identity', status: 'Missing', message: 'Preflight identity is incomplete.' },
    requestPayload?.audit_reason
      ? { area: 'Audit reason', status: 'OK', message: 'Audit reason preview is present.' }
      : { area: 'Audit reason', status: 'Info', message: 'Audit reason preview is not filled yet.' },
    requestPayload?.explicit_confirmation
      ? { area: 'Explicit confirmation', status: 'OK', message: 'Explicit confirmation preview is present.' }
      : { area: 'Explicit confirmation', status: 'Info', message: 'Explicit confirmation preview is not filled yet.' },
    requestPayload?.mutation_scope
      ? { area: 'Mutation scope', status: 'OK', message: 'Mutation scope preview is present.' }
      : { area: 'Mutation scope', status: 'Info', message: 'Mutation scope preview is not selected yet.' },
    typeof warningCount === 'number'
      ? warningCount === 0
        ? { area: 'Validation warnings', status: 'OK', message: `Validation warnings count: ${warningCount}.` }
        : { area: 'Validation warnings', status: 'Info', message: `Validation warnings count: ${warningCount}.` }
      : { area: 'Validation warnings', status: 'Missing', message: 'Validation warnings count: unavailable.' },
    typeof errorCount === 'number'
      ? errorCount === 0
        ? { area: 'Validation errors', status: 'OK', message: `Validation errors count: ${errorCount}.` }
        : { area: 'Validation errors', status: 'Blocked', message: `Validation errors count: ${errorCount}.` }
      : { area: 'Validation errors', status: 'Missing', message: 'Validation errors count: unavailable.' },
    { area: 'Next implementation step', status: 'Blocked', message: 'Real dry-run generation is not implemented yet.' }
  ]
}

export function DisabledDryRunReadinessSummaryPanel({ items }: { items: DisabledDryRunReadinessItem[] }): JSX.Element {
  return (
    <>
      <p>Read-only summary of the disabled dry-run contract state.</p>
      <table>
        <thead>
          <tr>
            <th scope="col">Area</th>
            <th scope="col">Status</th>
            <th scope="col">Message</th>
          </tr>
        </thead>
        <tbody>
          {items.map((item) => (
            <tr key={`${item.area}:${item.status}`}>
              <td>{item.area}</td>
              <td>{item.status}</td>
              <td>{item.message}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <p>The dry-run contract is visible, but execution remains disabled.</p>
    </>
  )
}

export function buildApplyCommandReadinessItems({
  dryRunResponse,
  applyContractResponse,
  applyRequestPayload
}: {
  dryRunResponse?: SeasonBuilderDryRunBuildResponse
  applyContractResponse?: SeasonBuilderApplyCommandContractResponse
  applyRequestPayload?: SeasonBuilderApplyCommandContractRequest
}): ApplyCommandReadinessItem[] {
  const identityReadinessStatusValue = ((dryRunResponse?.dry_run_result_preview as Record<string, unknown> | undefined)?.identity_readiness as Record<string, unknown> | undefined)?.status
  const identityReadinessStatus = typeof identityReadinessStatusValue === 'string' ? identityReadinessStatusValue : undefined
  const validationErrorCount = applyContractResponse?.validation_errors.length
  const validationWarningCount = applyContractResponse?.validation_warnings.length
  return [
    applyContractResponse
      ? { area: 'Apply contract endpoint', status: 'OK', message: 'Disabled apply command contract endpoint returned a response.' }
      : { area: 'Apply contract endpoint', status: 'Missing', message: 'Disabled apply command contract endpoint has not returned a response yet.' },
    applyContractResponse
      ? applyContractResponse.enabled === false && applyContractResponse.can_execute === false
        ? { area: 'Execution flag', status: 'Blocked', message: 'Apply execution is disabled in this phase.' }
        : { area: 'Execution flag', status: 'Info', message: 'Apply execution is disabled in this phase.' }
      : { area: 'Execution flag', status: 'Info', message: 'Apply execution is disabled in this phase.' },
    applyContractResponse
      ? applyContractResponse.can_mutate === false
        ? { area: 'Mutation flag', status: 'Blocked', message: 'can_mutate is false; no calendar mutation is permitted.' }
        : { area: 'Mutation flag', status: 'Info', message: 'can_mutate is false; no calendar mutation is permitted.' }
      : { area: 'Mutation flag', status: 'Info', message: 'can_mutate is false; no calendar mutation is permitted.' },
    applyRequestPayload?.preflight_fingerprint && applyRequestPayload.reviewed_diff_id
      ? { area: 'Preflight identity', status: 'OK', message: 'Preflight fingerprint and reviewed diff identity are present.' }
      : { area: 'Preflight identity', status: 'Missing', message: 'Preflight identity is incomplete.' },
    applyRequestPayload?.dry_run_result_fingerprint && applyRequestPayload.dry_run_result_id
      ? { area: 'Dry-run result identity', status: 'OK', message: 'Dry-run result fingerprint and id are present.' }
      : { area: 'Dry-run result identity', status: 'Missing', message: 'Dry-run result identity is incomplete.' },
    applyContractResponse
      ? applyContractResponse.required_identity.all_identity_fields_present === true
        ? { area: 'Required identity contract', status: 'OK', message: 'Apply contract reports all identity fields present.' }
        : { area: 'Required identity contract', status: 'Missing', message: 'Apply contract reports missing identity fields.' }
      : { area: 'Required identity contract', status: 'Info', message: 'Apply contract reports missing identity fields.' },
    applyContractResponse
      ? applyContractResponse.required_audit_metadata.all_audit_metadata_present === true
        ? { area: 'Required audit metadata', status: 'OK', message: 'Apply contract reports all audit metadata present.' }
        : { area: 'Required audit metadata', status: 'Info', message: 'Apply audit metadata is not complete yet.' }
      : { area: 'Required audit metadata', status: 'Info', message: 'Apply audit metadata is not complete yet.' },
    identityReadinessStatus === 'ready_reference'
      ? { area: 'Dry-run identity readiness', status: 'OK', message: `Dry-run identity readiness status: ${identityReadinessStatus}.` }
      : identityReadinessStatus === 'blocked_reference'
        ? { area: 'Dry-run identity readiness', status: 'Blocked', message: `Dry-run identity readiness status: ${identityReadinessStatus}.` }
        : identityReadinessStatus === 'missing_identity'
          ? { area: 'Dry-run identity readiness', status: 'Missing', message: `Dry-run identity readiness status: ${identityReadinessStatus}.` }
          : { area: 'Dry-run identity readiness', status: 'Info', message: `Dry-run identity readiness status: ${identityReadinessStatus ?? 'unavailable'}.` },
    typeof validationErrorCount === 'number'
      ? validationErrorCount === 0
        ? { area: 'Validation errors', status: 'OK', message: `Apply validation errors count: ${validationErrorCount}.` }
        : { area: 'Validation errors', status: 'Blocked', message: `Apply validation errors count: ${validationErrorCount}.` }
      : { area: 'Validation errors', status: 'Missing', message: 'Apply validation errors count: unavailable.' },
    typeof validationWarningCount === 'number'
      ? validationWarningCount === 0
        ? { area: 'Validation warnings', status: 'OK', message: `Apply validation warnings count: ${validationWarningCount}.` }
        : { area: 'Validation warnings', status: 'Info', message: `Apply validation warnings count: ${validationWarningCount}.` }
      : { area: 'Validation warnings', status: 'Missing', message: 'Apply validation warnings count: unavailable.' },
    { area: 'Next implementation step', status: 'Blocked', message: 'Real apply execution is not implemented yet.' }
  ]
}

export function ApplyCommandReadinessSummaryPanel({ items }: { items: ApplyCommandReadinessItem[] }): JSX.Element {
  return (
    <>
      <p>Read-only summary of the disabled apply command contract state.</p>
      <table>
        <thead>
          <tr>
            <th scope="col">Area</th>
            <th scope="col">Status</th>
            <th scope="col">Message</th>
          </tr>
        </thead>
        <tbody>
          {items.map((item) => (
            <tr key={`${item.area}:${item.status}`}>
              <td>{item.area}</td>
              <td>{item.status}</td>
              <td>{item.message}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <p>The apply command contract is visible, but execution remains disabled.</p>
    </>
  )
}

type DryRunAuditMetadataPreviewPanelProps = {
  auditReason: string
  setAuditReason: (value: string) => void
  explicitConfirmation: string
  setExplicitConfirmation: (value: string) => void
  mutationScope: string
  setMutationScope: (value: string) => void
}

export function DryRunAuditMetadataPreviewPanel({
  auditReason,
  setAuditReason,
  explicitConfirmation,
  setExplicitConfirmation,
  mutationScope,
  setMutationScope
}: DryRunAuditMetadataPreviewPanelProps): JSX.Element {
  return (
    <>
      <p>Read-only preview inputs. These fields only change the disabled dry-run contract payload.</p>
      <p>
        <label htmlFor="dry-run-audit-reason-preview">Future audit reason preview</label><br />
        <textarea
          id="dry-run-audit-reason-preview"
          value={auditReason}
          onChange={(event) => setAuditReason(event.target.value)}
          rows={3}
        />
      </p>
      <p>
        <label htmlFor="dry-run-explicit-confirmation-preview">Future explicit confirmation preview</label><br />
        <input
          id="dry-run-explicit-confirmation-preview"
          value={explicitConfirmation}
          onChange={(event) => setExplicitConfirmation(event.target.value)}
        />
      </p>
      <p>
        <label htmlFor="dry-run-mutation-scope-preview">Future mutation scope preview</label><br />
        <select
          id="dry-run-mutation-scope-preview"
          value={mutationScope}
          onChange={(event) => setMutationScope(event.target.value)}
        >
          <option value="">No mutation scope selected</option>
          <option value="create_only_preview">Create-only preview</option>
          <option value="merge_preview">Merge preview</option>
          <option value="overwrite_preview">Overwrite preview</option>
          <option value="repair_preview">Repair preview</option>
        </select>
      </p>
      <p>These values are not submitted as a command and do not enable execution.</p>
      <p>Changing these fields only re-runs the disabled dry-run contract check.</p>
    </>
  )
}

type DisabledDryRunBuildContractPanelProps = {
  queryEnabled: boolean
  requestPayload: SeasonBuilderDryRunBuildRequest
  query: {
    isLoading: boolean
    error: unknown
    data: SeasonBuilderDryRunBuildResponse | undefined
  }
}

export function DisabledDryRunBuildContractPanel({ queryEnabled, requestPayload, query }: DisabledDryRunBuildContractPanelProps): JSX.Element {
  const formatValue = (value: unknown): string => (value === null || value === undefined ? '—' : String(value))
  const auditPreview = query.data?.audit_preview ?? {}
  const generationDesignPreview = query.data?.generation_design_preview
  const candidateEventContractPreview = query.data?.candidate_event_contract_preview
  const conflictContractPreview = query.data?.conflict_contract_preview
  const dryRunResultContractPreview = query.data?.dry_run_result_contract_preview
  const dryRunResultPreview = query.data?.dry_run_result_preview
  const generationDesignPreviewRecord = generationDesignPreview && typeof generationDesignPreview === 'object'
    ? generationDesignPreview as Record<string, unknown>
    : null
  const candidateEventContractPreviewRecord = candidateEventContractPreview && typeof candidateEventContractPreview === 'object'
    ? candidateEventContractPreview as Record<string, unknown>
    : null
  const conflictContractPreviewRecord = conflictContractPreview && typeof conflictContractPreview === 'object'
    ? conflictContractPreview as Record<string, unknown>
    : null
  const dryRunResultContractPreviewRecord = dryRunResultContractPreview && typeof dryRunResultContractPreview === 'object'
    ? dryRunResultContractPreview as Record<string, unknown>
    : null
  const dryRunResultPreviewRecord = dryRunResultPreview && typeof dryRunResultPreview === 'object'
    ? dryRunResultPreview as Record<string, unknown>
    : null
  const shapeRecord = (value: unknown): Record<string, unknown> | null => value && typeof value === 'object' ? value as Record<string, unknown> : null
  const previewList = (value: unknown): unknown[] => Array.isArray(value) ? value : []

  return (
    <>
      <p>Read-only disabled command contract check. This does not build, merge, overwrite, or apply anything.</p>
      {!queryEnabled ? <p>Dry-run build contract check is waiting for backend preflight fingerprint and reviewed diff identity.</p> : null}
      {queryEnabled && query.isLoading ? <p>Loading disabled dry-run build contract…</p> : null}
      {queryEnabled && query.error ? <p className="error">Disabled dry-run build contract check failed: {formatApiError(query.error)}</p> : null}
      {queryEnabled && query.data ? (
        <>
          <table>
            <thead><tr><th scope="col">Field</th><th scope="col">Value</th></tr></thead>
            <tbody>
              <tr><td>command</td><td>{query.data.command}</td></tr>
              <tr><td>enabled</td><td>{String(query.data.enabled)}</td></tr>
              <tr><td>can_execute</td><td>{String(query.data.can_execute)}</td></tr>
              <tr><td>can_mutate</td><td>{String(query.data.can_mutate)}</td></tr>
              <tr><td>target_season_label</td><td>{query.data.target_season_label}</td></tr>
              <tr><td>source_type</td><td>{query.data.source_type}</td></tr>
              <tr><td>source_template_id</td><td>{query.data.source_template_id ?? '—'}</td></tr>
              <tr><td>overwrite_policy</td><td>{query.data.overwrite_policy ?? '—'}</td></tr>
              <tr><td>preflight_fingerprint</td><td>{query.data.preflight_fingerprint}</td></tr>
              <tr><td>reviewed_diff_id</td><td>{query.data.reviewed_diff_id}</td></tr>
              <tr><td>validation_errors count</td><td>{query.data.validation_errors.length}</td></tr>
              <tr><td>validation_warnings count</td><td>{query.data.validation_warnings.length}</td></tr>
              <tr><td>message</td><td>{query.data.message}</td></tr>
            </tbody>
          </table>
          <h4>Validation warnings</h4>
          {query.data.validation_warnings.length === 0 ? <p>No dry-run build contract warnings returned.</p> : <ul>{query.data.validation_warnings.map((warning) => <li key={warning}>{warning}</li>)}</ul>}
          <h4>Validation errors</h4>
          {query.data.validation_errors.length === 0 ? <p>No dry-run build contract errors returned.</p> : <ul>{query.data.validation_errors.map((error) => <li key={error}>{error}</li>)}</ul>}
          <h4>Audit preview</h4>
          <table>
            <thead><tr><th scope="col">Field</th><th scope="col">Value</th></tr></thead>
            <tbody>
              <tr><td>action</td><td>{formatValue(auditPreview.action)}</td></tr>
              <tr><td>read_only</td><td>{formatValue(auditPreview.read_only)}</td></tr>
              <tr><td>mutation_permitted</td><td>{formatValue(auditPreview.mutation_permitted)}</td></tr>
              <tr><td>execution_enabled</td><td>{formatValue(auditPreview.execution_enabled)}</td></tr>
              <tr><td>target_season_label</td><td>{formatValue(auditPreview.target_season_label)}</td></tr>
              <tr><td>source_type</td><td>{formatValue(auditPreview.source_type)}</td></tr>
              <tr><td>source_template_id</td><td>{formatValue(auditPreview.source_template_id)}</td></tr>
              <tr><td>overwrite_policy</td><td>{formatValue(auditPreview.overwrite_policy)}</td></tr>
              <tr><td>preflight_fingerprint</td><td>{formatValue(auditPreview.preflight_fingerprint)}</td></tr>
              <tr><td>reviewed_diff_id</td><td>{formatValue(auditPreview.reviewed_diff_id)}</td></tr>
              <tr><td>requested_by</td><td>{formatValue(auditPreview.requested_by)}</td></tr>
              <tr><td>audit_reason</td><td>{formatValue(auditPreview.audit_reason)}</td></tr>
              <tr><td>explicit_confirmation_present</td><td>{formatValue(auditPreview.explicit_confirmation_present)}</td></tr>
              <tr><td>mutation_scope</td><td>{formatValue(auditPreview.mutation_scope)}</td></tr>
              <tr><td>generation_design_preview_available</td><td>{formatValue(auditPreview.generation_design_preview_available)}</td></tr>
              <tr><td>candidate_event_contract_preview_available</td><td>{formatValue(auditPreview.candidate_event_contract_preview_available)}</td></tr>
              <tr><td>conflict_contract_preview_available</td><td>{formatValue(auditPreview.conflict_contract_preview_available)}</td></tr>
              <tr><td>dry_run_result_contract_preview_available</td><td>{formatValue(auditPreview.dry_run_result_contract_preview_available)}</td></tr>
              <tr><td>dry_run_result_preview_available</td><td>{formatValue(auditPreview.dry_run_result_preview_available)}</td></tr>
              <tr><td>dry_run_result_identity_available</td><td>{formatValue(auditPreview.dry_run_result_identity_available)}</td></tr>
            </tbody>
          </table>
          <h4>Future dry-run generation design preview</h4>
          {generationDesignPreviewRecord ? (
            <>
              <table>
                <thead><tr><th scope="col">Field</th><th scope="col">Value</th></tr></thead>
                <tbody>
                  <tr><td>status</td><td>{formatValue(generationDesignPreviewRecord.status)}</td></tr>
                  <tr><td>execution_enabled</td><td>{formatValue(generationDesignPreviewRecord.execution_enabled)}</td></tr>
                  <tr><td>will_generate_events</td><td>{formatValue(generationDesignPreviewRecord.will_generate_events)}</td></tr>
                  <tr><td>will_persist_calendar</td><td>{formatValue(generationDesignPreviewRecord.will_persist_calendar)}</td></tr>
                  <tr><td>will_mutate_existing_calendar</td><td>{formatValue(generationDesignPreviewRecord.will_mutate_existing_calendar)}</td></tr>
                  <tr><td>blocked_reason</td><td>{formatValue(generationDesignPreviewRecord.blocked_reason)}</td></tr>
                </tbody>
              </table>
              <h5>Planned steps</h5>
              {previewList(generationDesignPreviewRecord.planned_steps).length === 0 ? <p>No planned steps returned.</p> : (
                <ul>{previewList(generationDesignPreviewRecord.planned_steps).map((step, idx) => <li key={`planned-step-${idx}`}>{formatValue(step)}</li>)}</ul>
              )}
              <h5>Required future inputs</h5>
              {previewList(generationDesignPreviewRecord.required_future_inputs).length === 0 ? <p>No required future inputs returned.</p> : (
                <ul>{previewList(generationDesignPreviewRecord.required_future_inputs).map((input, idx) => <li key={`required-input-${idx}`}>{formatValue(input)}</li>)}</ul>
              )}
              <h5>Planned output sections</h5>
              {previewList(generationDesignPreviewRecord.planned_output_sections).length === 0 ? <p>No planned output sections returned.</p> : (
                <ul>{previewList(generationDesignPreviewRecord.planned_output_sections).map((section, idx) => <li key={`planned-output-${idx}`}>{formatValue(section)}</li>)}</ul>
              )}
            </>
          ) : <p>Future dry-run generation design preview is unavailable.</p>}
          <h4>Candidate event contract preview</h4>
          {candidateEventContractPreviewRecord ? (
            <>
              <table>
                <thead><tr><th scope="col">Field</th><th scope="col">Value</th></tr></thead>
                <tbody>
                  <tr><td>status</td><td>{formatValue(candidateEventContractPreviewRecord.status)}</td></tr>
                  <tr><td>will_generate_candidates</td><td>{formatValue(candidateEventContractPreviewRecord.will_generate_candidates)}</td></tr>
                  <tr><td>candidate_count</td><td>{formatValue(candidateEventContractPreviewRecord.candidate_count)}</td></tr>
                  <tr><td>blocked_reason</td><td>{formatValue(candidateEventContractPreviewRecord.blocked_reason)}</td></tr>
                </tbody>
              </table>
              <h5>Candidate event shape</h5>
              {shapeRecord(candidateEventContractPreviewRecord.event_shape) ? (
                <table>
                  <thead><tr><th scope="col">Field</th><th scope="col">Value</th></tr></thead>
                  <tbody>{Object.entries(shapeRecord(candidateEventContractPreviewRecord.event_shape) ?? {}).map(([key, value]) => <tr key={`event-shape-${key}`}><td>{key}</td><td>{formatValue(value)}</td></tr>)}</tbody>
                </table>
              ) : <p>Candidate event shape is unavailable.</p>}
              <h5>Structural summary shape</h5>
              {shapeRecord(candidateEventContractPreviewRecord.structural_summary_shape) ? (
                <table>
                  <thead><tr><th scope="col">Field</th><th scope="col">Value</th></tr></thead>
                  <tbody>{Object.entries(shapeRecord(candidateEventContractPreviewRecord.structural_summary_shape) ?? {}).map(([key, value]) => <tr key={`structural-shape-${key}`}><td>{key}</td><td>{formatValue(value)}</td></tr>)}</tbody>
                </table>
              ) : <p>Structural summary shape is unavailable.</p>}
              <h5>Conflict summary shape</h5>
              {shapeRecord(candidateEventContractPreviewRecord.conflict_summary_shape) ? (
                <table>
                  <thead><tr><th scope="col">Field</th><th scope="col">Value</th></tr></thead>
                  <tbody>{Object.entries(shapeRecord(candidateEventContractPreviewRecord.conflict_summary_shape) ?? {}).map(([key, value]) => <tr key={`conflict-shape-${key}`}><td>{key}</td><td>{formatValue(value)}</td></tr>)}</tbody>
                </table>
              ) : <p>Conflict summary shape is unavailable.</p>}
            </>
          ) : <p>Candidate event contract preview is unavailable.</p>}
          <h4>Conflict contract preview</h4>
          {conflictContractPreviewRecord ? (
            <>
              <table>
                <thead><tr><th scope="col">Field</th><th scope="col">Value</th></tr></thead>
                <tbody>
                  <tr><td>status</td><td>{formatValue(conflictContractPreviewRecord.status)}</td></tr>
                  <tr><td>will_compute_conflicts</td><td>{formatValue(conflictContractPreviewRecord.will_compute_conflicts)}</td></tr>
                  <tr><td>conflict_count</td><td>{formatValue(conflictContractPreviewRecord.conflict_count)}</td></tr>
                  <tr><td>blocked_reason</td><td>{formatValue(conflictContractPreviewRecord.blocked_reason)}</td></tr>
                </tbody>
              </table>
              <h5>Week conflict shape</h5>
              {shapeRecord(conflictContractPreviewRecord.week_conflict_shape) ? <table><thead><tr><th scope="col">Field</th><th scope="col">Value</th></tr></thead><tbody>{Object.entries(shapeRecord(conflictContractPreviewRecord.week_conflict_shape) ?? {}).map(([key, value]) => <tr key={`week-conflict-shape-${key}`}><td>{key}</td><td>{formatValue(value)}</td></tr>)}</tbody></table> : <p>Week conflict shape is unavailable.</p>}
              <h5>Slot conflict shape</h5>
              {shapeRecord(conflictContractPreviewRecord.slot_conflict_shape) ? <table><thead><tr><th scope="col">Field</th><th scope="col">Value</th></tr></thead><tbody>{Object.entries(shapeRecord(conflictContractPreviewRecord.slot_conflict_shape) ?? {}).map(([key, value]) => <tr key={`slot-conflict-shape-${key}`}><td>{key}</td><td>{formatValue(value)}</td></tr>)}</tbody></table> : <p>Slot conflict shape is unavailable.</p>}
              <h5>Policy conflict shape</h5>
              {shapeRecord(conflictContractPreviewRecord.policy_conflict_shape) ? <table><thead><tr><th scope="col">Field</th><th scope="col">Value</th></tr></thead><tbody>{Object.entries(shapeRecord(conflictContractPreviewRecord.policy_conflict_shape) ?? {}).map(([key, value]) => <tr key={`policy-conflict-shape-${key}`}><td>{key}</td><td>{formatValue(value)}</td></tr>)}</tbody></table> : <p>Policy conflict shape is unavailable.</p>}
              <h5>Validation conflict shape</h5>
              {shapeRecord(conflictContractPreviewRecord.validation_conflict_shape) ? <table><thead><tr><th scope="col">Field</th><th scope="col">Value</th></tr></thead><tbody>{Object.entries(shapeRecord(conflictContractPreviewRecord.validation_conflict_shape) ?? {}).map(([key, value]) => <tr key={`validation-conflict-shape-${key}`}><td>{key}</td><td>{formatValue(value)}</td></tr>)}</tbody></table> : <p>Validation conflict shape is unavailable.</p>}
            </>
          ) : <p>Conflict contract preview is unavailable.</p>}
          <h4>Dry-run result contract preview</h4>
          {dryRunResultContractPreviewRecord ? (
            <>
              <table>
                <thead><tr><th scope="col">Field</th><th scope="col">Value</th></tr></thead>
                <tbody>
                  <tr><td>status</td><td>{formatValue(dryRunResultContractPreviewRecord.status)}</td></tr>
                  <tr><td>will_return_real_result</td><td>{formatValue(dryRunResultContractPreviewRecord.will_return_real_result)}</td></tr>
                  <tr><td>blocked_reason</td><td>{formatValue(dryRunResultContractPreviewRecord.blocked_reason)}</td></tr>
                </tbody>
              </table>
              <h5>Structural summary preview</h5>
              {shapeRecord(dryRunResultContractPreviewRecord.structural_summary) ? <table><thead><tr><th scope="col">Field</th><th scope="col">Value</th></tr></thead><tbody>{Object.entries(shapeRecord(dryRunResultContractPreviewRecord.structural_summary) ?? {}).map(([key, value]) => <tr key={`dry-run-structural-${key}`}><td>{key}</td><td>{formatValue(value)}</td></tr>)}</tbody></table> : <p>Structural summary preview is unavailable.</p>}
              <h5>Conflict summary preview</h5>
              {shapeRecord(dryRunResultContractPreviewRecord.conflict_summary) ? (
                <table><thead><tr><th scope="col">Field</th><th scope="col">Value</th></tr></thead><tbody>
                  <tr><td>week_conflicts count</td><td>{previewList(shapeRecord(dryRunResultContractPreviewRecord.conflict_summary)?.week_conflicts).length}</td></tr>
                  <tr><td>slot_conflicts count</td><td>{previewList(shapeRecord(dryRunResultContractPreviewRecord.conflict_summary)?.slot_conflicts).length}</td></tr>
                  <tr><td>policy_conflicts count</td><td>{previewList(shapeRecord(dryRunResultContractPreviewRecord.conflict_summary)?.policy_conflicts).length}</td></tr>
                  <tr><td>validation_conflicts count</td><td>{previewList(shapeRecord(dryRunResultContractPreviewRecord.conflict_summary)?.validation_conflicts).length}</td></tr>
                </tbody></table>
              ) : <p>Conflict summary preview is unavailable.</p>}
              <h5>Result metadata preview</h5>
              {shapeRecord(dryRunResultContractPreviewRecord.result_metadata) ? <table><thead><tr><th scope="col">Field</th><th scope="col">Value</th></tr></thead><tbody>{Object.entries(shapeRecord(dryRunResultContractPreviewRecord.result_metadata) ?? {}).map(([key, value]) => <tr key={`dry-run-result-meta-${key}`}><td>{key}</td><td>{formatValue(value)}</td></tr>)}</tbody></table> : <p>Result metadata preview is unavailable.</p>}
              <h5>Candidate events preview</h5>
              {previewList(dryRunResultContractPreviewRecord.candidate_events).length === 0 ? <p>No candidate events returned in this contract-only phase.</p> : <p>{previewList(dryRunResultContractPreviewRecord.candidate_events).length} candidate events included in preview.</p>}
            </>
          ) : <p>Dry-run result contract preview is unavailable.</p>}
          <h4>Read-only generated dry-run result preview</h4>
          {dryRunResultPreviewRecord ? (
            <>
              <table><thead><tr><th scope="col">Field</th><th scope="col">Value</th></tr></thead><tbody>
                <tr><td>status</td><td>{formatValue(dryRunResultPreviewRecord.status)}</td></tr>
                <tr><td>execution_enabled</td><td>{formatValue(dryRunResultPreviewRecord.execution_enabled)}</td></tr>
                <tr><td>mutation_permitted</td><td>{formatValue(dryRunResultPreviewRecord.mutation_permitted)}</td></tr>
                <tr><td>dry_run_result_fingerprint</td><td>{formatValue(dryRunResultPreviewRecord.dry_run_result_fingerprint)}</td></tr>
                <tr><td>dry_run_result_id</td><td>{formatValue(dryRunResultPreviewRecord.dry_run_result_id)}</td></tr>
              </tbody></table>
              <h5>Structural summary</h5>
              {shapeRecord(dryRunResultPreviewRecord.structural_summary) ? <table><thead><tr><th scope="col">Field</th><th scope="col">Value</th></tr></thead><tbody>{Object.entries(shapeRecord(dryRunResultPreviewRecord.structural_summary) ?? {}).map(([key, value]) => <tr key={`dry-run-result-struct-${key}`}><td>{key}</td><td>{formatValue(value)}</td></tr>)}</tbody></table> : <p>Structural summary is unavailable.</p>}
              <h5>Result metadata</h5>
              {shapeRecord(dryRunResultPreviewRecord.result_metadata) ? (
                <table><thead><tr><th scope="col">Field</th><th scope="col">Value</th></tr></thead><tbody>
                  <tr><td>target_calendar_exists</td><td>{formatValue(shapeRecord(dryRunResultPreviewRecord.result_metadata)?.target_calendar_exists)}</td></tr>
                  <tr><td>target_event_count</td><td>{formatValue(shapeRecord(dryRunResultPreviewRecord.result_metadata)?.target_event_count)}</td></tr>
                  <tr><td>comparison_performed</td><td>{formatValue(shapeRecord(dryRunResultPreviewRecord.result_metadata)?.comparison_performed)}</td></tr>
                  <tr><td>dry_run_result_fingerprint</td><td>{formatValue(shapeRecord(dryRunResultPreviewRecord.result_metadata)?.dry_run_result_fingerprint)}</td></tr>
                  <tr><td>dry_run_result_id</td><td>{formatValue(shapeRecord(dryRunResultPreviewRecord.result_metadata)?.dry_run_result_id)}</td></tr>
                </tbody></table>
              ) : <p>Result metadata is unavailable.</p>}
              <h5>Read-only comparison conflicts</h5>
              {shapeRecord(dryRunResultPreviewRecord.conflict_summary) ? (
                <>
                  <table><thead><tr><th scope="col">Field</th><th scope="col">Value</th></tr></thead><tbody>
                    <tr><td>week_conflicts count</td><td>{previewList(shapeRecord(dryRunResultPreviewRecord.conflict_summary)?.week_conflicts).length}</td></tr>
                    <tr><td>slot_conflicts count</td><td>{previewList(shapeRecord(dryRunResultPreviewRecord.conflict_summary)?.slot_conflicts).length}</td></tr>
                    <tr><td>policy_conflicts count</td><td>{previewList(shapeRecord(dryRunResultPreviewRecord.conflict_summary)?.policy_conflicts).length}</td></tr>
                    <tr><td>validation_conflicts count</td><td>{previewList(shapeRecord(dryRunResultPreviewRecord.conflict_summary)?.validation_conflicts).length}</td></tr>
                  </tbody></table>
                  {previewList(shapeRecord(dryRunResultPreviewRecord.conflict_summary)?.policy_conflicts).length > 0 ? (
                    <ul>
                      {previewList(shapeRecord(dryRunResultPreviewRecord.conflict_summary)?.policy_conflicts).map((conflict, idx) => {
                        const row = shapeRecord(conflict)
                        return <li key={`policy-conflict-${idx}`}>{formatValue(row?.severity)}: {formatValue(row?.message)}</li>
                      })}
                    </ul>
                  ) : (
                    <p>No read-only comparison conflicts returned.</p>
                  )}
                </>
              ) : <p>Read-only comparison conflicts are unavailable.</p>}
              <h5>Dry-run validation summary</h5>
              {shapeRecord(dryRunResultPreviewRecord.validation_summary) ? (
                <>
                  <table><thead><tr><th scope="col">Field</th><th scope="col">Value</th></tr></thead><tbody>
                    <tr><td>status</td><td>{formatValue(shapeRecord(dryRunResultPreviewRecord.validation_summary)?.status)}</td></tr>
                    <tr><td>blocking_count</td><td>{formatValue(shapeRecord(dryRunResultPreviewRecord.validation_summary)?.blocking_count)}</td></tr>
                    <tr><td>warning_count</td><td>{formatValue(shapeRecord(dryRunResultPreviewRecord.validation_summary)?.warning_count)}</td></tr>
                    <tr><td>info_count</td><td>{formatValue(shapeRecord(dryRunResultPreviewRecord.validation_summary)?.info_count)}</td></tr>
                  </tbody></table>
                  <h6>Candidate status counts</h6>
                  {shapeRecord(shapeRecord(dryRunResultPreviewRecord.validation_summary)?.candidate_status_counts) ? <table><thead><tr><th scope="col">Field</th><th scope="col">Value</th></tr></thead><tbody>{Object.entries(shapeRecord(shapeRecord(dryRunResultPreviewRecord.validation_summary)?.candidate_status_counts) ?? {}).map(([key, value]) => <tr key={`candidate-status-count-${key}`}><td>{key}</td><td>{formatValue(value)}</td></tr>)}</tbody></table> : <p>Candidate status counts are unavailable.</p>}
                  <h6>Conflict type counts</h6>
                  {shapeRecord(shapeRecord(dryRunResultPreviewRecord.validation_summary)?.conflict_type_counts) ? <table><thead><tr><th scope="col">Field</th><th scope="col">Value</th></tr></thead><tbody>{Object.entries(shapeRecord(shapeRecord(dryRunResultPreviewRecord.validation_summary)?.conflict_type_counts) ?? {}).map(([key, value]) => <tr key={`conflict-type-count-${key}`}><td>{key}</td><td>{formatValue(value)}</td></tr>)}</tbody></table> : <p>Conflict type counts are unavailable.</p>}
                  <h6>Blocking reasons</h6>
                  {previewList(shapeRecord(dryRunResultPreviewRecord.validation_summary)?.blocking_reasons).length === 0 ? <p>No dry-run blocking reasons returned.</p> : <ul>{previewList(shapeRecord(dryRunResultPreviewRecord.validation_summary)?.blocking_reasons).map((reason, idx) => <li key={`dry-run-blocking-reason-${idx}`}>{formatValue(reason)}</li>)}</ul>}
                  <h6>Warning reasons</h6>
                  {previewList(shapeRecord(dryRunResultPreviewRecord.validation_summary)?.warning_reasons).length === 0 ? <p>No dry-run warning reasons returned.</p> : <ul>{previewList(shapeRecord(dryRunResultPreviewRecord.validation_summary)?.warning_reasons).map((reason, idx) => <li key={`dry-run-warning-reason-${idx}`}>{formatValue(reason)}</li>)}</ul>}
                  <h6>Info messages</h6>
                  {previewList(shapeRecord(dryRunResultPreviewRecord.validation_summary)?.info_messages).length === 0 ? <p>No dry-run info messages returned.</p> : <ul>{previewList(shapeRecord(dryRunResultPreviewRecord.validation_summary)?.info_messages).map((message, idx) => <li key={`dry-run-info-message-${idx}`}>{formatValue(message)}</li>)}</ul>}
                </>
              ) : <p>Dry-run validation summary is unavailable.</p>}
              <h5>Plan readiness</h5>
              {shapeRecord(dryRunResultPreviewRecord.plan_readiness) ? (
                <table><thead><tr><th scope="col">Field</th><th scope="col">Value</th></tr></thead><tbody>
                  <tr><td>read_only_plan_available</td><td>{formatValue(shapeRecord(dryRunResultPreviewRecord.plan_readiness)?.read_only_plan_available)}</td></tr>
                  <tr><td>has_blocking_issues</td><td>{formatValue(shapeRecord(dryRunResultPreviewRecord.plan_readiness)?.has_blocking_issues)}</td></tr>
                  <tr><td>has_warnings</td><td>{formatValue(shapeRecord(dryRunResultPreviewRecord.plan_readiness)?.has_warnings)}</td></tr>
                  <tr><td>mutation_still_disabled</td><td>{formatValue(shapeRecord(dryRunResultPreviewRecord.plan_readiness)?.mutation_still_disabled)}</td></tr>
                  <tr><td>next_required_step</td><td>{formatValue(shapeRecord(dryRunResultPreviewRecord.plan_readiness)?.next_required_step)}</td></tr>
                </tbody></table>
              ) : <p>Plan readiness is unavailable.</p>}
              <h5>Dry-run identity readiness</h5>
              {shapeRecord(dryRunResultPreviewRecord.identity_readiness) ? (
                <>
                  <table><thead><tr><th scope="col">Field</th><th scope="col">Value</th></tr></thead><tbody>
                    <tr><td>status</td><td>{formatValue(shapeRecord(dryRunResultPreviewRecord.identity_readiness)?.status)}</td></tr>
                  </tbody></table>
                  <h6>Future command reference</h6>
                  {shapeRecord(shapeRecord(dryRunResultPreviewRecord.identity_readiness)?.future_command_reference) ? (
                    <table><thead><tr><th scope="col">Field</th><th scope="col">Value</th></tr></thead><tbody>
                      <tr><td>preflight_fingerprint</td><td>{formatValue(shapeRecord(shapeRecord(dryRunResultPreviewRecord.identity_readiness)?.future_command_reference)?.preflight_fingerprint)}</td></tr>
                      <tr><td>reviewed_diff_id</td><td>{formatValue(shapeRecord(shapeRecord(dryRunResultPreviewRecord.identity_readiness)?.future_command_reference)?.reviewed_diff_id)}</td></tr>
                      <tr><td>dry_run_result_fingerprint</td><td>{formatValue(shapeRecord(shapeRecord(dryRunResultPreviewRecord.identity_readiness)?.future_command_reference)?.dry_run_result_fingerprint)}</td></tr>
                      <tr><td>dry_run_result_id</td><td>{formatValue(shapeRecord(shapeRecord(dryRunResultPreviewRecord.identity_readiness)?.future_command_reference)?.dry_run_result_id)}</td></tr>
                      <tr><td>can_reference_future_command</td><td>{formatValue(shapeRecord(shapeRecord(dryRunResultPreviewRecord.identity_readiness)?.future_command_reference)?.can_reference_future_command)}</td></tr>
                      <tr><td>mutation_still_disabled</td><td>{formatValue(shapeRecord(shapeRecord(dryRunResultPreviewRecord.identity_readiness)?.future_command_reference)?.mutation_still_disabled)}</td></tr>
                    </tbody></table>
                  ) : <p>Future command reference is unavailable.</p>}
                  <h6>Checklist items</h6>
                  {previewList(shapeRecord(dryRunResultPreviewRecord.identity_readiness)?.items).length > 0 ? (
                    <table><thead><tr><th scope="col">Area</th><th scope="col">Status</th><th scope="col">Message</th></tr></thead><tbody>
                      {previewList(shapeRecord(dryRunResultPreviewRecord.identity_readiness)?.items).map((item, idx) => {
                        const row = shapeRecord(item)
                        return <tr key={`identity-readiness-item-${idx}`}><td>{formatValue(row?.area)}</td><td>{formatValue(row?.status)}</td><td>{formatValue(row?.message)}</td></tr>
                      })}
                    </tbody></table>
                  ) : <p>Identity readiness checklist items are unavailable.</p>}
                </>
              ) : <p>Dry-run identity readiness is unavailable.</p>}
              <h5>Candidate events</h5>
              {previewList(dryRunResultPreviewRecord.candidate_events).length === 0 ? <p>No read-only candidate events generated.</p> : (
                <table><thead><tr><th scope="col">candidate_id</th><th scope="col">source_slot_id</th><th scope="col">season_week_start</th><th scope="col">season_week_end</th><th scope="col">event_name</th><th scope="col">tour_level</th><th scope="col">category</th><th scope="col">host_country</th><th scope="col">candidate_status</th><th scope="col">comparison_classification</th><th scope="col">comparison_reason</th><th scope="col">matched_existing_event_id</th></tr></thead><tbody>{previewList(dryRunResultPreviewRecord.candidate_events).slice(0, 5).map((candidate, idx) => { const row = shapeRecord(candidate); return <tr key={`dry-run-result-candidate-${idx}`}><td>{formatValue(row?.candidate_id)}</td><td>{formatValue(row?.source_slot_id)}</td><td>{formatValue(row?.season_week_start)}</td><td>{formatValue(row?.season_week_end)}</td><td>{formatValue(row?.event_name)}</td><td>{formatValue(row?.tour_level)}</td><td>{formatValue(row?.category)}</td><td>{formatValue(row?.host_country)}</td><td>{formatValue(row?.candidate_status)}</td><td>{formatValue(row?.comparison_classification)}</td><td>{formatValue(row?.comparison_reason)}</td><td>{formatValue(row?.matched_existing_event_id)}</td></tr> })}</tbody></table>
              )}
              <p>Read-only generated candidates are not persisted.</p>
            </>
          ) : <p>Read-only generated dry-run result preview is unavailable.</p>}
          <h4>Current disabled dry-run request payload</h4>
          <table>
            <thead><tr><th scope="col">Field</th><th scope="col">Value</th></tr></thead>
            <tbody>
              <tr><td>audit_reason</td><td>{formatValue(requestPayload.audit_reason)}</td></tr>
              <tr><td>explicit_confirmation</td><td>{formatValue(requestPayload.explicit_confirmation)}</td></tr>
              <tr><td>mutation_scope</td><td>{formatValue(requestPayload.mutation_scope)}</td></tr>
            </tbody>
          </table>
          <h4>Raw disabled dry-run build contract JSON</h4>
          <pre>{JSON.stringify(query.data, null, 2)}</pre>
        </>
      ) : null}
      <p>Execution remains disabled; this panel is not a build control.</p>
      <pre>{JSON.stringify(requestPayload, null, 2)}</pre>
    </>
  )
}

type DisabledApplyCommandContractPanelProps = {
  queryEnabled: boolean
  requestPayload: SeasonBuilderApplyCommandContractRequest
  query: {
    isLoading: boolean
    error: unknown
    data: SeasonBuilderApplyCommandContractResponse | undefined
  }
}

export function DisabledApplyCommandContractPanel({ queryEnabled, requestPayload, query }: DisabledApplyCommandContractPanelProps): JSX.Element {
  const formatValue = (value: unknown): string => (value === null || value === undefined ? '—' : String(value))
  const requiredIdentity = query.data?.required_identity ?? {}
  const requiredAuditMetadata = query.data?.required_audit_metadata ?? {}
  const auditPreview = query.data?.audit_preview ?? {}
  const auditTrailContractPreview = query.data?.audit_trail_contract_preview
  const safetyGateContractPreview = query.data?.safety_gate_contract_preview
  const auditTrailContractPreviewRecord = auditTrailContractPreview && typeof auditTrailContractPreview === 'object'
    ? auditTrailContractPreview as Record<string, unknown>
    : null
  const safetyGateContractPreviewRecord = safetyGateContractPreview && typeof safetyGateContractPreview === 'object'
    ? safetyGateContractPreview as Record<string, unknown>
    : null
  const previewList = (value: unknown): unknown[] => Array.isArray(value) ? value : []
  const shapeRecord = (value: unknown): Record<string, unknown> | null => value && typeof value === 'object' ? value as Record<string, unknown> : null
  return (
    <>
      <p>Read-only disabled apply command contract check. This does not build, merge, overwrite, or apply anything.</p>
      {!queryEnabled ? <p>Apply command contract check is waiting for preflight and dry-run result identities.</p> : null}
      {queryEnabled && query.isLoading ? <p>Loading disabled apply command contract…</p> : null}
      {queryEnabled && query.error ? <p className="error">Disabled apply command contract check failed: {formatApiError(query.error)}</p> : null}
      {queryEnabled && query.data ? (
        <>
          <table><thead><tr><th scope="col">Field</th><th scope="col">Value</th></tr></thead><tbody>
            <tr><td>command</td><td>{query.data.command}</td></tr>
            <tr><td>enabled</td><td>{String(query.data.enabled)}</td></tr>
            <tr><td>can_execute</td><td>{String(query.data.can_execute)}</td></tr>
            <tr><td>can_mutate</td><td>{String(query.data.can_mutate)}</td></tr>
            <tr><td>target_season_label</td><td>{query.data.target_season_label}</td></tr>
            <tr><td>source_type</td><td>{query.data.source_type}</td></tr>
            <tr><td>source_template_id</td><td>{query.data.source_template_id ?? '—'}</td></tr>
            <tr><td>overwrite_policy</td><td>{query.data.overwrite_policy ?? '—'}</td></tr>
            <tr><td>validation_errors count</td><td>{query.data.validation_errors.length}</td></tr>
            <tr><td>validation_warnings count</td><td>{query.data.validation_warnings.length}</td></tr>
            <tr><td>message</td><td>{query.data.message}</td></tr>
          </tbody></table>
          <h4>Required identity</h4>
          <table><thead><tr><th scope="col">Field</th><th scope="col">Value</th></tr></thead><tbody>
            <tr><td>preflight_fingerprint</td><td>{formatValue(requiredIdentity.preflight_fingerprint)}</td></tr>
            <tr><td>reviewed_diff_id</td><td>{formatValue(requiredIdentity.reviewed_diff_id)}</td></tr>
            <tr><td>dry_run_result_fingerprint</td><td>{formatValue(requiredIdentity.dry_run_result_fingerprint)}</td></tr>
            <tr><td>dry_run_result_id</td><td>{formatValue(requiredIdentity.dry_run_result_id)}</td></tr>
            <tr><td>all_identity_fields_present</td><td>{formatValue(requiredIdentity.all_identity_fields_present)}</td></tr>
          </tbody></table>
          <h4>Required audit metadata</h4>
          <table><thead><tr><th scope="col">Field</th><th scope="col">Value</th></tr></thead><tbody>
            <tr><td>requested_by</td><td>{formatValue(requiredAuditMetadata.requested_by)}</td></tr>
            <tr><td>audit_reason_present</td><td>{formatValue(requiredAuditMetadata.audit_reason_present)}</td></tr>
            <tr><td>explicit_confirmation_present</td><td>{formatValue(requiredAuditMetadata.explicit_confirmation_present)}</td></tr>
            <tr><td>mutation_scope</td><td>{formatValue(requiredAuditMetadata.mutation_scope)}</td></tr>
            <tr><td>all_audit_metadata_present</td><td>{formatValue(requiredAuditMetadata.all_audit_metadata_present)}</td></tr>
          </tbody></table>
          <h4>Validation warnings</h4>
          {query.data.validation_warnings.length === 0 ? <p>No apply command contract warnings returned.</p> : <ul>{query.data.validation_warnings.map((warning) => <li key={warning}>{warning}</li>)}</ul>}
          <h4>Validation errors</h4>
          {query.data.validation_errors.length === 0 ? <p>No apply command contract errors returned.</p> : <ul>{query.data.validation_errors.map((error) => <li key={error}>{error}</li>)}</ul>}
          <h4>Audit preview</h4>
          <table><thead><tr><th scope="col">Field</th><th scope="col">Value</th></tr></thead><tbody>
            <tr><td>action</td><td>{formatValue(auditPreview.action)}</td></tr>
            <tr><td>read_only</td><td>{formatValue(auditPreview.read_only)}</td></tr>
            <tr><td>mutation_permitted</td><td>{formatValue(auditPreview.mutation_permitted)}</td></tr>
            <tr><td>execution_enabled</td><td>{formatValue(auditPreview.execution_enabled)}</td></tr>
            <tr><td>target_season_label</td><td>{formatValue(auditPreview.target_season_label)}</td></tr>
            <tr><td>source_type</td><td>{formatValue(auditPreview.source_type)}</td></tr>
            <tr><td>source_template_id</td><td>{formatValue(auditPreview.source_template_id)}</td></tr>
            <tr><td>overwrite_policy</td><td>{formatValue(auditPreview.overwrite_policy)}</td></tr>
            <tr><td>preflight_fingerprint</td><td>{formatValue(auditPreview.preflight_fingerprint)}</td></tr>
            <tr><td>reviewed_diff_id</td><td>{formatValue(auditPreview.reviewed_diff_id)}</td></tr>
            <tr><td>dry_run_result_fingerprint</td><td>{formatValue(auditPreview.dry_run_result_fingerprint)}</td></tr>
            <tr><td>dry_run_result_id</td><td>{formatValue(auditPreview.dry_run_result_id)}</td></tr>
            <tr><td>requested_by</td><td>{formatValue(auditPreview.requested_by)}</td></tr>
            <tr><td>audit_reason</td><td>{formatValue(auditPreview.audit_reason)}</td></tr>
            <tr><td>explicit_confirmation_present</td><td>{formatValue(auditPreview.explicit_confirmation_present)}</td></tr>
            <tr><td>mutation_scope</td><td>{formatValue(auditPreview.mutation_scope)}</td></tr>
            <tr><td>audit_trail_contract_preview_available</td><td>{formatValue(auditPreview.audit_trail_contract_preview_available)}</td></tr>
            <tr><td>safety_gate_contract_preview_available</td><td>{formatValue(auditPreview.safety_gate_contract_preview_available)}</td></tr>
          </tbody></table>
          <h4>Apply audit trail contract preview</h4>
          {auditTrailContractPreviewRecord ? (
            <>
              <table><thead><tr><th scope="col">Field</th><th scope="col">Value</th></tr></thead><tbody>
                <tr><td>status</td><td>{formatValue(auditTrailContractPreviewRecord.status)}</td></tr>
                <tr><td>will_persist_audit</td><td>{formatValue(auditTrailContractPreviewRecord.will_persist_audit)}</td></tr>
                <tr><td>audit_event_type</td><td>{formatValue(auditTrailContractPreviewRecord.audit_event_type)}</td></tr>
                <tr><td>blocked_reason</td><td>{formatValue(auditTrailContractPreviewRecord.blocked_reason)}</td></tr>
              </tbody></table>
              <h5>Required identity fields</h5>
              {previewList(auditTrailContractPreviewRecord.required_identity_fields).length === 0 ? <p>No required identity fields returned.</p> : (
                <ul>{previewList(auditTrailContractPreviewRecord.required_identity_fields).map((value, idx) => <li key={`apply-audit-identity-${idx}`}>{formatValue(value)}</li>)}</ul>
              )}
              <h5>Required actor fields</h5>
              {previewList(auditTrailContractPreviewRecord.required_actor_fields).length === 0 ? <p>No required actor fields returned.</p> : (
                <ul>{previewList(auditTrailContractPreviewRecord.required_actor_fields).map((value, idx) => <li key={`apply-audit-actor-${idx}`}>{formatValue(value)}</li>)}</ul>
              )}
              <h5>Audit record shape</h5>
              {shapeRecord(auditTrailContractPreviewRecord.audit_record_shape) ? (
                <table><thead><tr><th scope="col">Field</th><th scope="col">Value</th></tr></thead><tbody>
                  {Object.entries(shapeRecord(auditTrailContractPreviewRecord.audit_record_shape) ?? {}).map(([key, value]) => (
                    <tr key={`apply-audit-record-shape-${key}`}><td>{key}</td><td>{formatValue(value)}</td></tr>
                  ))}
                </tbody></table>
              ) : <p>Audit record shape is unavailable.</p>}
            </>
          ) : <p>Apply audit trail contract preview is unavailable.</p>}
          <h4>Apply safety gate contract preview</h4>
          {safetyGateContractPreviewRecord ? (
            <>
              <table><thead><tr><th scope="col">Field</th><th scope="col">Value</th></tr></thead><tbody>
                <tr><td>status</td><td>{formatValue(safetyGateContractPreviewRecord.status)}</td></tr>
                <tr><td>will_execute_apply</td><td>{formatValue(safetyGateContractPreviewRecord.will_execute_apply)}</td></tr>
                <tr><td>will_mutate_calendar</td><td>{formatValue(safetyGateContractPreviewRecord.will_mutate_calendar)}</td></tr>
                <tr><td>gate_result</td><td>{formatValue(safetyGateContractPreviewRecord.gate_result)}</td></tr>
                <tr><td>blocked_reason</td><td>{formatValue(safetyGateContractPreviewRecord.blocked_reason)}</td></tr>
              </tbody></table>
              <h5>Required gates</h5>
              {previewList(safetyGateContractPreviewRecord.required_gates).length === 0 ? <p>No required gates returned.</p> : (
                <table><thead><tr><th scope="col">gate</th><th scope="col">required</th><th scope="col">currently_satisfied</th><th scope="col">message</th></tr></thead><tbody>
                  {previewList(safetyGateContractPreviewRecord.required_gates).map((gate, idx) => {
                    const gateRecord = shapeRecord(gate)
                    return (
                      <tr key={`apply-safety-gate-${idx}`}>
                        <td>{formatValue(gateRecord?.gate)}</td>
                        <td>{formatValue(gateRecord?.required)}</td>
                        <td>{formatValue(gateRecord?.currently_satisfied)}</td>
                        <td>{formatValue(gateRecord?.message)}</td>
                      </tr>
                    )
                  })}
                </tbody></table>
              )}
              <h5>Future allowed mutation scopes</h5>
              {previewList(safetyGateContractPreviewRecord.future_allowed_mutation_scopes).length === 0 ? <p>No future allowed mutation scopes returned.</p> : (
                <ul>{previewList(safetyGateContractPreviewRecord.future_allowed_mutation_scopes).map((value, idx) => <li key={`apply-safety-scope-${idx}`}>{formatValue(value)}</li>)}</ul>
              )}
            </>
          ) : <p>Apply safety gate contract preview is unavailable.</p>}
          <h4>Raw disabled apply command contract JSON</h4>
          <pre>{JSON.stringify(query.data, null, 2)}</pre>
        </>
      ) : null}
      <p>Execution remains disabled; this panel is not an apply control.</p>
      <pre>{JSON.stringify(requestPayload, null, 2)}</pre>
    </>
  )
}

type CreateOnlyApplyReadinessPanelProps = {
  queryEnabled: boolean
  query: {
    isLoading: boolean
    error: unknown
    data: SeasonBuilderApplyCreateOnlyReadinessResponse | undefined
  }
}

type CreateOnlyApplyDangerZonePreviewPanelProps = {
  readinessData: SeasonBuilderApplyCreateOnlyReadinessResponse | undefined
  selectedTargetSeasonLabel: string
  requiredConfirmationPhrase: string
  confirmationText: string
  setConfirmationText: (value: string) => void
  mutationScopePreview: string
  setMutationScopePreview: (value: string) => void
  canSubmitCreateOnlyApply: boolean
  onConfirmCreateOnlyApply: () => void
  applyMutationStatus: 'idle' | 'pending' | 'success' | 'error'
  applyMutationError: unknown
  applyMutationResult: SeasonBuilderApplyCreateOnlyCommandResponse | undefined
  targetCalendarExistsAfterApply: boolean
  createOnlyBlockedReason: string | null
}
type CreateOnlyApplyGuardSummaryPanelProps = {
  items: CreateOnlyApplyGuardSummaryItem[]
  canSubmitCreateOnlyApply: boolean
  createOnlyBlockedReason: string | null
}


type TargetCalendarValidationPanelProps = {
  queryEnabled: boolean
  issueCodeRegistryData?: SeasonCalendarValidationIssueCodeRegistryResponse
  query: {
    isLoading: boolean
    isFetching: boolean
    error: unknown
    data: SeasonCalendarValidationResponse | undefined
  }
}

function parseValidationCount(value: unknown): number | null {
  if (typeof value === 'number' && Number.isFinite(value)) return value
  if (typeof value === 'string') {
    const parsed = Number(value)
    return Number.isFinite(parsed) ? parsed : null
  }
  return null
}

export function describeValidationStatus(status: unknown, errorCount?: unknown, warningCount?: unknown): string {
  const parsedErrorCount = parseValidationCount(errorCount)
  const parsedWarningCount = parseValidationCount(warningCount)
  if (parsedErrorCount !== null && parsedErrorCount > 0) return 'Validation has blocking errors.'
  if (status === 'errors') return 'Validation has blocking errors.'
  if (parsedWarningCount !== null && parsedWarningCount > 0) return 'Validation has warnings but no blocking errors.'
  if (status === 'warnings') return 'Validation has warnings but no blocking errors.'
  if (status === 'clean') return 'Validation is clean.'
  return 'Validation status is unavailable.'
}

type IssueSeverityGroupCounts = {
  error: number
  warning: number
  info: number
  unknown: number
}

type IssueSeverityCodeGroups = {
  error: string[]
  warning: string[]
  info: string[]
  unknown: string[]
}

function normalizeIssueSeverity(severity: unknown): keyof IssueSeverityGroupCounts {
  if (severity === 'error' || severity === 'warning' || severity === 'info') return severity
  return 'unknown'
}

function normalizeIssueCode(code: unknown): string {
  if (typeof code === 'string' && code.trim().length > 0) return code
  return '(missing_code)'
}

function groupIssueCountsBySeverity(issues: SeasonCalendarValidationResponse['issues']): IssueSeverityGroupCounts {
  return issues.reduce<IssueSeverityGroupCounts>((counts, issue) => {
    const severity = normalizeIssueSeverity(issue?.severity)
    counts[severity] += 1
    return counts
  }, { error: 0, warning: 0, info: 0, unknown: 0 })
}

function groupIssueCodesBySeverity(issues: SeasonCalendarValidationResponse['issues']): IssueSeverityCodeGroups {
  const grouped = issues.reduce<Record<keyof IssueSeverityCodeGroups, Set<string>>>((acc, issue) => {
    const severity = normalizeIssueSeverity(issue?.severity)
    acc[severity].add(normalizeIssueCode(issue?.code))
    return acc
  }, { error: new Set(), warning: new Set(), info: new Set(), unknown: new Set() })
  return {
    error: Array.from(grouped.error),
    warning: Array.from(grouped.warning),
    info: Array.from(grouped.info),
    unknown: Array.from(grouped.unknown)
  }
}

export function TargetCalendarValidationPanel({ queryEnabled, issueCodeRegistryData, query }: TargetCalendarValidationPanelProps): JSX.Element {
  if (!queryEnabled) return <p>Select a target season to view read-only calendar validation.</p>
  if (query.isLoading) return <p>Loading target calendar validation…</p>
  if (query.error) return <p>Unable to load target calendar validation: {formatApiError(query.error)}</p>
  if (!query.data) return <p>No validation data returned.</p>
  const { calendar_exists, validation_summary, issues, read_only, message } = query.data
  const topIssues = issues.slice(0, 10)
  const hidden = Math.max(issues.length - topIssues.length, 0)
  const issueSeverityCounts = groupIssueCountsBySeverity(issues)
  const issueCodesBySeverity = groupIssueCodesBySeverity(issues)
  const issueMetadataByCode = new Map(
    (issueCodeRegistryData?.codes ?? []).map((registryCode) => [registryCode.code, registryCode] as const)
  )
  const renderShape = (label: string, value: Record<string, unknown>) => {
    const count = typeof value.count === 'number' ? value.count : null
    const vals = Array.isArray(value.values) ? value.values.join(', ') : null
    return <>
      <p>{label} count: {count ?? 'n/a'}</p>
      <p>{label} values: {vals ?? 'n/a'}</p>
    </>
  }
  return <>
    <p>Read-only persisted target calendar validation. No mutation path is available in this panel.</p>
    <p>{message}</p>
    <p>Read-only: {String(read_only)}</p>
    <p>Calendar exists: {String(calendar_exists)}</p>
    <p>Validation status: {validation_summary.status}</p>
    <p>Target validation interpretation: {describeValidationStatus(validation_summary.status, validation_summary.error_count, validation_summary.warning_count)}</p>
    <p>Error count: {validation_summary.error_count}</p>
    <p>Warning count: {validation_summary.warning_count}</p>
    <p>Info count: {validation_summary.info_count}</p>
    <p>Event count: {validation_summary.event_count}</p>
    <p>First season week: {validation_summary.first_season_week ?? 'n/a'}</p>
    <p>Last season week: {validation_summary.last_season_week ?? 'n/a'}</p>
    {renderShape('Categories', validation_summary.categories)}
    {renderShape('Tour levels', validation_summary.tour_levels)}
    {renderShape('Host countries', validation_summary.host_countries)}
    <h5>Validation issue severity summary</h5>
    <p>Error issues: {issueSeverityCounts.error}</p>
    <p>Warning issues: {issueSeverityCounts.warning}</p>
    <p>Info issues: {issueSeverityCounts.info}</p>
    <p>Unknown-severity issues: {issueSeverityCounts.unknown}</p>
    <p>Error issue codes: {issueCodesBySeverity.error.length > 0 ? issueCodesBySeverity.error.join(', ') : 'none'}</p>
    <p>Warning issue codes: {issueCodesBySeverity.warning.length > 0 ? issueCodesBySeverity.warning.join(', ') : 'none'}</p>
    <p>Info issue codes: {issueCodesBySeverity.info.length > 0 ? issueCodesBySeverity.info.join(', ') : 'none'}</p>
    <p>Unknown issue codes: {issueCodesBySeverity.unknown.length > 0 ? issueCodesBySeverity.unknown.join(', ') : 'none'}</p>
    <p>Issue rows below are enriched from the registry when metadata is available.</p>
    <table><thead><tr><th>Severity</th><th>Code</th><th>Registry title</th><th>Event</th><th>Field</th><th>Message</th><th>Registry description</th></tr></thead>
    <tbody>{topIssues.map((issue, i) => {
      const issueCode = normalizeIssueCode(issue.code)
      const metadata = issueMetadataByCode.get(issueCode)
      return <tr key={`${issue.code}-${i}`}>
        <td>{issue.severity}</td>
        <td>{issue.code}</td>
        <td>{metadata?.title ?? 'Unknown issue code'}</td>
        <td>{issue.event_id ?? '-'}</td>
        <td>{issue.field ?? '-'}</td>
        <td>{issue.message}</td>
        <td>{metadata?.description ?? 'No registry metadata available for this issue code.'}</td>
      </tr>
    })}</tbody></table>
    {hidden > 0 ? <p>{hidden} additional issues hidden.</p> : null}
    {query.isFetching ? <p>Refreshing validation…</p> : null}
  </>
}

type PostApplyCalendarVerificationPanelProps = {
  targetCalendarData: SeasonCalendarBuildResponse | undefined
  targetCalendarLoading: boolean
  targetCalendarFetching: boolean
  targetCalendarError: unknown
  readinessData: SeasonBuilderApplyCreateOnlyReadinessResponse | undefined
  readinessFetching: boolean
  applyMutationResult: SeasonBuilderApplyCreateOnlyCommandResponse | undefined
  targetCalendarExistsAfterApply: boolean
}

type PostApplyAuditStatusPanelProps = {
  applyMutationResult: SeasonBuilderApplyCreateOnlyCommandResponse | undefined
  requestedBy: string
  auditReason: string
  explicitConfirmation: string
  mutationScope: string
}
type ApplyResponseValidationPreviewPanelProps = {
  applyMutationResult: SeasonBuilderApplyCreateOnlyCommandResponse | undefined
  issueCodeRegistryData?: SeasonCalendarValidationIssueCodeRegistryResponse
}

type ValidationIssueCodeRegistryPanelProps = {
  query: {
    isLoading: boolean
    isFetching: boolean
    error: unknown
    data: SeasonCalendarValidationIssueCodeRegistryResponse | undefined
  }
}

export function ValidationIssueCodeRegistryPanel({ query }: ValidationIssueCodeRegistryPanelProps): JSX.Element {
  if (query.isLoading) return <p>Loading validation issue code registry…</p>
  if (query.error) return <p>Unable to load validation issue code registry: {formatApiError(query.error)}</p>
  if (!query.data) return <p>No validation issue code registry data returned.</p>

  const { codes, code_count, read_only, message } = query.data
  const errorCount = codes.filter((code) => code.severity === 'error').length
  const warningCount = codes.filter((code) => code.severity === 'warning').length
  const infoCount = codes.filter((code) => code.severity === 'info').length

  return <>
    <p>Read-only validation issue code registry. These codes document validation output meanings.</p>
    <p>This registry is the full reference list; individual validation panels show only codes present in their result.</p>
    {query.isFetching ? <p>Refreshing issue code registry…</p> : null}
    <p>Read-only: {String(read_only)}</p>
    <p>Code count: {code_count}</p>
    <p>{message}</p>
    <h5>Issue code severity summary</h5>
    <p>Error code count: {errorCount}</p>
    <p>Warning code count: {warningCount}</p>
    <p>Info code count: {infoCount}</p>
    <h5>Issue code registry table</h5>
    {codes.length === 0 ? <p>No issue codes returned.</p> : (
      <table>
        <thead><tr><th>code</th><th>severity</th><th>title</th><th>field</th><th>description</th></tr></thead>
        <tbody>
          {codes.map((item) => <tr key={item.code}><td>{item.code}</td><td>{item.severity}</td><td>{item.title}</td><td>{item.field ?? 'n/a'}</td><td>{item.description}</td></tr>)}
        </tbody>
      </table>
    )}
  </>
}

type ApplyResponseVsTargetValidationComparisonPanelProps = {
  applyMutationResult: SeasonBuilderApplyCreateOnlyCommandResponse | undefined
  targetValidationData: SeasonCalendarValidationResponse | undefined
  targetValidationFetching: boolean
  targetValidationError: unknown
}

export function PostApplyCalendarVerificationPanel({
  targetCalendarData,
  targetCalendarLoading,
  targetCalendarFetching,
  targetCalendarError,
  readinessData,
  readinessFetching,
  applyMutationResult,
  targetCalendarExistsAfterApply
}: PostApplyCalendarVerificationPanelProps): JSX.Element {
  const applyResultExists = Boolean(applyMutationResult)
  const applyWasSuccessful = applyMutationResult?.applied === true
  const targetCalendarExists = Boolean(targetCalendarData?.calendar)
  const targetSummary = targetCalendarData?.summary
  const targetEventCount = targetSummary?.event_count
  const appliedEventCount = applyMutationResult?.applied_event_count
  const targetCountMatchesApplied = applyWasSuccessful
    && typeof targetEventCount === 'number'
    && typeof appliedEventCount === 'number'
    && targetEventCount === appliedEventCount
  const targetCalendarRefreshPending = targetCalendarLoading || targetCalendarFetching
  const readinessRefreshPending = readinessFetching

  return (
    <>
      <p>Read-only post-apply verification panel using refreshed target calendar and readiness data.</p>
      {!applyResultExists ? <p>No create-only apply result to verify yet.</p> : null}
      {applyResultExists && !applyWasSuccessful ? (
        <p>Create-only apply did not report applied=true; calendar verification is informational only.</p>
      ) : null}
      {applyWasSuccessful ? <p>Create-only apply reported success. Verify the refreshed target calendar below.</p> : null}
      {applyWasSuccessful && targetCalendarRefreshPending ? <p>Post-apply verification pending refreshed target calendar data.</p> : null}
      {applyWasSuccessful && !targetCalendarRefreshPending && targetCalendarExists && targetCountMatchesApplied ? <p>Post-apply calendar verification passed.</p> : null}
      {applyWasSuccessful && targetCalendarExistsAfterApply ? <p>Create-only command should now be unavailable for this target.</p> : null}
      {applyWasSuccessful && !targetCalendarRefreshPending && targetCalendarExists && !targetCountMatchesApplied ? (
        <p className="error">Post-apply calendar event count does not match apply response.</p>
      ) : null}
      {applyWasSuccessful && !targetCalendarRefreshPending && !targetCalendarExists ? (
        <p className="error">Apply reported success, but target calendar is not visible in refreshed data yet.</p>
      ) : null}
      {targetCalendarError ? <p className="error">Target calendar refresh error: {formatApiError(targetCalendarError)}</p> : null}
      {applyWasSuccessful && !readinessRefreshPending && readinessData && (readinessData.can_execute_apply === false || readinessData.would_create_calendar === false) ? (
        <p>Refreshed readiness now reports non-create-only state, which is expected after a successful create-only apply.</p>
      ) : null}
      <table><thead><tr><th scope="col">Field</th><th scope="col">Value</th></tr></thead><tbody>
        <tr><td>verification.apply_result_exists</td><td>{applyResultExists ? 'yes' : 'no'}</td></tr>
        <tr><td>verification.apply_result_applied</td><td>{applyMutationResult ? String(applyMutationResult.applied) : '—'}</td></tr>
        <tr><td>applyMutationResult.applied_event_count</td><td>{applyMutationResult ? String(applyMutationResult.applied_event_count) : '—'}</td></tr>
        <tr><td>applyMutationResult.target_season_label</td><td>{applyMutationResult?.target_season_label ?? '—'}</td></tr>
        <tr><td>verification.target_calendar_exists</td><td>{targetCalendarData ? (targetCalendarExists ? 'yes' : 'no') : '—'}</td></tr>
        <tr><td>verification.target_calendar_event_count</td><td>{typeof targetEventCount === 'number' ? String(targetEventCount) : '—'}</td></tr>
        <tr><td>target first event week</td><td>{targetSummary?.first_event_week ?? '—'}</td></tr>
        <tr><td>target last event week</td><td>{targetSummary?.last_event_week ?? '—'}</td></tr>
        <tr><td>target validation warnings count</td><td>{typeof targetSummary?.validation_warning_count === 'number' ? String(targetSummary.validation_warning_count) : '—'}</td></tr>
        <tr><td>target validation errors count</td><td>{typeof targetSummary?.validation_error_count === 'number' ? String(targetSummary.validation_error_count) : '—'}</td></tr>
        <tr><td>verification.readiness_can_execute_apply</td><td>{readinessData ? String(readinessData.can_execute_apply) : '—'}</td></tr>
        <tr><td>verification.readiness_would_create_calendar</td><td>{readinessData ? String(readinessData.would_create_calendar) : '—'}</td></tr>
      </tbody></table>
    </>
  )
}

export function PostApplyAuditStatusPanel({
  applyMutationResult,
  requestedBy,
  auditReason,
  explicitConfirmation,
  mutationScope
}: PostApplyAuditStatusPanelProps): JSX.Element {
  const applyResultExists = Boolean(applyMutationResult)
  const auditPreview = applyMutationResult?.audit_preview ?? {}
  const dryRunIdentity = applyMutationResult?.dry_run_identity ?? {}
  const createdCalendarIdentity = applyMutationResult?.created_calendar_identity ?? {}
  const applyGateSummary = applyMutationResult?.apply_gate_summary ?? {}
  const auditPersisted = auditPreview.audit_persisted
  const explicitConfirmationPresent = explicitConfirmation.trim().length > 0

  return (
    <>
      <p>Read-only post-apply audit/status summary panel.</p>
      {!applyResultExists ? <p>No create-only apply audit/status result yet.</p> : null}
      {auditPersisted === true ? <p>Audit persistence reported by backend.</p> : <p>Audit persistence is not confirmed by this response.</p>}
      {explicitConfirmationPresent ? <p>Explicit confirmation was provided.</p> : <p>Explicit confirmation is not present in this UI summary.</p>}
      <table><thead><tr><th scope="col">Field</th><th scope="col">Value</th></tr></thead><tbody>
        <tr><td>audit_status.apply_result_exists</td><td>{applyResultExists ? 'yes' : 'no'}</td></tr>
        <tr><td>audit_status.apply_result_applied</td><td>{applyMutationResult ? String(applyMutationResult.applied) : '—'}</td></tr>
        <tr><td>audit_status.requested_by</td><td>{requestedBy || '—'}</td></tr>
        <tr><td>audit_status.audit_reason</td><td>{auditReason || '—'}</td></tr>
        <tr><td>explicit_confirmation present</td><td>{explicitConfirmationPresent ? 'yes' : 'no'}</td></tr>
        <tr><td>audit_status.mutation_scope</td><td>{mutationScope || '—'}</td></tr>
        <tr><td>audit_preview.audit_persisted</td><td>{String(auditPreview.audit_persisted ?? '—')}</td></tr>
        <tr><td>audit_preview.audit_persistence_status</td><td>{String(auditPreview.audit_persistence_status ?? '—')}</td></tr>
        <tr><td>dry_run_identity.identity_matches</td><td>{String(dryRunIdentity.identity_matches ?? '—')}</td></tr>
        <tr><td>created_calendar_identity.applied_event_count</td><td>{String(createdCalendarIdentity.applied_event_count ?? '—')}</td></tr>
        <tr><td>apply_gate_summary.service_insert_succeeded</td><td>{String(applyGateSummary.service_insert_succeeded ?? '—')}</td></tr>
        <tr><td>audit_status.validation_errors_count</td><td>{applyMutationResult ? String(applyMutationResult.validation_errors.length) : '—'}</td></tr>
        <tr><td>audit_status.validation_warnings_count</td><td>{applyMutationResult ? String(applyMutationResult.validation_warnings.length) : '—'}</td></tr>
      </tbody></table>
    </>
  )
}

export function ApplyResponseValidationPreviewPanel({
  applyMutationResult,
  issueCodeRegistryData
}: ApplyResponseValidationPreviewPanelProps): JSX.Element {
  if (!applyMutationResult) return <p>No create-only apply validation preview yet.</p>
  const preview = applyMutationResult.created_calendar_validation_preview
  const previewEntries = Object.keys(preview)
  if (previewEntries.length === 0) {
    return <p>No created-calendar validation preview was returned with this apply response.</p>
  }

  const readText = (key: string): string => {
    const value = preview[key]
    return value === undefined || value === null ? 'n/a' : String(value)
  }
  const readCountValuesShape = (key: string): { count: string; values: string } => {
    const value = preview[key]
    if (!value || typeof value !== 'object') return { count: 'n/a', values: 'n/a' }
    const recordValue = value as Record<string, unknown>
    const count = typeof recordValue.count === 'number' ? String(recordValue.count) : 'n/a'
    const values = Array.isArray(recordValue.values) ? recordValue.values.map(String).join(', ') : 'n/a'
    return { count, values }
  }
  const categoriesShape = readCountValuesShape('categories')
  const tourLevelsShape = readCountValuesShape('tour_levels')
  const hostCountriesShape = readCountValuesShape('host_countries')
  const issueCodesValue = Array.isArray(preview.issue_codes_first_10)
    ? preview.issue_codes_first_10.map(String).join(', ')
    : 'n/a'
  const previewIssueCodes = Array.isArray(preview.issue_codes_first_10)
    ? preview.issue_codes_first_10.map(String)
    : null
  const issueMetadataByCode = new Map(
    (issueCodeRegistryData?.codes ?? []).map((registryCode) => [registryCode.code, registryCode] as const)
  )

  return (
    <>
      <p>This preview comes from the create-only apply response. The separate target calendar validation panel may refetch the latest persisted state.</p>
      <p>Read-only apply-response validation preview. No mutation path is available in this panel.</p>
      <p>Validation status: {readText('validation_status')}</p>
      <p>Apply response validation interpretation: {describeValidationStatus(preview.validation_status, preview.error_count, preview.warning_count)}</p>
      <p>Calendar exists: {readText('calendar_exists')}</p>
      <p>Read-only: {readText('read_only')}</p>
      <p>Event count: {readText('event_count')}</p>
      <p>Error count: {readText('error_count')}</p>
      <p>Warning count: {readText('warning_count')}</p>
      <p>Info count: {readText('info_count')}</p>
      <p>First season week: {readText('first_season_week')}</p>
      <p>Last season week: {readText('last_season_week')}</p>
      <p>Categories count: {categoriesShape.count}</p>
      <p>Categories values: {categoriesShape.values}</p>
      <p>Tour levels count: {tourLevelsShape.count}</p>
      <p>Tour levels values: {tourLevelsShape.values}</p>
      <p>Host countries count: {hostCountriesShape.count}</p>
      <p>Host countries values: {hostCountriesShape.values}</p>
      <p>Issue codes (first 10): {issueCodesValue}</p>
      {previewIssueCodes ? <p>Apply-response issue code count: {previewIssueCodes.length}</p> : null}
      {previewIssueCodes ? (
        <>
          <h5>Apply-response issue code metadata</h5>
          <p>Metadata below documents only the issue codes returned in this apply response.</p>
          {previewIssueCodes.length > 0 ? (
            <table>
              <thead><tr><th>code</th><th>registry title</th><th>registry severity</th><th>registry field</th><th>registry description</th></tr></thead>
              <tbody>
                {previewIssueCodes.map((issueCode) => {
                  const metadata = issueMetadataByCode.get(issueCode)
                  return (
                    <tr key={issueCode}>
                      <td>{issueCode}</td>
                      <td>{metadata?.title ?? 'Unknown issue code'}</td>
                      <td>{metadata?.severity ?? 'n/a'}</td>
                      <td>{metadata?.field ?? 'n/a'}</td>
                      <td>{metadata?.description ?? 'No registry metadata available for this issue code.'}</td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          ) : <p>No apply-response issue codes to enrich.</p>}
        </>
      ) : null}
      <p>Message: {readText('message')}</p>
    </>
  )
}

export function ApplyResponseVsTargetValidationComparisonPanel({
  applyMutationResult,
  targetValidationData,
  targetValidationFetching,
  targetValidationError
}: ApplyResponseVsTargetValidationComparisonPanelProps): JSX.Element {
  if (!applyMutationResult) return <p>No apply-response validation preview to compare yet.</p>
  const preview = applyMutationResult.created_calendar_validation_preview
  if (Object.keys(preview).length === 0) return <p>Apply response did not include a created-calendar validation preview.</p>
  if (targetValidationFetching) return <p>Comparison pending refreshed target validation data.</p>
  if (targetValidationError) return <p>Unable to compare validation sources because target validation failed: {formatApiError(targetValidationError)}</p>
  if (!targetValidationData) return <p>Comparison pending refreshed target validation data.</p>

  const normalizeComparableValue = (value: unknown): string => {
    if (value === null || value === undefined) return 'n/a'
    if (typeof value === 'boolean') return value ? 'true' : 'false'
    if (typeof value === 'number' || typeof value === 'string') return String(value)
    if (typeof value === 'object') {
      try {
        return JSON.stringify(value)
      } catch {
        return 'n/a'
      }
    }
    return 'n/a'
  }
  const readPreviewValue = (key: string): string => normalizeComparableValue(preview[key])
  const readShapeCount = (value: unknown): string => {
    if (!value || typeof value !== 'object') return 'n/a'
    const recordValue = value as Record<string, unknown>
    return typeof recordValue.count === 'number' ? String(recordValue.count) : 'n/a'
  }
  const readPreviewShapeCount = (key: string): string => readShapeCount(preview[key])

  const targetSummary = targetValidationData.validation_summary
  const rows = [
    { field: 'validation_status', apply: readPreviewValue('validation_status'), target: normalizeComparableValue(targetSummary.status) },
    { field: 'calendar_exists', apply: readPreviewValue('calendar_exists'), target: normalizeComparableValue(targetValidationData.calendar_exists) },
    { field: 'read_only', apply: readPreviewValue('read_only'), target: normalizeComparableValue(targetValidationData.read_only) },
    { field: 'event_count', apply: readPreviewValue('event_count'), target: normalizeComparableValue(targetSummary.event_count) },
    { field: 'error_count', apply: readPreviewValue('error_count'), target: normalizeComparableValue(targetSummary.error_count) },
    { field: 'warning_count', apply: readPreviewValue('warning_count'), target: normalizeComparableValue(targetSummary.warning_count) },
    { field: 'info_count', apply: readPreviewValue('info_count'), target: normalizeComparableValue(targetSummary.info_count) },
    { field: 'first_season_week', apply: readPreviewValue('first_season_week'), target: normalizeComparableValue(targetSummary.first_season_week) },
    { field: 'last_season_week', apply: readPreviewValue('last_season_week'), target: normalizeComparableValue(targetSummary.last_season_week) },
    { field: 'categories.count', apply: readPreviewShapeCount('categories'), target: readShapeCount(targetSummary.categories) },
    { field: 'tour_levels.count', apply: readPreviewShapeCount('tour_levels'), target: readShapeCount(targetSummary.tour_levels) },
    { field: 'host_countries.count', apply: readPreviewShapeCount('host_countries'), target: readShapeCount(targetSummary.host_countries) }
  ]
  const allMatch = rows.every((row) => row.apply === row.target)
  const severityMatch = rows
    .filter((row) => ['validation_status', 'error_count', 'warning_count'].includes(row.field))
    .every((row) => row.apply === row.target)

  return (
    <>
      <p>Read-only diagnostic comparison between create-only apply response preview and refetched target validation.</p>
      <p>
        {allMatch
          ? 'Apply-response validation preview matches refetched target validation.'
          : 'Apply-response validation preview differs from refetched target validation.'}
      </p>
      <p>{severityMatch
        ? 'Both validation sources report the same validation severity.'
        : 'Validation severity differs between apply response and refetched target validation.'}
      </p>
      <table>
        <thead><tr><th scope="col">Field</th><th scope="col">Apply response preview</th><th scope="col">Refetched target validation</th><th scope="col">Match</th></tr></thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.field}>
              <td>{row.field}</td>
              <td>{row.apply}</td>
              <td>{row.target}</td>
              <td>{row.apply === row.target ? 'yes' : 'no'}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </>
  )
}

export function CreateOnlyApplyDangerZonePreviewPanel({
  readinessData,
  selectedTargetSeasonLabel,
  requiredConfirmationPhrase,
  confirmationText,
  setConfirmationText,
  mutationScopePreview,
  setMutationScopePreview,
  canSubmitCreateOnlyApply,
  onConfirmCreateOnlyApply,
  applyMutationStatus,
  applyMutationError,
  applyMutationResult,
  targetCalendarExistsAfterApply,
  createOnlyBlockedReason
}: CreateOnlyApplyDangerZonePreviewPanelProps): JSX.Element {
  const isBackendReadyForCreateOnly = readinessData?.can_execute_apply === true
    && readinessData?.would_create_calendar === true
    && readinessData?.can_mutate === false
    && readinessData?.service_insert_applicable === false
  const confirmationPhraseMatches = confirmationText.trim() === requiredConfirmationPhrase
  const mutationScopeMatches = mutationScopePreview.trim() === 'create_only'
  const futureSubmitEligibilityPreview = isBackendReadyForCreateOnly && confirmationPhraseMatches && mutationScopeMatches
  const applyWasSuccessful = applyMutationResult?.applied === true
  return (
    <>
      <p>Danger-zone guarded create-only apply command. This command can only create a missing calendar. It cannot merge or overwrite.</p>
      <p>A successful command will create persistent season calendar data.</p>
      <p>
        <label htmlFor="create-only-confirmation-preview">Future confirmation phrase preview</label><br />
        <textarea
          id="create-only-confirmation-preview"
          value={confirmationText}
          onChange={(event) => setConfirmationText(event.target.value)}
          placeholder={requiredConfirmationPhrase}
          rows={2}
        />
      </p>
      <p>
        <label htmlFor="create-only-mutation-scope-preview">Future create-only mutation scope preview</label><br />
        <input
          id="create-only-mutation-scope-preview"
          type="text"
          value={mutationScopePreview}
          onChange={(event) => setMutationScopePreview(event.target.value)}
          placeholder="create_only"
        />
      </p>
      <table><thead><tr><th scope="col">Requirement</th><th scope="col">Preview status</th></tr></thead><tbody>
        <tr><td>Backend readiness satisfied</td><td>{isBackendReadyForCreateOnly ? 'yes' : 'no'}</td></tr>
        <tr><td>Danger-zone target season</td><td>{readinessData?.target_season_label ?? (selectedTargetSeasonLabel || '—')}</td></tr>
        <tr><td>Required confirmation phrase</td><td>{requiredConfirmationPhrase}</td></tr>
        <tr><td>Danger-zone required mutation scope</td><td>create_only</td></tr>
        <tr><td>Confirmation phrase matches required phrase</td><td>{confirmationPhraseMatches ? 'yes' : 'no'}</td></tr>
        <tr><td>Mutation scope equals create_only</td><td>{mutationScopeMatches ? 'yes' : 'no'}</td></tr>
        <tr><td>Future submit eligibility preview</td><td>{futureSubmitEligibilityPreview ? 'yes' : 'no'}</td></tr>
        <tr><td>Danger-zone guarded command enabled</td><td>{canSubmitCreateOnlyApply ? 'yes' : 'no'}</td></tr>
      </tbody></table>
      {futureSubmitEligibilityPreview
        ? <p>All visible preview conditions are satisfied.</p>
        : <p>Create-only apply is not fully armed yet.</p>}
      {targetCalendarExistsAfterApply || createOnlyBlockedReason ? (
        <>
          <p>{createOnlyBlockedReason ?? 'Target calendar now exists. Create-only apply is locked out for this target.'}</p>
          <p>Use a future audited merge/overwrite workflow if changes are needed.</p>
        </>
      ) : null}
      <p>
        <button type="button" onClick={onConfirmCreateOnlyApply} disabled={!canSubmitCreateOnlyApply}>
          Execute create-only season calendar command
        </button>
      </p>
      {applyMutationStatus === 'pending' ? <p>Submitting guarded create-only command…</p> : null}
      {applyMutationStatus === 'error' ? (
        <div className="error">
          <p>Create-only command was rejected or failed; no success result is recorded in this panel.</p>
          <p>Create-only command failed: {formatApiError(applyMutationError)}</p>
        </div>
      ) : null}
      {applyMutationResult ? (
        <>
          <h4>{applyWasSuccessful ? 'Create-only apply result' : 'Create-only apply response (not applied)'}</h4>
          {!applyWasSuccessful ? <p className="error">Command response did not report applied=true.</p> : null}
          {applyWasSuccessful ? <p>Create-only calendar apply reported success.</p> : null}
          <table><thead><tr><th scope="col">Field</th><th scope="col">Value</th></tr></thead><tbody>
            <tr><td>applied</td><td>{String(applyMutationResult.applied)}</td></tr>
            <tr><td>applied_event_count</td><td>{String(applyMutationResult.applied_event_count)}</td></tr>
            <tr><td>target_season_label</td><td>{applyMutationResult.target_season_label}</td></tr>
            <tr><td>created_calendar_summary.event_count</td><td>{String(applyMutationResult.created_calendar_summary?.event_count ?? '—')}</td></tr>
            <tr><td>message</td><td>{applyMutationResult.message}</td></tr>
          </tbody></table>
        </>
      ) : null}
    </>
  )
}

export function CreateOnlyApplyGuardSummaryPanel({
  items,
  canSubmitCreateOnlyApply,
  createOnlyBlockedReason
}: CreateOnlyApplyGuardSummaryPanelProps): JSX.Element {
  return (
    <>
      <p>Read-only create-only apply guard summary checklist.</p>
      {canSubmitCreateOnlyApply
        ? <p>Create-only command is currently enabled by all guards.</p>
        : <p>Create-only command is currently blocked by one or more guards.</p>}
      {createOnlyBlockedReason ? <p>{createOnlyBlockedReason}</p> : null}
      <table><thead><tr><th scope="col">Create-only guard key</th><th scope="col">Create-only guard</th><th scope="col">Create-only guard passed</th><th scope="col">Create-only guard detail</th></tr></thead><tbody>
        {items.map((item) => (
          <tr key={item.key}>
            <td>{item.key}</td>
            <td>{item.label}</td>
            <td>{item.passed ? 'yes' : 'no'}</td>
            <td>{item.detail ?? '—'}</td>
          </tr>
        ))}
      </tbody></table>
    </>
  )
}

export function CreateOnlyApplyReadinessPanel({ queryEnabled, query }: CreateOnlyApplyReadinessPanelProps): JSX.Element {
  const formatValue = (value: unknown): string => {
    if (value === null || value === undefined) return '—'
    if (typeof value === 'object') return JSON.stringify(value)
    return String(value)
  }
  const shapeRecord = (value: unknown): Record<string, unknown> | null => value && typeof value === 'object' ? value as Record<string, unknown> : null
  const previewList = (value: unknown): unknown[] => Array.isArray(value) ? value : []
  const readStringArraySummary = (value: unknown): { count: number | null; values: string[] } => {
    const record = shapeRecord(value)
    if (!record) return { count: null, values: [] }
    const count = typeof record.count === 'number' ? record.count : null
    const values = Array.isArray(record.values) ? record.values.filter((item): item is string => typeof item === 'string') : []
    return { count, values }
  }
  const candidateSummary = shapeRecord(query.data?.candidate_summary)
  const categoriesSummary = readStringArraySummary(candidateSummary?.categories)
  const tourLevelsSummary = readStringArraySummary(candidateSummary?.tour_levels)
  const applyGateSummary = shapeRecord(query.data?.apply_gate_summary)
  const auditPreview = shapeRecord(query.data?.audit_preview)
  const isBackendReadyForCreateOnly = query.data?.can_execute_apply === true
    && query.data?.would_create_calendar === true
    && query.data?.can_mutate === false
    && query.data?.service_insert_applicable === false

  return (
    <>
      <p>Read-only create-only apply readiness check. This panel does not execute apply or create a calendar.</p>
      {!queryEnabled ? <p>Create-only apply readiness is waiting for required identities.</p> : null}
      {queryEnabled && query.isLoading ? <p>Loading create-only apply readiness…</p> : null}
      {queryEnabled && query.error ? <p className="error">Create-only apply readiness check failed: {formatApiError(query.error)}</p> : null}
      {queryEnabled && query.data ? (
        <>
          <table><thead><tr><th scope="col">Field</th><th scope="col">Value</th></tr></thead><tbody>
            <tr><td>enabled</td><td>{String(query.data.enabled)}</td></tr>
            <tr><td>can_execute_apply</td><td>{String(query.data.can_execute_apply)}</td></tr>
            <tr><td>can_mutate</td><td>{String(query.data.can_mutate)}</td></tr>
            <tr><td>would_create_calendar</td><td>{String(query.data.would_create_calendar)}</td></tr>
            <tr><td>service_insert_applicable</td><td>{String(query.data.service_insert_applicable)}</td></tr>
            <tr><td>target_season_label</td><td>{query.data.target_season_label}</td></tr>
            <tr><td>message</td><td>{query.data.message}</td></tr>
          </tbody></table>
          {!query.data.can_mutate ? <p>This panel is read-only because can_mutate is false.</p> : null}
          {isBackendReadyForCreateOnly
            ? <p>Backend readiness says create-only apply is ready, but this panel is still read-only. No calendar is created from this UI.</p>
            : <p>Create-only apply is not ready according to backend readiness.</p>}
          <h4>Safety checklist</h4>
          <table><thead><tr><th scope="col">Check</th><th scope="col">Value</th></tr></thead><tbody>
            <tr><td>Real apply endpoint called from UI</td><td>no</td></tr>
            <tr><td>Mutation hook installed</td><td>no</td></tr>
            <tr><td>Calendar created by this panel</td><td>no</td></tr>
            <tr><td>Backend readiness satisfied</td><td>{isBackendReadyForCreateOnly ? 'yes' : 'no'}</td></tr>
            <tr><td>Audit persisted</td><td>no</td></tr>
          </tbody></table>
          <h4>Apply gate checklist</h4>
          {applyGateSummary ? <table><thead><tr><th scope="col">gate</th><th scope="col">value</th></tr></thead><tbody>{Object.entries(applyGateSummary).map(([key, value]) => <tr key={`create-only-gate-${key}`}><td>{key}</td><td>{formatValue(value)}</td></tr>)}</tbody></table> : <p>Apply gate summary is unavailable.</p>}
          <h4>Candidate summary</h4>
          {candidateSummary ? <table><thead><tr><th scope="col">field</th><th scope="col">value</th></tr></thead><tbody>{Object.entries(candidateSummary).map(([key, value]) => <tr key={`create-only-candidate-${key}`}><td>{key}</td><td>{formatValue(value)}</td></tr>)}</tbody></table> : <p>Candidate summary is unavailable.</p>}
          <p>Candidate count: {formatValue(candidateSummary?.candidate_count)}</p>
          <p>First season week: {formatValue(candidateSummary?.first_season_week)}</p>
          <p>Last season week: {formatValue(candidateSummary?.last_season_week)}</p>
          <p>Categories count: {categoriesSummary.count ?? '—'}</p>
          <p>Categories values: {categoriesSummary.values.length ? categoriesSummary.values.join(', ') : '—'}</p>
          <p>Tour levels count: {tourLevelsSummary.count ?? '—'}</p>
          <p>Tour levels values: {tourLevelsSummary.values.length ? tourLevelsSummary.values.join(', ') : '—'}</p>
          <p>Audit persisted: {formatValue(auditPreview?.audit_persisted)}</p>
          <h4>Validation warnings</h4>
          {query.data.validation_warnings.length === 0 ? <p>No create-only readiness warnings returned.</p> : <ul>{query.data.validation_warnings.map((warning) => <li key={warning}>{warning}</li>)}</ul>}
          <h4>Validation errors</h4>
          {query.data.validation_errors.length === 0 ? <p>No create-only readiness errors returned.</p> : <ul>{query.data.validation_errors.map((error) => <li key={error}>{error}</li>)}</ul>}
        </>
      ) : null}
    </>
  )
}

export function FutureAuditedCommandFlowPanel(): JSX.Element {
  return (
    <>
      <ol>
        <li>Select target season.</li>
        <li>Select source.</li>
        <li>Review preflight diff.</li>
        <li>Submit explicit audited backend command.</li>
        <li>Reopen/validate resulting concrete season calendar.</li>
      </ol>
      <p>None of these commands are implemented on this page.</p>
    </>
  )
}

type ReadOnlyPreflightChecklistPanelProps = {
  registryLoaded: boolean
  hasTemplates: boolean
  allTemplatesWeek61: boolean
  slotsWithinRange: boolean
  validationQueryData: TourSeasonsValidationResponse | undefined
  validationQueryError: unknown
}

export function ReadOnlyPreflightChecklistPanel({
  registryLoaded,
  hasTemplates,
  allTemplatesWeek61,
  slotsWithinRange,
  validationQueryData,
  validationQueryError
}: ReadOnlyPreflightChecklistPanelProps): JSX.Element {
  return (
    <>
      <p>Read-only preflight preview. Not an authoritative build gate.</p>
      <ul className="dashboard-help-list">
        <li><strong>Severity: {registryLoaded ? 'OK' : 'Warning'}</strong> — Registry loaded</li>
        <li><strong>Severity: {hasTemplates ? 'OK' : 'Warning'}</strong> — At least one season template available</li>
        <li><strong>Severity: {hasTemplates && allTemplatesWeek61 ? 'OK' : 'Info'}</strong> — Template week_count is 61</li>
        <li><strong>Severity: {hasTemplates && slotsWithinRange ? 'OK' : 'Info'}</strong> — Template slots are within SW1–SW61</li>
        <li><strong>Severity: {validationQueryData ? 'Info' : validationQueryError ? 'Warning' : 'Info'}</strong> — Backend validation foundation available</li>
      </ul>
    </>
  )
}
