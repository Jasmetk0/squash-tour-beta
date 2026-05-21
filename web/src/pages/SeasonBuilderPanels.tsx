import { Link } from 'react-router-dom'

import type { SeasonBuilderPreflightResponse, SeasonCalendarBuildResponse, SeasonRegistryEntry, SeasonTemplateSummary, TourSeasonsValidationResponse } from '../api/types'
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
  query: {
    isLoading: boolean
    error: unknown
    data: SeasonBuilderPreflightResponse | undefined
  }
}

export function BackendPreflightResultPanel({ queryEnabled, query }: BackendPreflightResultPanelProps): JSX.Element {
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

  return (
    <>
      <p>Authoritative read-only backend preflight result. This endpoint does not build, merge, overwrite, or apply anything.</p>
      <table>
        <thead><tr><th scope="col">Field</th><th scope="col">Value</th></tr></thead>
        <tbody>
          <tr><td>can_build</td><td><strong>{String(data.can_build)}</strong></td></tr>
          <tr><td>target_season_label</td><td>{data.target_season_label}</td></tr>
          <tr><td>source_type</td><td>{data.source_type}</td></tr>
          <tr><td>source_template_id</td><td>{data.source_template_id ?? '—'}</td></tr>
          <tr><td>target_calendar_exists</td><td>{String(data.target_calendar_exists)}</td></tr>
          <tr><td>target_event_count</td><td>{String(data.target_event_count)}</td></tr>
          <tr><td>source_resolved</td><td>{String(data.source_resolved)}</td></tr>
          <tr><td>validation_warnings count</td><td>{data.validation_warnings.length}</td></tr>
          <tr><td>validation_errors count</td><td>{data.validation_errors.length}</td></tr>
        </tbody>
      </table>
      {!data.can_build ? <p><strong>can_build is false in this phase.</strong></p> : null}
      {data.validation_warnings.length ? <><h4>Validation warnings</h4><ul>{data.validation_warnings.map((w)=><li key={w}>{w}</li>)}</ul></> : null}
      {data.validation_errors.length ? <><h4>Validation errors</h4><ul>{data.validation_errors.map((e)=><li key={e}>{e}</li>)}</ul></> : null}
      <h4>Authoritative diff summary</h4>
      <pre>{JSON.stringify(data.authoritative_diff_summary, null, 2)}</pre>
      <h4>Audit preview</h4>
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
