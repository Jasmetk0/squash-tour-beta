import { useEffect, useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'

import { getSeasonRegistry, getSeasonTemplates, getTourSeasonsValidation } from '../api/client'
import { DetailList } from '../components/DetailUi'
import { PageIntro, SectionCard } from '../components/RunScopedUi'
import type { SeasonRegistryEntry, SeasonTemplateSummary, TourSeasonsValidationResponse } from '../api/types'
import { formatApiError } from '../utils/apiErrors'
import { safeToLongSeasonLabel } from '../utils/seasonLabels'


type SourceType = 'season_template' | 'blank_calendar_planned' | 'another_season_planned' | 'custom_slot_planned'

const SOURCE_TYPE_OPTIONS: Array<{ value: SourceType; label: string }> = [
  { value: 'season_template', label: 'Season template' },
  { value: 'blank_calendar_planned', label: 'Blank calendar (planned)' },
  { value: 'another_season_planned', label: 'Another season (planned)' },
  { value: 'custom_slot_planned', label: 'Custom slot (planned)' }
]

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

function BuilderSelectionPanel(props: BuilderSelectionPanelProps): JSX.Element {
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

type TemplatePreview = {
  slotsWithinSw61: boolean
  qualificationSlotsCount: number
  earliestSlot: number | null
  latestSlot: number | null
}


function renderPreviewValue(value: string | number | null | undefined): string {
  if (value === null || value === undefined) return '—'
  if (typeof value === 'string' && value.trim() === '') return '—'
  return String(value)
}

type SelectionPreviewPanelProps = {
  selectedTargetSeason: SeasonRegistryEntry | null
  selectedSourceType: SourceType
  selectedTemplate: SeasonTemplateSummary | null
  selectedTemplatePreview: TemplatePreview | null
}

function SelectionPreviewPanel({ selectedTargetSeason, selectedSourceType, selectedTemplate, selectedTemplatePreview }: SelectionPreviewPanelProps): JSX.Element {
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


type DiffPreviewStatus = 'OK' | 'Info' | 'Warning' | 'Planned'

type DiffPreviewItem = {
  area: string
  status: DiffPreviewStatus
  message: string
}

function buildDiffPreviewItems(
  selectedTargetSeason: SeasonRegistryEntry | null,
  selectedSourceType: SourceType,
  selectedTemplate: SeasonTemplateSummary | null,
  selectedTemplatePreview: TemplatePreview | null
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
    { area: 'Existing calendar conflict detection', status: 'Planned', message: 'Planned; no concrete season calendar conflict diff is performed on this page.' },
    { area: 'Missing/extra slot comparison', status: 'Planned', message: 'Planned; missing/extra slot compare is not implemented on this page.' },
    { area: 'Category mismatch comparison', status: 'Planned', message: 'Planned; category-level diff checks are not implemented on this page.' },
    { area: 'Host/region travel conflict checks', status: 'Planned', message: 'Planned; host/region travel conflict checks are not implemented on this page.' },
    { area: 'Apply/replace action plan', status: 'Planned', message: 'Planned; apply/replace actions are intentionally not executable from this page.' }
  )

  return items
}

function DiffPreviewSkeletonPanel({ items }: { items: DiffPreviewItem[] }): JSX.Element {
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

function FutureAuditedCommandFlowPanel(): JSX.Element {
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

function ReadOnlyPreflightChecklistPanel({
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


export function AdminSeasonBuilderPage(): JSX.Element {
  const registryQuery = useQuery({ queryKey: ['season-registry'], queryFn: getSeasonRegistry, retry: false })
  const templatesQuery = useQuery({ queryKey: ['season-templates'], queryFn: getSeasonTemplates, retry: false })
  const validationQuery = useQuery({ queryKey: ['tour-seasons-validation'], queryFn: getTourSeasonsValidation, retry: false })

  const registry = registryQuery.data
  const templates = templatesQuery.data?.templates ?? []
  const seasonExamples = registry?.seasons.slice(0, 5) ?? []
  const [selectedTargetSeasonLabel, setSelectedTargetSeasonLabel] = useState('')
  const [selectedSourceType, setSelectedSourceType] = useState<SourceType>('season_template')
  const [selectedTemplateId, setSelectedTemplateId] = useState('')
  const hasTemplates = templates.length > 0
  const slotsWithinRange = templates.every((template) => template.slots.every((slot) => slot.season_week_start >= 1 && slot.season_week_end <= 61))
  const allTemplatesWeek61 = templates.every((template) => template.week_count === 61)

  useEffect(() => {
    if (!selectedTargetSeasonLabel && registry?.seasons.length) {
      setSelectedTargetSeasonLabel(registry.seasons[0].label)
    }
  }, [registry, selectedTargetSeasonLabel])

  useEffect(() => {
    if (!selectedTemplateId && templates.length) {
      setSelectedTemplateId(templates[0].template_id)
    }
  }, [templates, selectedTemplateId])

  const selectedTargetSeason = registry?.seasons.find((season) => season.label === selectedTargetSeasonLabel) ?? null
  const selectedTemplate = templates.find((template) => template.template_id === selectedTemplateId) ?? null

  const selectedTemplatePreview = useMemo(() => {
    if (!selectedTemplate) return null
    const slotsWithinSw61 = selectedTemplate.slots.every((slot) => slot.season_week_start >= 1 && slot.season_week_end <= 61)
    const qualificationSlotsCount = selectedTemplate.slots.filter((slot) => slot.has_qualification).length
    const allWeekStarts = selectedTemplate.slots.map((slot) => slot.season_week_start)
    const allWeekEnds = selectedTemplate.slots.map((slot) => slot.season_week_end)
    const earliestSlot = allWeekStarts.length ? Math.min(...allWeekStarts) : null
    const latestSlot = allWeekEnds.length ? Math.max(...allWeekEnds) : null
    return { slotsWithinSw61, qualificationSlotsCount, earliestSlot, latestSlot }
  }, [selectedTemplate])

  const diffPreviewItems = useMemo(
    () => buildDiffPreviewItems(selectedTargetSeason, selectedSourceType, selectedTemplate, selectedTemplatePreview),
    [selectedTargetSeason, selectedSourceType, selectedTemplate, selectedTemplatePreview]
  )

  return (
    <section className="panel">
      <PageIntro title="Season Builder" subtitle="Read-only preflight foundation for future season creation workflows." />

      <SectionCard title="Read-only foundation notes">
        <ul className="dashboard-help-list">
          <li>This page does not build or modify calendars.</li>
          <li>Build from template is planned.</li>
          <li>Copy from another season is planned.</li>
          <li>Blank calendar creation is planned.</li>
          <li>Compare/apply workflow is planned.</li>
          <li>Actual build actions will require explicit audited backend commands in a later phase.</li>
        </ul>
      </SectionCard>

      <SectionCard title="Target season candidates">
        {registryQuery.isLoading ? <p className="status">Loading season registry…</p> : null}
        {registryQuery.error ? <p className="error">Failed to load season registry: {formatApiError(registryQuery.error)}</p> : null}
        {registry ? (
          <>
            <div className="dashboard-grid">
              <article className="metric-card"><span>First season</span><strong>{registry.start_season}</strong></article>
              <article className="metric-card"><span>Last season</span><strong>{registry.end_season}</strong></article>
              <article className="metric-card"><span>Season count</span><strong>{registry.season_count}</strong></article>
              <article className="metric-card"><span>Week count</span><strong>{registry.week_count}</strong></article>
            </div>
            <p>Example season targets:</p>
            <DetailList
              items={seasonExamples.map((season) => (
                <Link key={season.label} to={`/admin/seasons/detail/${encodeURIComponent(season.label)}`}>{season.label}</Link>
              ))}
              emptyLabel="No season examples available."
            />
          </>
        ) : null}
      </SectionCard>

      <SectionCard title="Available season templates">
        {templatesQuery.isLoading ? <p className="status">Loading season templates…</p> : null}
        {templatesQuery.error ? <p className="error">Failed to load season templates: {formatApiError(templatesQuery.error)}</p> : null}
        {templatesQuery.data ? (
          <>
            <ul className="dashboard-help-list">
              <li>Template count: {templates.length}</li>
              <li>Source path: {templatesQuery.data.source_path ?? '—'}</li>
            </ul>
            {templates.map((template) => (
              <article key={template.template_id} className="metric-card">
                <p><strong>{template.name}</strong></p>
                <p>Template ID: {template.template_id}</p>
                <p>Slot count: {template.slot_count}</p>
                <p>Week count: {template.week_count}</p>
                <p>Status: {template.status}</p>
                <p><Link to={`/admin/tour-seasons/season-templates/${template.template_id}`}>Open template detail</Link></p>
              </article>
            ))}
          </>
        ) : null}
      </SectionCard>



      <SectionCard title="Planned source types">
        <ul className="dashboard-help-list">
          <li>Blank calendar</li>
          <li>Season template</li>
          <li>Another concrete season</li>
          <li>Existing tournament copied into season</li>
          <li>Custom tournament slot</li>
        </ul>
      </SectionCard>

      <SectionCard title="Read-only builder selection">
        <BuilderSelectionPanel
          selectedTargetSeasonLabel={selectedTargetSeasonLabel}
          setSelectedTargetSeasonLabel={setSelectedTargetSeasonLabel}
          selectedSourceType={selectedSourceType}
          setSelectedSourceType={setSelectedSourceType}
          selectedTemplateId={selectedTemplateId}
          setSelectedTemplateId={setSelectedTemplateId}
          seasons={registry?.seasons ?? []}
          templates={templates}
        />
      </SectionCard>

      <SectionCard title="Selection preview">
        <SelectionPreviewPanel
          selectedTargetSeason={selectedTargetSeason}
          selectedSourceType={selectedSourceType}
          selectedTemplate={selectedTemplate}
          selectedTemplatePreview={selectedTemplatePreview}
        />
      </SectionCard>

      <SectionCard title="Read-only diff preview skeleton">
        <DiffPreviewSkeletonPanel items={diffPreviewItems} />
      </SectionCard>

      <SectionCard title="Future audited command flow">
        <FutureAuditedCommandFlowPanel />
      </SectionCard>

      <SectionCard title="Read-only preflight checklist">
        <ReadOnlyPreflightChecklistPanel
          registryLoaded={Boolean(registry)}
          hasTemplates={hasTemplates}
          allTemplatesWeek61={allTemplatesWeek61}
          slotsWithinRange={slotsWithinRange}
          validationQueryData={validationQuery.data}
          validationQueryError={validationQuery.error}
        />
      </SectionCard>

      <SectionCard title="Navigation">
        <p><Link to="/admin/seasons">Back to Seasons</Link></p>
        <p><Link to="/admin/tour-seasons/season-registry">Open Season Registry</Link></p>
        <p><Link to="/admin/tour-seasons/season-templates">Open Season Templates</Link></p>
        <p><Link to="/admin/tour-seasons/compare">Open Calendar Compare / Apply</Link></p>
        <p><Link to="/admin/tour-seasons/validation">Open Calendar Validation</Link></p>
      </SectionCard>
    </section>
  )
}
