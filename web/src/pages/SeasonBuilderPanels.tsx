import { Link } from 'react-router-dom'

import type { SeasonCalendarBuildResponse, SeasonRegistryEntry, SeasonTemplateSummary, TourSeasonsValidationResponse } from '../api/types'
import { safeToLongSeasonLabel } from '../utils/seasonLabels'

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
