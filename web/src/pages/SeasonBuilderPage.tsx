import { useEffect, useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Link } from 'react-router-dom'

import { getSeasonCalendar, getSeasonCalendarValidation, getSeasonRegistry, getSeasonTemplates, getTourSeasonsValidation, postSeasonBuilderApplyCommandContract, postSeasonBuilderApplyCreateOnlyCommand, postSeasonBuilderApplyCreateOnlyReadiness, postSeasonBuilderDryRunBuild, postSeasonBuilderPreflight } from '../api/client'
import { DetailList } from '../components/DetailUi'
import { PageIntro, SectionCard } from '../components/RunScopedUi'
import {
  buildSourceTargetPreflightSummaryItems,
  buildSourceTargetDiffDetailItems,
  buildBackendPreflightContractItems,
  buildFutureBuildCommandContractItems,
  buildFutureCommandReadinessItems,
  buildDisabledDryRunReadinessItems,
  buildApplyCommandReadinessItems,
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
  DisabledApplyCommandContractPanel,
  ApplyCommandReadinessSummaryPanel,
  CreateOnlyApplyReadinessPanel,
  CreateOnlyApplyGuardSummaryPanel,
  CreateOnlyApplyDangerZonePreviewPanel,
  PostApplyCalendarVerificationPanel,
  TargetCalendarValidationPanel,
  PostApplyAuditStatusPanel,
  DisabledDryRunReadinessSummaryPanel,
  ReadOnlyPreflightChecklistPanel,
  SelectionPreviewPanel,
  SourceTargetPreflightSummaryPanel,
  SourceTargetDiffDetailPanel,
  TargetCalendarStatusPanel,
  TemplateValidationSummaryPanel
} from './SeasonBuilderPanels'
import type { SourceType } from './SeasonBuilderPanels'
import type { CreateOnlyApplyGuardSummaryItem } from './SeasonBuilderPanels'
import type { SeasonBuilderApplyCommandContractRequest, SeasonBuilderApplyCreateOnlyCommandRequest, SeasonBuilderDryRunBuildRequest, SeasonBuilderPreflightRequest } from '../api/types'
import { formatApiError } from '../utils/apiErrors'


