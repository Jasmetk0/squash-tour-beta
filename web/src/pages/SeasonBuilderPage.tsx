import { useEffect, useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'

import { getSeasonRegistry, getSeasonTemplates, getTourSeasonsValidation } from '../api/client'
import { DetailList } from '../components/DetailUi'
import { PageIntro, SectionCard } from '../components/RunScopedUi'
import { formatApiError } from '../utils/apiErrors'


type SourceType = 'season_template' | 'blank_calendar_planned' | 'another_season_planned' | 'custom_slot_planned'

const SOURCE_TYPE_OPTIONS: Array<{ value: SourceType; label: string }> = [
  { value: 'season_template', label: 'Season template' },
  { value: 'blank_calendar_planned', label: 'Blank calendar (planned)' },
  { value: 'another_season_planned', label: 'Another season (planned)' },
  { value: 'custom_slot_planned', label: 'Custom slot (planned)' }
]


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



      <SectionCard title="Read-only builder selection">
        <div className="dashboard-grid">
          <label>
            Target season
            <select aria-label="Target season select" value={selectedTargetSeasonLabel} onChange={(event) => setSelectedTargetSeasonLabel(event.target.value)}>
              {(registry?.seasons ?? []).map((season) => <option key={season.label} value={season.label}>{season.label}</option>)}
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
      </SectionCard>

      <SectionCard title="Selection preview">
        {selectedTargetSeason ? (
          <ul className="dashboard-help-list">
            <li>Target compact label: {selectedTargetSeason.label}</li>
            <li>Target start year: {selectedTargetSeason.season_start_year}</li>
            <li>Target registry status: {selectedTargetSeason.status}</li>
            <li>Target week count: {selectedTargetSeason.week_count}</li>
          </ul>
        ) : <p>No target season available for preview.</p>}

        {selectedSourceType === 'season_template' ? (
          selectedTemplate && selectedTemplatePreview ? (
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
          ) : <p>No season template available for preview.</p>
        ) : <p>Preview only. This source type has no executable workflow yet.</p>}
      </SectionCard>

      <SectionCard title="Future audited command flow">
        <ol>
          <li>Select target season.</li>
          <li>Select source.</li>
          <li>Review preflight diff.</li>
          <li>Submit explicit audited backend command.</li>
          <li>Reopen/validate resulting concrete season calendar.</li>
        </ol>
        <p>None of these commands are implemented on this page.</p>
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

      <SectionCard title="Read-only preflight checklist">
        <p>Read-only preflight preview. Not an authoritative build gate.</p>
        <ul className="dashboard-help-list">
          <li><strong>Severity: {registry ? 'OK' : 'Warning'}</strong> — Registry loaded</li>
          <li><strong>Severity: {hasTemplates ? 'OK' : 'Warning'}</strong> — At least one season template available</li>
          <li><strong>Severity: {hasTemplates && allTemplatesWeek61 ? 'OK' : 'Info'}</strong> — Template week_count is 61</li>
          <li><strong>Severity: {hasTemplates && slotsWithinRange ? 'OK' : 'Info'}</strong> — Template slots are within SW1–SW61</li>
          <li><strong>Severity: {validationQuery.data ? 'Info' : validationQuery.error ? 'Warning' : 'Info'}</strong> — Backend validation foundation available</li>
        </ul>
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
