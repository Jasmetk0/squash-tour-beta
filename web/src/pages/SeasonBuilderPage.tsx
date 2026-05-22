import { useEffect, useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'

import { getSeasonCalendar, getSeasonRegistry, getSeasonTemplates, getTourSeasonsValidation, postSeasonBuilderDryRunBuild, postSeasonBuilderPreflight } from '../api/client'
import { DetailList } from '../components/DetailUi'
import { PageIntro, SectionCard } from '../components/RunScopedUi'
import {
  buildSourceTargetPreflightSummaryItems,
  buildSourceTargetDiffDetailItems,
  buildBackendPreflightContractItems,
  buildFutureBuildCommandContractItems,
  buildFutureCommandReadinessItems,
  buildDiffPreviewItems,
  BackendPreflightContractPreviewPanel,
  BuildPolicyPreviewPanel,
  OverwriteMergePolicySelectorPanel,
  BackendPreflightResultPanel,
  BuilderSelectionPanel,
  DiffPreviewSkeletonPanel,
  FutureBuildCommandContractPanel,
  FutureCommandReadinessChecklistPanel,
  DryRunAuditMetadataPreviewPanel,
  FutureAuditedCommandFlowPanel,
  DisabledDryRunBuildContractPanel,
  ReadOnlyPreflightChecklistPanel,
  SelectionPreviewPanel,
  SourceTargetPreflightSummaryPanel,
  SourceTargetDiffDetailPanel,
  TargetCalendarStatusPanel,
  TemplateValidationSummaryPanel
} from './SeasonBuilderPanels'
import type { SourceType } from './SeasonBuilderPanels'
import type { SeasonBuilderDryRunBuildRequest, SeasonBuilderPreflightRequest } from '../api/types'
import { formatApiError } from '../utils/apiErrors'


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
  const [selectedOverwritePolicy, setSelectedOverwritePolicy] = useState<'none' | 'merge_preview' | 'overwrite_preview'>('none')
  const [dryRunAuditReason, setDryRunAuditReason] = useState('')
  const [dryRunExplicitConfirmation, setDryRunExplicitConfirmation] = useState('')
  const [dryRunMutationScope, setDryRunMutationScope] = useState('')
  const targetCalendarQuery = useQuery({
    queryKey: ['season-builder-target-calendar', selectedTargetSeasonLabel],
    queryFn: () => getSeasonCalendar(selectedTargetSeasonLabel),
    enabled: Boolean(selectedTargetSeasonLabel),
    retry: false
  })
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
  const targetCalendarExists = targetCalendarQuery.error
    ? null
    : targetCalendarQuery.data
      ? Boolean(targetCalendarQuery.data.calendar)
      : null

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
    () => buildDiffPreviewItems(selectedTargetSeason, selectedSourceType, selectedTemplate, selectedTemplatePreview, targetCalendarExists),
    [selectedTargetSeason, selectedSourceType, selectedTemplate, selectedTemplatePreview, targetCalendarExists]
  )
  const sourceTargetPreflightSummaryItems = useMemo(
    () => buildSourceTargetPreflightSummaryItems({ selectedTargetSeason, selectedSourceType, selectedTemplate, selectedTemplatePreview, targetCalendarExists }),
    [selectedTargetSeason, selectedSourceType, selectedTemplate, selectedTemplatePreview, targetCalendarExists]
  )
  const sourceTargetDiffDetailItems = useMemo(
    () => buildSourceTargetDiffDetailItems({
      selectedTargetSeason,
      selectedSourceType,
      selectedTemplate,
      selectedTemplatePreview,
      targetCalendarData: targetCalendarQuery.data,
      targetCalendarExists
    }),
    [selectedTargetSeason, selectedSourceType, selectedTemplate, selectedTemplatePreview, targetCalendarQuery.data, targetCalendarExists]
  )
  const backendPreflightContractItems = useMemo(() => buildBackendPreflightContractItems(), [])
  const futureBuildCommandContractItems = useMemo(() => buildFutureBuildCommandContractItems(), [])

  const backendPreflightPayload = useMemo<SeasonBuilderPreflightRequest>(() => ({
    target_season_label: selectedTargetSeasonLabel,
    source_type: selectedSourceType,
    source_template_id: selectedSourceType === 'season_template' ? selectedTemplateId || null : null,
    overwrite_policy: selectedOverwritePolicy === 'none' ? null : selectedOverwritePolicy,
    requested_by: 'local-admin-preview'
  }), [selectedTargetSeasonLabel, selectedSourceType, selectedTemplateId, selectedOverwritePolicy])

  const backendPreflightEnabled = Boolean(selectedTargetSeasonLabel)
    && (selectedSourceType !== 'season_template' || Boolean(selectedTemplateId))

  const backendPreflightQuery = useQuery({
    queryKey: ['season-builder-backend-preflight', selectedTargetSeasonLabel, selectedSourceType, selectedTemplateId, selectedOverwritePolicy],
    queryFn: () => postSeasonBuilderPreflight(backendPreflightPayload),
    enabled: backendPreflightEnabled,
    retry: false
  })
  const futureCommandReadinessItems = useMemo(
    () => buildFutureCommandReadinessItems({
      currentPreflightPayload: backendPreflightPayload,
      currentPreflightResult: backendPreflightQuery.data
    }),
    [backendPreflightPayload, backendPreflightQuery.data]
  )
  const disabledDryRunBuildPayload = useMemo<SeasonBuilderDryRunBuildRequest>(() => ({
    target_season_label: backendPreflightPayload.target_season_label,
    source_type: backendPreflightPayload.source_type,
    source_template_id: backendPreflightPayload.source_template_id,
    overwrite_policy: backendPreflightPayload.overwrite_policy,
    preflight_fingerprint: backendPreflightQuery.data?.preflight_fingerprint ?? '',
    reviewed_diff_id: backendPreflightQuery.data?.reviewed_diff_id ?? '',
    requested_by: backendPreflightPayload.requested_by,
    audit_reason: dryRunAuditReason.trim() || null,
    explicit_confirmation: dryRunExplicitConfirmation.trim() || null,
    mutation_scope: dryRunMutationScope || null
  }), [backendPreflightPayload, backendPreflightQuery.data?.preflight_fingerprint, backendPreflightQuery.data?.reviewed_diff_id, dryRunAuditReason, dryRunExplicitConfirmation, dryRunMutationScope])

  const disabledDryRunBuildQueryEnabled = backendPreflightEnabled
    && Boolean(backendPreflightQuery.data?.preflight_fingerprint)
    && Boolean(backendPreflightQuery.data?.reviewed_diff_id)

  const disabledDryRunBuildQuery = useQuery({
    queryKey: [
      'season-builder-dry-run-build-contract',
      selectedTargetSeasonLabel,
      selectedSourceType,
      selectedTemplateId,
      selectedOverwritePolicy,
      backendPreflightQuery.data?.preflight_fingerprint,
      backendPreflightQuery.data?.reviewed_diff_id,
      dryRunAuditReason,
      dryRunExplicitConfirmation,
      dryRunMutationScope
    ],
    queryFn: () => postSeasonBuilderDryRunBuild(disabledDryRunBuildPayload),
    enabled: disabledDryRunBuildQueryEnabled,
    retry: false
  })

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

      <SectionCard title="Target existing calendar preview">
        <TargetCalendarStatusPanel
          selectedTargetSeasonLabel={selectedTargetSeasonLabel}
          query={{ isLoading: targetCalendarQuery.isLoading, error: targetCalendarQuery.error, data: targetCalendarQuery.data }}
        />
      </SectionCard>

      <SectionCard title="Overwrite / merge policy preview">
        <BuildPolicyPreviewPanel targetCalendarExists={targetCalendarExists} />
      </SectionCard>

      <SectionCard title="Overwrite / merge policy selection for preflight">
        <OverwriteMergePolicySelectorPanel
          selectedOverwritePolicy={selectedOverwritePolicy}
          setSelectedOverwritePolicy={setSelectedOverwritePolicy}
          targetCalendarExists={targetCalendarExists}
        />
      </SectionCard>

      <SectionCard title="Source vs target preflight summary">
        <SourceTargetPreflightSummaryPanel items={sourceTargetPreflightSummaryItems} />
      </SectionCard>

      <SectionCard title="Read-only source/target diff detail">
        <SourceTargetDiffDetailPanel items={sourceTargetDiffDetailItems} />
      </SectionCard>

      <SectionCard title="Backend preflight contract preview">
        <BackendPreflightContractPreviewPanel items={backendPreflightContractItems} />
      </SectionCard>

      <SectionCard title="Backend preflight result">
        <BackendPreflightResultPanel
          queryEnabled={backendPreflightEnabled}
          requestPayload={backendPreflightPayload}
          query={{ isLoading: backendPreflightQuery.isLoading, error: backendPreflightQuery.error, data: backendPreflightQuery.data }}
        />
      </SectionCard>

      <SectionCard title="Future build command contract preview">
        <FutureBuildCommandContractPanel
          items={futureBuildCommandContractItems}
          currentPreflightPayload={backendPreflightPayload}
          currentPreflightResult={backendPreflightQuery.data}
        />
      </SectionCard>

      <SectionCard title="Future command readiness checklist">
        <FutureCommandReadinessChecklistPanel items={futureCommandReadinessItems} />
      </SectionCard>

      <SectionCard title="Dry-run audit metadata preview inputs">
        <DryRunAuditMetadataPreviewPanel
          auditReason={dryRunAuditReason}
          setAuditReason={setDryRunAuditReason}
          explicitConfirmation={dryRunExplicitConfirmation}
          setExplicitConfirmation={setDryRunExplicitConfirmation}
          mutationScope={dryRunMutationScope}
          setMutationScope={setDryRunMutationScope}
        />
      </SectionCard>

      <SectionCard title="Disabled dry-run build contract result">
        <DisabledDryRunBuildContractPanel
          queryEnabled={disabledDryRunBuildQueryEnabled}
          requestPayload={disabledDryRunBuildPayload}
          query={{ isLoading: disabledDryRunBuildQuery.isLoading, error: disabledDryRunBuildQuery.error, data: disabledDryRunBuildQuery.data }}
        />
      </SectionCard>

      {selectedSourceType === 'season_template' ? (
        <SectionCard title="Selected template validation summary">
          <TemplateValidationSummaryPanel selectedTemplate={selectedTemplate} />
        </SectionCard>
      ) : null}

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