export function AdminSeasonBuilderPage(): JSX.Element {

  const queryClient = useQueryClient()
  const REQUIRED_CONFIRMATION_PHRASE = 'I understand this will create a new season calendar.'
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
  const [dangerZoneConfirmationText, setDangerZoneConfirmationText] = useState('')
  const [dangerZoneMutationScope, setDangerZoneMutationScope] = useState('')
  const targetCalendarQueryEnabled = Boolean(selectedTargetSeasonLabel)
  const targetCalendarQuery = useQuery({
    queryKey: ['season-builder-target-calendar', selectedTargetSeasonLabel],
    queryFn: () => getSeasonCalendar(selectedTargetSeasonLabel),
    enabled: targetCalendarQueryEnabled,
    retry: false
  })
  const targetCalendarValidationQuery = useQuery({
    queryKey: ['season-builder-target-calendar-validation', selectedTargetSeasonLabel],
    queryFn: () => getSeasonCalendarValidation(selectedTargetSeasonLabel),
    enabled: targetCalendarQueryEnabled,
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
  const disabledDryRunReadinessItems = useMemo(
    () => buildDisabledDryRunReadinessItems({ requestPayload: disabledDryRunBuildPayload, response: disabledDryRunBuildQuery.data }),
    [disabledDryRunBuildPayload, disabledDryRunBuildQuery.data]
  )
  const dryRunResultFingerprint = typeof disabledDryRunBuildQuery.data?.dry_run_result_preview?.dry_run_result_fingerprint === 'string'
    ? disabledDryRunBuildQuery.data?.dry_run_result_preview?.dry_run_result_fingerprint
    : ''
  const dryRunResultId = typeof disabledDryRunBuildQuery.data?.dry_run_result_preview?.dry_run_result_id === 'string'
    ? disabledDryRunBuildQuery.data?.dry_run_result_preview?.dry_run_result_id
    : ''
  const disabledApplyCommandContractPayload = useMemo<SeasonBuilderApplyCommandContractRequest>(() => ({
    target_season_label: backendPreflightPayload.target_season_label,
    source_type: backendPreflightPayload.source_type,
    source_template_id: backendPreflightPayload.source_template_id,
    overwrite_policy: backendPreflightPayload.overwrite_policy,
    preflight_fingerprint: backendPreflightQuery.data?.preflight_fingerprint ?? '',
    reviewed_diff_id: backendPreflightQuery.data?.reviewed_diff_id ?? '',
    dry_run_result_fingerprint: dryRunResultFingerprint,
    dry_run_result_id: dryRunResultId,
    requested_by: backendPreflightPayload.requested_by,
    audit_reason: dryRunAuditReason.trim() || null,
    explicit_confirmation: dryRunExplicitConfirmation.trim() || null,
    mutation_scope: dryRunMutationScope || null
  }), [backendPreflightPayload, backendPreflightQuery.data?.preflight_fingerprint, backendPreflightQuery.data?.reviewed_diff_id, dryRunResultFingerprint, dryRunResultId, dryRunAuditReason, dryRunExplicitConfirmation, dryRunMutationScope])
  const disabledApplyCommandContractEnabled = backendPreflightEnabled
    && Boolean(backendPreflightQuery.data?.preflight_fingerprint)
    && Boolean(backendPreflightQuery.data?.reviewed_diff_id)
    && Boolean(dryRunResultFingerprint)
    && Boolean(dryRunResultId)
  const disabledApplyCommandContractQuery = useQuery({
    queryKey: [
      'season-builder-apply-command-contract',
      selectedTargetSeasonLabel,
      selectedSourceType,
      selectedTemplateId,
      selectedOverwritePolicy,
      backendPreflightQuery.data?.preflight_fingerprint,
      backendPreflightQuery.data?.reviewed_diff_id,
      dryRunResultFingerprint,
      dryRunResultId,
      dryRunAuditReason,
      dryRunExplicitConfirmation,
      dryRunMutationScope
    ],
    queryFn: () => postSeasonBuilderApplyCommandContract(disabledApplyCommandContractPayload),
    enabled: disabledApplyCommandContractEnabled,
    retry: false
  })
  const createOnlyApplyReadinessEnabled = disabledApplyCommandContractEnabled
  const createOnlyApplyReadinessQuery = useQuery({
    queryKey: [
      'season-builder-apply-create-only-readiness',
      selectedTargetSeasonLabel,
      selectedSourceType,
      selectedTemplateId,
      selectedOverwritePolicy,
      backendPreflightQuery.data?.preflight_fingerprint,
      backendPreflightQuery.data?.reviewed_diff_id,
      dryRunResultFingerprint,
      dryRunResultId,
      dryRunAuditReason,
      dryRunExplicitConfirmation,
      dryRunMutationScope
    ],
    queryFn: () => postSeasonBuilderApplyCreateOnlyReadiness(disabledApplyCommandContractPayload),
    enabled: createOnlyApplyReadinessEnabled,
    retry: false
  })

  const hasRequiredApplyIdentities = Boolean(
    disabledApplyCommandContractPayload.target_season_label
    && disabledApplyCommandContractPayload.source_type === 'season_template'
    && disabledApplyCommandContractPayload.source_template_id
    && disabledApplyCommandContractPayload.preflight_fingerprint
    && disabledApplyCommandContractPayload.reviewed_diff_id
    && disabledApplyCommandContractPayload.dry_run_result_fingerprint
    && disabledApplyCommandContractPayload.dry_run_result_id
  )

  const createOnlyApplyMutation = useMutation({
    mutationFn: (payload: SeasonBuilderApplyCreateOnlyCommandRequest) => postSeasonBuilderApplyCreateOnlyCommand(payload),
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['season-builder-target-calendar', selectedTargetSeasonLabel] }),
        queryClient.invalidateQueries({ queryKey: ['season-builder-apply-create-only-readiness'] }),
        queryClient.invalidateQueries({ queryKey: ['season-builder-target-calendar-validation', selectedTargetSeasonLabel] }),
        queryClient.invalidateQueries({ queryKey: ['season-registry'] })
      ])
    },
    onError: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['season-builder-target-calendar', selectedTargetSeasonLabel] }),
        queryClient.invalidateQueries({ queryKey: ['season-builder-apply-create-only-readiness'] }),
        queryClient.invalidateQueries({ queryKey: ['season-builder-target-calendar-validation', selectedTargetSeasonLabel] })
      ])
    }
  })


  const readinessValidationClear = (createOnlyApplyReadinessQuery.data?.validation_errors?.length ?? 0) === 0
  const targetCalendarExistsStable = Boolean(targetCalendarQuery.data?.calendar) && !targetCalendarQuery.isFetching
  const targetCalendarExistsAfterApply = createOnlyApplyMutation.data?.applied === true
    && targetCalendarExistsStable
  const createOnlyBlockedByExistingTarget = targetCalendarExistsStable || targetCalendarExistsAfterApply
  const createOnlyBlockedReason = createOnlyBlockedByExistingTarget
    ? 'Target calendar now exists. Create-only apply is locked out for this target.'
    : null

  const canSubmitCreateOnlyApply = createOnlyApplyReadinessQuery.data?.can_execute_apply === true
    && createOnlyApplyReadinessQuery.data?.would_create_calendar === true
    && createOnlyApplyReadinessQuery.data?.can_mutate === false
    && createOnlyApplyReadinessQuery.data?.service_insert_applicable === false
    && dangerZoneConfirmationText.trim() === REQUIRED_CONFIRMATION_PHRASE
    && dangerZoneMutationScope.trim() === 'create_only'
    && hasRequiredApplyIdentities
    && readinessValidationClear
    && !createOnlyBlockedByExistingTarget
    && !createOnlyApplyMutation.isPending
  const createOnlyApplyGuardSummaryItems = useMemo<CreateOnlyApplyGuardSummaryItem[]>(() => [
    {
      key: 'backend_readiness_can_execute',
      label: 'Backend readiness allows execution',
      passed: createOnlyApplyReadinessQuery.data?.can_execute_apply === true
    },
    {
      key: 'backend_would_create_calendar',
      label: 'Backend would create calendar',
      passed: createOnlyApplyReadinessQuery.data?.would_create_calendar === true
    },
    {
      key: 'backend_endpoint_read_only_readiness',
      label: 'Readiness endpoint remains non-mutating',
      passed: createOnlyApplyReadinessQuery.data?.can_mutate === false && createOnlyApplyReadinessQuery.data?.service_insert_applicable === false
    },
    {
      key: 'confirmation_phrase',
      label: 'Exact confirmation phrase entered',
      passed: dangerZoneConfirmationText.trim() === REQUIRED_CONFIRMATION_PHRASE,
      detail: dangerZoneConfirmationText.trim() === REQUIRED_CONFIRMATION_PHRASE ? undefined : `Expected: ${REQUIRED_CONFIRMATION_PHRASE}`
    },
    {
      key: 'mutation_scope',
      label: 'Mutation scope is create_only',
      passed: dangerZoneMutationScope.trim() === 'create_only',
      detail: dangerZoneMutationScope.trim() === 'create_only' ? undefined : 'Enter create_only to satisfy this guard.'
    },
    {
      key: 'required_identities',
      label: 'Required identity fields are present',
      passed: hasRequiredApplyIdentities
    },
    {
      key: 'readiness_validation_clear',
      label: 'Readiness validation has no errors',
      passed: readinessValidationClear,
      detail: readinessValidationClear ? undefined : `validation_errors count: ${createOnlyApplyReadinessQuery.data?.validation_errors?.length ?? 0}`
    },
    {
      key: 'target_calendar_absent',
      label: 'Target calendar is absent/still eligible for create-only',
      passed: !createOnlyBlockedByExistingTarget,
      detail: createOnlyBlockedByExistingTarget ? 'Target calendar exists or was just created by a successful apply.' : undefined
    },
    {
      key: 'not_pending',
      label: 'No create-only command is currently pending',
      passed: !createOnlyApplyMutation.isPending
    }
  ], [
    createOnlyApplyReadinessQuery.data,
    dangerZoneConfirmationText,
    REQUIRED_CONFIRMATION_PHRASE,
    dangerZoneMutationScope,
    hasRequiredApplyIdentities,
    readinessValidationClear,
    createOnlyBlockedByExistingTarget,
    createOnlyApplyMutation.isPending
  ])

  const handleConfirmCreateOnlyApply = (): void => {
    if (!canSubmitCreateOnlyApply) return
    const payload: SeasonBuilderApplyCreateOnlyCommandRequest = {
      target_season_label: disabledApplyCommandContractPayload.target_season_label,
      source_type: disabledApplyCommandContractPayload.source_type,
      // Backend create-only apply contract currently supports season_template sources only.
      source_template_id: disabledApplyCommandContractPayload.source_template_id,
      overwrite_policy: disabledApplyCommandContractPayload.overwrite_policy,
      preflight_fingerprint: disabledApplyCommandContractPayload.preflight_fingerprint,
      reviewed_diff_id: disabledApplyCommandContractPayload.reviewed_diff_id,
      dry_run_result_fingerprint: disabledApplyCommandContractPayload.dry_run_result_fingerprint,
      dry_run_result_id: disabledApplyCommandContractPayload.dry_run_result_id,
      requested_by: disabledApplyCommandContractPayload.requested_by ?? 'local-admin-preview',
      audit_reason: disabledApplyCommandContractPayload.audit_reason ?? 'create-only calendar command',
      explicit_confirmation: dangerZoneConfirmationText.trim(),
      mutation_scope: dangerZoneMutationScope.trim()
    }
    createOnlyApplyMutation.mutate(payload)
  }


  const applyCommandReadinessItems = useMemo(
    () => buildApplyCommandReadinessItems({
      dryRunResponse: disabledDryRunBuildQuery.data,
      applyContractResponse: disabledApplyCommandContractQuery.data,
      applyRequestPayload: disabledApplyCommandContractPayload
    }),
    [disabledDryRunBuildQuery.data, disabledApplyCommandContractQuery.data, disabledApplyCommandContractPayload]
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
      <SectionCard title="Disabled apply command contract result">
        <DisabledApplyCommandContractPanel
          queryEnabled={disabledApplyCommandContractEnabled}
          requestPayload={disabledApplyCommandContractPayload}
          query={{ isLoading: disabledApplyCommandContractQuery.isLoading, error: disabledApplyCommandContractQuery.error, data: disabledApplyCommandContractQuery.data }}
        />
      </SectionCard>
      <SectionCard title="Create-only apply workflow guide">
        <p>Follow this create-only sequence before executing the guarded command:</p>
        <ol>
          <li>Review backend readiness and candidate summary.</li>
          <li>Review guard summary.</li>
          <li>Enter exact confirmation phrase and create_only scope.</li>
          <li>Execute the guarded create-only command only if all guards pass.</li>
          <li>Verify refreshed target calendar and post-apply lockout.</li>
          <li>Review audit/status summary.</li>
        </ol>
        <p>This workflow can only create a missing calendar.</p>
        <p>It cannot merge or overwrite an existing calendar.</p>
        <p>Merge/overwrite remain future audited workflows.</p>
      </SectionCard>

      <SectionCard title="Create-only apply readiness">
        <CreateOnlyApplyReadinessPanel
          queryEnabled={createOnlyApplyReadinessEnabled}
          query={{ isLoading: createOnlyApplyReadinessQuery.isLoading, error: createOnlyApplyReadinessQuery.error, data: createOnlyApplyReadinessQuery.data }}
        />
      </SectionCard>
      <SectionCard title="Create-only apply guard summary">
        <CreateOnlyApplyGuardSummaryPanel
          items={createOnlyApplyGuardSummaryItems}
          canSubmitCreateOnlyApply={canSubmitCreateOnlyApply}
          createOnlyBlockedReason={createOnlyBlockedReason}
        />
      </SectionCard>
      <SectionCard title="Create-only apply danger-zone command">
        <CreateOnlyApplyDangerZonePreviewPanel
          readinessData={createOnlyApplyReadinessQuery.data}
          selectedTargetSeasonLabel={selectedTargetSeasonLabel}
          requiredConfirmationPhrase={REQUIRED_CONFIRMATION_PHRASE}
          confirmationText={dangerZoneConfirmationText}
          setConfirmationText={setDangerZoneConfirmationText}
          mutationScopePreview={dangerZoneMutationScope}
          setMutationScopePreview={setDangerZoneMutationScope}
          canSubmitCreateOnlyApply={canSubmitCreateOnlyApply}
          onConfirmCreateOnlyApply={handleConfirmCreateOnlyApply}
          applyMutationStatus={createOnlyApplyMutation.status}
          applyMutationError={createOnlyApplyMutation.error}
          applyMutationResult={createOnlyApplyMutation.data}
          targetCalendarExistsAfterApply={targetCalendarExistsAfterApply}
          createOnlyBlockedReason={createOnlyBlockedReason}
        />
      </SectionCard>
      <SectionCard title="Post-apply calendar verification">
        <PostApplyCalendarVerificationPanel
          targetCalendarData={targetCalendarQuery.data}
          targetCalendarLoading={targetCalendarQuery.isLoading}
          targetCalendarFetching={targetCalendarQuery.isFetching}
          targetCalendarError={targetCalendarQuery.error}
          readinessData={createOnlyApplyReadinessQuery.data}
          readinessFetching={createOnlyApplyReadinessQuery.isFetching}
          applyMutationResult={createOnlyApplyMutation.data}
          targetCalendarExistsAfterApply={targetCalendarExistsAfterApply}
        />
      </SectionCard>
      <SectionCard title="Target calendar validation">
        <TargetCalendarValidationPanel
          queryEnabled={targetCalendarQueryEnabled}
          query={{
            isLoading: targetCalendarValidationQuery.isLoading,
            isFetching: targetCalendarValidationQuery.isFetching,
            error: targetCalendarValidationQuery.error,
            data: targetCalendarValidationQuery.data
          }}
        />
      </SectionCard>
      <SectionCard title="Post-apply audit/status summary">
        <PostApplyAuditStatusPanel
          applyMutationResult={createOnlyApplyMutation.data}
          requestedBy={disabledApplyCommandContractPayload.requested_by ?? 'local-admin-preview'}
          auditReason={disabledApplyCommandContractPayload.audit_reason ?? 'create-only calendar command'}
          explicitConfirmation={dangerZoneConfirmationText}
          mutationScope={dangerZoneMutationScope}
        />
      </SectionCard>

      <SectionCard title="Apply command readiness summary">
        <ApplyCommandReadinessSummaryPanel items={applyCommandReadinessItems} />
      </SectionCard>

      <SectionCard title="Disabled dry-run readiness summary">
        <DisabledDryRunReadinessSummaryPanel items={disabledDryRunReadinessItems} />
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
