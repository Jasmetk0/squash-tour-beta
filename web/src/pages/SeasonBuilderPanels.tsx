import { Link } from 'react-router-dom'

import type {
  SeasonBuilderDryRunBuildRequest,
  SeasonBuilderDryRunBuildResponse,
  SeasonBuilderPreflightRequest,
  SeasonBuilderPreflightResponse,
  SeasonCalendarBuildResponse,
  SeasonRegistryEntry,
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
  const generationDesignPreviewRecord = generationDesignPreview && typeof generationDesignPreview === 'object'
    ? generationDesignPreview as Record<string, unknown>
    : null
  const candidateEventContractPreviewRecord = candidateEventContractPreview && typeof candidateEventContractPreview === 'object'
    ? candidateEventContractPreview as Record<string, unknown>
    : null
  const conflictContractPreviewRecord = conflictContractPreview && typeof conflictContractPreview === 'object'
    ? conflictContractPreview as Record<string, unknown>
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
