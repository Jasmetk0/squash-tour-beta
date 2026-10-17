import { isBoundaryTarget } from './fullSimulationBoundaryTargets'
import { validateCalendarCreationPreview, validateExtensionPreview } from './runCalendarCreation'
import type { RunCalendarCreationInput, RunCalendarCreationPreview } from './runCalendarCreation'
import type {
  BootstrapNextSeasonPayload,
  BootstrapNextSeasonResponse,
  CountriesListResponse,
  CountriesImportPayload,
  CountriesImportResponse,
  CountriesMetadataResponse,
  ManualPlayerOverrideRecord,
  ManualPlayerOverridesListResponse,
  ManualPlayerOverrideUpsertPayload,
  ManualPlayerOverridesImportPayload,
  ManualPlayerOverridesImportResponse,
  TalentClassSummaryResponse,
  TalentClassYearPreviewResponse,
  TalentCalibrationResponse,
  TalentCalibrationCompareRequest,
  TalentCalibrationCompareResponse,
  TalentCalibrationMultiSeedRequest,
  TalentCalibrationMultiSeedResponse,
  MatchLabRequest,
  MatchLabResult,
  CountryRecord,
  CountryUpsertPayload,
  CreateRunPayload,
  EventListResponse,
  RunActivityResponse,
  EventRecord,
  FinalsQualificationResponse,
  FinalsResultResponse,
  FinalsSimulationResponse,
  FinalsSummaryResponse,
  FinalsEffectiveParticipantStateResponse,
  FinalsReplacementAuthorityResponse,
  FinalsReplacementPreviewPayload,
  FinalsReplacementDecisionPayload,
  HealthResponse,
  InitialPoolGeneratePayload,
  InitialPoolRegeneratePayload,
  CustomInitialPoolPlayerCreatePayload,
  InitialPoolPlayerUpdatePayload,
  InitialPoolAuditResponse,
  InitialPoolPlayer,
  InitialPoolResponse,
  RankingSnapshot,
  RaceSnapshot,
  RaceSnapshotListResponse,
  RankingSnapshotListResponse,
  NextSeasonPlayersResponse,
  PlayerTransitionsResponse,
  CanonicalTournamentEntryFieldState,
  CanonicalTournamentPreparationState,
  TournamentGroupMatchScheduleAuthority,
  GenerateTournamentGroupMatchSchedulePayload,
  TournamentRankingSnapshotAuthority,
  TournamentRankingPublicationOptions,
  AdoptTournamentRankingSnapshotPayload,
  TournamentEntryField,
  CreateTournamentEntryFieldPayload,
  CreateFinalsTournamentEntryFieldPayload,
  CanonicalPreDrawWithdrawalPayload,
  CanonicalPreDrawWithdrawalResult,
  CanonicalTournamentDrawState,
  CanonicalTournamentDrawAuthority,
  CanonicalDrawInputCommitPayload,
  CanonicalDrawGeneratePayload,
  CanonicalTournamentDrawProcessState,
  CanonicalDrawProcessConfigurePayload,
  CanonicalTournamentDrawRevisionHistoryState,
  CanonicalFrozenMainReplacementPreviewRequest,
  CanonicalFrozenMainReplacementPreview,
  CanonicalFrozenMainReplacementCommitPayload,
  CanonicalFrozenMainReplacementCommitResult,
  RunLineageApiResponse,
  RunStatusSummary,
  RunWorldStatus,
  RunSourceApiResponse,
  RunTalentPlanSummary,
  RunsIndexResponse,
  SeasonRolloverExecutionResponse,
  SeasonRolloverSummaryApiResponse,
  GeneratedPlayerProvenance,
  GeneratedPlayerProvenanceListResponse,
  MaterializeRunProspectsRequest,
  MaterializeRunProspectsResponse,
  MaterializedRunProspectTalentSummaryResponse,
  RunProspectListResponse,
  RunSummary,
  RunContainer,
  RunContainerListResponse,
  ViewerOfficialRunContext,
  ViewerTournamentEntryField,
  ViewerTournamentDraw,
  ViewerTournamentWildCards,
  ViewerTournamentHistory,
  ViewerRunCalendar,
  ViewerPlayers,
  ViewerCountries,
  ViewerTournamentResult,
  ViewerFinalsRaceHistory,
  ViewerOfficialRanking,
  ViewerOfficialRankingHistory,
  RunBranch,
  RunBranchListResponse,
  CreateRunBranchFromSavedRevisionRequest,
  ViewerBranchWorkingDraft,
  SavedRevisionHistoryResponse,
  SavedRevisionHistoryPageResponse,
  SavedRevisionComparison,
  SavedRevisionRecoveryActivityResponse,
  SavedRevisionHistoryDetail,
  RestoreSavedRevisionRequest,
  RestoreSavedRevisionResponse,
  SavedRevisionRestorePreflight,
  BranchCheckpoint,
  BranchCheckpointListResponse,
  CaptureInitialBranchCheckpointRequest,
  CaptureCurrentBranchCheckpointRequest,
  CaptureSeasonRolloverBranchCheckpointRequest,
  CaptureBootstrapStartBranchCheckpointRequest,
  CaptureCompletedEventBranchCheckpointRequest,
  CaptureCompletedWeekBranchCheckpointRequest,
  CaptureAdminActionBranchCheckpointRequest,
  BranchState,
  BranchStateListResponse,
  AdminForkRunBranchRequest,
  AdminForkRunBranchResponse,
  AdminSetOfficialRunBranchRequest,
  AdminSetOfficialRunBranchResponse,
  AdminBranchSimulateNextMatchRequest,
  AdminBranchSimulateNextMatchResponse,
  AdminBranchSimulateNextRoundRequest,
  AdminBranchSimulateNextRoundResponse,
  AdminBranchSimulateNextWeekRequest,
  AdminBranchSimulateNextWeekResponse,
  AdminBranchSimulateNextTournamentRequest,
  AdminBranchSimulateNextTournamentResponse,
  AdminBranchSimulateFullSeasonRequest,
  AdminBranchSimulateFullSeasonResponse,
  AdminBranchSimulateWorldTourFinalsRequest,
  AdminBranchSimulateWorldTourFinalsResponse,
  AuthoritativeSimulationPosition,
  AuthoritativeEntryDecisionSlotInspection,
  AuthoritativeExplicitApplicationValidationPayload,
  AuthoritativeApplicationValidationCommitResult,
  WeekTournamentLockInspection,
  WeekTournamentLockPreviewPayload,
  WeekTournamentLockPreview,
  WeekTournamentLockCommitPayload,
  WeekTournamentLockCommitResult,
  AuthoritativeSeasonTransitionPreflight,
  SeasonTransitionConfigurationPreview,
  OrdinarySeasonTransitionPayload,
  OrdinarySeasonTransitionResult,
  FinalSeasonTransitionPayload,
  FinalSeasonTransitionResult,
  AuthoritativeWeekScheduleInspection,
  AuthoritativeWeekSchedulePreflight,
  AuthoritativeWeekScheduleProposal,
  AuthoritativeWeekScheduleManualPreview,
  PreviewAuthoritativeWeekSchedulePayload,
  AdoptAuthoritativeWeekSchedulePayload,
  AdoptAuthoritativeWeekScheduleProposalPayload,
  AuthoritativeWeekScheduleAdoptionResult,
  AuthoritativeSimulationCommandPayload,
  AuthoritativeNextRallyPayload,
  AuthoritativeNextRallyResult,
  AuthoritativeMatchReplayCursor,
  AuthoritativeMatchReplayContext,
  AuthoritativeMatchReplayFrame,
  AuthoritativeMatchReplayList,
  AuthoritativeMatchTimelineCursor,
  AuthoritativeMatchStaminaCursor,
  AuthoritativeLiveMatchInspection,
  AuthoritativeLiveMatchTimeline,
  AuthoritativeLiveConfirmPayload,
  AuthoritativeLiveConfirmResult,
  AuthoritativeLiveReturnPayload,
  AuthoritativeLiveReturnResult,
  AuthoritativeLiveRangePayload,
  AuthoritativeLiveRangeResult,
  AuthoritativeMatchDayPreview,
  AuthoritativeMatchDayCommandPayload,
  AuthoritativeMatchDayResult,
  AuthoritativeRoundPreview,
  AuthoritativeRoundCommandPayload,
  AuthoritativeRoundResult,
  AuthoritativeTournamentPreview,
  AuthoritativeTournamentCommandPayload,
  AuthoritativeTournamentResult,
  AuthoritativeWeekPreviewPayload,
  AuthoritativeWeekPreview,
  AuthoritativeWeekCommandPayload,
  AuthoritativeWeekExecution,
  AuthoritativeSeasonPreviewPayload,
  AuthoritativeSeasonPreview,
  AuthoritativeSeasonCommandPayload,
  AuthoritativeSeasonExecution,
  AuthoritativeFullSimulationPreviewPayload,
  AuthoritativeFullSimulationPreview,
  AuthoritativeFullSimulationCommandPayload,
  AuthoritativeFullSimulationExecution,
  AuthoritativeFullSimulationPendingCollection,
  GlobalFullSimulationOperations,
  AuthoritativeFullSimulationAbandonPayload,
  AuthoritativeFullSimulationControlPayload,
  AuthoritativeFullSimulationControlResult,
  AuthoritativeFullSimulationRetargetPayload,
  AuthoritativeFullSimulationRetargetResult,
  AuthoritativeFullSimulationAbandonResult,
  AuthoritativeFullSimulationHistory,
  AuthoritativeFullSimulationParentDetail,
  AuthoritativeMatchReconstructionState,
  AuthoritativeMatchReconstructionPreviewPayload,
  AuthoritativeMatchReconstructionPreview,
  AuthoritativeMatchReconstructionCommitPayload,
  AuthoritativeMatchReconstructionCommitResult,
  AuthoritativeSimulationSavePreview,
  AuthoritativeSimulationSavePayload,
  AuthoritativeSimulationSaveResponse,
  RunProspectSourceSavePreview,
  RunProspectSourceSavePayload,
  RunProspectSourceSaveResponse,
  ProspectBridgeInspection,
  DerivedAuthoritativeWeekTransitionPreview,
  AuthoritativeWeekTransitionCommand,
  RunWeeklyIntakeCohortSeasonPreviewParams,
  RunWeeklyIntakeCohortSeasonPreviewResponse,
  RunPlayerDetail,
  AdminPlayerHealthView,
  AdminHealthEditRequest,
  AdminHealthEditPreview,
  AdminHealthEditResult,
  PlayerHealthSavePreview,
  PlayerHealthSavePayload,
  PlayerHealthSaveResponse,
  PlayerCareerHistoryResponse,
  PlayerCareerPerformanceResponse,
  PlayerTournamentResultsTimelineResponse,
  RunPlayersListResponse,
  RunNationDetail,
  RunNationsSummaryResponse,
  SeasonStateResponse,
  HistoricalBranchSeasonStateResponse,
  SimulateResponse,
  CanonicalWildCardState,
  CanonicalWildCardReviewPayload,
  CanonicalWildCardPreview,
  CanonicalWildCardCommitPayload,
  CanonicalWildCardCommitResult,
  WorldPackage,
  WorldPackageClonePayload,
  WorldPackageCloneResponse,
  WorldPackageCountriesResponse,
  WorldPackageCountryDetail,
  WorldPackageCountryUpdatePayload,
  WorldPackageCountryCreatePayload,
  WorldPackageCountryDeleteResponse,
  WorldPackageCountryUpdateResponse,
  WorldPackageCountryPopulationUpdatePayload,
  WorldPackageGeography,
  WorldPackageCountryEffectivePopulationResponse,
  WeeklyIntakePreviewParams,
  WeeklyIntakePreviewResponse,
  WeeklyIntakeSeasonSchedulePreviewParams,
  WeeklyIntakeSeasonSchedulePreviewResponse,
  WorldPackageImportPayload,
  WorldPackageImportResponse,
  WorldPackageListResponse,
  WorldPackageValidation,
  TournamentTemplatesDatasetResponse,
  TournamentTemplatesImportPayload,
  TournamentTemplatesImportResponse,
  TournamentTemplatesListResponse,
  TournamentTemplatesMetadataResponse,
  TournamentTemplateRecord,
  TournamentTemplateUpsertPayload,
  SeasonActivePlayersResponse,
  SeasonCalendarBuildResponse,
  SeasonCalendarEvent,
  TournamentProgressionStatus,
  SeasonEventDrawPackageResult,
  SeasonEventMatchPackageResult,
  MatchReplayCursorResponse,
  MatchReplayResponse,
  SeasonEventResultPackageResult,
  EventPointAwardPackageResult,
  PlayerPointBreakdownQueryParams,
  PlayerPointBreakdownResponse,
  RankingTableQueryParams,
  RankingTableResponse,
  WeeklyRankingSnapshotGeneratePayload,
  WeeklyRankingSnapshotResult,
  SeasonEventEntryListResult,
  SeasonLifecycleResponse,
  SimulateSeasonWeekPreflightRequest,
  SimulateSeasonWeekPreflightResult,
  SeasonWeekRecoveryRequest,
  SeasonWeekRecoveryResult,
  SeasonReadinessRequest,
  SeasonReadinessResult,
  SeasonRangePreflightRequest,
  SeasonRangePreflightResult,
  CalendarTemplateCompareDryRunRequest,
  CalendarTemplateCompareDryRunResponse,
  CalendarTemplateDetailResponse,
  CalendarTemplateListResponse,
  CalendarTemplateUpsertPayload,
  PlanningSeasonCalendarDetailResponse,
  PlanningSeasonCalendarListResponse,
  PlanningCalendarApplyTemplateCommandRequest,
  PlanningCalendarApplyTemplateCommandResponse,
  SeasonRegistryResponse,
  SeasonTemplatesResponse,
  SeasonTemplateSlotValidationResponse,
  SeasonTemplateSlotValidationIssueCodeRegistryResponse,
  SeasonTemplateSlotConflictReportResponse,
  SeasonTemplateSlotConflictCodeRegistryResponse,
  SeasonBuilderPreflightRequest,
  SeasonBuilderPreflightResponse,
  SeasonBuilderDryRunBuildRequest,
  SeasonBuilderDryRunBuildResponse,
  SeasonBuilderApplyCommandContractRequest,
  SeasonBuilderApplyCommandContractResponse,
  SeasonBuilderApplyCreateOnlyCommandRequest,
  SeasonBuilderApplyCreateOnlyCommandResponse,
  SeasonBuilderApplyCreateOnlyReadinessResponse,
  SeasonBuilderFutureApplyRequestValidationPreviewRequest,
  SeasonBuilderFutureApplyRequestValidationPreviewResponse,
  CategoriesResponse,
  TournamentMastersResponse,
  TourSeasonsValidationResponse,
  SeasonCalendarValidationResponse,
  SeasonCalendarValidationIssueCodeRegistryResponse
} from './types'

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:8000'

class ApiError extends Error {
  status: number

  constructor(message: string, status: number) {
    super(message)
    this.status = status
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: { 'Content-Type': 'application/json', ...(init?.headers ?? {}) }
  })

  if (!response.ok) {
    const body = await response.text()
    throw new ApiError(body || 'Request failed', response.status)
  }

  if (response.status === 204) {
    return undefined as T
  }

  const text = await response.text()
  if (!text) {
    return undefined as T
  }
  return JSON.parse(text) as T
}

export function previewRunCalendarPlayerPool(runId: string, branchId: string,
  input: import('./calendarInitialPool').CalendarPoolInput): Promise<unknown> {
  return request(`/admin/players/runs/${encodeURIComponent(runId)}/branches/${encodeURIComponent(branchId)}/initial-pool/world-package/calendar-preview`,
    {method: 'POST', body: JSON.stringify(input)})
}

export async function getRunCalendarPopulation(runId:string,branchId:string):Promise<unknown|null> {
  try {return await request(`${runInitialWorldRoot(runId,branchId)}/calendar-adoption`)}
  catch(e) {if(e instanceof ApiError && e.status===404)return null;throw e}
}
export function reviewRunCalendarPopulation(runId:string,branchId:string,
  payload:import('./calendarPopulation').CalendarPopulationRequest):Promise<unknown> {
  return request(`${runInitialWorldRoot(runId,branchId)}/calendar-adoption/preview`,{method:'POST',body:JSON.stringify(payload)})
}
export function confirmRunCalendarPopulation(runId:string,branchId:string,
  review:import('./calendarPopulation').CalendarPopulationRequest,expectedFingerprint:string):Promise<unknown> {
  return request(`${runInitialWorldRoot(runId,branchId)}/calendar-adoption`,{method:'POST',body:JSON.stringify({
    review,expected_initial_world_fingerprint:expectedFingerprint})})
}


export function getInitialPlayerPool(season = '2000/2001'): Promise<InitialPoolResponse> {
  return request(`/admin/players/initial-pool?season=${encodeURIComponent(season)}`)
}

export function getSeasonActivePlayers(season = '2000/2001'): Promise<SeasonActivePlayersResponse> {
  return request(`/admin/seasons/${encodeURIComponent(season)}/players`)
}

export function getSeasonRegistry(): Promise<SeasonRegistryResponse> {
  return request('/admin/seasons/registry')
}

export function getSeasonTemplates(): Promise<SeasonTemplatesResponse> {
  return request('/admin/seasons/templates')
}

export function listCalendarTemplates(): Promise<CalendarTemplateListResponse> {
  return request('/admin/seasons/calendar-templates')
}

export function getCalendarTemplate(templateId: string): Promise<CalendarTemplateDetailResponse> {
  return request(`/admin/seasons/calendar-templates/${encodeURIComponent(templateId)}`)
}

export function createCalendarTemplate(payload: CalendarTemplateUpsertPayload): Promise<CalendarTemplateDetailResponse> {
  return request('/admin/seasons/calendar-templates', { method: 'POST', body: JSON.stringify(payload) })
}

export function updateCalendarTemplate(templateId: string, payload: CalendarTemplateUpsertPayload): Promise<CalendarTemplateDetailResponse> {
  return request(`/admin/seasons/calendar-templates/${encodeURIComponent(templateId)}`, { method: 'PUT', body: JSON.stringify(payload) })
}

export function compareCalendarTemplateDryRun(payload: CalendarTemplateCompareDryRunRequest): Promise<CalendarTemplateCompareDryRunResponse> {
  return request('/admin/seasons/calendar-templates/compare-dry-run', { method: 'POST', body: JSON.stringify(payload) })
}

export function listPlanningSeasonCalendars(): Promise<PlanningSeasonCalendarListResponse> {
  return request('/admin/seasons/planning-calendars')
}

export function getPlanningSeasonCalendar(seasonLabel: string): Promise<PlanningSeasonCalendarDetailResponse> {
  return request(`/admin/seasons/planning-calendars/${encodeURIComponent(seasonLabel)}`)
}

export function applyCalendarTemplateToPlanningCalendar(
  seasonLabel: string,
  payload: PlanningCalendarApplyTemplateCommandRequest
): Promise<PlanningCalendarApplyTemplateCommandResponse> {
  return request(`/admin/seasons/planning-calendars/${encodeURIComponent(seasonLabel)}/apply-template`, { method: 'POST', body: JSON.stringify(payload) })
}

export function getSeasonTemplateSlotValidation(templateId: string): Promise<SeasonTemplateSlotValidationResponse> {
  return request(`/admin/seasons/templates/${encodeURIComponent(templateId)}/slot-validation`)
}

export function getSeasonTemplateSlotValidationIssueCodes(): Promise<SeasonTemplateSlotValidationIssueCodeRegistryResponse> {
  return request('/admin/seasons/templates/slot-validation/issue-codes')
}

export function getSeasonTemplateSlotConflicts(templateId: string): Promise<SeasonTemplateSlotConflictReportResponse> {
  return request(`/admin/seasons/templates/${encodeURIComponent(templateId)}/slot-conflicts`)
}

export function getSeasonTemplateSlotConflictCodes(): Promise<SeasonTemplateSlotConflictCodeRegistryResponse> {
  return request('/admin/seasons/templates/slot-conflicts/codes')
}

export function postSeasonBuilderPreflight(payload: SeasonBuilderPreflightRequest): Promise<SeasonBuilderPreflightResponse> {
  return request('/admin/seasons/builder/preflight', { method: 'POST', body: JSON.stringify(payload) })
}

export function postSeasonBuilderDryRunBuild(payload: SeasonBuilderDryRunBuildRequest): Promise<SeasonBuilderDryRunBuildResponse> {
  return request('/admin/seasons/builder/dry-run-build', { method: 'POST', body: JSON.stringify(payload) })
}

export function postSeasonBuilderApplyCommandContract(
  payload: SeasonBuilderApplyCommandContractRequest
): Promise<SeasonBuilderApplyCommandContractResponse> {
  return request('/admin/seasons/builder/apply-command-contract', { method: 'POST', body: JSON.stringify(payload) })
}


export function postSeasonBuilderApplyCreateOnlyCommand(
  payload: SeasonBuilderApplyCreateOnlyCommandRequest
): Promise<SeasonBuilderApplyCreateOnlyCommandResponse> {
  return request('/admin/seasons/builder/apply-create-only-command', { method: 'POST', body: JSON.stringify(payload) })
}

export function postSeasonBuilderApplyCreateOnlyReadiness(
  payload: SeasonBuilderApplyCommandContractRequest
): Promise<SeasonBuilderApplyCreateOnlyReadinessResponse> {
  return request('/admin/seasons/builder/apply-create-only-readiness', { method: 'POST', body: JSON.stringify(payload) })
}


export async function validateFutureApplyRequestPreview(
  payload: SeasonBuilderFutureApplyRequestValidationPreviewRequest
): Promise<SeasonBuilderFutureApplyRequestValidationPreviewResponse> {
  return request('/admin/seasons/builder/future-apply-request-validation-preview', {
    method: 'POST',
    body: JSON.stringify(payload)
  })
}

export function getCategories(): Promise<CategoriesResponse> {
  return request('/admin/categories')
}

export function getTournaments(): Promise<TournamentMastersResponse> {
  return request('/admin/tournaments')
}

export function getTourSeasonsValidation(): Promise<TourSeasonsValidationResponse> {
  return request('/admin/tour-seasons/validation')
}


function rankingTableQuery(params: RankingTableQueryParams = {}): string {
  const query = new URLSearchParams()
  if (params.table_type) query.set('table_type', params.table_type)
  if (typeof params.limit === 'number') query.set('limit', String(params.limit))
  if (params.country_code) query.set('country_code', params.country_code)
  if (params.search) query.set('search', params.search)
  if (typeof params.include_zero_points === 'boolean') query.set('include_zero_points', String(params.include_zero_points))
  if (typeof params.min_points === 'number') query.set('min_points', String(params.min_points))
  return query.size ? `?${query.toString()}` : ''
}

export function getAdminRankingTable(season = '2000/2001', params: RankingTableQueryParams = {}): Promise<RankingTableResponse> {
  return request(`/admin/rankings/${encodeURIComponent(season)}${rankingTableQuery(params)}`)
}

export function getViewerRankingTable(season = '2000/2001', params: RankingTableQueryParams = {}): Promise<RankingTableResponse> {
  return request(`/viewer/rankings/${encodeURIComponent(season)}${rankingTableQuery(params)}`)
}

export function getAdminRankingSnapshot(season = '2000/2001', seasonWeek = 1): Promise<WeeklyRankingSnapshotResult> {
  return request(`/admin/ranking-snapshots/${encodeURIComponent(season)}?season_week=${seasonWeek}`)
}

export function generateAdminRankingSnapshot(season = '2000/2001', seasonWeek = 1, payload: WeeklyRankingSnapshotGeneratePayload = {}): Promise<WeeklyRankingSnapshotResult> {
  return request(`/admin/ranking-snapshots/${encodeURIComponent(season)}/generate?season_week=${seasonWeek}`, { method: 'POST', body: JSON.stringify(payload) })
}

export function getViewerRankingSnapshot(season = '2000/2001', seasonWeek = 1): Promise<WeeklyRankingSnapshotResult> {
  return request(`/viewer/ranking-snapshots/${encodeURIComponent(season)}?season_week=${seasonWeek}`)
}

function pointBreakdownQuery(params: PlayerPointBreakdownQueryParams = {}): string {
  const query = new URLSearchParams()
  if (params.player_id) query.set('player_id', params.player_id)
  if (params.search) query.set('search', params.search)
  if (params.country_code) query.set('country_code', params.country_code)
  if (typeof params.applied_only === 'boolean') query.set('applied_only', String(params.applied_only))
  if (params.table_type) query.set('table_type', params.table_type)
  if (typeof params.limit === 'number') query.set('limit', String(params.limit))
  if (typeof params.include_zero_point_awards === 'boolean') query.set('include_zero_point_awards', String(params.include_zero_point_awards))
  return query.size ? `?${query.toString()}` : ''
}

export function getAdminPointBreakdown(season = '2000/2001', params: PlayerPointBreakdownQueryParams = {}): Promise<PlayerPointBreakdownResponse> {
  return request(`/admin/point-breakdowns/${encodeURIComponent(season)}${pointBreakdownQuery(params)}`)
}

export function getViewerPointBreakdown(season = '2000/2001', params: PlayerPointBreakdownQueryParams = {}): Promise<PlayerPointBreakdownResponse> {
  return request(`/viewer/point-breakdowns/${encodeURIComponent(season)}${pointBreakdownQuery(params)}`)
}

export function getSeasonCalendar(season: string): Promise<SeasonCalendarBuildResponse> {
  return request(`/admin/seasons/${encodeURIComponent(season)}/calendar`)
}

export function getSeasonCategoryPoints(season: string): Promise<import('./types').SeasonCategoryPointsResponse> {
  return request(`/admin/seasons/${encodeURIComponent(season)}/category-points`)
}

export function initializeSeasonCategoryPoints(season: string): Promise<import('./types').SeasonCategoryPointsResponse> {
  return request(`/admin/seasons/${encodeURIComponent(season)}/category-points/initialize`, { method: 'POST' })
}

export function updateSeasonCategoryPoints(season: string, category: string, rankingPointsTable: Record<string, number>): Promise<import('./types').SeasonCategoryPointsTable> {
  return request(`/admin/seasons/${encodeURIComponent(season)}/category-points/${encodeURIComponent(category)}`, { method: 'PUT', body: JSON.stringify({ ranking_points_table: rankingPointsTable }) })
}

export function updateTournamentEditionRanking(season: string, eventId: string, payload: { ranking_status: 'ranked' | 'unranked'; ranking_points_table: Record<string, unknown> }): Promise<SeasonCalendarEvent> {
  return request(`/admin/seasons/${encodeURIComponent(season)}/calendar/events/${encodeURIComponent(eventId)}/ranking`, { method: 'PATCH', body: JSON.stringify(payload) })
}

export function getSeasonCalendarValidation(season: string): Promise<SeasonCalendarValidationResponse> {
  return request(`/admin/seasons/${encodeURIComponent(season)}/calendar/validation`)
}

export function getSeasonCalendarValidationIssueCodes(): Promise<SeasonCalendarValidationIssueCodeRegistryResponse> {
  return request('/admin/seasons/calendar/validation/issue-codes')
}

export function getSeasonLifecycle(season: string): Promise<SeasonLifecycleResponse> {
  return request(`/admin/lifecycle/${encodeURIComponent(season)}`)
}


function verifyLegacySeasonReadinessBoundary(metadata: {
  authority_scope: string
  canonical_run_readiness_eligible: boolean
}): void {
  if (
    metadata.authority_scope !== 'legacy_global_season_tooling.v1' ||
    metadata.canonical_run_readiness_eligible !== false
  ) {
    throw new Error(
      'Legacy season readiness endpoint returned an invalid authority boundary.'
    )
  }
}

export async function preflightSeasonWeek(payload: SimulateSeasonWeekPreflightRequest): Promise<SimulateSeasonWeekPreflightResult> {
  const data = await request<SimulateSeasonWeekPreflightResult>(
    `/admin/weeks/preflight`,
    { method: 'POST', body: JSON.stringify(payload) }
  )
  verifyLegacySeasonReadinessBoundary(data.metadata)
  return data
}

export function recoverSeasonWeek(payload: SeasonWeekRecoveryRequest): Promise<SeasonWeekRecoveryResult> {
  return request(`/admin/weeks/recovery`, { method: 'POST', body: JSON.stringify(payload) })
}

export async function getSeasonReadiness(payload: SeasonReadinessRequest): Promise<SeasonReadinessResult> {
  const data = await request<SeasonReadinessResult>(
    `/admin/seasons/readiness`,
    { method: 'POST', body: JSON.stringify(payload) }
  )
  verifyLegacySeasonReadinessBoundary(data.metadata)
  return data
}

export async function preflightSeasonRange(payload: SeasonRangePreflightRequest): Promise<SeasonRangePreflightResult> {
  const data = await request<SeasonRangePreflightResult>(
    `/admin/seasons/range-preflight`,
    { method: 'POST', body: JSON.stringify(payload) }
  )
  verifyLegacySeasonReadinessBoundary(data.metadata)
  return data
}


export function getEventEntryList(eventId: string): Promise<SeasonEventEntryListResult> {
  return request(`/admin/entries/${encodeURIComponent(eventId)}`)
}


export function getEventDrawPackage(eventId: string): Promise<SeasonEventDrawPackageResult> {
  return request(`/admin/draws/${encodeURIComponent(eventId)}`)
}


export function getEventMatchPackage(eventId: string): Promise<SeasonEventMatchPackageResult> {
  return request(`/admin/matches/${encodeURIComponent(eventId)}`)
}




export function getEventMatchReplay(eventId: string, matchId: string): Promise<MatchReplayResponse> {
  return request(`/admin/matches/${encodeURIComponent(eventId)}/replay/${encodeURIComponent(matchId)}`)
}

export function getEventMatchReplayCursor(eventId: string, matchId: string, rallyIndex: number): Promise<MatchReplayCursorResponse> {
  const query = new URLSearchParams({ rally_index: String(rallyIndex) })
  return request(`/admin/matches/${encodeURIComponent(eventId)}/replay/${encodeURIComponent(matchId)}/cursor?${query.toString()}`)
}

export function getEventProgressionStatus(eventId: string): Promise<TournamentProgressionStatus> {
  return request(`/admin/matches/${encodeURIComponent(eventId)}/progression`)
}






export function getEventResultPackage(eventId: string): Promise<SeasonEventResultPackageResult> {
  return request(`/admin/results/${encodeURIComponent(eventId)}`)
}


export function getEventPointAwards(eventId: string): Promise<EventPointAwardPackageResult> {
  return request(`/admin/points/${encodeURIComponent(eventId)}`)
}



export function generateInitialPlayerPool(payload: InitialPoolGeneratePayload): Promise<InitialPoolResponse> {
  return request('/admin/players/initial-pool/generate', { method: 'POST', body: JSON.stringify(payload) })
}

export function regenerateInitialPlayerPool(payload: InitialPoolRegeneratePayload): Promise<InitialPoolResponse> {
  return request('/admin/players/initial-pool/regenerate-unlocked', { method: 'POST', body: JSON.stringify(payload) })
}


export function createCustomInitialPoolPlayer(payload: CustomInitialPoolPlayerCreatePayload): Promise<InitialPoolPlayer> {
  return request('/admin/players/custom', { method: 'POST', body: JSON.stringify(payload) })
}

export function updateInitialPoolPlayer(playerId: string, payload: InitialPoolPlayerUpdatePayload): Promise<InitialPoolPlayer> {
  return request(`/admin/players/${encodeURIComponent(playerId)}`, { method: 'PATCH', body: JSON.stringify(payload) })
}

export function getInitialPoolAuditEvents(params: { season?: string; playerId?: string } = {}): Promise<InitialPoolAuditResponse> {
  const query = new URLSearchParams()
  if (params.season) query.set('season', params.season)
  if (params.playerId) query.set('player_id', params.playerId)
  const suffix = query.toString() ? `?${query.toString()}` : ''
  return request(`/admin/players/audit${suffix}`)
}

export function lockInitialPoolPlayer(playerId: string): Promise<InitialPoolPlayer> {
  return request(`/admin/players/${encodeURIComponent(playerId)}/lock`, { method: 'POST' })
}

export function unlockInitialPoolPlayer(playerId: string): Promise<InitialPoolPlayer> {
  return request(`/admin/players/${encodeURIComponent(playerId)}/unlock`, { method: 'POST' })
}

export function getHealth(): Promise<HealthResponse> {
  return request('/health')
}

export function listCountries(): Promise<CountriesListResponse> {
  return request('/world/countries')
}

export function getCountriesMetadata(): Promise<CountriesMetadataResponse> {
  return request('/world/countries/metadata')
}

export function createCountry(payload: CountryUpsertPayload): Promise<CountryRecord> {
  return request('/world/countries', { method: 'POST', body: JSON.stringify(payload) })
}

export function updateCountry(code: string, payload: CountryUpsertPayload): Promise<CountryRecord> {
  return request(`/world/countries/${encodeURIComponent(code)}`, { method: 'PUT', body: JSON.stringify(payload) })
}

export function deleteCountry(code: string): Promise<void> {
  return request(`/world/countries/${encodeURIComponent(code)}`, { method: 'DELETE' })
}

export async function exportCountriesCsv(): Promise<string> {
  const response = await fetch(`${API_BASE}/world/countries/export`)
  if (!response.ok) {
    const body = await response.text()
    throw new ApiError(body || 'Request failed', response.status)
  }
  return response.text()
}

export function importCountries(payload: CountriesImportPayload): Promise<CountriesImportResponse> {
  return request('/world/countries/import', { method: 'POST', body: JSON.stringify(payload) })
}


export function listTournamentTemplates(): Promise<TournamentTemplatesListResponse> {
  return request('/world/tournament-templates')
}

export function getTournamentTemplatesMetadata(): Promise<TournamentTemplatesMetadataResponse> {
  return request('/world/tournament-templates/metadata')
}

export function getTournamentTemplate(templateId: string): Promise<TournamentTemplateRecord> {
  return request(`/world/tournament-templates/${encodeURIComponent(templateId)}`)
}

export function createTournamentTemplate(payload: TournamentTemplateUpsertPayload): Promise<TournamentTemplateRecord> {
  return request('/world/tournament-templates', { method: 'POST', body: JSON.stringify(payload) })
}

export function updateTournamentTemplate(templateId: string, payload: TournamentTemplateUpsertPayload): Promise<TournamentTemplateRecord> {
  return request(`/world/tournament-templates/${encodeURIComponent(templateId)}`, { method: 'PUT', body: JSON.stringify(payload) })
}

export function deleteTournamentTemplate(templateId: string): Promise<void> {
  return request(`/world/tournament-templates/${encodeURIComponent(templateId)}`, { method: 'DELETE' })
}

export function exportTournamentTemplates(): Promise<TournamentTemplatesDatasetResponse> {
  return request('/world/tournament-templates/export')
}

export function importTournamentTemplates(payload: TournamentTemplatesImportPayload): Promise<TournamentTemplatesImportResponse> {
  return request('/world/tournament-templates/import', { method: 'POST', body: JSON.stringify(payload) })
}

export function getTalentClassPreview(params: { year: number; seed: number }): Promise<TalentClassYearPreviewResponse> {
  const query = new URLSearchParams({ year: String(params.year), seed: String(params.seed) })
  return request(`/world/talent-class/preview?${query.toString()}`)
}

export function getTalentClassSummary(params: {
  year_start: number
  years: number
  seed: number
}): Promise<TalentClassSummaryResponse> {
  const query = new URLSearchParams({
    year_start: String(params.year_start),
    years: String(params.years),
    seed: String(params.seed)
  })
  return request(`/world/talent-class/summary?${query.toString()}`)
}

export function getTalentCalibration(params: { seed: number; sample_count: number }): Promise<TalentCalibrationResponse> {
  const query = new URLSearchParams({ seed: String(params.seed), sample_count: String(params.sample_count) })
  return request(`/world/talent-class/calibration?${query.toString()}`)
}

export function compareTalentCalibration(body: TalentCalibrationCompareRequest): Promise<TalentCalibrationCompareResponse> {
  return request('/world/talent-class/calibration/compare', { method: 'POST', body: JSON.stringify(body) })
}

export function compareTalentCalibrationMultiSeed(body: TalentCalibrationMultiSeedRequest): Promise<TalentCalibrationMultiSeedResponse> {
  return request('/world/talent-class/calibration/compare-multi-seed', { method: 'POST', body: JSON.stringify(body) })
}

export function listManualPlayerOverrides(params?: {
  season?: number
  country_code?: string
  enabled?: boolean
}): Promise<ManualPlayerOverridesListResponse> {
  const query = new URLSearchParams()
  if (typeof params?.season === 'number') query.set('season', String(params.season))
  if (params?.country_code) query.set('country_code', params.country_code)
  if (typeof params?.enabled === 'boolean') query.set('enabled', String(params.enabled))
  const suffix = query.size ? `?${query.toString()}` : ''
  return request(`/world/manual-player-overrides${suffix}`)
}

export function getManualPlayerOverride(overrideId: string): Promise<ManualPlayerOverrideRecord> {
  return request(`/world/manual-player-overrides/${encodeURIComponent(overrideId)}`)
}

export function createManualPlayerOverride(payload: ManualPlayerOverrideUpsertPayload): Promise<ManualPlayerOverrideRecord> {
  return request('/world/manual-player-overrides', { method: 'POST', body: JSON.stringify(payload) })
}

export function updateManualPlayerOverride(
  overrideId: string,
  payload: ManualPlayerOverrideUpsertPayload
): Promise<ManualPlayerOverrideRecord> {
  return request(`/world/manual-player-overrides/${encodeURIComponent(overrideId)}`, {
    method: 'PUT',
    body: JSON.stringify(payload)
  })
}

export function deleteManualPlayerOverride(overrideId: string): Promise<void> {
  return request(`/world/manual-player-overrides/${encodeURIComponent(overrideId)}`, { method: 'DELETE' })
}

export async function exportManualPlayerOverridesCsv(): Promise<string> {
  const response = await fetch(`${API_BASE}/world/manual-player-overrides/export`)
  if (!response.ok) {
    const body = await response.text()
    throw new ApiError(body || 'Request failed', response.status)
  }
  return response.text()
}

export function importManualPlayerOverrides(
  payload: ManualPlayerOverridesImportPayload
): Promise<ManualPlayerOverridesImportResponse> {
  return request('/world/manual-player-overrides/import', { method: 'POST', body: JSON.stringify(payload) })
}


export async function exportWorldPackageJson(): Promise<string> {
  const response = await fetch(`${API_BASE}/world/package/export`)
  if (!response.ok) {
    const body = await response.text()
    throw new ApiError(body || 'Request failed', response.status)
  }
  return response.text()
}

export function importWorldPackage(payload: WorldPackageImportPayload): Promise<WorldPackageImportResponse> {
  return request('/world/package/import', { method: 'POST', body: JSON.stringify(payload) })
}

export function listWorldPackages(): Promise<WorldPackageListResponse> {
  return request('/world/packages')
}

export function getWorldPackage(worldId: string): Promise<WorldPackage> {
  return request(`/world/packages/${encodeURIComponent(worldId)}`)
}

export function getWorldPackageValidation(worldId: string): Promise<WorldPackageValidation> {
  return request(`/world/packages/${encodeURIComponent(worldId)}/validation`)
}

export function getWorldPackageCountries(worldId: string): Promise<WorldPackageCountriesResponse> {
  return request(`/world/packages/${encodeURIComponent(worldId)}/countries`)
}

export function getWorldPackageGeography(worldId: string): Promise<WorldPackageGeography> {
  return request(`/world/packages/${encodeURIComponent(worldId)}/geography`)
}

export function replaceWorldPackageTimezoneAreas(worldId: string, timezoneAreas: { code: string, name: string, position: number }[], fingerprint: string): Promise<WorldPackageGeography> {
  return request(`/world/packages/${encodeURIComponent(worldId)}/geography/timezone-areas`, { method: 'PUT', body: JSON.stringify({ timezone_areas: timezoneAreas, expected_package_fingerprint: fingerprint }) })
}

export function getWorldPackageCountry(worldId: string, countryCode: string): Promise<WorldPackageCountryDetail> {
  return request(`/world/packages/${encodeURIComponent(worldId)}/countries/${encodeURIComponent(countryCode)}`)
}

export function updateWorldPackageCountry(worldId: string, countryCode: string, payload: WorldPackageCountryUpdatePayload): Promise<WorldPackageCountryUpdateResponse> {
  return request(`/world/packages/${encodeURIComponent(worldId)}/countries/${encodeURIComponent(countryCode)}`, {
    method: 'PUT', body: JSON.stringify(payload)
  })
}

export function updateWorldPackageCountryPopulation(worldId: string, countryCode: string, payload: WorldPackageCountryPopulationUpdatePayload): Promise<WorldPackageCountryUpdateResponse> {
  return request(`/world/packages/${encodeURIComponent(worldId)}/countries/${encodeURIComponent(countryCode)}/population`, {
    method: 'PUT', body: JSON.stringify(payload)
  })
}

export function createWorldPackageCountry(worldId: string, payload: WorldPackageCountryCreatePayload): Promise<WorldPackageCountryUpdateResponse> {
  return request(`/world/packages/${encodeURIComponent(worldId)}/countries`, { method: 'POST', body: JSON.stringify(payload) })
}

export function deleteWorldPackageCountry(worldId: string, countryCode: string, fingerprint: string): Promise<WorldPackageCountryDeleteResponse> {
  const query = new URLSearchParams({ expected_package_fingerprint: fingerprint })
  return request(`/world/packages/${encodeURIComponent(worldId)}/countries/${encodeURIComponent(countryCode)}?${query}`, { method: 'DELETE' })
}


export function getWorldPackageWeeklyIntakePreview(
  worldId: string,
  params: WeeklyIntakePreviewParams
): Promise<WeeklyIntakePreviewResponse> {
  const query = new URLSearchParams({
    season: params.season,
    season_week: String(params.season_week),
    target_intake_count: String(params.target_intake_count)
  })
  if (params.country_code !== undefined) query.set('country_code', params.country_code)
  if (params.region !== undefined) query.set('region', params.region)
  return request(`/world/packages/${encodeURIComponent(worldId)}/weekly-intake/preview?${query.toString()}`)
}


export function getWorldPackageWeeklyIntakeSeasonSchedulePreview(
  worldId: string,
  params: WeeklyIntakeSeasonSchedulePreviewParams
): Promise<WeeklyIntakeSeasonSchedulePreviewResponse> {
  const query = new URLSearchParams({ season: params.season })
  if (params.base_annual_intake_target !== undefined) {
    query.set('base_annual_intake_target', String(params.base_annual_intake_target))
  }
  if (params.season_growth_rate !== undefined) {
    query.set('season_growth_rate', String(params.season_growth_rate))
  }
  return request(`/world/packages/${encodeURIComponent(worldId)}/weekly-intake/season-schedule/preview?${query.toString()}`)
}

export function getWorldPackageCountryEffectivePopulation(
  worldId: string,
  countryCode: string,
  year: number
): Promise<WorldPackageCountryEffectivePopulationResponse> {
  const query = new URLSearchParams({ year: String(year) })
  return request(
    `/world/packages/${encodeURIComponent(worldId)}/countries/${encodeURIComponent(countryCode)}/effective-population?${query.toString()}`
  )
}

export function cloneWorldPackage(sourceWorldId: string, payload: WorldPackageClonePayload): Promise<WorldPackageCloneResponse> {
  return request(`/world/packages/${encodeURIComponent(sourceWorldId)}/clone`, { method: 'POST', body: JSON.stringify(payload) })
}

export function cloneOfficialWorldPackage(payload: WorldPackageClonePayload): Promise<WorldPackageCloneResponse> {
  return cloneWorldPackage('official_fax_world', payload)
}

export function createRun(payload: CreateRunPayload): Promise<RunSummary> {
  return request('/runs', { method: 'POST', body: JSON.stringify(payload) })
}

export function listRuns(): Promise<RunsIndexResponse> {
  return request('/runs')
}

/** Create an independent, initially empty Product Run with a saved initial revision. */
export function createEmptyRunContainer(displayName: string, calendar?: RunCalendarCreationInput): Promise<RunContainer> {
  return request('/run-containers', {
    method: 'POST',
    body: JSON.stringify({ display_name: displayName, ...(calendar ? {calendar} : {}) })
  })
}

export async function previewRunCalendarCreation(calendar: RunCalendarCreationInput): Promise<RunCalendarCreationPreview> {
  const result = await request<unknown>('/run-containers/calendar/creation-preview', {
    method: 'POST', body: JSON.stringify(calendar)
  })
  return validateCalendarCreationPreview(result, calendar)
}

export function listRunContainers(): Promise<RunContainerListResponse> {
  return request('/run-containers')
}

export function getRunContainer(runId: string): Promise<RunContainer> {
  return request(`/run-containers/${encodeURIComponent(runId)}`)
}

export function getViewerOfficialRunContext(productRunId: string): Promise<ViewerOfficialRunContext> {
  return request(`/viewer/runs/${encodeURIComponent(productRunId)}/official-context`)
}

export function getViewerOfficialRanking(productRunId: string): Promise<ViewerOfficialRanking> {
  return request(`/viewer/runs/${encodeURIComponent(productRunId)}/rankings/current`)
}

export function getViewerTournamentEntryField(productRunId: string, eventId: string): Promise<ViewerTournamentEntryField> {
  return request(`/viewer/runs/${encodeURIComponent(productRunId)}/tournaments/${encodeURIComponent(eventId)}/entry-field`)
}

export function getViewerTournamentDraw(productRunId: string, eventId: string): Promise<ViewerTournamentDraw> {
  return request(`/viewer/runs/${encodeURIComponent(productRunId)}/tournaments/${encodeURIComponent(eventId)}/draw`)
}

export function getViewerTournamentWildCards(productRunId: string, eventId: string): Promise<ViewerTournamentWildCards> {
  return request(`/viewer/runs/${encodeURIComponent(productRunId)}/tournaments/${encodeURIComponent(eventId)}/wild-cards`)
}

export function getViewerRunCalendar(productRunId: string): Promise<ViewerRunCalendar> {
  return request(`/viewer/runs/${encodeURIComponent(productRunId)}/calendar`)
}

export function getViewerPlayers(productRunId: string): Promise<ViewerPlayers> {
  return request(`/viewer/runs/${encodeURIComponent(productRunId)}/players`)
}

export function getViewerCountries(productRunId: string): Promise<ViewerCountries> {
  return request(`/viewer/runs/${encodeURIComponent(productRunId)}/countries`)
}

export function getViewerTournamentHistory(productRunId: string): Promise<ViewerTournamentHistory> {
  return request(`/viewer/runs/${encodeURIComponent(productRunId)}/tournaments`)
}

export function getViewerTournamentResult(productRunId: string, eventId: string): Promise<ViewerTournamentResult> {
  return request(`/viewer/runs/${encodeURIComponent(productRunId)}/tournaments/${encodeURIComponent(eventId)}/result`)
}

export function getViewerFinalsRace(productRunId: string): Promise<ViewerFinalsRaceHistory> {
  return request(`/viewer/runs/${encodeURIComponent(productRunId)}/race/finals`)
}

export function listViewerOfficialRankingHistory(productRunId: string): Promise<ViewerOfficialRankingHistory> {
  return request(`/viewer/runs/${encodeURIComponent(productRunId)}/rankings/history`)
}

export function getViewerOfficialRankingHistoryDetail(productRunId: string, weekOrdinal: number): Promise<ViewerOfficialRanking> {
  return request(`/viewer/runs/${encodeURIComponent(productRunId)}/rankings/history/${weekOrdinal}`)
}

export function listRunBranches(runId?: string): Promise<RunBranchListResponse> {
  const suffix = runId === undefined ? '' : `?${new URLSearchParams({ run_id: runId }).toString()}`
  return request(`/run-branches${suffix}`)
}

export function getRunBranch(branchId: string): Promise<RunBranch> {
  return request(`/run-branches/${encodeURIComponent(branchId)}`)
}

export function createRunBranchFromSavedRevision(
  runId: string,
  payload: CreateRunBranchFromSavedRevisionRequest
): Promise<RunBranch> {
  return request(`/run-containers/${encodeURIComponent(runId)}/branches`, {
    method: 'POST',
    body: JSON.stringify(payload)
  })
}

export function getBranchWorkingDraft(
  runId: string,
  branchId: string
): Promise<ViewerBranchWorkingDraft> {
  return request(
    `/run-containers/${encodeURIComponent(runId)}/branches/${encodeURIComponent(branchId)}/working-draft`
  )
}

export function listSavedRevisionHistory(
  runId: string,
  branchId: string,
  options?: { limit?: number; beforeSequence?: number }
): Promise<SavedRevisionHistoryPageResponse> {
  const query = new URLSearchParams()
  if (options?.limit !== undefined) query.set('limit', String(options.limit))
  if (options?.beforeSequence !== undefined) {
    query.set('before_sequence', String(options.beforeSequence))
  }
  const suffix = query.size ? `?${query.toString()}` : ''
  return request(
    `/run-containers/${encodeURIComponent(runId)}/branches/${encodeURIComponent(branchId)}/saved-revisions${suffix}`
  )
}

export function compareSavedRevisions(
  runId: string,
  branchId: string,
  fromRevisionId: string,
  toRevisionId: string
): Promise<SavedRevisionComparison> {
  const query = new URLSearchParams({
    from_revision_id: fromRevisionId,
    to_revision_id: toRevisionId
  })
  return request(
    `/run-containers/${encodeURIComponent(runId)}/branches/${encodeURIComponent(branchId)}/saved-revisions/compare?${query.toString()}`
  )
}

export function getSavedRevisionRecoveryActivity(
  runId: string,
  branchId: string
): Promise<SavedRevisionRecoveryActivityResponse> {
  return request(
    `/run-containers/${encodeURIComponent(runId)}/branches/${encodeURIComponent(branchId)}/saved-revision-recovery-activity`
  )
}

export function getSavedRevision(
  runId: string,
  branchId: string,
  revisionId: string
): Promise<SavedRevisionHistoryDetail> {
  return request(
    `/run-containers/${encodeURIComponent(runId)}/branches/${encodeURIComponent(branchId)}/saved-revisions/${encodeURIComponent(revisionId)}`
  )
}

export function getSavedRevisionRestorePreflight(
  runId: string,
  branchId: string,
  revisionId: string
): Promise<SavedRevisionRestorePreflight> {
  return request(
    `/run-containers/${encodeURIComponent(runId)}/branches/${encodeURIComponent(branchId)}/saved-revisions/${encodeURIComponent(revisionId)}/restore-preflight`
  )
}

export function restoreSavedRevision(
  runId: string,
  branchId: string,
  revisionId: string,
  payload: RestoreSavedRevisionRequest
): Promise<RestoreSavedRevisionResponse> {
  return request(
    `/run-containers/${encodeURIComponent(runId)}/branches/${encodeURIComponent(branchId)}/saved-revisions/${encodeURIComponent(revisionId)}/restore`,
    { method: 'POST', body: JSON.stringify(payload) }
  )
}

export function listBranchCheckpoints(params?: { branch_id?: string; run_id?: string }): Promise<BranchCheckpointListResponse> {
  const query = new URLSearchParams()
  if (params?.branch_id) query.set('branch_id', params.branch_id)
  if (params?.run_id) query.set('run_id', params.run_id)
  return request(`/branch-checkpoints${query.size ? `?${query}` : ''}`)
}
export function getBranchCheckpoint(checkpointId: string): Promise<BranchCheckpoint> { return request(`/branch-checkpoints/${encodeURIComponent(checkpointId)}`) }
export function getAdminBranchCheckpointSeasonState(productRunId: string, branchId: string, checkpointId: string): Promise<HistoricalBranchSeasonStateResponse> {
  return request(`/admin/runs/${encodeURIComponent(productRunId)}/branches/${encodeURIComponent(branchId)}/checkpoints/${encodeURIComponent(checkpointId)}/season-state`)
}
export function captureInitialBranchCheckpoint(payload: CaptureInitialBranchCheckpointRequest): Promise<BranchCheckpoint> { return request('/branch-checkpoints/capture-initial', { method: 'POST', body: JSON.stringify(payload) }) }
export function captureSeasonRolloverBranchCheckpoint(payload: CaptureSeasonRolloverBranchCheckpointRequest): Promise<BranchCheckpoint> { return request('/branch-checkpoints/capture-season-rollover', { method: 'POST', body: JSON.stringify(payload) }) }
export function captureBootstrapStartBranchCheckpoint(payload: CaptureBootstrapStartBranchCheckpointRequest): Promise<BranchCheckpoint> { return request('/branch-checkpoints/capture-bootstrap-start', { method: 'POST', body: JSON.stringify(payload) }) }
export function captureCurrentBranchCheckpoint(payload: CaptureCurrentBranchCheckpointRequest): Promise<BranchCheckpoint> { return request('/branch-checkpoints/capture-current', { method: 'POST', body: JSON.stringify(payload) }) }
export function captureCompletedEventBranchCheckpoint(payload: CaptureCompletedEventBranchCheckpointRequest): Promise<BranchCheckpoint> { return request('/branch-checkpoints/capture-completed-event', { method: 'POST', body: JSON.stringify(payload) }) }
export function captureCompletedWeekBranchCheckpoint(payload: CaptureCompletedWeekBranchCheckpointRequest): Promise<BranchCheckpoint> { return request('/branch-checkpoints/capture-completed-week', { method: 'POST', body: JSON.stringify(payload) }) }
export function captureAdminActionBranchCheckpoint(payload: CaptureAdminActionBranchCheckpointRequest): Promise<BranchCheckpoint> { return request('/branch-checkpoints/capture-admin-action', { method: 'POST', body: JSON.stringify(payload) }) }
export function listBranchStates(params?: { run_id?: string }): Promise<BranchStateListResponse> {
  const query = new URLSearchParams()
  if (params?.run_id) query.set('run_id', params.run_id)
  return request(`/branch-states${query.size ? `?${query}` : ''}`)
}
export function getBranchState(branchId: string): Promise<BranchState> { return request(`/branch-states/${encodeURIComponent(branchId)}`) }
export function forkRunBranch(productRunId: string, payload: AdminForkRunBranchRequest): Promise<AdminForkRunBranchResponse> {
  return request(`/admin/runs/${encodeURIComponent(productRunId)}/branches/fork`, { method: 'POST', body: JSON.stringify(payload) })
}
export function makeOfficialRunBranch(productRunId: string, targetBranchId: string, payload: AdminSetOfficialRunBranchRequest): Promise<AdminSetOfficialRunBranchResponse> {
  return request(`/admin/runs/${encodeURIComponent(productRunId)}/branches/${encodeURIComponent(targetBranchId)}/make-official`, { method: 'POST', body: JSON.stringify(payload) })
}

export function simulateNextMatchOnBranch(productRunId: string, branchId: string, payload: AdminBranchSimulateNextMatchRequest): Promise<AdminBranchSimulateNextMatchResponse> {
  return request(`/admin/runs/${encodeURIComponent(productRunId)}/branches/${encodeURIComponent(branchId)}/simulate-next-match`, { method: 'POST', body: JSON.stringify(payload) })
}

export function simulateNextRoundOnBranch(productRunId: string, branchId: string, payload: AdminBranchSimulateNextRoundRequest): Promise<AdminBranchSimulateNextRoundResponse> {
  return request(`/admin/runs/${encodeURIComponent(productRunId)}/branches/${encodeURIComponent(branchId)}/simulate-next-round`, { method: 'POST', body: JSON.stringify(payload) })
}

export function simulateNextWeekOnBranch(productRunId: string, branchId: string, payload: AdminBranchSimulateNextWeekRequest): Promise<AdminBranchSimulateNextWeekResponse> {
  return request(`/admin/runs/${encodeURIComponent(productRunId)}/branches/${encodeURIComponent(branchId)}/simulate-next-week`, { method: 'POST', body: JSON.stringify(payload) })
}

export function simulateNextTournamentOnBranch(productRunId: string, branchId: string, payload: AdminBranchSimulateNextTournamentRequest): Promise<AdminBranchSimulateNextTournamentResponse> {
  return request(`/admin/runs/${encodeURIComponent(productRunId)}/branches/${encodeURIComponent(branchId)}/simulate-next-tournament`, { method: 'POST', body: JSON.stringify(payload) })
}

export function simulateFullSeasonOnBranch(productRunId: string, branchId: string, payload: AdminBranchSimulateFullSeasonRequest): Promise<AdminBranchSimulateFullSeasonResponse> {
  return request(`/admin/runs/${encodeURIComponent(productRunId)}/branches/${encodeURIComponent(branchId)}/simulate-full-season`, { method: 'POST', body: JSON.stringify(payload) })
}

export function simulateWorldTourFinalsOnBranch(productRunId: string, branchId: string, payload: AdminBranchSimulateWorldTourFinalsRequest): Promise<AdminBranchSimulateWorldTourFinalsResponse> {
  return request(`/admin/runs/${encodeURIComponent(productRunId)}/branches/${encodeURIComponent(branchId)}/simulate-world-tour-finals`, { method: 'POST', body: JSON.stringify(payload) })
}

function authoritativeSimulationRoot(runId: string, branchId: string): string {
  return `/admin/runs/${encodeURIComponent(runId)}/branches/${encodeURIComponent(branchId)}/authoritative-simulation`
}

function verifyAuthoritativeSimulationScope(
  runId: string,
  branchId: string,
  data: { run_id: string; branch_id: string }
): void {
  if (data.run_id !== runId || data.branch_id !== branchId) {
    throw new Error('Authoritative simulation response does not match the requested Run/Branch.')
  }
}

export async function getProspectBridgeInspection(
  runId: string,
  branchId: string
): Promise<ProspectBridgeInspection> {
  const data = await request<ProspectBridgeInspection>(
    authoritativeSimulationRoot(runId, branchId) + '/prospect-bridge'
  )
  verifyAuthoritativeSimulationScope(runId, branchId, data)
  if (
    data.schema_version !== 'prospect_bridge_inspection.v1' ||
    data.bridge_supported !== false ||
    !/^[0-9a-f]{64}$/.test(data.inspection_fingerprint)
  ) {
    throw new Error('Prospect Bridge inspection response is invalid.')
  }
  return data
}

export async function getAuthoritativeSeasonTransitionPreflight(
  runId: string,
  branchId: string
): Promise<AuthoritativeSeasonTransitionPreflight> {
  const data = await request<AuthoritativeSeasonTransitionPreflight>(
    authoritativeSimulationRoot(runId, branchId) + '/season-transition/preflight'
  )
  verifyAuthoritativeSimulationScope(runId, branchId, data)
  if (data.schema_version !== 'authoritative_season_transition_preflight.v1') {
    throw new Error('Season Transition preflight has an unsupported schema.')
  }
  if (
    !/^[0-9a-f]{64}$/.test(data.position_fingerprint) ||
    !/^[0-9a-f]{64}$/.test(data.preflight_fingerprint) ||
    (
      data.default_configuration_fingerprint !== null &&
      !/^[0-9a-f]{64}$/.test(data.default_configuration_fingerprint)
    ) ||
    (
      data.default_closing_ranking_fingerprint !== null &&
      !/^[0-9a-f]{64}$/.test(data.default_closing_ranking_fingerprint)
    ) ||
    (
      data.default_sporting_fingerprint !== null &&
      !/^[0-9a-f]{64}$/.test(data.default_sporting_fingerprint)
    ) ||
    (
      data.default_lifecycle_fingerprint !== null &&
      !/^[0-9a-f]{64}$/.test(data.default_lifecycle_fingerprint)
    ) ||
    (
      data.default_health_fingerprint !== null &&
      !/^[0-9a-f]{64}$/.test(data.default_health_fingerprint)
    ) ||
    (
      data.default_ranking_fingerprint !== null &&
      !/^[0-9a-f]{64}$/.test(data.default_ranking_fingerprint)
    )
  ) {
    throw new Error('Season Transition preflight fingerprint is invalid.')
  }
  if (data.completed_week.week === 61) {
    if (data.final_season) {
      if (data.target_week !== null) {
        throw new Error('Final Season preflight must not open another season.')
      }
    } else if (
      data.target_week?.season_index !== data.completed_week.season_index + 1 ||
      data.target_week.week !== 1
    ) {
      throw new Error('Season Transition preflight has an invalid target Week 1 boundary.')
    }
  }
  return data
}

export async function previewAuthoritativeSeasonTransitionConfiguration(
  runId: string,
  branchId: string
): Promise<SeasonTransitionConfigurationPreview> {
  const data = await request<SeasonTransitionConfigurationPreview>(
    authoritativeSimulationRoot(runId, branchId) + '/season-transition/configuration/preview',
    { method: 'POST', body: JSON.stringify({}) }
  )
  verifyAuthoritativeSimulationScope(runId, branchId, data.configuration)
  if (
    data.configuration.schema_version !== 'season_transition_configuration.v1' ||
    !/^[0-9a-f]{64}$/.test(data.configuration_fingerprint)
  ) {
    throw new Error('Season Transition configuration preview is invalid.')
  }
  return data
}

export async function advanceAuthoritativeOrdinarySeason(
  runId: string,
  branchId: string,
  payload: OrdinarySeasonTransitionPayload
): Promise<OrdinarySeasonTransitionResult> {
  const data = await request<OrdinarySeasonTransitionResult>(
    authoritativeSimulationRoot(runId, branchId) + '/season-transition/advance',
    { method: 'POST', body: JSON.stringify(payload) }
  )
  verifyAuthoritativeSimulationScope(runId, branchId, data)
  if (
    data.schema_version !== 'ordinary_season_transition_result.v1' ||
    data.completed_week.week !== 61 ||
    data.target_week.week !== 1 ||
    data.target_week.season_index !== data.completed_week.season_index + 1 ||
    data.world_event_kind !== 'season_transition_completed' ||
    !/^[0-9a-f]{64}$/.test(data.configuration_fingerprint) ||
    !/^[0-9a-f]{64}$/.test(data.closing_ranking_fingerprint) ||
    !/^[0-9a-f]{64}$/.test(data.season_summary_fingerprint) ||
    !/^[0-9a-f]{64}$/.test(data.closure_marker_fingerprint) ||
    !/^[0-9a-f]{64}$/.test(data.player_sporting_fingerprint) ||
    !/^[0-9a-f]{64}$/.test(data.player_lifecycle_fingerprint) ||
    data.player_health_fingerprint === null ||
    !/^[0-9a-f]{64}$/.test(data.player_health_fingerprint) ||
    !/^[0-9a-f]{64}$/.test(data.official_ranking_fingerprint)
  ) {
    throw new Error('Ordinary Season Transition response is invalid.')
  }
  return data
}

export async function finalizeAuthoritativeFinalSeason(
  runId: string,
  branchId: string,
  payload: FinalSeasonTransitionPayload
): Promise<FinalSeasonTransitionResult> {
  const data = await request<FinalSeasonTransitionResult>(
    authoritativeSimulationRoot(runId, branchId) + '/season-transition/finalize',
    { method: 'POST', body: JSON.stringify(payload) }
  )
  verifyAuthoritativeSimulationScope(runId, branchId, data)
  if (
    data.schema_version !== 'final_season_transition_result.v1' ||
    data.run_status !== 'completed' ||
    data.completed_week.season_index !== 49 ||
    data.completed_week.week !== 61 ||
    !/^[0-9a-f]{64}$/.test(data.closing_ranking_fingerprint) ||
    !/^[0-9a-f]{64}$/.test(data.season_summary_fingerprint) ||
    !/^[0-9a-f]{64}$/.test(data.closure_marker_fingerprint)
  ) {
    throw new Error('Final Season Transition response is invalid.')
  }
  return data
}

export async function getPreAlphaFaxEntryValidationPolicyGate(
  runId: string,
  branchId: string
): Promise<import('./types').PreAlphaFaxEntryValidationPolicyGate> {
  const data = await request<import('./types').PreAlphaFaxEntryValidationPolicyGate>(
    authoritativeSimulationRoot(runId, branchId) + '/pre-alpha/fax-entry-validation-policy-gate'
  )
  verifyAuthoritativeSimulationScope(runId, branchId, data)
  return data
}

export async function getPreAlphaFaxAcceptanceProfile(
  runId: string,
  branchId: string
): Promise<import('./types').PreAlphaFaxAcceptanceProfile> {
  const data = await request<import('./types').PreAlphaFaxAcceptanceProfile>(
    authoritativeSimulationRoot(runId, branchId) + '/pre-alpha/fax-acceptance-profile'
  )
  verifyAuthoritativeSimulationScope(runId, branchId, data)
  if (
    data.schema_version !== 'pre_alpha_fax_acceptance_profile.v1' ||
    !/^[0-9a-f]{64}$/.test(data.profile_fingerprint)
  ) {
    throw new Error('Pre-alpha FAX acceptance profile response is invalid.')
  }
  return data
}

export async function getAuthoritativeSimulationPosition(
  runId: string,
  branchId: string
): Promise<AuthoritativeSimulationPosition> {
  const data = await request<AuthoritativeSimulationPosition>(
    authoritativeSimulationRoot(runId, branchId) + '/position'
  )
  verifyAuthoritativeSimulationScope(runId, branchId, data)
  return data
}

export async function completeAuthoritativeEmptyWeek(
  runId: string,
  branchId: string,
  payload: Omit<AuthoritativeSimulationCommandPayload, 'group_id'> & {
    operator_label: string
    audit_reason: string
  }
): Promise<{ position: AuthoritativeSimulationPosition }> {
  const data = await request<{ run_id: string; branch_id: string; position: AuthoritativeSimulationPosition }>(
    authoritativeSimulationRoot(runId, branchId) + '/empty-week/complete',
    { method: 'POST', body: JSON.stringify(payload) }
  )
  verifyAuthoritativeSimulationScope(runId, branchId, data)
  verifyAuthoritativeSimulationScope(runId, branchId, data.position)
  return data
}

/** Production current Entry adapter: Run-owned roster + Calendar + shared Slot. */
export async function previewRunCurrentEntryDecisions(
  runId: string, branchId: string
): Promise<import('./runCurrentEntryFreeze').CurrentEntryDecisionPreview> {
  const data = await request<import('./runCurrentEntryFreeze').CurrentEntryDecisionPreview>(
    authoritativeSimulationRoot(runId, branchId) + '/pre-alpha/fax-current-entry/preview'
  )
  if (data.schema_version !== 'pre_alpha_fax_current_entry_decision_preview.v1' ||
    data.run_id !== runId || data.branch_id !== branchId ||
    !/^[0-9a-f]{64}$/.test(data.preview_fingerprint) ||
    !/^[0-9a-f]{64}$/.test(data.slot_fingerprint)) {
    throw new Error('Current Entry preview is not scoped to the selected Run/Branch.')
  }
  return data
}

export async function applyRunCurrentEntryDecisions(
  runId: string, branchId: string,
  preview: import('./runCurrentEntryFreeze').CurrentEntryDecisionPreview,
  commandId: string
): Promise<import('./runCurrentEntryFreeze').CurrentEntryDecisionApplyResult> {
  if (preview.run_id !== runId || preview.branch_id !== branchId ||
    !/^[0-9a-f]{64}$/.test(preview.preview_fingerprint) ||
    !commandId || commandId.length > 128) {
    throw new Error('Current Entry apply requires exact scoped reviewed preview.')
  }
  const data = await request<import('./runCurrentEntryFreeze').CurrentEntryDecisionApplyResult>(
    authoritativeSimulationRoot(runId, branchId) + '/pre-alpha/fax-current-entry/apply',
    { method: 'POST', body: JSON.stringify({
      command_id: commandId,
      expected_preview_fingerprint: preview.preview_fingerprint
    }) }
  )
  if (!(data.schema_version === 'pre_alpha_fax_current_entry_decision_apply.v1' &&
    data.run_id === runId && data.branch_id === branchId &&
    data.slot_fingerprint === preview.slot_fingerprint &&
    data.decision_slot_ordinal === preview.decision_slot_ordinal &&
    data.current_week.season_index === preview.current_week.season_index &&
    data.current_week.week === preview.current_week.week &&
    data.decision_count === preview.decision_count &&
    data.event_ids.length === preview.event_ids.length &&
    data.event_ids.every((id, index) => id === preview.event_ids[index]) &&
    data.validation_required === true &&
    data.validation_policy_status === 'automatic_policy_unresolved' &&
    (data.adoption === 'committed' || data.adoption === 'exact_retry') &&
    /^[0-9a-f]{64}$/.test(data.application_fingerprint))) {
    throw new Error('Current Entry apply result differs from the reviewed frozen Slot.')
  }
  return data
}

export async function inspectAuthoritativeEntryDecisionSlot(
  runId: string,
  branchId: string,
  decisionSlotOrdinal: number
): Promise<AuthoritativeEntryDecisionSlotInspection> {
  const data = await request<AuthoritativeEntryDecisionSlotInspection>(
    authoritativeSimulationRoot(runId, branchId) +
      `/entry-decision-slot/${encodeURIComponent(String(decisionSlotOrdinal))}`
  )
  verifyAuthoritativeSimulationScope(runId, branchId, data)
  if (
    data.decision_slot_ordinal !== decisionSlotOrdinal ||
    data.authority.decision_slot_ordinal !== decisionSlotOrdinal ||
    data.authority.run_id !== runId ||
    data.authority.branch_id !== branchId ||
    !/^[0-9a-f]{64}$/.test(data.slot_fingerprint)
  ) {
    throw new Error('Authoritative Entry decision slot response is invalid.')
  }
  return data
}

export async function reviewAuthoritativeEntryDecisionSlot(
  runId: string,
  branchId: string,
  payload: AuthoritativeExplicitApplicationValidationPayload
): Promise<AuthoritativeApplicationValidationCommitResult> {
  const data = await request<AuthoritativeApplicationValidationCommitResult>(
    authoritativeSimulationRoot(runId, branchId) + '/entry-decision-slot/validation/review',
    { method: 'POST', body: JSON.stringify(payload) }
  )
  verifyAuthoritativeSimulationScope(runId, branchId, data)
  if (
    data.decision_slot_ordinal !== payload.decision_slot_ordinal ||
    data.entry_slot_fingerprint !== payload.expected_entry_slot_fingerprint ||
    data.validation_mode !== 'explicit_admin_review.v1' ||
    !/^[0-9a-f]{64}$/.test(data.validation_fingerprint) ||
    !/^[0-9a-f]{64}$/.test(data.validation_policy_fingerprint)
  ) {
    throw new Error('Explicit Entry application validation response is invalid.')
  }
  return data
}

export async function inspectWeekTournamentLock(
  runId: string,
  branchId: string
): Promise<WeekTournamentLockInspection> {
  const data = await request<WeekTournamentLockInspection>(
    authoritativeSimulationRoot(runId, branchId) + '/week-tournament-lock'
  )
  verifyAuthoritativeSimulationScope(runId, branchId, data)
  if (
    data.authority_fingerprint !== null &&
    !/^[0-9a-f]{64}$/.test(data.authority_fingerprint)
  ) {
    throw new Error('Week Tournament Lock authority fingerprint is invalid.')
  }
  return data
}

export async function previewWeekTournamentLock(
  runId: string,
  branchId: string,
  payload: WeekTournamentLockPreviewPayload
): Promise<WeekTournamentLockPreview> {
  const data = await request<WeekTournamentLockPreview>(
    authoritativeSimulationRoot(runId, branchId) + '/week-tournament-lock/preview',
    { method: 'POST', body: JSON.stringify(payload) }
  )
  verifyAuthoritativeSimulationScope(runId, branchId, data)
  if (
    data.persisted !== false ||
    !/^[0-9a-f]{64}$/.test(data.authority_fingerprint) ||
    data.authority.run_id !== runId ||
    data.authority.branch_id !== branchId
  ) {
    throw new Error('Week Tournament Lock preview response is invalid.')
  }
  return data
}

export async function commitWeekTournamentLock(
  runId: string,
  branchId: string,
  payload: WeekTournamentLockCommitPayload
): Promise<WeekTournamentLockCommitResult> {
  const data = await request<WeekTournamentLockCommitResult>(
    authoritativeSimulationRoot(runId, branchId) + '/week-tournament-lock/commit',
    { method: 'POST', body: JSON.stringify(payload) }
  )
  verifyAuthoritativeSimulationScope(runId, branchId, data)
  if (
    data.authority_fingerprint !== payload.expected_authority_fingerprint ||
    !/^[0-9a-f]{64}$/.test(data.authority_fingerprint)
  ) {
    throw new Error('Week Tournament Lock commit response is invalid.')
  }
  return data
}

export async function inspectAuthoritativeWeekSchedule(
  runId: string,
  branchId: string
): Promise<AuthoritativeWeekScheduleInspection> {
  const data = await request<AuthoritativeWeekScheduleInspection>(
    authoritativeSimulationRoot(runId, branchId) + '/week-schedule'
  )
  verifyAuthoritativeSimulationScope(runId, branchId, data)
  return data
}

export async function inspectAuthoritativeWeekSchedulePreflight(
  runId: string,
  branchId: string
): Promise<AuthoritativeWeekSchedulePreflight> {
  const data = await request<AuthoritativeWeekSchedulePreflight>(
    authoritativeSimulationRoot(runId, branchId) + '/week-schedule/preflight'
  )
  verifyAuthoritativeSimulationScope(runId, branchId, data)
  if (
    data.schema_version !== 'authoritative_week_schedule_preflight.v1' ||
    data.read_only !== true ||
    !/^[0-9a-f]{64}$/.test(data.preflight_fingerprint) ||
    !/^[0-9a-f]{64}$/.test(data.expected_position_fingerprint)
  ) {
    throw new Error('Authoritative Week Schedule preflight response is invalid.')
  }
  if (
    data.canonical_preparation !== null &&
    (!/^[0-9a-f]{64}$/.test(
      data.canonical_preparation.preparation_fingerprint
    ) ||
      data.canonical_preparation.run_id !== runId ||
      data.canonical_preparation.branch_id !== branchId)
  ) {
    throw new Error('Canonical Week Schedule preparation response is invalid.')
  }
  return data
}

export async function proposeAuthoritativeWeekSchedule(
  runId: string,
  branchId: string
): Promise<AuthoritativeWeekScheduleProposal> {
  const data = await request<AuthoritativeWeekScheduleProposal>(
    authoritativeSimulationRoot(runId, branchId) + '/week-schedule/proposal'
  )
  if (data.schedule.run_id !== runId || data.schedule.branch_id !== branchId) {
    throw new Error('Authoritative schedule proposal does not match the requested Run/Branch.')
  }
  return data
}

export async function previewAuthoritativeWeekSchedule(
  runId: string,
  branchId: string,
  payload: PreviewAuthoritativeWeekSchedulePayload
): Promise<AuthoritativeWeekScheduleManualPreview> {
  const data = await request<AuthoritativeWeekScheduleManualPreview>(
    authoritativeSimulationRoot(runId, branchId) + '/week-schedule/preview',
    { method: 'POST', body: JSON.stringify(payload) }
  )
  if (data.schedule.run_id !== runId || data.schedule.branch_id !== branchId) {
    throw new Error('Manual Match Day schedule preview scope mismatch.')
  }
  if (
    !/^[0-9a-f]{64}$/.test(data.schedule_fingerprint) ||
    !/^[0-9a-f]{64}$/.test(data.position_fingerprint)
  ) {
    throw new Error('Manual Match Day schedule preview fingerprints are invalid.')
  }
  return data
}

export async function adoptAuthoritativeWeekSchedule(
  runId: string,
  branchId: string,
  payload: AdoptAuthoritativeWeekSchedulePayload
): Promise<AuthoritativeWeekScheduleAdoptionResult> {
  const data = await request<AuthoritativeWeekScheduleAdoptionResult>(
    authoritativeSimulationRoot(runId, branchId) + '/week-schedule',
    { method: 'POST', body: JSON.stringify(payload) }
  )
  const scope = 'run_id' in data ? data : data.schedule
  verifyAuthoritativeSimulationScope(runId, branchId, scope)
  return data
}

export async function adoptAuthoritativeWeekScheduleProposal(
  runId: string,
  branchId: string,
  payload: AdoptAuthoritativeWeekScheduleProposalPayload
): Promise<AuthoritativeWeekScheduleAdoptionResult> {
  const data = await request<AuthoritativeWeekScheduleAdoptionResult>(
    authoritativeSimulationRoot(runId, branchId) + '/week-schedule/adopt-proposal',
    { method: 'POST', body: JSON.stringify(payload) }
  )
  const scope = 'run_id' in data ? data : data.schedule
  verifyAuthoritativeSimulationScope(runId, branchId, scope)
  return data
}

export async function inspectAuthoritativeMatchReconstruction(
  runId: string,
  branchId: string,
  groupId: string
): Promise<AuthoritativeMatchReconstructionState> {
  const data = await request<AuthoritativeMatchReconstructionState>(
    authoritativeSimulationRoot(runId, branchId) +
      '/match-reconstruction/state?group_id=' +
      encodeURIComponent(groupId)
  )
  verifyAuthoritativeSimulationScope(runId, branchId, data)
  return data
}

export async function previewAuthoritativeMatchReconstruction(
  runId: string,
  branchId: string,
  payload: AuthoritativeMatchReconstructionPreviewPayload
): Promise<AuthoritativeMatchReconstructionPreview> {
  const data = await request<AuthoritativeMatchReconstructionPreview>(
    authoritativeSimulationRoot(runId, branchId) + '/match-reconstruction/preview',
    { method: 'POST', body: JSON.stringify(payload) }
  )
  verifyAuthoritativeSimulationScope(runId, branchId, data)
  return data
}

export async function commitAuthoritativeMatchReconstruction(
  runId: string,
  branchId: string,
  payload: AuthoritativeMatchReconstructionCommitPayload
): Promise<AuthoritativeMatchReconstructionCommitResult> {
  const data = await request<AuthoritativeMatchReconstructionCommitResult>(
    authoritativeSimulationRoot(runId, branchId) + '/match-reconstruction/commit',
    { method: 'POST', body: JSON.stringify(payload) }
  )
  verifyAuthoritativeSimulationScope(runId, branchId, data)
  verifyAuthoritativeSimulationScope(runId, branchId, data.position)
  return data
}

export async function simulateAuthoritativeNextRally(
  runId: string,
  branchId: string,
  payload: AuthoritativeNextRallyPayload
): Promise<AuthoritativeNextRallyResult> {
  const data = await request<AuthoritativeNextRallyResult>(
    authoritativeSimulationRoot(runId, branchId) + '/simulate-next-rally',
    { method: 'POST', body: JSON.stringify(payload) }
  )
  verifyAuthoritativeSimulationScope(runId, branchId, data)
  verifyAuthoritativeSimulationScope(runId, branchId, data.position)
  if (data.schema_version !== 'authoritative_next_rally_result.v1') {
    throw new Error('Authoritative Next Rally response is invalid.')
  }
  return data
}

export async function listAuthoritativeMatchReplays(
  runId: string,
  branchId: string,
  limit = 20
): Promise<AuthoritativeMatchReplayList> {
  const data = await request<AuthoritativeMatchReplayList>(
    authoritativeSimulationRoot(runId, branchId) +
      '/match-replays?limit=' +
      encodeURIComponent(String(limit))
  )
  verifyAuthoritativeSimulationScope(runId, branchId, data)
  if (data.schema_version !== 'authoritative_match_replay_list.v1') {
    throw new Error('Authoritative replay list response is invalid.')
  }
  return data
}

export async function getAuthoritativeMatchReplayContext(
  runId: string,
  branchId: string,
  groupId: string
): Promise<AuthoritativeMatchReplayContext> {
  const data = await request<AuthoritativeMatchReplayContext>(
    authoritativeSimulationRoot(runId, branchId) +
      '/match-replay/context?group_id=' +
      encodeURIComponent(groupId)
  )
  verifyAuthoritativeSimulationScope(runId, branchId, data)
  if (
    data.schema_version !== 'authoritative_match_replay_context.v1' ||
    data.group_id !== groupId
  ) {
    throw new Error('Authoritative replay context response is invalid.')
  }
  return data
}

export async function getAuthoritativeMatchReplayCursor(
  runId: string,
  branchId: string,
  groupId: string,
  rallyIndex: number
): Promise<AuthoritativeMatchReplayCursor> {
  const data = await request<AuthoritativeMatchReplayCursor>(
    authoritativeSimulationRoot(runId, branchId) +
      '/match-replay/cursor?group_id=' +
      encodeURIComponent(groupId) +
      '&rally_index=' +
      encodeURIComponent(String(rallyIndex))
  )
  verifyAuthoritativeSimulationScope(runId, branchId, data)
  if (
    data.schema_version !== 'authoritative_match_replay_cursor.v1' ||
    data.group_id !== groupId ||
    data.rally_index !== rallyIndex
  ) {
    throw new Error('Authoritative replay cursor response is invalid.')
  }
  return data
}

export async function getAuthoritativeMatchReplayFrame(
  runId: string,
  branchId: string,
  groupId: string,
  rallyIndex: number
): Promise<AuthoritativeMatchReplayFrame> {
  const data = await request<AuthoritativeMatchReplayFrame>(
    authoritativeSimulationRoot(runId, branchId) +
      '/match-replay/frame?group_id=' +
      encodeURIComponent(groupId) +
      '&rally_index=' +
      encodeURIComponent(String(rallyIndex))
  )
  verifyAuthoritativeSimulationScope(runId, branchId, data)
  if (
    data.schema_version !== 'authoritative_match_replay_frame.v1' ||
    data.group_id !== groupId ||
    data.rally_index !== rallyIndex
  ) {
    throw new Error('Authoritative replay frame response is invalid.')
  }
  return data
}

export async function getAuthoritativeMatchTimelineCursor(
  runId: string,
  branchId: string,
  groupId: string,
  timelineIndex: number
): Promise<AuthoritativeMatchTimelineCursor> {
  const data = await request<AuthoritativeMatchTimelineCursor>(
    authoritativeSimulationRoot(runId, branchId) +
      '/match-replay/timeline-cursor?group_id=' +
      encodeURIComponent(groupId) +
      '&timeline_index=' +
      encodeURIComponent(String(timelineIndex))
  )
  verifyAuthoritativeSimulationScope(runId, branchId, data)
  if (
    data.schema_version !== 'authoritative_match_timeline_cursor.v1' ||
    data.group_id !== groupId ||
    data.timeline_index !== timelineIndex
  ) {
    throw new Error('Authoritative timeline replay cursor response is invalid.')
  }
  return data
}

export async function getAuthoritativeMatchStaminaCursor(
  runId: string,
  branchId: string,
  groupId: string,
  timelineIndex: number
): Promise<AuthoritativeMatchStaminaCursor> {
  const data = await request<AuthoritativeMatchStaminaCursor>(
    authoritativeSimulationRoot(runId, branchId) +
      '/match-replay/stamina-cursor?group_id=' +
      encodeURIComponent(groupId) +
      '&timeline_index=' +
      encodeURIComponent(String(timelineIndex))
  )
  verifyAuthoritativeSimulationScope(runId, branchId, data)
  if (
    data.schema_version !== 'authoritative_match_stamina_cursor.v1' ||
    data.group_id !== groupId ||
    data.timeline_index !== timelineIndex
  ) {
    throw new Error('Authoritative stamina replay cursor response is invalid.')
  }
  return data
}

export async function inspectAuthoritativeLiveMatch(
  runId: string,
  branchId: string,
  groupId: string
): Promise<AuthoritativeLiveMatchInspection> {
  const data = await request<AuthoritativeLiveMatchInspection>(
    authoritativeSimulationRoot(runId, branchId) +
      '/live-match?group_id=' +
      encodeURIComponent(groupId)
  )
  verifyAuthoritativeSimulationScope(runId, branchId, data)
  if (
    data.schema_version !== 'authoritative_live_match_inspection.v1' ||
    data.group_id !== groupId
  ) {
    throw new Error('Authoritative live match inspection response is invalid.')
  }
  return data
}

export async function confirmAuthoritativeLiveMatch(
  runId: string,
  branchId: string,
  payload: AuthoritativeLiveConfirmPayload
): Promise<AuthoritativeLiveConfirmResult> {
  const data = await request<AuthoritativeLiveConfirmResult>(
    authoritativeSimulationRoot(runId, branchId) + '/live-match/confirm',
    { method: 'POST', body: JSON.stringify(payload) }
  )
  verifyAuthoritativeSimulationScope(runId, branchId, data)
  verifyAuthoritativeSimulationScope(runId, branchId, data.position)
  if (data.schema_version !== 'authoritative_live_confirm_result.v1') {
    throw new Error('Authoritative live confirmation response is invalid.')
  }
  return data
}

export async function inspectAuthoritativeLiveMatchTimeline(
  runId: string,
  branchId: string,
  groupId: string
): Promise<AuthoritativeLiveMatchTimeline> {
  const data = await request<AuthoritativeLiveMatchTimeline>(
    authoritativeSimulationRoot(runId, branchId) +
      '/live-match/timeline?group_id=' +
      encodeURIComponent(groupId)
  )
  verifyAuthoritativeSimulationScope(runId, branchId, data)
  return data
}

export async function restoreAuthoritativeLiveReturnPoint(
  runId: string,
  branchId: string,
  payload: AuthoritativeLiveReturnPayload
): Promise<AuthoritativeLiveReturnResult> {
  const data = await request<AuthoritativeLiveReturnResult>(
    authoritativeSimulationRoot(runId, branchId) + '/live-match/restore',
    { method: 'POST', body: JSON.stringify(payload) }
  )
  verifyAuthoritativeSimulationScope(runId, branchId, data)
  verifyAuthoritativeSimulationScope(runId, branchId, data.position)
  return data
}

export async function simulateAuthoritativeGame(
  runId: string,
  branchId: string,
  payload: AuthoritativeLiveRangePayload
): Promise<AuthoritativeLiveRangeResult> {
  const data = await request<AuthoritativeLiveRangeResult>(
    authoritativeSimulationRoot(runId, branchId) + '/simulate-game',
    { method: 'POST', body: JSON.stringify(payload) }
  )
  verifyAuthoritativeSimulationScope(runId, branchId, data)
  verifyAuthoritativeSimulationScope(runId, branchId, data.position)
  if (data.schema_version !== 'authoritative_simulate_game_result.v1') {
    throw new Error('Authoritative Simulate Game response is invalid.')
  }
  return data
}

export async function simulateAuthoritativeRestOfMatch(
  runId: string,
  branchId: string,
  payload: AuthoritativeLiveRangePayload
): Promise<AuthoritativeLiveRangeResult> {
  const data = await request<AuthoritativeLiveRangeResult>(
    authoritativeSimulationRoot(runId, branchId) + '/simulate-rest-of-match',
    { method: 'POST', body: JSON.stringify(payload) }
  )
  verifyAuthoritativeSimulationScope(runId, branchId, data)
  verifyAuthoritativeSimulationScope(runId, branchId, data.position)
  if (data.schema_version !== 'authoritative_simulate_rest_of_match_result.v1') {
    throw new Error('Authoritative Rest of Match response is invalid.')
  }
  return data
}

export async function simulateAuthoritativeNextMatch(
  runId: string,
  branchId: string,
  payload: AuthoritativeSimulationCommandPayload
): Promise<AuthoritativeSimulationPosition> {
  const data = await request<AuthoritativeSimulationPosition>(
    authoritativeSimulationRoot(runId, branchId) + '/simulate-next-match',
    { method: 'POST', body: JSON.stringify(payload) }
  )
  verifyAuthoritativeSimulationScope(runId, branchId, data)
  return data
}

export async function simulateAuthoritativeNextSlot(
  runId: string,
  branchId: string,
  payload: AuthoritativeSimulationCommandPayload
): Promise<AuthoritativeSimulationPosition> {
  const data = await request<AuthoritativeSimulationPosition>(
    authoritativeSimulationRoot(runId, branchId) + '/simulate-next-slot',
    { method: 'POST', body: JSON.stringify(payload) }
  )
  verifyAuthoritativeSimulationScope(runId, branchId, data)
  return data
}

export async function previewAuthoritativeNextMatchDay(
  runId: string,
  branchId: string
): Promise<AuthoritativeMatchDayPreview> {
  const data = await request<AuthoritativeMatchDayPreview>(
    authoritativeSimulationRoot(runId, branchId) + '/next-match-day/preview'
  )
  verifyAuthoritativeSimulationScope(runId, branchId, data)
  if (
    data.schema_version !== 'authoritative_match_day_preview.v1' ||
    data.match_day_ordinal < 1 ||
    data.target_slot_ordinals.length === 0 ||
    data.target_slot_ordinals.length !== data.target_group_ids.length ||
    !/^[0-9a-f]{64}$/.test(data.schedule_fingerprint) ||
    !/^[0-9a-f]{64}$/.test(data.expected_position_fingerprint) ||
    !/^[0-9a-f]{64}$/.test(data.preview_fingerprint)
  ) {
    throw new Error('Authoritative Match Day preview response is invalid.')
  }
  return data
}

export async function simulateAuthoritativeNextMatchDay(
  runId: string,
  branchId: string,
  payload: AuthoritativeMatchDayCommandPayload
): Promise<AuthoritativeMatchDayResult> {
  const data = await request<AuthoritativeMatchDayResult>(
    authoritativeSimulationRoot(runId, branchId) + '/simulate-next-match-day',
    { method: 'POST', body: JSON.stringify(payload) }
  )
  verifyAuthoritativeSimulationScope(runId, branchId, data)
  verifyAuthoritativeSimulationScope(runId, branchId, data.position)
  if (
    data.schema_version !== 'authoritative_match_day_result.v1' ||
    data.completed_slot_count !== data.target_slot_ordinals.length ||
    data.child_command_ids.length !== data.target_slot_ordinals.length ||
    !/^[0-9a-f]{64}$/.test(data.schedule_fingerprint)
  ) {
    throw new Error('Authoritative Match Day result is invalid.')
  }
  return data
}

export async function previewAuthoritativeNextRound(
  runId: string,
  branchId: string
): Promise<AuthoritativeRoundPreview> {
  const data = await request<AuthoritativeRoundPreview>(
    authoritativeSimulationRoot(runId, branchId) + '/next-round/preview'
  )
  verifyAuthoritativeSimulationScope(runId, branchId, data)
  if (
    data.schema_version !== 'authoritative_round_preview.v1' ||
    !data.round_identity.event_id ||
    data.round_identity.round_number < 1 ||
    data.target_slot_ordinals.length === 0 ||
    data.target_slot_ordinals.length !== data.target_group_ids.length ||
    data.horizon_slot_ordinals.length === 0 ||
    data.horizon_slot_ordinals[0] !== data.target_slot_ordinals[0] ||
    data.horizon_slot_ordinals[
      data.horizon_slot_ordinals.length - 1
    ] !== data.target_slot_ordinals[data.target_slot_ordinals.length - 1] ||
    !/^[0-9a-f]{64}$/.test(data.schedule_fingerprint) ||
    !/^[0-9a-f]{64}$/.test(data.expected_position_fingerprint) ||
    !/^[0-9a-f]{64}$/.test(data.preview_fingerprint)
  ) {
    throw new Error('Authoritative Round preview response is invalid.')
  }
  return data
}

export async function simulateAuthoritativeNextRound(
  runId: string,
  branchId: string,
  payload: AuthoritativeRoundCommandPayload
): Promise<AuthoritativeRoundResult> {
  const data = await request<AuthoritativeRoundResult>(
    authoritativeSimulationRoot(runId, branchId) + '/simulate-next-round',
    { method: 'POST', body: JSON.stringify(payload) }
  )
  verifyAuthoritativeSimulationScope(runId, branchId, data)
  verifyAuthoritativeSimulationScope(runId, branchId, data.position)
  if (
    data.schema_version !== 'authoritative_round_result.v1' ||
    data.completed_slot_count !== data.horizon_slot_ordinals.length ||
    data.child_command_ids.length !== data.horizon_slot_ordinals.length ||
    data.target_slot_ordinals.length !== data.target_group_ids.length ||
    !/^[0-9a-f]{64}$/.test(data.schedule_fingerprint)
  ) {
    throw new Error('Authoritative Round result is invalid.')
  }
  return data
}

export async function previewAuthoritativeNextTournament(
  runId: string,
  branchId: string
): Promise<AuthoritativeTournamentPreview> {
  const data = await request<AuthoritativeTournamentPreview>(
    authoritativeSimulationRoot(runId, branchId) + '/next-tournament/preview'
  )
  verifyAuthoritativeSimulationScope(runId, branchId, data)
  if (
    data.schema_version !== 'authoritative_tournament_preview.v1' ||
    !data.event_id ||
    data.target_slot_ordinals.length === 0 ||
    data.target_slot_ordinals.length !== data.target_group_ids.length ||
    data.horizon_slot_ordinals.length === 0 ||
    data.horizon_slot_ordinals[0] !== data.target_slot_ordinals[0] ||
    data.horizon_slot_ordinals[
      data.horizon_slot_ordinals.length - 1
    ] !== data.target_slot_ordinals[data.target_slot_ordinals.length - 1] ||
    !/^[0-9a-f]{64}$/.test(data.schedule_fingerprint) ||
    !/^[0-9a-f]{64}$/.test(data.expected_position_fingerprint) ||
    !/^[0-9a-f]{64}$/.test(data.preview_fingerprint)
  ) {
    throw new Error('Authoritative Tournament preview response is invalid.')
  }
  return data
}

export async function simulateAuthoritativeNextTournament(
  runId: string,
  branchId: string,
  payload: AuthoritativeTournamentCommandPayload
): Promise<AuthoritativeTournamentResult> {
  const data = await request<AuthoritativeTournamentResult>(
    authoritativeSimulationRoot(runId, branchId) + '/simulate-next-tournament',
    { method: 'POST', body: JSON.stringify(payload) }
  )
  verifyAuthoritativeSimulationScope(runId, branchId, data)
  verifyAuthoritativeSimulationScope(runId, branchId, data.position)
  if (
    data.schema_version !== 'authoritative_tournament_result.v1' ||
    !data.event_id ||
    data.completed_slot_count !== data.horizon_slot_ordinals.length ||
    data.child_command_ids.length !== data.horizon_slot_ordinals.length ||
    data.target_slot_ordinals.length !== data.target_group_ids.length ||
    !/^[0-9a-f]{64}$/.test(data.schedule_fingerprint) ||
    !/^[0-9a-f]{64}$/.test(data.owned_tournament_source_fingerprint)
  ) {
    throw new Error('Authoritative Tournament result is invalid.')
  }
  return data
}

export async function previewAuthoritativeNextWeek(
  runId: string,
  branchId: string,
  payload: AuthoritativeWeekPreviewPayload
): Promise<AuthoritativeWeekPreview> {
  const data = await request<AuthoritativeWeekPreview>(
    authoritativeSimulationRoot(runId, branchId) + '/next-week/preview',
    { method: 'POST', body: JSON.stringify(payload) }
  )
  verifyAuthoritativeSimulationScope(runId, branchId, data)
  if (
    data.schema_version !== 'authoritative_week_preview.v1' ||
    data.target_week.season_index !== data.week.season_index ||
    data.target_week.week !== data.week.week + 1 ||
    data.target_slot_ordinals.length !== data.target_group_ids.length ||
    (data.schedule_fingerprint != null &&
      !/^[0-9a-f]{64}$/.test(data.schedule_fingerprint)) ||
    !/^[0-9a-f]{64}$/.test(data.ranking_authority_fingerprint) ||
    !/^[0-9a-f]{64}$/.test(data.expected_position_fingerprint) ||
    !/^[0-9a-f]{64}$/.test(data.preview_fingerprint)
  ) {
    throw new Error('Authoritative Week preview response is invalid.')
  }
  return data
}

export async function simulateAuthoritativeNextWeek(
  runId: string,
  branchId: string,
  payload: AuthoritativeWeekCommandPayload
): Promise<AuthoritativeWeekExecution> {
  const data = await request<AuthoritativeWeekExecution>(
    authoritativeSimulationRoot(runId, branchId) + '/simulate-next-week',
    { method: 'POST', body: JSON.stringify(payload) }
  )
  verifyAuthoritativeSimulationScope(runId, branchId, data)
  if (data.schema_version === 'authoritative_week_progress.v1') {
    verifyAuthoritativeSimulationScope(runId, branchId, data.position)
    if (
      data.status !== 'blocked' ||
      data.transition_blockers.length === 0 ||
      data.completed_slot_count !== data.target_slot_ordinals.length
    ) {
      throw new Error('Authoritative Week progress response is invalid.')
    }
    return data
  }
  if (
    data.schema_version !== 'authoritative_week_result.v1' ||
    data.status !== 'complete' ||
    data.completed_slot_count !== data.target_slot_ordinals.length ||
    data.child_command_ids.length !== data.target_slot_ordinals.length ||
    data.target_slot_ordinals.length !== data.target_group_ids.length ||
    !/^[0-9a-f]{64}$/.test(data.ranking_authority_fingerprint) ||
    !/^[0-9a-f]{64}$/.test(data.week_transition_request_fingerprint) ||
    !/^[0-9a-f]{64}$/.test(data.official_ranking_fingerprint) ||
    !/^[0-9a-f]{64}$/.test(data.player_lifecycle_fingerprint) ||
    !/^[0-9a-f]{64}$/.test(data.player_sporting_fingerprint) ||
    data.player_health_fingerprint === null ||
    !/^[0-9a-f]{64}$/.test(data.player_health_fingerprint)
  ) {
    throw new Error('Authoritative Week result is invalid.')
  }
  return data
}

export async function previewAuthoritativeNextSeason(
  runId: string,
  branchId: string,
  payload: AuthoritativeSeasonPreviewPayload
): Promise<AuthoritativeSeasonPreview> {
  const data = await request<AuthoritativeSeasonPreview>(
    authoritativeSimulationRoot(runId, branchId) + '/next-season/preview',
    { method: 'POST', body: JSON.stringify(payload) }
  )
  verifyAuthoritativeSimulationScope(runId, branchId, data)
  if (
    data.schema_version !== 'authoritative_season_preview.v1' ||
    data.target_week.season_index !== data.start_week.season_index + 1 ||
    data.target_week.week !== 1 ||
    data.weeks_including_current !== 62 - data.start_week.week ||
    data.auto_empty_week_policy !== 'calendar_proven_audited_child_only' ||
    data.season_transition_mode !== 'explicit_save_and_review_checkpoint' ||
    !/^[0-9a-f]{64}$/.test(data.expected_position_fingerprint) ||
    !/^[0-9a-f]{64}$/.test(data.preview_fingerprint)
  ) {
    throw new Error('Authoritative Season preview response is invalid.')
  }
  return data
}

export async function simulateAuthoritativeNextSeason(
  runId: string,
  branchId: string,
  payload: AuthoritativeSeasonCommandPayload
): Promise<AuthoritativeSeasonExecution> {
  const data = await request<AuthoritativeSeasonExecution>(
    authoritativeSimulationRoot(runId, branchId) + '/simulate-next-season',
    { method: 'POST', body: JSON.stringify(payload) }
  )
  verifyAuthoritativeSimulationScope(runId, branchId, data)
  verifyAuthoritativeSimulationScope(runId, branchId, data.position)
  if (data.schema_version === 'authoritative_season_progress.v1') {
    if (
      data.status !== 'blocked' ||
      !data.checkpoint ||
      data.completed_week_count !== data.completed_weeks.length
    ) {
      throw new Error('Authoritative Season progress response is invalid.')
    }
    return data
  }
  if (
    data.schema_version !== 'authoritative_season_result.v1' ||
    data.status !== 'complete' ||
    data.completed_week_count !== data.completed_weeks.length ||
    data.season_transition_observed !== true ||
    data.target_week.season_index !== data.start_week.season_index + 1 ||
    data.target_week.week !== 1
  ) {
    throw new Error('Authoritative Season result is invalid.')
  }
  return data
}

export async function getAuthoritativeFullSimulationParentDetail(
  runId: string,
  branchId: string,
  commandId: string
): Promise<AuthoritativeFullSimulationParentDetail> {
  const data = await request<AuthoritativeFullSimulationParentDetail>(
    authoritativeSimulationRoot(runId, branchId) +
      '/full-simulation/parents/' +
      encodeURIComponent(commandId)
  )
  verifyAuthoritativeSimulationScope(runId, branchId, data)
  if (
    data.schema_version !== 'authoritative_full_simulation_parent_detail.v1' ||
    data.command_id !== commandId ||
    !/^[0-9a-f]{64}$/.test(data.receipt_request_fingerprint)
  ) {
    throw new Error('Full Simulation parent detail response is invalid.')
  }
  return data
}

export async function getAuthoritativeFullSimulationHistory(
  runId: string,
  branchId: string
): Promise<AuthoritativeFullSimulationHistory> {
  const data = await request<AuthoritativeFullSimulationHistory>(
    authoritativeSimulationRoot(runId, branchId) + '/full-simulation/history'
  )
  verifyAuthoritativeSimulationScope(runId, branchId, data)
  if (
    data.schema_version !== 'authoritative_full_simulation_history.v1' ||
    data.item_count !== data.items.length
  ) {
    throw new Error('Full Simulation history response is invalid.')
  }
  for (const item of data.items) {
    if (
      item.completed_season_count !== item.completed_seasons.length ||
      item.final_completed_week_count !== item.final_completed_weeks.length
    ) {
      throw new Error('Full Simulation history item is invalid.')
    }
  }
  return data
}

function isBoundedFullSimulationWeek(value: unknown): boolean {
  if (!value || typeof value !== 'object' || Array.isArray(value)) return false
  const week = value as Record<string, unknown>
  return Object.keys(week).length === 2 &&
    Number.isInteger(week.season_index) && (week.season_index as number) >= 0 &&
    (week.season_index as number) <= 49 &&
    Number.isInteger(week.week) && (week.week as number) >= 1 &&
    (week.week as number) <= 61
}

export async function getGlobalFullSimulationOperations(): Promise<GlobalFullSimulationOperations> {
  const data = await request<GlobalFullSimulationOperations>(
    '/run-containers/full-simulation/operations'
  )
  if (
    !data || data.schema_version !== 'global_full_simulation_operations.v1' ||
    data.visibility !== 'durable_receipts_only' ||
    !Array.isArray(data.operations) ||
    !Number.isSafeInteger(data.pending_count) ||
    data.pending_count !== data.operations.length ||
    !Number.isSafeInteger(data.legacy_pending_count) ||
    data.legacy_pending_count < 0
  ) {
    throw new Error('Global Full Simulation receipt inventory is invalid.')
  }
  const seen = new Set<string>()
  const seenParentScopes = new Set<string>()
  for (const operation of data.operations) {
    const key = JSON.stringify([operation.run_id, operation.branch_id, operation.command_id])
    const scope = JSON.stringify([operation.run_id, operation.branch_id])
    const validStart = isBoundedFullSimulationWeek(operation.start_week)
    const validFinal = isBoundedFullSimulationWeek(operation.final_week) &&
      operation.final_week.season_index === 49 && operation.final_week.week === 61
    const target = operation.effective_target_week ?? operation.final_week
    const validTarget = isBoundedFullSimulationWeek(target) &&
      (!validStart || target.season_index * 61 + target.week >=
        operation.start_week.season_index * 61 + operation.start_week.week) &&
      (operation.target_revision === undefined ||
        (Number.isSafeInteger(operation.target_revision) && operation.target_revision >= 0))
    const validLease = [
      'absent', 'matching_active', 'matching_expired', 'other_active', 'other_expired'
    ].includes(operation.lease_state) &&
      (operation.lease_state === 'absent'
        ? operation.lease_expires_at_unix === null
        : Number.isSafeInteger(operation.lease_expires_at_unix) &&
          (operation.lease_expires_at_unix as number) >= 0)
    const maxSeasons = validStart ? 49 - operation.start_week.season_index : 0
    const firstFinalWeek = validStart && operation.start_week.season_index === 49
      ? operation.start_week.week : 1
    if (
      (operation.effective_boundary_target != null && !isBoundaryTarget(operation.effective_boundary_target)) ||
      !operation || typeof operation.run_id !== 'string' || !operation.run_id ||
      typeof operation.branch_id !== 'string' || !operation.branch_id ||
      typeof operation.command_id !== 'string' || !operation.command_id ||
      typeof operation.run_name !== 'string' || !operation.run_name ||
      typeof operation.branch_name !== 'string' || !operation.branch_name ||
      typeof operation.run_status !== 'string' ||
      typeof operation.branch_status !== 'string' ||
      typeof operation.run_read_only !== 'boolean' ||
      typeof operation.branch_read_only !== 'boolean' ||
      seen.has(key) || seenParentScopes.has(scope) ||
      (operation.effective_boundary_target != null && !isBoundaryTarget(operation.effective_boundary_target)) ||
      !['running', 'pause_requested', 'paused'].includes(operation.control_state) ||
      operation.worker_activity !== 'unknown' ||
      !Number.isSafeInteger(operation.completed_season_count) ||
      operation.completed_season_count < 0 ||
      operation.completed_season_count > maxSeasons ||
      !Number.isSafeInteger(operation.final_completed_week_count) ||
      operation.final_completed_week_count < 0 ||
      operation.final_completed_week_count > 62 - firstFinalWeek ||
      !validStart || !validFinal || !validTarget || !validLease ||
      typeof operation.review_fingerprint !== 'string' ||
      !/^[a-f0-9]{64}$/.test(operation.review_fingerprint)
    ) {
      throw new Error('Global Full Simulation parent evidence is invalid.')
    }
    seen.add(key)
    seenParentScopes.add(scope)
  }
  return data
}

export async function getPendingAuthoritativeFullSimulations(
  runId: string,
  branchId: string
): Promise<AuthoritativeFullSimulationPendingCollection> {
  const data = await request<AuthoritativeFullSimulationPendingCollection>(
    authoritativeSimulationRoot(runId, branchId) + '/full-simulation/pending'
  )
  verifyAuthoritativeSimulationScope(runId, branchId, data)
  if (
    data.schema_version !== 'authoritative_full_simulation_pending_collection.v1' ||
    data.legacy_pending_count < 0
  ) {
    throw new Error('Pending Full Simulation response is invalid.')
  }
  for (const operation of data.operations) {
    if (
      !['running', 'pause_requested', 'paused'].includes(operation.control_state) ||
      operation.command.expected_preview_fingerprint !==
        operation.review.preview_fingerprint ||
      operation.command.expected_position_fingerprint !==
        operation.review.expected_position_fingerprint ||
      operation.command.expected_revision_id !==
        operation.review.expected_revision_id ||
      operation.completed_season_count !== operation.completed_seasons.length ||
      operation.final_completed_week_count !==
        operation.final_completed_weeks.length ||
      (operation.effective_target_week !== undefined && !isBoundedFullSimulationWeek(operation.effective_target_week)) ||
      (operation.target_revision !== undefined &&
        (!Number.isSafeInteger(operation.target_revision) || operation.target_revision < 0))
    ) {
      throw new Error('Pending Full Simulation operation is invalid.')
    }
  }
  return data
}

export async function retargetAuthoritativeFullSimulation(
  runId: string,
  branchId: string,
  payload: AuthoritativeFullSimulationRetargetPayload
): Promise<AuthoritativeFullSimulationRetargetResult> {
  const data = await request<AuthoritativeFullSimulationRetargetResult>(
    authoritativeSimulationRoot(runId, branchId) + '/full-simulation/target',
    { method: 'POST', body: JSON.stringify(payload) }
  )
  verifyAuthoritativeSimulationScope(runId, branchId, data)
  const week = (w: {season_index:number; week:number}) =>
    w.season_index * 61 + w.week
  const relative = payload.relative_target
  const validRelative = relative !== undefined &&
    (relative.unit === 'weeks' || relative.unit === 'seasons') &&
    Number.isSafeInteger(relative.count) &&
    relative.count >= 1 &&
    relative.count <= (relative.unit === 'seasons' ? 49 : 3050)
  const validRequest = relative === undefined
    ? payload.target_week !== undefined &&
      data.requested_relative_target == null &&
      week(data.requested_target_week) === week(payload.target_week)
    : validRelative &&
      data.requested_relative_target?.unit === relative.unit &&
      data.requested_relative_target?.count === relative.count &&
      data.resolved_from_week != null &&
      isBoundedFullSimulationWeek(data.resolved_from_week) &&
      week(data.requested_target_week) === week(data.resolved_from_week) +
        relative.count * (relative.unit === 'seasons' ? 61 : 1)
  if (
    data.schema_version !== 'authoritative_full_simulation_target_result.v1' ||
    data.control_command_id !== payload.control_command_id ||
    data.target_command_id !== payload.target_command_id ||
    !isBoundedFullSimulationWeek(data.effective_target_week) ||
    !isBoundedFullSimulationWeek(data.original_final_week) ||
    !isBoundedFullSimulationWeek(data.requested_target_week) ||
    !validRequest ||
    data.original_final_week.season_index !== 49 ||
    data.original_final_week.week !== 61 ||
    !Number.isSafeInteger(data.applied_revision) || data.applied_revision < 1 ||
    !Number.isSafeInteger(data.target_revision) ||
    data.target_revision < data.applied_revision ||
    typeof data.replayed !== 'boolean' ||
    data.committed_child_work_persists !== true
  ) {
    throw new Error('Full Simulation target revision response is invalid.')
  }
  return data
}

export async function controlAuthoritativeFullSimulation(
  runId: string,
  branchId: string,
  payload: AuthoritativeFullSimulationControlPayload
): Promise<AuthoritativeFullSimulationControlResult> {
  const data = await request<AuthoritativeFullSimulationControlResult>(
    authoritativeSimulationRoot(runId, branchId) + '/full-simulation/control',
    { method: 'POST', body: JSON.stringify(payload) }
  )
  verifyAuthoritativeSimulationScope(runId, branchId, data)
  if (
    data.schema_version !== 'authoritative_full_simulation_control_result.v1' ||
    data.target_command_id !== payload.target_command_id ||
    data.control_command_id !== payload.control_command_id ||
    data.action !== payload.action ||
    typeof data.replayed !== 'boolean' ||
    !['running', 'pause_requested', 'paused', 'stopped'].includes(data.observed_control_state) ||
    data.committed_child_work_persists !== true ||
    !['running', 'pause_requested', 'paused', 'stopped'].includes(data.control_state) ||
    (payload.action === 'pause' && data.control_state !== 'pause_requested') ||
    (payload.action === 'resume' && data.control_state !== 'running') ||
    (payload.action === 'stop' && data.control_state !== 'stopped')
  ) {
    throw new Error('Full Simulation control response is invalid.')
  }
  return data
}

export async function abandonAuthoritativeFullSimulation(
  runId: string,
  branchId: string,
  payload: AuthoritativeFullSimulationAbandonPayload
): Promise<AuthoritativeFullSimulationAbandonResult> {
  const data = await request<AuthoritativeFullSimulationAbandonResult>(
    authoritativeSimulationRoot(runId, branchId) + '/full-simulation/abandon',
    { method: 'POST', body: JSON.stringify(payload) }
  )
  verifyAuthoritativeSimulationScope(runId, branchId, data)
  if (
    data.schema_version !== 'authoritative_full_simulation_abandon_result.v1' ||
    data.status !== 'abandoned' ||
    data.committed_child_work_persists !== true ||
    data.completed_season_count !== data.completed_seasons.length ||
    data.final_completed_week_count !== data.final_completed_weeks.length ||
    data.target_command_id !== payload.target_command_id
  ) {
    throw new Error('Full Simulation abandon response is invalid.')
  }
  return data
}

export async function previewAuthoritativeFullSimulation(
  runId: string,
  branchId: string,
  payload: AuthoritativeFullSimulationPreviewPayload
): Promise<AuthoritativeFullSimulationPreview> {
  const data = await request<AuthoritativeFullSimulationPreview>(
    authoritativeSimulationRoot(runId, branchId) + '/full-simulation/preview',
    { method: 'POST', body: JSON.stringify(payload) }
  )
  verifyAuthoritativeSimulationScope(runId, branchId, data)
  if (
    data.schema_version !== 'authoritative_full_simulation_preview.v1' ||
    data.final_week.season_index !== 49 ||
    data.final_week.week !== 61 ||
    data.remaining_weeks_including_current < 1 ||
    data.remaining_seasons_including_current < 1 ||
    data.season_child_mode !== 'canonical_next_season' ||
    data.final_season_mode !== 'canonical_final_run_closure' ||
    data.explicit_boundary_policy !==
      'save_and_review_required_at_every_season_boundary' ||
    !/^[0-9a-f]{64}$/.test(data.expected_position_fingerprint) ||
    !/^[0-9a-f]{64}$/.test(data.preview_fingerprint)
  ) {
    throw new Error('Authoritative Full Simulation preview response is invalid.')
  }
  return data
}

export async function simulateAuthoritativeFullSimulation(
  runId: string,
  branchId: string,
  payload: AuthoritativeFullSimulationCommandPayload
): Promise<AuthoritativeFullSimulationExecution> {
  const data = await request<AuthoritativeFullSimulationExecution>(
    authoritativeSimulationRoot(runId, branchId) + '/simulate-full-simulation',
    { method: 'POST', body: JSON.stringify(payload) }
  )
  verifyAuthoritativeSimulationScope(runId, branchId, data)
  if (data.schema_version === 'authoritative_full_simulation_progress.v1') {
    if (
      !['blocked', 'stopped', 'target_reached'].includes(data.status) ||
      (data.status === 'stopped' && data.checkpoint !== 'operator_stopped') ||
      (data.status === 'target_reached' && data.checkpoint !== 'operator_target_reached') ||
      (data.status === 'blocked' && ['operator_stopped','operator_target_reached'].includes(data.checkpoint)) ||
      (data.effective_target_week !== undefined && !isBoundedFullSimulationWeek(data.effective_target_week)) ||
      (data.target_revision !== undefined && (!Number.isSafeInteger(data.target_revision) || data.target_revision < 0)) ||
      data.completed_season_count !== data.completed_seasons.length ||
      data.final_completed_week_count !== data.final_completed_weeks.length
    ) {
      throw new Error('Authoritative Full Simulation progress response is invalid.')
    }
    if (data.position) {
      verifyAuthoritativeSimulationScope(runId, branchId, data.position)
    }
    return data
  }
  if (
    data.schema_version !== 'authoritative_full_simulation_result.v1' ||
    data.status !== 'complete' ||
    data.run_status !== 'completed' ||
    data.final_week.season_index !== 49 ||
    data.final_week.week !== 61 ||
    data.completed_season_count !== data.completed_seasons.length ||
    !/^[0-9a-f]{64}$/.test(data.closure_marker_fingerprint) ||
    !/^[0-9a-f]{64}$/.test(data.season_summary_fingerprint)
  ) {
    throw new Error('Authoritative Full Simulation result is invalid.')
  }
  return data
}

export async function previewRunProspectSourceSave(
  runId: string,
  branchId: string
): Promise<RunProspectSourceSavePreview> {
  const data = await request<RunProspectSourceSavePreview>(
    authoritativeSimulationRoot(runId, branchId) + '/prospect-source/save/preview'
  )
  verifyAuthoritativeSimulationScope(runId, branchId, data)
  if (
    data.run_prospect_source_fingerprint !== null &&
    !/^[0-9a-f]{64}$/.test(data.run_prospect_source_fingerprint)
  ) {
    throw new Error('Run prospect source Save preview fingerprint is invalid.')
  }
  return data
}

export async function saveRunProspectSource(
  runId: string,
  branchId: string,
  payload: RunProspectSourceSavePayload
): Promise<RunProspectSourceSaveResponse> {
  const data = await request<RunProspectSourceSaveResponse>(
    authoritativeSimulationRoot(runId, branchId) + '/prospect-source/save',
    { method: 'POST', body: JSON.stringify(payload) }
  )
  verifyAuthoritativeSimulationScope(runId, branchId, data)
  return data
}

export async function previewAuthoritativeSimulationSave(
  runId: string,
  branchId: string
): Promise<AuthoritativeSimulationSavePreview> {
  const data = await request<AuthoritativeSimulationSavePreview>(
    authoritativeSimulationRoot(runId, branchId) + '/save/preview'
  )
  if (data.run_id && data.run_id !== runId) throw new Error('Authoritative simulation Save preview Run mismatch.')
  if (data.branch_id && data.branch_id !== branchId) throw new Error('Authoritative simulation Save preview Branch mismatch.')
  return data
}

export async function saveAuthoritativeSimulation(
  runId: string,
  branchId: string,
  payload: AuthoritativeSimulationSavePayload
): Promise<AuthoritativeSimulationSaveResponse> {
  const data = await request<AuthoritativeSimulationSaveResponse>(
    authoritativeSimulationRoot(runId, branchId) + '/save',
    { method: 'POST', body: JSON.stringify(payload) }
  )
  verifyAuthoritativeSimulationScope(runId, branchId, data)
  return data
}

function authoritativeWeekTransitionRoot(runId: string, branchId: string): string {
  return `/admin/runs/${encodeURIComponent(runId)}/branches/${encodeURIComponent(branchId)}/week-transitions`
}

function verifyWeekTransitionCommandScope(
  runId: string,
  branchId: string,
  command: AuthoritativeWeekTransitionCommand
): void {
  if (command.run_id !== runId || command.branch_id !== branchId) {
    throw new Error('Week Transition command does not match the requested Run/Branch.')
  }
  if (
    command.target_week.season_index !== command.completed_week.season_index ||
    command.target_week.week !== command.completed_week.week + 1
  ) {
    throw new Error('Week Transition command has an invalid week boundary.')
  }
}

export async function previewDerivedAuthoritativeWeekTransition(
  runId: string,
  branchId: string,
  commandId: string
): Promise<DerivedAuthoritativeWeekTransitionPreview> {
  const data = await request<DerivedAuthoritativeWeekTransitionPreview>(
    authoritativeWeekTransitionRoot(runId, branchId) + '/derived/preview',
    {
      method: 'POST',
      body: JSON.stringify({ command_id: commandId })
    }
  )
  verifyWeekTransitionCommandScope(runId, branchId, data.command)
  verifyAuthoritativeSimulationScope(runId, branchId, data.result)
  if (data.result.command_id !== data.command.command_id) {
    throw new Error('Week Transition preview command/result identity mismatch.')
  }
  if (
    data.result.completed_week.season_index !== data.command.completed_week.season_index ||
    data.result.completed_week.week !== data.command.completed_week.week ||
    data.result.target_week.season_index !== data.command.target_week.season_index ||
    data.result.target_week.week !== data.command.target_week.week
  ) {
    throw new Error('Week Transition preview result has a different week boundary.')
  }
  if (!/^[0-9a-f]{64}$/.test(data.request_fingerprint)) {
    throw new Error('Week Transition preview request fingerprint is invalid.')
  }
  if (
    !/^[0-9a-f]{64}$/.test(data.result.official_ranking_fingerprint) ||
    !/^[0-9a-f]{64}$/.test(data.result.player_lifecycle_fingerprint) ||
    !/^[0-9a-f]{64}$/.test(data.result.player_sporting_fingerprint) ||
    data.result.player_health_fingerprint === null ||
    !/^[0-9a-f]{64}$/.test(data.result.player_health_fingerprint)
  ) {
    throw new Error('Week Transition preview authority fingerprints are invalid.')
  }
  return data
}

export async function confirmAuthoritativeWeekTransition(
  runId: string,
  branchId: string,
  preview: DerivedAuthoritativeWeekTransitionPreview
): Promise<DerivedAuthoritativeWeekTransitionPreview> {
  verifyWeekTransitionCommandScope(runId, branchId, preview.command)
  const data = await request<{
    request_fingerprint: string
    result: DerivedAuthoritativeWeekTransitionPreview['result']
  }>(
    authoritativeWeekTransitionRoot(runId, branchId),
    {
      method: 'POST',
      body: JSON.stringify(preview.command),
      headers: {
        'Content-Type': 'application/json',
        'X-Week-Transition-Ranking-Fingerprint': preview.result.official_ranking_fingerprint,
        'X-Week-Transition-Lifecycle-Fingerprint': preview.result.player_lifecycle_fingerprint,
        'X-Week-Transition-Sporting-Fingerprint': preview.result.player_sporting_fingerprint,
        'X-Week-Transition-Health-Fingerprint': preview.result.player_health_fingerprint ?? '',
        'X-Week-Transition-Request-Fingerprint': preview.request_fingerprint
      }
    }
  )
  if (data.request_fingerprint !== preview.request_fingerprint) {
    throw new Error('Confirmed Week Transition differs from the reviewed request.')
  }
  verifyAuthoritativeSimulationScope(runId, branchId, data.result)
  if (
    data.result.command_id !== preview.result.command_id ||
    data.result.official_ranking_fingerprint !== preview.result.official_ranking_fingerprint ||
    data.result.player_lifecycle_fingerprint !== preview.result.player_lifecycle_fingerprint ||
    data.result.player_sporting_fingerprint !== preview.result.player_sporting_fingerprint ||
    data.result.player_health_fingerprint !== preview.result.player_health_fingerprint
  ) {
    throw new Error('Confirmed Week Transition differs from the reviewed preview.')
  }
  return { ...preview, result: data.result }
}

export function getRun(runId: string): Promise<SeasonStateResponse> {
  return request(`/runs/${encodeURIComponent(runId)}`)
}


export function getRunWeeklyIntakeCohortSeasonPreview(
  runId: string,
  params: RunWeeklyIntakeCohortSeasonPreviewParams = {}
): Promise<RunWeeklyIntakeCohortSeasonPreviewResponse> {
  const query = new URLSearchParams()
  if (params.base_annual_intake_target !== undefined) {
    query.set('base_annual_intake_target', String(params.base_annual_intake_target))
  }
  if (params.season_growth_rate !== undefined) {
    query.set('season_growth_rate', String(params.season_growth_rate))
  }
  if (params.country_code !== undefined) query.set('country_code', params.country_code)
  if (params.region !== undefined) query.set('region', params.region)
  const suffix = query.toString() ? `?${query.toString()}` : ''
  return request(`/runs/${encodeURIComponent(runId)}/weekly-intake/cohort-season/preview${suffix}`)
}

export function getRunStatusSummary(runId: string): Promise<RunStatusSummary> {
  return request(`/runs/${encodeURIComponent(runId)}/status-summary`)
}

export function getRunWorldStatus(runId: string): Promise<RunWorldStatus> {
  return request(`/runs/${encodeURIComponent(runId)}/world-status`)
}

export function rebuildRunWorld(runId: string): Promise<RunWorldStatus> {
  return request(`/runs/${encodeURIComponent(runId)}/rebuild-world`, { method: 'POST' })
}

export function getRunTalentPlan(runId: string): Promise<RunTalentPlanSummary> {
  return request(`/runs/${encodeURIComponent(runId)}/world/talent-plan`)
}


export function getViewerVisibleProspects(
  productRunId: string,
  params: { limit?: number; offset?: number } = {}
): Promise<import('./types').VisiblePreTourProspects> {
  const query = new URLSearchParams()
  if (typeof params.limit === 'number') query.set('limit', String(params.limit))
  if (typeof params.offset === 'number') query.set('offset', String(params.offset))
  const suffix = query.size ? `?${query.toString()}` : ''
  return request(
    `/viewer/runs/${encodeURIComponent(productRunId)}/prospects/next-gen${suffix}`
  )
}

export function getAdminVisibleProspects(
  runId: string,
  branchId: string,
  params: {
    season_index?: number
    week?: number
    limit?: number
    offset?: number
  } = {}
): Promise<import('./types').VisiblePreTourProspects> {
  const query = new URLSearchParams()
  if (typeof params.season_index === 'number') query.set('season_index', String(params.season_index))
  if (typeof params.week === 'number') query.set('week', String(params.week))
  if (typeof params.limit === 'number') query.set('limit', String(params.limit))
  if (typeof params.offset === 'number') query.set('offset', String(params.offset))
  const suffix = query.size ? `?${query.toString()}` : ''
  return request(
    `/admin/runs/${encodeURIComponent(runId)}/branches/${encodeURIComponent(branchId)}/prospects/visible${suffix}`
  )
}


export function listRunProspects(
  runId: string,
  params?: { country_code?: string; status?: string; season_start_year?: number; season_week?: number; limit?: number; offset?: number }
): Promise<RunProspectListResponse> {
  const query = new URLSearchParams()
  if (params?.country_code) query.set('country_code', params.country_code)
  if (params?.status) query.set('status', params.status)
  if (typeof params?.season_start_year === 'number') query.set('season_start_year', String(params.season_start_year))
  if (typeof params?.season_week === 'number') query.set('season_week', String(params.season_week))
  if (typeof params?.limit === 'number') query.set('limit', String(params.limit))
  if (typeof params?.offset === 'number') query.set('offset', String(params.offset))
  const suffix = query.toString() ? `?${query.toString()}` : ''
  return request(`/runs/${encodeURIComponent(runId)}/prospects${suffix}`)
}


export function getRunProspectTalentSummary(
  runId: string,
  seasonStartYear?: number
): Promise<MaterializedRunProspectTalentSummaryResponse> {
  const query = new URLSearchParams()
  if (seasonStartYear !== undefined) {
    query.set('season_start_year', String(seasonStartYear))
  }
  const suffix = query.toString() ? `?${query.toString()}` : ''
  return request(`/runs/${encodeURIComponent(runId)}/prospects/talent-summary${suffix}`)
}

export function materializeRunProspects(
  runId: string,
  payload: MaterializeRunProspectsRequest
): Promise<MaterializeRunProspectsResponse> {
  return request(`/runs/${encodeURIComponent(runId)}/prospects/materialize-15yo-cohort`, { method: 'POST', body: JSON.stringify(payload) })
}

export function listGeneratedPlayersProvenance(
  runId: string,
  params?: { country_code?: string; quality_band?: string; limit?: number; offset?: number }
): Promise<GeneratedPlayerProvenanceListResponse> {
  const query = new URLSearchParams()
  if (params?.country_code) query.set('country_code', params.country_code)
  if (params?.quality_band) query.set('quality_band', params.quality_band)
  if (typeof params?.limit === 'number') query.set('limit', String(params.limit))
  if (typeof params?.offset === 'number') query.set('offset', String(params.offset))
  const suffix = query.size ? `?${query.toString()}` : ''
  return request(`/runs/${encodeURIComponent(runId)}/world/generated-players${suffix}`)
}

export function getGeneratedPlayerProvenance(runId: string, playerId: string): Promise<GeneratedPlayerProvenance> {
  return request(`/runs/${encodeURIComponent(runId)}/world/generated-players/${encodeURIComponent(playerId)}`)
}

export function listRunPlayers(
  runId: string,
  params?: {
    country_code?: string
    source_type?: string
    min_age?: number
    max_age?: number
    search?: string
    limit?: number
    offset?: number
    sort?: string
  }
): Promise<RunPlayersListResponse> {
  const query = new URLSearchParams()
  if (params?.country_code) query.set('country_code', params.country_code)
  if (params?.source_type) query.set('source_type', params.source_type)
  if (typeof params?.min_age === 'number') query.set('min_age', String(params.min_age))
  if (typeof params?.max_age === 'number') query.set('max_age', String(params.max_age))
  if (params?.search) query.set('search', params.search)
  if (typeof params?.limit === 'number') query.set('limit', String(params.limit))
  if (typeof params?.offset === 'number') query.set('offset', String(params.offset))
  if (params?.sort) query.set('sort', params.sort)
  const suffix = query.size ? `?${query.toString()}` : ''
  return request(`/runs/${encodeURIComponent(runId)}/players${suffix}`)
}

export function getRunPlayerDetail(runId: string, playerId: string): Promise<RunPlayerDetail> {
  return request(`/runs/${encodeURIComponent(runId)}/players/${encodeURIComponent(playerId)}`)
}

export function getAdminPlayerHealth(
  runId: string,
  branchId: string,
  playerId: string
): Promise<AdminPlayerHealthView> {
  return request(
    `/admin/runs/${encodeURIComponent(runId)}/branches/${encodeURIComponent(branchId)}/players/${encodeURIComponent(playerId)}/health`
  )
}

export function previewAdminPlayerHealthEdit(
  runId: string,
  branchId: string,
  playerId: string,
  payload: AdminHealthEditRequest
): Promise<AdminHealthEditPreview> {
  return request(
    `/admin/runs/${encodeURIComponent(runId)}/branches/${encodeURIComponent(branchId)}/players/${encodeURIComponent(playerId)}/health/preview`,
    { method: 'POST', body: JSON.stringify(payload) }
  )
}

export function commitAdminPlayerHealthEdit(
  runId: string,
  branchId: string,
  playerId: string,
  payload: AdminHealthEditRequest,
  previewFingerprint: string
): Promise<AdminHealthEditResult> {
  return request(
    `/admin/runs/${encodeURIComponent(runId)}/branches/${encodeURIComponent(branchId)}/players/${encodeURIComponent(playerId)}/health`,
    {
      method: 'POST',
      headers: { 'X-Player-Health-Preview-Fingerprint': previewFingerprint },
      body: JSON.stringify(payload)
    }
  )
}

export function previewPlayerHealthSave(
  runId: string,
  branchId: string
): Promise<PlayerHealthSavePreview> {
  return request(
    `/admin/runs/${encodeURIComponent(runId)}/branches/${encodeURIComponent(branchId)}/player-health/save/preview`
  )
}

export function savePlayerHealthRevision(
  runId: string,
  branchId: string,
  payload: PlayerHealthSavePayload
): Promise<PlayerHealthSaveResponse> {
  return request(
    `/admin/runs/${encodeURIComponent(runId)}/branches/${encodeURIComponent(branchId)}/player-health/save`,
    { method: 'POST', body: JSON.stringify(payload) }
  )
}

export function getRunPlayerCareerHistory(runId: string, playerId: string): Promise<PlayerCareerHistoryResponse> {
  return request(`/runs/${encodeURIComponent(runId)}/players/${encodeURIComponent(playerId)}/career`)
}

export function getRunPlayerCareerPerformance(runId: string, playerId: string): Promise<PlayerCareerPerformanceResponse> {
  return request(`/runs/${encodeURIComponent(runId)}/players/${encodeURIComponent(playerId)}/career/performance`)
}

export function getRunPlayerTournamentResults(
  runId: string,
  playerId: string
): Promise<PlayerTournamentResultsTimelineResponse> {
  return request(`/runs/${encodeURIComponent(runId)}/players/${encodeURIComponent(playerId)}/career/results`)
}

export function listRunNations(
  runId: string,
  params?: { search?: string; sort?: string; limit?: number; offset?: number }
): Promise<RunNationsSummaryResponse> {
  const query = new URLSearchParams()
  if (params?.search) query.set('search', params.search)
  if (params?.sort) query.set('sort', params.sort)
  if (typeof params?.limit === 'number') query.set('limit', String(params.limit))
  if (typeof params?.offset === 'number') query.set('offset', String(params.offset))
  const suffix = query.size ? `?${query.toString()}` : ''
  return request(`/runs/${encodeURIComponent(runId)}/nations${suffix}`)
}

export function getRunNationDetail(runId: string, countryCode: string, topLimit = 10): Promise<RunNationDetail> {
  return request(`/runs/${encodeURIComponent(runId)}/nations/${encodeURIComponent(countryCode)}?top_limit=${topLimit}`)
}

function simulate<T>(runId: string, suffix: string): Promise<T> {
  return request(`/runs/${encodeURIComponent(runId)}/simulate/${suffix}`, { method: 'POST' })
}

export function simulateNextTournament(runId: string): Promise<SimulateResponse> {
  return simulate<SimulateResponse>(runId, 'next-tournament')
}

export function simulateNextMatch(runId: string): Promise<SimulateResponse> {
  return simulate<SimulateResponse>(runId, 'next-match')
}

export function simulateNextRound(runId: string): Promise<SimulateResponse> {
  return simulate<SimulateResponse>(runId, 'next-round')
}

export function simulateNextWeek(runId: string): Promise<SimulateResponse> {
  return simulate<SimulateResponse>(runId, 'next-week')
}

export function simulateFullSeason(runId: string): Promise<SimulateResponse> {
  return simulate<SimulateResponse>(runId, 'full-season')
}

export function listEvents(runId: string): Promise<EventListResponse> {
  return request(`/runs/${encodeURIComponent(runId)}/events`)
}

export function getRunActivity(runId: string): Promise<RunActivityResponse> {
  return request(`/runs/${encodeURIComponent(runId)}/activity`)
}

export function getEvent(runId: string, eventId: string): Promise<EventRecord> {
  return request(`/runs/${encodeURIComponent(runId)}/events/${encodeURIComponent(eventId)}`)
}

function canonicalWildCardRoot(runId: string, branchId: string, eventId: string): string {
  return `/admin/runs/${encodeURIComponent(runId)}/branches/${encodeURIComponent(branchId)}/tournaments/${encodeURIComponent(eventId)}/wild-cards`
}

function verifyCanonicalWildCardScope(
  runId: string,
  branchId: string,
  eventId: string,
  data: { run_id: string; branch_id: string; event_id: string }
): void {
  if (data.run_id !== runId || data.branch_id !== branchId || data.event_id !== eventId) {
    throw new Error('Canonical WC response does not match the requested scope.')
  }
}

export async function getCanonicalWildCardState(
  runId: string,
  branchId: string,
  eventId: string
): Promise<CanonicalWildCardState> {
  const data = await request<CanonicalWildCardState>(canonicalWildCardRoot(runId, branchId, eventId))
  verifyCanonicalWildCardScope(runId, branchId, eventId, data)
  if (data.schema_version !== 'authoritative_wild_card_assignment_state.v1') {
    throw new Error('Canonical WC state has an unsupported schema.')
  }
  return data
}

export async function previewCanonicalWildCardAssignment(
  runId: string,
  branchId: string,
  eventId: string,
  payload: CanonicalWildCardReviewPayload
): Promise<CanonicalWildCardPreview> {
  const data = await request<CanonicalWildCardPreview>(
    canonicalWildCardRoot(runId, branchId, eventId) + '/preview',
    { method: 'POST', body: JSON.stringify(payload) }
  )
  verifyCanonicalWildCardScope(runId, branchId, eventId, data)
  if (data.schema_version !== 'authoritative_wild_card_assignment_preview.v1') {
    throw new Error('Canonical WC preview has an unsupported schema.')
  }
  return data
}

export async function commitCanonicalWildCardAssignment(
  runId: string,
  branchId: string,
  eventId: string,
  payload: CanonicalWildCardCommitPayload
): Promise<CanonicalWildCardCommitResult> {
  const data = await request<CanonicalWildCardCommitResult>(
    canonicalWildCardRoot(runId, branchId, eventId) + '/commit',
    { method: 'POST', body: JSON.stringify(payload) }
  )
  verifyCanonicalWildCardScope(runId, branchId, eventId, data)
  if (
    data.schema_version !== 'authoritative_wild_card_assignment_commit.v1' ||
    data.proposal_fingerprint !== payload.expected_proposal_fingerprint
  ) {
    throw new Error('Canonical WC commit does not match the reviewed proposal.')
  }
  return data
}

function canonicalTournamentRankingSnapshotRoot(runId: string, branchId: string, eventId: string): string {
  return `/admin/runs/${encodeURIComponent(runId)}/branches/${encodeURIComponent(branchId)}/tournaments/${encodeURIComponent(eventId)}/ranking-snapshot-authority`
}

export async function listTournamentRankingPublicationOptions(
  runId: string,
  branchId: string,
  eventId: string
): Promise<TournamentRankingPublicationOptions> {
  const data = await request<TournamentRankingPublicationOptions>(
    canonicalTournamentRankingSnapshotRoot(runId, branchId, eventId) + '/available'
  )
  if (
    data.run_id !== runId || data.branch_id !== branchId || data.event_id !== eventId ||
    data.source !== 'published_official_rankings.v1' || data.publication_count !== data.publications.length
  ) {
    throw new Error('Published Official Ranking options do not match the requested tournament scope.')
  }
  return data
}

export async function adoptTournamentRankingSnapshotAuthority(
  runId: string,
  branchId: string,
  eventId: string,
  payload: AdoptTournamentRankingSnapshotPayload
): Promise<TournamentRankingSnapshotAuthority> {
  const data = await request<TournamentRankingSnapshotAuthority>(
    canonicalTournamentRankingSnapshotRoot(runId, branchId, eventId),
    { method: 'POST', body: JSON.stringify(payload) }
  )
  if (
    data.schema_version !== 'tournament_ranking_snapshot_authority.v1' ||
    data.run_id !== runId || data.branch_id !== branchId || data.event_id !== eventId ||
    data.ranking_week.season_index !== payload.ranking_week.season_index ||
    data.ranking_week.week !== payload.ranking_week.week ||
    data.adopted_by_command_id !== payload.command_id
  ) {
    throw new Error('Tournament Ranking Snapshot authority response does not match the requested command.')
  }
  return data
}

/** Read-only authoritative field cut, including exactly ranked/validated player partitions. */
export async function previewRunReviewedEntryField(
  runId: string, branchId: string, eventId: string,
  capacity: import('./types').TournamentEntryFieldCapacity
): Promise<import('./runReviewedEntryField').ReviewedEntryFieldPreview> {
  const root = `/admin/runs/${encodeURIComponent(runId)}/branches/${encodeURIComponent(branchId)}/tournaments/${encodeURIComponent(eventId)}/entry-field`
  const data = await request<import('./runReviewedEntryField').ReviewedEntryFieldPreview>(
    root + '/from-valid-submissions/preview',
    { method: 'POST', body: JSON.stringify({ capacity }) }
  )
  if (!(
    data?.preview_only === true && data.run_id === runId &&
    data.branch_id === branchId && data.event_id === eventId &&
    /^[a-f0-9]{64}$/.test(data.field_fingerprint) &&
    data.field?.run_id === runId && data.field.branch_id === branchId &&
    data.field.event_id === eventId && data.field.mode === 'initial'
  )) throw new Error('Reviewed Entry Field preview returned incorrect Run/Branch/Event.')
  return data
}

export async function commitRunReviewedEntryField(
  runId: string, branchId: string, eventId: string,
  preview: import('./runReviewedEntryField').ReviewedEntryFieldPreview,
  commandId: string
): Promise<TournamentEntryField> {
  if (!commandId || commandId.length > 128 ||
    preview.run_id !== runId || preview.branch_id !== branchId ||
    preview.event_id !== eventId || !/^[a-f0-9]{64}$/.test(preview.field_fingerprint)) {
    throw new Error('Reviewed Entry Field commit requires valid scoped preflight evidence.')
  }
  const root = `/admin/runs/${encodeURIComponent(runId)}/branches/${encodeURIComponent(branchId)}/tournaments/${encodeURIComponent(eventId)}/entry-field`
  const saved = await request<TournamentEntryField>(
    root + '/from-valid-submissions/reviewed',
    { method: 'POST', body: JSON.stringify({
      command_id: commandId, capacity: preview.field.capacity,
      expected_field_fingerprint: preview.field_fingerprint
    }) }
  )
  if (!(
    saved.schema_version === 'tournament_entry_field.v1' &&
    saved.run_id === runId && saved.branch_id === branchId &&
    saved.event_id === eventId && saved.mode === 'initial' &&
    saved.applications_fingerprint === preview.field.applications_fingerprint &&
    saved.tournament_ranking_authority_fingerprint === preview.field.tournament_ranking_authority_fingerprint &&
    saved.direct_main_player_ids.join('|') === preview.field.direct_main_player_ids.join('|') &&
    saved.qualification_player_ids.join('|') === preview.field.qualification_player_ids.join('|') &&
    saved.below_qualification_cut_player_ids.join('|') === preview.field.below_qualification_cut_player_ids.join('|')
  )) throw new Error('Reviewed Entry Field commit differs from the exact verified preview.')
  return saved
}

export async function createTournamentEntryFieldFromValidSubmissions(
  runId: string,
  branchId: string,
  eventId: string,
  payload: CreateTournamentEntryFieldPayload
): Promise<TournamentEntryField> {
  const data = await request<TournamentEntryField>(
    `/admin/runs/${encodeURIComponent(runId)}/branches/${encodeURIComponent(branchId)}/tournaments/${encodeURIComponent(eventId)}/entry-field/from-valid-submissions`,
    { method: 'POST', body: JSON.stringify(payload) }
  )
  if (
    data.schema_version !== 'tournament_entry_field.v1' ||
    data.run_id !== runId || data.branch_id !== branchId || data.event_id !== eventId ||
    data.mode !== 'initial'
  ) {
    throw new Error('Tournament Entry Field response does not match the requested scope.')
  }
  return data
}

export async function createTournamentEntryFieldFromFinalsSelection(
  runId: string,
  branchId: string,
  eventId: string,
  payload: CreateFinalsTournamentEntryFieldPayload
): Promise<TournamentEntryField> {
  const data = await request<TournamentEntryField>(
    `/admin/runs/${encodeURIComponent(runId)}/branches/${encodeURIComponent(branchId)}/tournaments/${encodeURIComponent(eventId)}/entry-field/from-finals-participant-selection`,
    { method: 'POST', body: JSON.stringify(payload) }
  )
  if (
    data.schema_version !== 'tournament_entry_field.v2' ||
    data.run_id !== runId ||
    data.branch_id !== branchId ||
    data.event_id !== eventId ||
    data.mode !== 'initial' ||
    data.source_kind !== 'finals_participant_selection' ||
    data.finals_target_season_index !== payload.target_season_index
  ) {
    throw new Error('Finals Tournament Entry Field response does not match the requested selection authority.')
  }
  return data
}

export async function generateTournamentGroupMatchSchedule(
  runId: string,
  branchId: string,
  eventId: string,
  payload: GenerateTournamentGroupMatchSchedulePayload
): Promise<TournamentGroupMatchScheduleAuthority> {
  const data = await request<TournamentGroupMatchScheduleAuthority>(
    `/admin/runs/${encodeURIComponent(runId)}/branches/${encodeURIComponent(branchId)}/tournaments/${encodeURIComponent(eventId)}/format/group-match-schedule/generate`,
    { method: 'POST', body: JSON.stringify(payload) }
  )
  if (
    data.schema_version !== 'tournament_group_match_schedule_authority.v1' ||
    data.run_id !== runId ||
    data.branch_id !== branchId ||
    data.event_id !== eventId ||
    !data.authority_fingerprint
  ) {
    throw new Error('Tournament Group Match Schedule response does not match the requested authority scope.')
  }
  return data
}

export async function getTournamentGroupMatchSchedule(
  runId: string,
  branchId: string,
  eventId: string
): Promise<TournamentGroupMatchScheduleAuthority> {
  const data = await request<TournamentGroupMatchScheduleAuthority>(
    `/admin/runs/${encodeURIComponent(runId)}/branches/${encodeURIComponent(branchId)}/tournaments/${encodeURIComponent(eventId)}/format/group-match-schedule`
  )
  if (
    data.schema_version !== 'tournament_group_match_schedule_authority.v1' ||
    data.run_id !== runId ||
    data.branch_id !== branchId ||
    data.event_id !== eventId ||
    !data.authority_fingerprint
  ) {
    throw new Error('Tournament Group Match Schedule response does not match the requested authority scope.')
  }
  return data
}

export function getCanonicalTournamentPreparation(
  runId: string,
  branchId: string,
  eventId: string
): Promise<CanonicalTournamentPreparationState> {
  return request(
    `/admin/runs/${encodeURIComponent(runId)}/branches/${encodeURIComponent(branchId)}/tournaments/${encodeURIComponent(eventId)}/preparation`
  )
}

export async function getCanonicalTournamentEntryFieldState(
  runId: string,
  branchId: string,
  eventId: string
): Promise<CanonicalTournamentEntryFieldState> {
  const data = await request<CanonicalTournamentEntryFieldState>(
    `/admin/runs/${encodeURIComponent(runId)}/branches/${encodeURIComponent(branchId)}/tournaments/${encodeURIComponent(eventId)}/entry-field`
  )
  if (
    data.schema_version !== 'canonical_tournament_entry_field_state.v2' ||
    data.run_id !== runId ||
    data.branch_id !== branchId ||
    data.event_id !== eventId
  ) {
    throw new Error('Canonical Tournament Entry Field response does not match the requested scope.')
  }
  return data
}

export async function commitCanonicalPreDrawWithdrawal(
  runId: string,
  branchId: string,
  eventId: string,
  payload: CanonicalPreDrawWithdrawalPayload
): Promise<CanonicalPreDrawWithdrawalResult> {
  const data = await request<CanonicalPreDrawWithdrawalResult>(
    `/admin/runs/${encodeURIComponent(runId)}/branches/${encodeURIComponent(branchId)}/tournaments/${encodeURIComponent(eventId)}/entry-field/pre-draw-withdrawal`,
    { method: 'POST', body: JSON.stringify(payload) }
  )
  if (
    data.schema_version !== 'canonical_pre_draw_withdrawal_result.v1' ||
    data.run_id !== runId ||
    data.branch_id !== branchId ||
    data.event_id !== eventId ||
    data.command_id !== payload.command_id ||
    data.predecessor_field_fingerprint !== payload.expected_field_fingerprint ||
    !/^[0-9a-f]{64}$/.test(data.field_fingerprint)
  ) {
    throw new Error('Canonical pre-draw withdrawal response does not match the reviewed field authority.')
  }
  return data
}

function canonicalTournamentDrawRoot(runId: string, branchId: string, eventId: string): string {
  return `/admin/runs/${encodeURIComponent(runId)}/branches/${encodeURIComponent(branchId)}/tournaments/${encodeURIComponent(eventId)}/draw`
}

function verifyCanonicalTournamentDrawScope(
  runId: string,
  branchId: string,
  eventId: string,
  data: { run_id: string; branch_id: string; event_id: string }
): void {
  if (data.run_id !== runId || data.branch_id !== branchId || data.event_id !== eventId) {
    throw new Error('Canonical Tournament Draw response does not match the requested scope.')
  }
}

export async function getCanonicalTournamentDrawState(
  runId: string,
  branchId: string,
  eventId: string
): Promise<CanonicalTournamentDrawState> {
  const data = await request<CanonicalTournamentDrawState>(
    canonicalTournamentDrawRoot(runId, branchId, eventId)
  )
  verifyCanonicalTournamentDrawScope(runId, branchId, eventId, data)
  if (data.schema_version !== 'canonical_tournament_draw_state.v1') {
    throw new Error('Canonical Tournament Draw state has an unsupported schema.')
  }
  return data
}

export async function commitCanonicalTournamentDrawInput(
  runId: string,
  branchId: string,
  eventId: string,
  payload: CanonicalDrawInputCommitPayload
): Promise<CanonicalTournamentDrawState> {
  const data = await request<CanonicalTournamentDrawState>(
    canonicalTournamentDrawRoot(runId, branchId, eventId) + '/commit-input',
    { method: 'POST', body: JSON.stringify(payload) }
  )
  verifyCanonicalTournamentDrawScope(runId, branchId, eventId, data)
  return data
}

export async function generateCanonicalTournamentDraw(
  runId: string,
  branchId: string,
  eventId: string,
  payload: CanonicalDrawGeneratePayload
): Promise<CanonicalTournamentDrawState> {
  const data = await request<CanonicalTournamentDrawState>(
    canonicalTournamentDrawRoot(runId, branchId, eventId) + '/generate',
    { method: 'POST', body: JSON.stringify(payload) }
  )
  verifyCanonicalTournamentDrawScope(runId, branchId, eventId, data)
  return data
}

export async function getCanonicalTournamentDrawAuthority(
  runId: string,
  branchId: string,
  eventId: string
): Promise<CanonicalTournamentDrawAuthority> {
  const data = await request<CanonicalTournamentDrawAuthority>(
    canonicalTournamentDrawRoot(runId, branchId, eventId) + '/authority'
  )
  verifyCanonicalTournamentDrawScope(runId, branchId, eventId, data)
  return data
}

export async function getCanonicalTournamentEffectiveDrawAuthority(
  runId: string,
  branchId: string,
  eventId: string
): Promise<CanonicalTournamentDrawAuthority> {
  const data = await request<CanonicalTournamentDrawAuthority>(
    canonicalTournamentDrawRoot(runId, branchId, eventId) + '/effective-authority'
  )
  verifyCanonicalTournamentDrawScope(runId, branchId, eventId, data)
  return data
}

export async function getCanonicalTournamentDrawRevisionHistory(
  runId: string,
  branchId: string,
  eventId: string
): Promise<CanonicalTournamentDrawRevisionHistoryState> {
  const data = await request<CanonicalTournamentDrawRevisionHistoryState>(
    canonicalTournamentDrawRoot(runId, branchId, eventId) + '/revisions'
  )
  verifyCanonicalTournamentDrawScope(runId, branchId, eventId, data)
  if (data.schema_version !== 'canonical_tournament_draw_revision_history.v1') {
    throw new Error('Canonical Tournament Draw revision history has an unsupported schema.')
  }
  return data
}

function canonicalTournamentDrawProcessRoot(runId: string, branchId: string, eventId: string): string {
  return canonicalTournamentDrawRoot(runId, branchId, eventId) + '/process'
}

export async function getCanonicalTournamentDrawProcessState(
  runId: string,
  branchId: string,
  eventId: string
): Promise<CanonicalTournamentDrawProcessState> {
  const data = await request<CanonicalTournamentDrawProcessState>(
    canonicalTournamentDrawProcessRoot(runId, branchId, eventId)
  )
  verifyCanonicalTournamentDrawScope(runId, branchId, eventId, data)
  if (data.schema_version !== 'canonical_tournament_draw_process_state.v1') {
    throw new Error('Canonical Tournament Draw process state has an unsupported schema.')
  }
  return data
}

export async function configureCanonicalTournamentDrawProcess(
  runId: string,
  branchId: string,
  eventId: string,
  payload: CanonicalDrawProcessConfigurePayload
): Promise<CanonicalTournamentDrawProcessState> {
  const data = await request<CanonicalTournamentDrawProcessState>(
    canonicalTournamentDrawProcessRoot(runId, branchId, eventId) + '/configure',
    { method: 'POST', body: JSON.stringify(payload) }
  )
  verifyCanonicalTournamentDrawScope(runId, branchId, eventId, data)
  return data
}

export async function previewCanonicalFrozenMainReplacement(
  runId: string,
  branchId: string,
  eventId: string,
  payload: CanonicalFrozenMainReplacementPreviewRequest
): Promise<CanonicalFrozenMainReplacementPreview> {
  const data = await request<CanonicalFrozenMainReplacementPreview>(
    canonicalTournamentDrawRoot(runId, branchId, eventId) + '/frozen-main-replacement/preview',
    { method: 'POST', body: JSON.stringify(payload) }
  )
  verifyCanonicalTournamentDrawScope(runId, branchId, eventId, data)
  if (
    data.schema_version !== 'authoritative_frozen_main_replacement_preview.v1' ||
    data.withdrawn_player_id !== payload.withdrawn_player_id ||
    !/^[0-9a-f]{64}$/.test(data.source_authority_fingerprint) ||
    data.physical_slot_index < 1
  ) {
    throw new Error('Frozen Main replacement preview is invalid.')
  }
  return data
}

export async function commitCanonicalFrozenMainReplacement(
  runId: string,
  branchId: string,
  eventId: string,
  payload: CanonicalFrozenMainReplacementCommitPayload
): Promise<CanonicalFrozenMainReplacementCommitResult> {
  const data = await request<CanonicalFrozenMainReplacementCommitResult>(
    canonicalTournamentDrawRoot(runId, branchId, eventId) + '/frozen-main-replacement/commit',
    { method: 'POST', body: JSON.stringify(payload) }
  )
  verifyCanonicalTournamentDrawScope(runId, branchId, eventId, data)
  if (
    data.schema_version !== 'authoritative_frozen_main_replacement_commit.v1' ||
    data.withdrawn_player_id !== payload.withdrawn_player_id ||
    data.source_authority_fingerprint !== payload.expected_source_fingerprint ||
    data.draw_revision_sequences.length !== data.draw_revision_fingerprints.length ||
    data.draw_revision_fingerprints.some((value) => !/^[0-9a-f]{64}$/.test(value)) ||
    (
      data.successor_draw_fingerprint !== null &&
      !/^[0-9a-f]{64}$/.test(data.successor_draw_fingerprint)
    )
  ) {
    throw new Error('Frozen Main replacement commit response is invalid.')
  }
  return data
}

function finalsReplacementRoot(
  runId: string,
  branchId: string,
  targetSeasonIndex: number
): string {
  return `/admin/runs/${encodeURIComponent(runId)}/branches/${encodeURIComponent(branchId)}/finals-participants/${targetSeasonIndex}/replacements`
}

export async function getFinalsEffectiveParticipantState(
  runId: string,
  branchId: string,
  targetSeasonIndex: number
): Promise<FinalsEffectiveParticipantStateResponse> {
  const data = await request<FinalsEffectiveParticipantStateResponse>(
    finalsReplacementRoot(runId, branchId, targetSeasonIndex) + '/effective'
  )
  if (
    data.state !== null &&
    (
      data.state.run_id !== runId ||
      data.state.branch_id !== branchId ||
      data.state.target_season_index !== targetSeasonIndex ||
      data.fingerprint === null ||
      !/^[0-9a-f]{64}$/.test(data.fingerprint)
    )
  ) {
    throw new Error('Finals effective participant state response does not match the requested scope.')
  }
  if (data.state === null && data.fingerprint !== null) {
    throw new Error('Empty Finals effective participant state cannot carry a fingerprint.')
  }
  return data
}

export async function previewFinalsRaceReplacement(
  runId: string,
  branchId: string,
  targetSeasonIndex: number,
  payload: FinalsReplacementPreviewPayload
): Promise<FinalsReplacementAuthorityResponse> {
  const data = await request<FinalsReplacementAuthorityResponse>(
    finalsReplacementRoot(runId, branchId, targetSeasonIndex) + '/preview',
    { method: 'POST', body: JSON.stringify(payload) }
  )
  if (
    data.authority.run_id !== runId ||
    data.authority.branch_id !== branchId ||
    data.authority.target_season_index !== targetSeasonIndex ||
    data.authority.vacancy_id !== payload.vacancy_id ||
    data.authority.withdrawn_player_id !== payload.withdrawn_player_id ||
    !/^[0-9a-f]{64}$/.test(data.fingerprint)
  ) {
    throw new Error('Finals replacement preview response does not match the requested command.')
  }
  return data
}

export async function decideFinalsRaceReplacement(
  runId: string,
  branchId: string,
  targetSeasonIndex: number,
  vacancyId: string,
  payload: FinalsReplacementDecisionPayload
): Promise<FinalsReplacementAuthorityResponse> {
  const data = await request<FinalsReplacementAuthorityResponse>(
    finalsReplacementRoot(runId, branchId, targetSeasonIndex) +
      `/${encodeURIComponent(vacancyId)}/decision`,
    { method: 'POST', body: JSON.stringify(payload) }
  )
  if (
    data.authority.run_id !== runId ||
    data.authority.branch_id !== branchId ||
    data.authority.target_season_index !== targetSeasonIndex ||
    data.authority.vacancy_id !== vacancyId ||
    !/^[0-9a-f]{64}$/.test(data.fingerprint)
  ) {
    throw new Error('Finals replacement decision response does not match the requested command.')
  }
  return data
}

export function listRankingSnapshots(runId: string): Promise<RankingSnapshotListResponse> {
  return request(`/runs/${encodeURIComponent(runId)}/snapshots/ranking`)
}

export function listRaceSnapshots(runId: string): Promise<RaceSnapshotListResponse> {
  return request(`/runs/${encodeURIComponent(runId)}/snapshots/race`)
}

export function getRankingSnapshot(runId: string, snapshotSequence: number): Promise<RankingSnapshot> {
  return request(`/runs/${encodeURIComponent(runId)}/snapshots/ranking/${snapshotSequence}`)
}

export function getRaceSnapshot(runId: string, snapshotSequence: number): Promise<RaceSnapshot> {
  return request(`/runs/${encodeURIComponent(runId)}/snapshots/race/${snapshotSequence}`)
}


export function getFinalsQualification(runId: string): Promise<FinalsQualificationResponse> {
  return request(`/runs/${encodeURIComponent(runId)}/finals/qualification`)
}

export function getFinalsResult(runId: string): Promise<FinalsResultResponse> {
  return request(`/runs/${encodeURIComponent(runId)}/finals/result`)
}

export function getFinalsSummary(runId: string): Promise<FinalsSummaryResponse> {
  return request(`/runs/${encodeURIComponent(runId)}/finals/summary`)
}

export function simulateWorldTourFinals(runId: string): Promise<FinalsSimulationResponse> {
  return simulate<FinalsSimulationResponse>(runId, 'world-tour-finals')
}


export function bootstrapNextSeason(
  runId: string,
  payload: BootstrapNextSeasonPayload
): Promise<BootstrapNextSeasonResponse> {
  return request(`/runs/${encodeURIComponent(runId)}/bootstrap-next-season`, {
    method: 'POST',
    body: JSON.stringify(payload)
  })
}

export function getRunLineage(runId: string): Promise<RunLineageApiResponse> {
  return request(`/runs/${encodeURIComponent(runId)}/lineage`)
}

export function getRunSource(runId: string): Promise<RunSourceApiResponse> {
  return request(`/runs/${encodeURIComponent(runId)}/source`)
}

export function rolloverNextSeason(runId: string): Promise<SeasonRolloverExecutionResponse> {
  return request(`/runs/${encodeURIComponent(runId)}/rollover/next-season`, { method: 'POST' })
}

export function getLatestRollover(runId: string): Promise<SeasonRolloverSummaryApiResponse> {
  return request(`/runs/${encodeURIComponent(runId)}/rollover/latest`)
}

export function getRolloverBySeason(runId: string, toSeason: number): Promise<SeasonRolloverSummaryApiResponse> {
  return request(`/runs/${encodeURIComponent(runId)}/rollover/${toSeason}`)
}

export function getNextSeasonPlayers(runId: string, toSeason: number): Promise<NextSeasonPlayersResponse> {
  return request(`/runs/${encodeURIComponent(runId)}/players/next-season/${toSeason}`)
}

export function getPlayerTransitions(runId: string, toSeason: number): Promise<PlayerTransitionsResponse> {
  return request(`/runs/${encodeURIComponent(runId)}/players/transitions/${toSeason}`)
}

export { ApiError }

function verifyRankingTransitionAuthority(
  runId: string,
  branchId: string,
  authority: import('./rankingCandidates').RankingTransitionAuthority
): void {
  if (authority.run_id !== runId || authority.branch_id !== branchId) {
    throw new Error('Ranking Transition Authority scope mismatch.')
  }
  if (
    authority.target_week.season_index !== authority.completed_week.season_index ||
    authority.target_week.week !== authority.completed_week.week + 1
  ) {
    throw new Error('Ranking Transition Authority has an invalid week boundary.')
  }
}

export async function previewDerivedRankingTransitionAuthority(
  runId: string,
  branchId: string,
  payload: import('./rankingCandidates').DerivedRankingTransitionAuthorityRequest
): Promise<import('./rankingCandidates').DerivedRankingTransitionAuthorityPreview> {
  const data = await request<import('./rankingCandidates').DerivedRankingTransitionAuthorityPreview>(
    `/admin/runs/${encodeURIComponent(runId)}/branches/${encodeURIComponent(branchId)}/ranking-candidates/transition-authorities/derived/preview`,
    { method: 'POST', body: JSON.stringify(payload) }
  )
  verifyRankingTransitionAuthority(runId, branchId, data.authority)
  if (data.authority.adopted_by_command_id !== payload.command_id) {
    throw new Error('Ranking Transition Authority command identity mismatch.')
  }
  if (
    data.authority.audit.actor_label !== payload.audit.actor_label ||
    data.authority.audit.reason !== payload.audit.reason
  ) {
    throw new Error('Ranking Transition Authority audit differs from the request.')
  }
  if (!/^[0-9a-f]{64}$/.test(data.authority_fingerprint)) {
    throw new Error('Ranking Transition Authority fingerprint is invalid.')
  }
  return data
}

export async function confirmDerivedRankingTransitionAuthority(
  runId: string,
  branchId: string,
  payload: import('./rankingCandidates').DerivedRankingTransitionAuthorityRequest,
  preview: import('./rankingCandidates').DerivedRankingTransitionAuthorityPreview
): Promise<import('./rankingCandidates').RankingTransitionAuthority> {
  verifyRankingTransitionAuthority(runId, branchId, preview.authority)
  const data = await request<import('./rankingCandidates').RankingTransitionAuthority>(
    `/admin/runs/${encodeURIComponent(runId)}/branches/${encodeURIComponent(branchId)}/ranking-candidates/transition-authorities/derived`,
    {
      method: 'POST',
      body: JSON.stringify(payload),
      headers: {
        'Content-Type': 'application/json',
        'X-Ranking-Transition-Authority-Fingerprint': preview.authority_fingerprint
      }
    }
  )
  verifyRankingTransitionAuthority(runId, branchId, data)
  if (
    data.base_revision_id !== preview.authority.base_revision_id ||
    data.adopted_by_command_id !== preview.authority.adopted_by_command_id ||
    data.completed_week.season_index !== preview.authority.completed_week.season_index ||
    data.completed_week.week !== preview.authority.completed_week.week ||
    data.target_week.season_index !== preview.authority.target_week.season_index ||
    data.target_week.week !== preview.authority.target_week.week ||
    data.policy.policy_id !== preview.authority.policy.policy_id ||
    data.policy.best_n !== preview.authority.policy.best_n ||
    data.players.length !== preview.authority.players.length
  ) {
    throw new Error('Confirmed Ranking Transition Authority differs from the reviewed preview.')
  }
  return data
}

export async function getRankingCandidates(runId: string, branchId: string): Promise<import('./rankingCandidates').RankingCandidateHistory> {
  const data = await request<import('./rankingCandidates').RankingCandidateHistory>(`/admin/runs/${encodeURIComponent(runId)}/branches/${encodeURIComponent(branchId)}/ranking-candidates`)
  if (data.run_id !== runId || data.branch_id !== branchId || data.publication_status !== 'candidate_only' || !Array.isArray(data.candidates) || data.candidates.some(c => c.publication_status !== 'candidate_only' || c.snapshot.run_id !== runId || c.snapshot.branch_id !== branchId)) {
    throw new Error('Ranking response does not match the requested Run and Branch.')
  }
  return data
}

/** Apply only through existing Run-owned Package preview/confirm authority. */
function sourcePackageRoot(runId: string, branchId: string, kind: import('./runPackageSetup').RunSourcePackageKind, sourceId: string): string {
  return `/admin/runs/${encodeURIComponent(runId)}/branches/${encodeURIComponent(branchId)}/packages/source-${kind}/${encodeURIComponent(sourceId)}`
}


export function previewWorldSelection(
  runId: string, branchId: string, worldId: string,
  payload: import('./worldSelection').WorldSelectionRequest
): Promise<import('./worldSelection').WorldSelectionPreview> {
  return request(
    sourcePackageRoot(runId, branchId, 'world', worldId) + '/selection-preview',
    { method: 'POST', body: JSON.stringify(payload) }
  )
}

export function confirmWorldSelection(
  runId: string, branchId: string, worldId: string,
  payload: import('./worldSelection').WorldSelectionConfirm
): Promise<import('./runPackageSetup').RunSourcePackageApplied> {
  return request(
    sourcePackageRoot(runId, branchId, 'world', worldId) + '/selection-confirm',
    { method: 'POST', body: JSON.stringify(payload) }
  )
}

export function previewRunSourcePackage(
  runId: string, branchId: string,
  kind: import('./runPackageSetup').RunSourcePackageKind, sourceId: string
): Promise<import('./runPackageSetup').RunSourcePackagePreview> {
  return request(`${sourcePackageRoot(runId, branchId, kind, sourceId)}/preview`, { method: 'POST' })
}

export function confirmRunSourcePackage(
  runId: string, branchId: string,
  kind: import('./runPackageSetup').RunSourcePackageKind, sourceId: string,
  payload: import('./runPackageSetup').RunSourcePackageConfirm
): Promise<import('./runPackageSetup').RunSourcePackageApplied> {
  return request(`${sourcePackageRoot(runId, branchId, kind, sourceId)}/confirm`, {
    method: 'POST', body: JSON.stringify(payload)
  })
}

export function saveRunPackageWorkingDraft(
  runId: string, branchId: string, expectedDraftVersion: number
): Promise<import('./runPackageSetup').RunWorkingDraftSaved> {
  return request(
    `/run-containers/${encodeURIComponent(runId)}/branches/${encodeURIComponent(branchId)}/working-draft/save`,
    { method: 'POST', body: JSON.stringify({ expected_draft_version: expectedDraftVersion }) }
  )
}

/** Server-side generated pool → reviewed InitialWorld adoption; never legacy global initial pool. */
function runInitialWorldRoot(runId: string, branchId: string): string {
  return `/admin/players/runs/${encodeURIComponent(runId)}/branches/${encodeURIComponent(branchId)}/initial-world`
}

/** Read verified country/region constraints only from this Branch's immutable World copy. */
export function getRunWorldGenerationOptions(
  runId: string, branchId: string, worldId: string,
  head: string, draftVersion: number, fingerprint: string
): Promise<import('./runInitialWorldSetup').RunWorldGenerationOptions> {
  if (!runId || !branchId || !worldId || !head ||
      !Number.isInteger(draftVersion) || draftVersion < 0 ||
      !/^[0-9a-f]{64}$/.test(fingerprint)) {
    throw new Error('Invalid saved Run World generation options scope.')
  }
  const query = new URLSearchParams({
    world_package_id: worldId, expected_head: head,
    expected_draft_version: String(draftVersion),
    expected_package_fingerprint: fingerprint
  })
  return request(`${runInitialWorldRoot(runId, branchId)}/world-package/generation-options?${query}`)
}

export function previewRunOwnedInitialWorld(
  runId: string, branchId: string,
  payload: import('./runInitialWorldSetup').RunInitialWorldAdoption
): Promise<import('./runInitialWorldSetup').RunInitialWorldPreview> {
  return request(`${runInitialWorldRoot(runId, branchId)}/world-package/preview`, {
    method: 'POST', body: JSON.stringify(payload)
  })
}

export function adoptRunOwnedInitialWorld(
  runId: string, branchId: string,
  payload: import('./runInitialWorldSetup').RunInitialWorldAdoption,
  expectedFingerprint: string,
  reviewed?: { head: string; draftVersion: number; packageFingerprint: string }
): Promise<import('./runInitialWorldSetup').RunInitialWorldState> {
  return request(`${runInitialWorldRoot(runId, branchId)}/world-package`, {
    method: 'POST',
    headers: {
      'X-Initial-World-Preview-Fingerprint': expectedFingerprint,
      ...(reviewed ? {
        'X-Expected-Saved-Revision-Id': reviewed.head,
        'X-Expected-Draft-Version': String(reviewed.draftVersion),
        'X-Expected-Run-Package-Fingerprint': reviewed.packageFingerprint
      } : {})
    },
    body: JSON.stringify(payload)
  })
}

/** Strict selected-append review; does not mutate an existing InitialWorld. */
export function previewSelectedInitialWorldAppend(
  runId: string, branchId: string,
  payload: import('./runInitialWorldSetup').SelectedInitialWorldAppendRequest
): Promise<import('./runInitialWorldSetup').SelectedInitialWorldAppendPreview> {
  return request(`${runInitialWorldRoot(runId, branchId)}/selected-append/preview`, {
    method: 'POST', body: JSON.stringify(payload)
  })
}

/** Commit only the exact selected append reviewed fingerprint. No implicit Saved Revision. */
export function commitSelectedInitialWorldAppend(
  runId: string, branchId: string,
  payload: import('./runInitialWorldSetup').SelectedInitialWorldAppendRequest,
  expectedFingerprint: string
): Promise<import('./runInitialWorldSetup').RunInitialWorldState> {
  return request(`${runInitialWorldRoot(runId, branchId)}/selected-append`, {
    method: 'POST',
    headers: {'X-Expected-Selected-Append-Fingerprint': expectedFingerprint},
    body: JSON.stringify(payload)
  })
}

/** Non-authoritative, Run/Branch-scoped saved generation reviews. */
export function getRunGenerationProposals(
  runId: string, branchId: string
): Promise<{proposals: import('./runInitialWorldSetup').RunSavedGenerationProposalSummary[]}> {
  return request(`${runInitialWorldRoot(runId, branchId)}/generation-proposals`)
}

export function saveRunGenerationProposal(
  runId: string, branchId: string,
  proposal: import('./runInitialWorldSetup').RunSaveGenerationProposal
): Promise<import('./runInitialWorldSetup').RunSavedGenerationProposal> {
  return request(`${runInitialWorldRoot(runId, branchId)}/generation-proposals`, {
    method: 'POST', body: JSON.stringify(proposal)
  })
}

export function loadRunGenerationProposal(
  runId: string, branchId: string, proposalId: string
): Promise<import('./runInitialWorldSetup').RunSavedGenerationProposal> {
  return request(`${runInitialWorldRoot(runId, branchId)}/generation-proposals/${encodeURIComponent(proposalId)}`)
}

/** Read only the exact historical bytes, even when Saved HEAD/World moved. */
export function inspectRunGenerationProposal(
  runId: string, branchId: string, proposalId: string
): Promise<import('./runInitialWorldSetup').RunGenerationProposalInspection> {
  return request(`${runInitialWorldRoot(runId, branchId)}/generation-proposals/${encodeURIComponent(proposalId)}/inspection`)
}

/** Explicit production rerun against the current, still-clean Run/Branch. No Adopt. */
export function revalidateRunGenerationProposal(
  runId: string, branchId: string, proposalId: string,
  context: { expected_head: string; expected_draft_version: number; expected_package_fingerprint: string }
): Promise<import('./runInitialWorldSetup').RunGenerationProposalRevalidation> {
  return request(`${runInitialWorldRoot(runId, branchId)}/generation-proposals/${encodeURIComponent(proposalId)}/revalidate`, {
    method: 'POST', body: JSON.stringify(context)
  })
}

export function deleteRunGenerationProposal(
  runId: string, branchId: string, proposalId: string
): Promise<void> {
  return request(`${runInitialWorldRoot(runId, branchId)}/generation-proposals/${encodeURIComponent(proposalId)}`,{
    method:'DELETE'
  })
}

export function getRunOwnedInitialWorld(
  runId: string, branchId: string
): Promise<import('./runInitialWorldSetup').RunInitialWorldState> {
  return request(runInitialWorldRoot(runId, branchId))
}

export function previewRunInitialWorldSave(
  runId: string, branchId: string
): Promise<import('./runInitialWorldSetup').RunInitialWorldSavePreview> {
  return request(`${runInitialWorldRoot(runId, branchId)}/save/preview`)
}

export function saveRunOwnedInitialWorld(
  runId: string, branchId: string,
  expectedDraftVersion: number, expectedFingerprint: string
): Promise<import('./runInitialWorldSetup').RunInitialWorldSaved> {
  return request(`${runInitialWorldRoot(runId, branchId)}/save`, {
    method: 'POST',
    body: JSON.stringify({
      expected_draft_version: expectedDraftVersion,
      expected_initial_world_fingerprint: expectedFingerprint
    })
  })
}

/** Canonical Calendar adapter, never legacy Simulation Run calendar reads. */
export async function getRunOwnedCalendar(
  runId: string, branchId: string, packageId: string
): Promise<import('./runFirstTournament').RunCalendarProjection> {
  const data = await request<import('./runFirstTournament').RunCalendarProjection>(
    `/admin/runs/${encodeURIComponent(runId)}/branches/${encodeURIComponent(branchId)}/packages/calendar/${encodeURIComponent(packageId)}`
  )
  if (!(
    data?.run_id === runId &&
    data.branch_id === branchId &&
    data.package_id === packageId &&
    data.calendar?.season === data.season &&
    /^[0-9a-f]{64}$/.test(data.fingerprint)
  )) throw new Error('Run-owned Calendar response does not match the selected Run/Branch/Package.')
  return data
}

export async function getRunPackageState(runId: string, branchId: string): Promise<import('./types').RunPackageStateResponse> {
  const data = await request<import('./types').RunPackageStateResponse>(`/admin/runs/${encodeURIComponent(runId)}/branches/${encodeURIComponent(branchId)}/packages`)
  if (data.state !== null && (data.state.run_id !== runId || data.state.branch_id !== branchId)) {
    throw new Error('Run Package state does not match the requested Run and Branch.')
  }
  return data
}

export async function getRankingCandidateSources(runId: string, branchId: string, seasonIndex: number, week: number): Promise<import('./rankingCandidates').RankingCandidateSources> {
  const data = await request<import('./rankingCandidates').RankingCandidateSources>(`/admin/runs/${encodeURIComponent(runId)}/branches/${encodeURIComponent(branchId)}/ranking-candidates/${seasonIndex}/${week}/sources`)
  if (data.run_id !== runId || data.branch_id !== branchId || data.week.season_index !== seasonIndex || data.week.week !== week || data.publication_status !== 'candidate_only') throw new Error('Ranking sources do not match the requested scope and week.')
  return data
}

export async function getRankingCandidateInputs(runId: string, branchId: string, seasonIndex: number, week: number): Promise<import('./rankingCandidates').RankingCandidateInputs> {
  const data = await request<import('./rankingCandidates').RankingCandidateInputs>(`/admin/runs/${encodeURIComponent(runId)}/branches/${encodeURIComponent(branchId)}/ranking-candidates/${seasonIndex}/${week}/inputs`)
  if (data.run_id !== runId || data.branch_id !== branchId || data.week.season_index !== seasonIndex || data.week.week !== week || data.publication_status !== 'candidate_only' ||
    (data.verification_status !== 'complete_manifest' && data.verification_status !== 'legacy_without_manifest') ||
    (data.verification_status === 'complete_manifest' ? (!data.manifest || !Array.isArray(data.manifest.players) || !Array.isArray(data.manifest.results)) : data.manifest !== null)) {
    throw new Error('Ranking inputs do not match the requested scope or verification status.')
  }
  return data
}

/** Derived initial-ranking path: server alone supplies roster, policy and tie-break tokens. */
function initialRankingRoot(runId: string, branchId: string): string {
  return `/admin/runs/${encodeURIComponent(runId)}/branches/${encodeURIComponent(branchId)}/ranking-candidates`
}

export async function previewRunDerivedInitialRanking(
  runId: string, branchId: string,
  payload: import('./runInitialRankingSetup').DerivedInitialRankingIntent,
  bestN: number
): Promise<import('./rankingCandidates').RankingPreparationPreview> {
  const data = await request<import('./rankingCandidates').RankingPreparationPreview>(
    `${initialRankingRoot(runId, branchId)}/prepare/initial/derived/preview`,
    { method: 'POST', body: JSON.stringify(payload) }
  )
  if (!importDerivedInitialPreviewGuard(runId, branchId, payload, bestN, data))
    throw new Error('Initial ranking preview does not match the selected Run, Branch, command, Week 1 or Best N.')
  return data
}

function importDerivedInitialPreviewGuard(
  runId: string, branchId: string,
  payload: import('./runInitialRankingSetup').DerivedInitialRankingIntent,
  bestN: number, data: import('./rankingCandidates').RankingPreparationPreview
): boolean {
  return data.preview_only === true &&
    /^[a-f0-9]{64}$/.test(data.request_fingerprint) &&
    data.candidate?.publication_status === 'candidate_only' &&
    /^[a-f0-9]{64}$/.test(data.candidate.fingerprint) &&
    data.candidate.command_ids.includes(payload.command_id) &&
    data.candidate.snapshot.run_id === runId &&
    data.candidate.snapshot.branch_id === branchId &&
    data.candidate.snapshot.week.season_index === 0 &&
    data.candidate.snapshot.week.week === 1 &&
    data.candidate.snapshot.policy.best_n === bestN
}

export async function confirmRunDerivedInitialRanking(
  runId: string, branchId: string,
  payload: import('./runInitialRankingSetup').DerivedInitialRankingIntent,
  preview: import('./rankingCandidates').RankingPreparationPreview,
  bestN: number
): Promise<import('./rankingCandidates').RankingCandidateDetail> {
  if (!importDerivedInitialPreviewGuard(runId, branchId, payload, bestN, preview))
    throw new Error('Reviewed initial ranking is no longer valid.')
  const result = await request<import('./rankingCandidates').RankingCandidateDetail>(
    `${initialRankingRoot(runId, branchId)}/prepare/initial/derived`, {
      method: 'POST',
      headers: {
        'X-Ranking-Preview-Fingerprint': preview.candidate.fingerprint,
        'X-Ranking-Preview-Request': preview.request_fingerprint
      },
      body: JSON.stringify(payload)
    }
  )
  if (result.fingerprint !== preview.candidate.fingerprint ||
    result.snapshot.policy.best_n !== bestN ||
    result.snapshot.run_id !== runId ||
    result.snapshot.branch_id !== branchId ||
    result.snapshot.week.season_index !== 0 ||
    result.snapshot.week.week !== 1 ||
    !result.command_ids.includes(payload.command_id) ||
    result.publication_status !== 'candidate_only')
    throw new Error('Confirmed ranking differs from the reviewed candidate.')
  return result
}

export async function saveRunDerivedInitialRankingRevision(
  runId: string, branchId: string, expectedDraftVersion: number, expectedRankingFingerprint: string
): Promise<import('./runPackageSetup').RunWorkingDraftSaved> {
  if (!/^[a-f0-9]{64}$/.test(expectedRankingFingerprint) || !Number.isInteger(expectedDraftVersion))
    throw new Error('Invalid ranking Save preflight.')
  const saved = await request<import('./runPackageSetup').RunWorkingDraftSaved>(
    `${initialRankingRoot(runId, branchId)}/save`,
    { method: 'POST', body: JSON.stringify({
      expected_draft_version: expectedDraftVersion,
      expected_ranking_fingerprint: expectedRankingFingerprint
    }) }
  )
  if (saved.run_id !== runId || saved.branch_id !== branchId ||
    saved.working_draft?.run_id !== runId ||
    saved.working_draft?.branch_id !== branchId ||
    saved.working_draft?.status !== 'clean' ||
    !saved.saved_revision?.revision_id ||
    saved.working_draft.base_saved_revision_id !== saved.saved_revision.revision_id)
    throw new Error('Ranking Save returned a mismatched or incomplete Run/Branch Saved Revision.')
  return saved
}

/** Publish only the exact reviewed canonical Week-1 ranking candidate. */
export async function publishRunInitialRanking(
  runId: string, branchId: string, expectedFingerprint: string
): Promise<import('./runInitialRankingPublication').InitialRankingPublication> {
  if (!/^[a-f0-9]{64}$/.test(expectedFingerprint)) {
    throw new Error('A valid initial ranking fingerprint is required for publication.')
  }
  const data = await request<import('./runInitialRankingPublication').InitialRankingPublication>(
    `/admin/runs/${encodeURIComponent(runId)}/branches/${encodeURIComponent(branchId)}/ranking-candidates/publish-initial`, {
      method: 'POST', body: JSON.stringify({ expected_ranking_fingerprint: expectedFingerprint })
    }
  )
  if (!(
    data.schema_version === 'initial_official_ranking_publication.v1' &&
    data.run_id === runId && data.branch_id === branchId &&
    data.week?.season_index === 0 && data.week.week === 1 &&
    data.ranking_fingerprint === expectedFingerprint &&
    typeof data.exact_retry === 'boolean'
  )) throw new Error('Initial ranking publication response does not match reviewed Run/Branch and candidate.')
  return data
}

export interface RankingSavePreview {
  run_id: string; branch_id: string; ranking_fingerprint: string; saved_head_revision_id: string;
  draft_version: number; has_unsaved_changes: boolean; can_save: boolean;
}
export async function previewRankingSave(runId: string, branchId: string): Promise<RankingSavePreview> {
  const data = await request<RankingSavePreview>(`/admin/runs/${encodeURIComponent(runId)}/branches/${encodeURIComponent(branchId)}/ranking-candidates/save/preview`)
  if (data.run_id !== runId || data.branch_id !== branchId) throw new Error('Ranking Save scope mismatch.')
  return data
}
export async function saveRankingPreparation(runId: string, branchId: string, preview: RankingSavePreview): Promise<unknown> {
  return request(`/admin/runs/${encodeURIComponent(runId)}/branches/${encodeURIComponent(branchId)}/ranking-candidates/save`, {
    method: 'POST', body: JSON.stringify({ expected_draft_version: preview.draft_version, expected_ranking_fingerprint: preview.ranking_fingerprint })
  })
}

export async function previewRankingCommand(runId: string, branchId: string, command: import('./rankingCandidates').RankingPreparationCommand): Promise<import('./rankingCandidates').RankingPreparationPreview> {
  const kind = 'context' in command ? 'week' : 'initial'
  const data = await request<import('./rankingCandidates').RankingPreparationPreview>(`/admin/runs/${encodeURIComponent(runId)}/branches/${encodeURIComponent(branchId)}/ranking-candidates/prepare/${kind}/preview`, {method:'POST',body:JSON.stringify(command)})
  if (data.preview_only !== true || !/^[0-9a-f]{64}$/.test(data.request_fingerprint)) throw new Error('Invalid preparation preview.')
  verifyPreparationCandidate(runId, branchId, command, data.candidate)
  return data
}

function verifyPreparationCandidate(runId: string, branchId: string, command: import('./rankingCandidates').RankingPreparationCommand, data: import('./rankingCandidates').RankingCandidateDetail) {
  const context = 'context' in command ? command.context : command
  if (data.publication_status !== 'candidate_only' || data.snapshot.run_id !== runId || data.snapshot.branch_id !== branchId ||
      data.snapshot.week.season_index !== context.target_week.season_index || data.snapshot.week.week !== context.target_week.week ||
      !/^[0-9a-f]{64}$/.test(data.fingerprint) || !data.command_ids.includes(command.command_id)) throw new Error('Prepared ranking does not match the requested scope, week or command.')
}

export async function confirmRankingCommand(runId: string, branchId: string, command: import('./rankingCandidates').RankingPreparationCommand, preview: import('./rankingCandidates').RankingPreparationPreview): Promise<import('./rankingCandidates').RankingCandidateDetail> {
  const kind = 'context' in command ? 'week' : 'initial'
  const data = await request<import('./rankingCandidates').RankingCandidateDetail>(`/admin/runs/${encodeURIComponent(runId)}/branches/${encodeURIComponent(branchId)}/ranking-candidates/prepare/${kind}`, {method:'POST',body:JSON.stringify(command),headers:{'Content-Type':'application/json','X-Ranking-Preview-Fingerprint':preview.candidate.fingerprint,'X-Ranking-Preview-Request':preview.request_fingerprint}})
  verifyPreparationCandidate(runId, branchId, command, data)
  if (data.fingerprint !== preview.candidate.fingerprint) throw new Error('Prepared ranking differs from the reviewed preview.')
  return data
}


export async function runMatchTestLab(payload: MatchLabRequest): Promise<MatchLabResult> {
  return request<MatchLabResult>('/admin/labs/match/run', {
    method: 'POST',
    body: JSON.stringify(payload)
  })
}


export async function getMatchLabBuiltInScenarios(): Promise<import('./types').BuiltInMatchLabScenario[]> {
  return request<import('./types').BuiltInMatchLabScenario[]>('/admin/labs/match/scenarios')
}

export async function getMatchLabSessions(): Promise<import('./types').MatchLabSession[]> {
  return request<import('./types').MatchLabSession[]>('/admin/labs/match/sessions')
}

export async function createMatchLabSession(
  payload: import('./types').MatchLabSessionCreateRequest
): Promise<import('./types').MatchLabSession> {
  return request<import('./types').MatchLabSession>('/admin/labs/match/sessions', {
    method: 'POST',
    body: JSON.stringify(payload)
  })
}

export async function updateMatchLabSession(
  sessionId: string,
  payload: import('./types').MatchLabSessionUpdateRequest
): Promise<import('./types').MatchLabSession> {
  return request<import('./types').MatchLabSession>(`/admin/labs/match/sessions/${encodeURIComponent(sessionId)}`, {
    method: 'PUT',
    body: JSON.stringify(payload)
  })
}

export async function runMatchLabSession(
  sessionId: string,
  payload: import('./types').MatchLabSessionRunRequest
): Promise<MatchLabResult> {
  return request<MatchLabResult>(`/admin/labs/match/sessions/${encodeURIComponent(sessionId)}/run`, {
    method: 'POST',
    body: JSON.stringify(payload)
  })
}


export async function importMatchLabSavedRevisionPlayer(
  sessionId: string,
  payload: import('./types').MatchLabSavedRevisionPlayerImportRequest
): Promise<import('./types').MatchLabSession> {
  return request<import('./types').MatchLabSession>(
    `/admin/labs/match/sessions/${encodeURIComponent(sessionId)}/import-saved-revision-player`,
    { method: 'POST', body: JSON.stringify(payload) }
  )
}


export async function getPlayerLabBuiltInScenarios(): Promise<import('./types').BuiltInPlayerLabScenario[]> {
  return request<import('./types').BuiltInPlayerLabScenario[]>('/admin/labs/player/scenarios')
}

export async function runPlayerTestLab(
  payload: import('./types').PlayerLabRequest
): Promise<import('./types').PlayerLabResult> {
  return request<import('./types').PlayerLabResult>('/admin/labs/player/run', {
    method: 'POST',
    body: JSON.stringify(payload)
  })
}


export async function getTournamentLabBuiltInScenarios(): Promise<import('./types').BuiltInTournamentLabScenario[]> {
  return request<import('./types').BuiltInTournamentLabScenario[]>('/admin/labs/tournament/scenarios')
}

export async function inspectTournamentLabScenario(
  scenario: import('./types').TournamentLabScenario
): Promise<import('./types').TournamentLabCompatibility> {
  return request<import('./types').TournamentLabCompatibility>('/admin/labs/tournament/inspect', {
    method: 'POST',
    body: JSON.stringify(scenario)
  })
}

export async function runTournamentTestLab(
  payload: import('./types').TournamentLabRequest
): Promise<import('./types').TournamentLabResult> {
  return request<import('./types').TournamentLabResult>('/admin/labs/tournament/run', {
    method: 'POST',
    body: JSON.stringify(payload)
  })
}


export async function getTournamentLabSessions(): Promise<import('./types').TournamentLabSession[]> {
  return request<import('./types').TournamentLabSession[]>('/admin/labs/tournament/sessions')
}

export async function createTournamentLabSession(
  payload: import('./types').TournamentLabSessionCreateRequest
): Promise<import('./types').TournamentLabSession> {
  return request<import('./types').TournamentLabSession>('/admin/labs/tournament/sessions', {
    method: 'POST',
    body: JSON.stringify(payload)
  })
}

export async function copySavedRevisionTournamentToLab(
  payload: import('./types').TournamentLabSavedRevisionCopyRequest
): Promise<import('./types').TournamentLabSession> {
  return request<import('./types').TournamentLabSession>(
    '/admin/labs/tournament/sessions/copy-saved-revision',
    { method: 'POST', body: JSON.stringify(payload) }
  )
}

export async function previewTournamentLabRunDraft(
  sessionId: string,
  payload: import('./types').TournamentLabRunDraftPreviewRequest
): Promise<import('./types').TournamentLabRunDraftPreview> {
  return request<import('./types').TournamentLabRunDraftPreview>(
    `/admin/labs/tournament/sessions/${encodeURIComponent(sessionId)}/run-draft-preview`,
    { method: 'POST', body: JSON.stringify(payload) }
  )
}

export async function applyTournamentLabRunDraft(
  sessionId: string,
  payload: import('./types').TournamentLabRunDraftApplyRequest
): Promise<import('./types').TournamentLabRunDraftApplyResult> {
  return request<import('./types').TournamentLabRunDraftApplyResult>(
    `/admin/labs/tournament/sessions/${encodeURIComponent(sessionId)}/run-draft-apply`,
    { method: 'POST', body: JSON.stringify(payload) }
  )
}

export async function updateTournamentLabSession(
  sessionId: string,
  payload: import('./types').TournamentLabSessionUpdateRequest
): Promise<import('./types').TournamentLabSession> {
  return request<import('./types').TournamentLabSession>(
    `/admin/labs/tournament/sessions/${encodeURIComponent(sessionId)}`,
    { method: 'PUT', body: JSON.stringify(payload) }
  )
}

export async function runTournamentLabSession(
  sessionId: string,
  payload: import('./types').TournamentLabSessionRunRequest
): Promise<import('./types').TournamentLabResult> {
  return request<import('./types').TournamentLabResult>(
    `/admin/labs/tournament/sessions/${encodeURIComponent(sessionId)}/run`,
    { method: 'POST', body: JSON.stringify(payload) }
  )
}

const populationComparisonRoot = '/admin/labs/player/population-comparisons'
function assertInitialPopulationIdentity(data: import('./initialPopulationComparison').PopulationComparison): void {
  const worlds = data.request.world_ids
  if (data.schema_version !== 'player_lab_initial_population_comparison.v1' ||
      worlds.length !== 2 || new Set(worlds).size !== 2 ||
      !worlds.every(world => world === 'fifa_earth' || world === 'atp_earth') ||
      data.sources.length !== 2 || data.aggregates.length !== 2 ||
      !worlds.every(world => data.sources.filter(source => source.world_id === world).length === 1 &&
        data.aggregates.filter(aggregate => aggregate.world_id === world).length === 1) ||
      data.runs.length !== worlds.length * data.request.seeds.length ||
      !worlds.every(world => data.request.seeds.every(seed => data.runs.filter(run =>
        run.world_id === world && run.seed === seed && run.summary.player_count === data.request.player_count).length === 1))) {
    throw new Error('Saved population comparison identity mismatch.')
  }
}
export async function runInitialPopulationComparison(payload: import('./initialPopulationComparison').PopulationRequest): Promise<import('./initialPopulationComparison').PopulationComparison> {
  const data = await request<import('./initialPopulationComparison').PopulationComparison>(populationComparisonRoot, {method: 'POST', body: JSON.stringify(payload)})
  assertInitialPopulationIdentity(data)
  const season = `${Number(payload.season.split('/')[0])}/${Number(payload.season.split('/')[0]) + 1}`
  if (JSON.stringify(data.request.world_ids) !== JSON.stringify(payload.world_ids) || data.request.season !== season ||
      data.request.player_count !== payload.player_count || JSON.stringify(data.request.seeds) !== JSON.stringify(payload.seeds)) {
    throw new Error('Generated population comparison differs from requested inputs.')
  }
  return data
}
export async function listInitialPopulationComparisons(): Promise<import('./initialPopulationComparison').PopulationSessionList> {
  return request(populationComparisonRoot)
}
export async function getInitialPopulationComparison(sessionId: string): Promise<import('./initialPopulationComparison').PopulationComparison> {
  const data = await request<import('./initialPopulationComparison').PopulationComparison>(populationComparisonRoot + '/' + encodeURIComponent(sessionId))
  assertInitialPopulationIdentity(data)
  if (data.session_id !== sessionId) throw new Error('Saved population comparison identity mismatch.')
  return data
}
export async function getInitialPopulationPlayers(sessionId: string, worldId: string, seed: number, expectedFingerprint?: string): Promise<import('./initialPopulationComparison').PopulationPlayers> {
  const data = await request<import('./initialPopulationComparison').PopulationPlayers>(populationComparisonRoot + '/' + encodeURIComponent(sessionId) + '/players/' + encodeURIComponent(worldId) + '/' + seed)
  if (data.session_id !== sessionId || data.world_id !== worldId || data.seed !== seed ||
      (expectedFingerprint != null && data.gameplay_fingerprint !== expectedFingerprint)) throw new Error('Saved population identity mismatch.')
  return data
}
export function initialPopulationExportUrl(sessionId: string, format: 'json' | 'csv'): string {
  return API_BASE + populationComparisonRoot + '/' + encodeURIComponent(sessionId) + '/export?format=' + format
}


/** Read-only, Saved Revision scoped; never falls back to legacy Run or Viewer Branch. */
export async function getRunHomeActivity(
  runId: string, branchId: string
): Promise<import('./types').RunHomeActivity> {
  const data = await request<import('./types').RunHomeActivity>(
    `/admin/runs/${encodeURIComponent(runId)}/branches/${encodeURIComponent(branchId)}/home-activity`
  )
  if (
    data.schema_version !== 'run_home_activity.v1' ||
    data.run_id !== runId || data.branch_id !== branchId ||
    data.source !== 'selected_branch_saved_revision' ||
    !data.saved_revision_id?.trim() ||
    !['empty','ready','unpositioned'].includes(data.calendar_status) ||
    !['empty','ready'].includes(data.result_status) ||
    data.ranking_changes_status !== 'unsupported' ||
    !Array.isArray(data.upcoming) || !Array.isArray(data.recent_results) ||
    data.upcoming.some(event => !event.event_id || event.season_index < 0 || event.season_index > 49 || event.week < 1 || event.week > 61) ||
    data.recent_results.some(event => !event.event_id || !event.champion_player_id || !event.finalist_player_id)
  ) throw new Error('Home activity does not belong to the selected Run / Branch or is invalid.')
  return data
}


/** Fail-closed saved ranking movement read, always scoped to the selected Branch. */
export async function getRunHomeRankingChanges(
  runId: string, branchId: string
): Promise<import('./types').RunHomeRankingChanges> {
  const data = await request<import('./types').RunHomeRankingChanges>(
    `/admin/runs/${encodeURIComponent(runId)}/branches/${encodeURIComponent(branchId)}/home-ranking-changes`
  )
  if (
    data.schema_version !== 'run_home_ranking_changes.v1' ||
    data.run_id !== runId || data.branch_id !== branchId ||
    data.source !== 'selected_branch_saved_revision' ||
    !data.saved_revision_id?.trim() ||
    !['unpublished', 'first_publication', 'ready'].includes(data.status) ||
    !Array.isArray(data.changes) ||
    !Number.isInteger(data.total_change_count) || data.total_change_count < data.changes.length ||
    data.changes.length > 10 ||
    data.changes.some(change => !change.player_id || !['up','down','entered','exited','points_only'].includes(change.movement))
  ) throw new Error('Home ranking movement does not match the selected Run / Branch.')
  return data
}

/** Bounded, explicit player IDs; no Viewer/legacy/live roster fallbacks. */
export async function getSavedHomePlayerIdentities(
  runId: string, branchId: string, playerIds: string[]
): Promise<import('./types').SavedHomePlayerIdentities> {
  if (playerIds.length < 1 || playerIds.length > 25 ||
      new Set(playerIds).size !== playerIds.length ||
      playerIds.some(id => !id || id.length > 128 || id.includes(',') || id.trim() !== id)) {
    throw new Error('Player identity lookup requires 1–25 distinct valid IDs.')
  }
  const data = await request<import('./types').SavedHomePlayerIdentities>(
    `/admin/runs/${encodeURIComponent(runId)}/branches/${encodeURIComponent(branchId)}/home-player-identities?player_ids=${encodeURIComponent(playerIds.join(','))}`
  )
  const requested = new Set(playerIds)
  const all = [...(data.players ?? []).map(player => player.player_id), ...(data.unresolved_ids ?? [])]
  if (data.schema_version !== 'run_home_player_identities.v1' ||
      data.run_id !== runId || data.branch_id !== branchId ||
      data.source !== 'selected_branch_saved_revision' || !data.saved_revision_id?.trim() ||
      !['ready', 'partial', 'unavailable'].includes(data.status) ||
      !Array.isArray(data.players) || !Array.isArray(data.unresolved_ids) ||
      !Array.isArray(data.requested_ids) ||
      data.requested_ids.join('\x1f') !== playerIds.join('\x1f') ||
      all.length !== requested.size || new Set(all).size !== requested.size ||
      all.some(id => !requested.has(id)) ||
      data.players.some(player => !player.display_name?.trim() ||
        !/^[A-Za-z]{3}$/.test(player.country_code) ||
        !['initial_world', 'run_prospect'].includes(player.identity_source))) {
    throw new Error('Saved identity response does not match selected Run/Branch or requested IDs.')
  }
  return data
}

/** Canonical present-only inventory; caller must provide the selected Saved HEAD. */
export async function getSavedPlayersInventory(
  runId: string, branchId: string, savedHead: string,
  filters: { search: string; country_code: string; status_filter: string;
    include_prepared: boolean; offset: number; limit: number }
): Promise<import('./types').SavedPlayersInventory> {
  if (!runId || !branchId || !savedHead || !Number.isInteger(filters.offset) ||
      filters.offset < 0 || !Number.isInteger(filters.limit) ||
      filters.limit < 1 || filters.limit > 100) {
    throw new Error('Invalid saved players context or page.')
  }
  const params = new URLSearchParams({
    search: filters.search, country_code: filters.country_code,
    status_filter: filters.status_filter,
    include_prepared: String(filters.include_prepared),
    offset: String(filters.offset), limit: String(filters.limit),
  })
  const data = await request<import('./types').SavedPlayersInventory>(
    `/admin/runs/${encodeURIComponent(runId)}/branches/${encodeURIComponent(branchId)}/saved-players?${params.toString()}`
  )
  if (data.schema_version !== 'saved_players_inventory.v1' ||
      data.run_id !== runId || data.branch_id !== branchId ||
      data.saved_revision_id !== savedHead ||
      data.source !== 'selected_branch_saved_revision' || data.time_context !== 'present' ||
      data.search !== filters.search || data.country_code !== filters.country_code ||
      data.status_filter !== filters.status_filter ||
      data.include_prepared !== filters.include_prepared ||
      data.offset !== filters.offset || data.limit !== filters.limit ||
      !Number.isInteger(data.total) || data.total < 0 ||
      data.has_more !== (filters.offset + filters.limit < data.total) ||
      !Array.isArray(data.players) || data.players.length > filters.limit ||
      new Set(data.players.map(row => row.player_id)).size !== data.players.length ||
      data.players.some(row => !row.player_id || !row.display_name?.trim() ||
        !/^[A-Za-z]{3}$/.test(row.country_code) ||
        !['initial_world', 'run_prospect'].includes(row.identity_source) ||
        (!filters.include_prepared && row.identity_source === 'run_prospect') ||
        !['unpublished', 'ranked', 'unranked'].includes(row.ranking_status) ||
        (row.ranking_status === 'ranked' ? !Number.isInteger(row.rank) || row.rank! < 1 : row.rank !== null) ||
        (row.ranking_status === 'unpublished' && data.ranking_week_ordinal !== null) ||
        (row.age != null && (!Number.isInteger(row.age) || row.age < 0)) ||
        (row.ovr != null && (!Number.isInteger(row.ovr) || row.ovr < 0 || row.ovr > 200)) ||
        (row.potential_ovr != null && (!Number.isInteger(row.potential_ovr) || row.potential_ovr < 0 || row.potential_ovr > 200)))) {
    throw new Error('Canonical Saved Players inventory has mismatched revision or invalid facts.')
  }
  return data
}

/** Strictly read-only saved Branch sporting summary, never legacy/Viewer/live. */
export async function getSavedPlayerProfile(
  runId: string, branchId: string, playerId: string
): Promise<import('./types').SavedPlayerProfile> {
  if (!playerId || playerId.length > 128 || playerId.trim() !== playerId) {
    throw new Error('Invalid saved player identifier.')
  }
  const data = await request<import('./types').SavedPlayerProfile>(
    `/admin/runs/${encodeURIComponent(runId)}/branches/${encodeURIComponent(branchId)}/player-profiles/${encodeURIComponent(playerId)}`
  )
  const ranked = data.ranking_status === 'ranked'
  if (data.schema_version !== 'saved_player_profile.v1' ||
      data.run_id !== runId || data.branch_id !== branchId || data.player_id !== playerId ||
      data.source !== 'selected_branch_saved_revision' || !data.saved_revision_id?.trim() ||
      !['identity_unavailable', 'unpublished', 'ranked', 'unranked'].includes(data.ranking_status) ||
      (ranked && (!Number.isInteger(data.rank) || data.rank! < 1 ||
        !Number.isInteger(data.points) || data.points! < 0 || data.ranking_week_ordinal == null)) ||
      (!ranked && (data.rank != null || data.points != null)) ||
      (data.identity == null) !== (data.ranking_status === 'identity_unavailable') ||
      (data.identity != null && (data.identity.player_id !== playerId ||
        !data.identity.display_name?.trim() || !/^[A-Za-z]{3}$/.test(data.identity.country_code))) ||
      !Number.isInteger(data.titles) || data.titles < 0 ||
      !Number.isInteger(data.final_appearances) || data.final_appearances < data.titles ||
      !Number.isInteger(data.total_tournament_results) ||
      data.total_tournament_results !== data.final_appearances ||
      !Array.isArray(data.tournament_results) || data.tournament_results.length > 10 ||
      data.tournament_results.some(row => !row.event_id || !row.event_name ||
        !['champion', 'runner_up'].includes(row.finish) || row.week < 1 || row.week > 61)) {
    throw new Error('Saved player profile does not match selected Branch or has invalid sporting facts.')
  }
  return data
}

/** Immutable saved tournament match page; never consult current live/Viewer state. */
export async function getSavedPlayerMatchHistory(
  runId: string, branchId: string, playerId: string,
  seasonIndex: number | null = null, offset = 0, limit = 20
): Promise<import('./types').SavedPlayerMatchHistory> {
  if (!playerId || playerId.length > 128 || playerId.trim() !== playerId ||
      (seasonIndex !== null && (!Number.isInteger(seasonIndex) || seasonIndex < 0 || seasonIndex > 49)) ||
      !Number.isInteger(offset) || offset < 0 || !Number.isInteger(limit) || limit < 1 || limit > 20) {
    throw new Error('Invalid saved player match history request.')
  }
  const search = new URLSearchParams({ offset: String(offset), limit: String(limit) })
  if (seasonIndex !== null) search.set('season_index', String(seasonIndex))
  const data = await request<import('./types').SavedPlayerMatchHistory>(
    `/admin/runs/${encodeURIComponent(runId)}/branches/${encodeURIComponent(branchId)}/player-profiles/${encodeURIComponent(playerId)}/matches?${search}`
  )
  if (data.schema_version !== 'saved_player_match_history.v1' ||
      data.run_id !== runId || data.branch_id !== branchId ||
      data.player_id !== playerId || !data.saved_revision_id?.trim() ||
      data.source !== 'selected_branch_saved_revision' ||
      !['ready', 'identity_unavailable'].includes(data.status) ||
      data.season_index !== seasonIndex || data.offset !== offset || data.limit !== limit ||
      !Array.isArray(data.matches) || data.matches.length > limit ||
      !Array.isArray(data.available_seasons) ||
      data.available_seasons.some(v => !Number.isInteger(v) || v < 0 || v > 49) ||
      ![data.total_results, data.played_wins, data.played_losses, data.walkovers,
        data.career_played_wins, data.career_played_losses, data.career_walkovers]
        .every(v => Number.isInteger(v) && v >= 0) ||
      data.total_results < offset + data.matches.length && data.matches.length > 0 ||
      data.matches.some(m => !m.event_id || !m.match_id || !m.opponent_player_id ||
        !m.event_name || !m.scoreline || !['win', 'loss'].includes(m.outcome) ||
        !['played', 'walkover'].includes(m.completion) ||
        !['main', 'qualification', 'group', 'knockout'].includes(m.draw_type) ||
        m.week < 1 || m.week > 61 ||
        (seasonIndex !== null && m.season_index !== seasonIndex)) ||
      typeof data.has_more !== 'boolean' ||
      data.has_more !== (offset + limit < data.total_results)) {
    throw new Error('Saved match history response does not match selected Run/Branch or page.')
  }
  return data
}

/** Saved canonical match result + optional archived replay frames (no live fallback). */
export async function getSavedPlayerMatchDetail(
  runId: string, branchId: string, playerId: string, eventId: string, matchId: string,
  offset = 0, limit = 25
): Promise<import('./types').SavedPlayerMatchDetail> {
  if ([playerId, eventId, matchId].some(id => !id || id.length > 128 || id.trim() !== id) ||
    !Number.isInteger(offset) || offset < 0 ||
    !Number.isInteger(limit) || limit < 1 || limit > 25) {
    throw new Error('Invalid saved match detail request.')
  }
  const query = new URLSearchParams({ offset: String(offset), limit: String(limit) })
  const data = await request<import('./types').SavedPlayerMatchDetail>(
    `/admin/runs/${encodeURIComponent(runId)}/branches/${encodeURIComponent(branchId)}/player-profiles/${encodeURIComponent(playerId)}/matches/${encodeURIComponent(eventId)}/${encodeURIComponent(matchId)}?${query}`
  )
  if (data.schema_version !== 'saved_player_match_detail.v1' ||
    data.run_id !== runId || data.branch_id !== branchId || data.player_id !== playerId ||
    !data.saved_revision_id?.trim() || data.source !== 'selected_branch_saved_revision' ||
    data.match?.event_id !== eventId || data.match?.match_id !== matchId ||
    data.offset !== offset || data.limit !== limit ||
    ![data.winner_player_id, data.loser_player_id].includes(playerId) ||
    data.winner_player_id === data.loser_player_id ||
    !['available', 'unavailable'].includes(data.replay_status) ||
    !Array.isArray(data.rallies) || data.rallies.length > limit ||
    !Number.isInteger(data.total_rallies) || data.total_rallies < 0 ||
    typeof data.has_more !== 'boolean' ||
    data.has_more !== (data.replay_status === 'available' && offset + limit < data.total_rallies) ||
    (data.replay_status === 'unavailable' && (data.total_rallies !== 0 ||
      data.rallies.length > 0 || data.player_a_id !== null || data.player_b_id !== null)) ||
    (data.replay_status === 'available' && (!data.player_a_id || !data.player_b_id ||
      data.player_a_id === data.player_b_id || (offset < data.total_rallies &&
        data.rallies.length !== Math.min(limit, data.total_rallies - offset)))) ||
    data.rallies.some((r, i) => r.rally_index !== offset + i + 1 ||
      r.set_number < 1 || !r.server_player_id || r.score_a_before < 0 ||
      r.score_b_before < 0 || r.score_a_after < 0 || r.score_b_after < 0)) {
    throw new Error('Saved replay is not consistent with the selected Branch match.')
  }
  return data
}

/** Country Records never use live Package drafts, Viewer, or a different Saved HEAD. */
export async function getRunCountryRecords(
  runId:string,branchId:string,countryCode:string,revisionId:string
):Promise<import('./types').RunCountryRecords>{
  if(!/^[A-Z]{3}$/.test(countryCode)||!revisionId.trim())
    throw new Error('Country Records requires a country and an exact Saved Revision')
  const data=await request<import('./types').RunCountryRecords>(
    '/admin/runs/'+encodeURIComponent(runId)+'/branches/'+encodeURIComponent(branchId)+
    '/country-records/'+encodeURIComponent(countryCode)+'?revision_id='+encodeURIComponent(revisionId)
  )
  const good=(row:import('./types').RunCountryRecordResult)=>Boolean(
    row.event_id&&row.event_name&&row.season&&row.host_country&&
    row.champion_player_id&&row.champion_name&&/^[A-Z]{3}$/.test(row.champion_country)&&
    row.finalist_player_id&&row.finalist_name&&/^[A-Z]{3}$/.test(row.finalist_country)&&
    Number.isInteger(row.season_week)&&row.season_week>=1&&row.season_week<=61)
  if(data.schema_version!=='run_country_records.v1'||data.source!=='reachable_saved_revision'||
    data.run_id!==runId||data.branch_id!==branchId||
    data.saved_revision_id!==revisionId||!data.revision_branch_id||
    data.country_code!==countryCode||!['empty','ready'].includes(data.calendar_status)||
    ![data.published_result_count,data.country_titles,data.country_finalists,
      data.hosted_published_results].every(n=>Number.isSafeInteger(n)&&n>=0)||
    !Array.isArray(data.player_results)||!Array.isArray(data.hosted_results)||
    data.country_titles>data.player_results.length||
    data.country_finalists>data.player_results.length||
    data.hosted_published_results!==data.hosted_results.length||
    data.player_results.some(x=>!good(x)||
      (x.champion_country!==countryCode&&x.finalist_country!==countryCode))||
    data.hosted_results.some(x=>!good(x)||x.host_country!==countryCode))
    throw new Error('Country Records scope or published result evidence is invalid')
  return data
}

/** Filters and paging are applied by the Saved Revision backend before slicing rows. */
export async function getCountrySavedMatchRecords(
  runId:string,branchId:string,countryCode:string,revisionId:string,
  opts:{seasonIndex:number|null;resultKind:import('./types').CountryMatchResultKind;
    outcome:import('./types').CountryMatchOutcome;offset:number;limit:number}
):Promise<import('./types').CountrySavedMatchRecords>{
  if(!runId||!branchId||!revisionId.trim()||!/^[A-Z]{3}$/.test(countryCode)||
    (opts.seasonIndex!==null&&(!Number.isInteger(opts.seasonIndex)||opts.seasonIndex<0||opts.seasonIndex>49))||
    !['all','played','walkover'].includes(opts.resultKind)||
    !['all','win','loss'].includes(opts.outcome)||
    !Number.isSafeInteger(opts.offset)||opts.offset<0||
    !Number.isSafeInteger(opts.limit)||opts.limit<1||opts.limit>50)
    throw new Error('Country saved match request scope and filters are invalid')
  const args=new URLSearchParams({
    revision_id:revisionId,offset:String(opts.offset),limit:String(opts.limit),
    result_kind:opts.resultKind,outcome:opts.outcome
  })
  if(opts.seasonIndex!==null)args.set('season_index',String(opts.seasonIndex))
  const data=await request<import('./types').CountrySavedMatchRecords>(
    '/admin/runs/'+encodeURIComponent(runId)+'/branches/'+encodeURIComponent(branchId)+
    '/country-match-records/'+encodeURIComponent(countryCode)+'?'+args.toString()
  )
  const validCount=(n:number)=>Number.isSafeInteger(n)&&n>=0
  const validCountry=(c:string)=>/^[A-Z]{3}$/.test(c)
  const validMatch=(m:import('./types').CountrySavedMatch)=>Boolean(
    m.event_id&&m.event_name&&m.season&&m.match_id&&m.scoreline.trim()&&
    m.winner_player_id&&m.winner_name&&m.loser_player_id&&m.loser_name&&
    m.winner_player_id!==m.loser_player_id&&validCountry(m.winner_country)&&
    validCountry(m.loser_country)&&validCountry(m.host_country)&&
    (m.winner_country===countryCode||m.loser_country===countryCode)&&
    ['qualification','main','group','knockout'].includes(m.draw_type)&&
    ['played','walkover'].includes(m.completion)&&
    Number.isInteger(m.round_number)&&m.round_number>=1&&
    Number.isInteger(m.season_week)&&m.season_week>=1&&m.season_week<=61&&
    (opts.seasonIndex===null||m.season.startsWith(String(opts.seasonIndex+2000)+'/'))&&
    (opts.resultKind==='all'||m.completion===opts.resultKind)&&
    (opts.outcome==='all'||(opts.outcome==='win'?m.winner_country:m.loser_country)===countryCode))
  const seasonOk=Array.isArray(data.available_seasons)&&
    data.available_seasons.every((s,i)=>Number.isInteger(s)&&s>=0&&s<=49&&
      (i===0||s>data.available_seasons[i-1]))
  const counts=[data.published_event_count,data.total_played_matches,data.total_walkovers,
    data.country_played_wins,data.country_played_losses,data.country_walkover_wins,
    data.country_walkover_losses,data.hosted_played_matches,data.hosted_walkovers,
    data.country_match_count,data.filtered_match_count]
  if(data.schema_version!=='country_saved_match_records.v1'||
    data.source!=='reachable_saved_revision'||data.run_id!==runId||
    data.branch_id!==branchId||!data.revision_branch_id||
    data.saved_revision_id!==revisionId||data.country_code!==countryCode||
    !['empty','ready'].includes(data.calendar_status)||
    data.season_index!==opts.seasonIndex||data.result_kind!==opts.resultKind||
    data.outcome!==opts.outcome||data.offset!==opts.offset||data.limit!==opts.limit||
    counts.some(n=>!validCount(n))||data.filtered_match_count>data.country_match_count||
    data.country_played_wins>data.total_played_matches||
    data.country_played_losses>data.total_played_matches||
    data.country_walkover_wins>data.total_walkovers||
    data.country_walkover_losses>data.total_walkovers||
    data.hosted_played_matches>data.total_played_matches||
    data.hosted_walkovers>data.total_walkovers||
    !seasonOk||!Array.isArray(data.matches)||data.matches.length>opts.limit||
    data.matches.length!==Math.max(0,Math.min(opts.limit,data.filtered_match_count-opts.offset))||
    data.matches.some(m=>!validMatch(m))||
    new Set(data.matches.map(m=>m.event_id+'\\0'+m.match_id)).size!==data.matches.length||
    data.has_more!==(opts.offset+opts.limit<data.filtered_match_count))
    throw new Error('Country matches differ from the selected exact Saved Revision or filters')
  return data
}

/** Aggregates a whole immutable sporting period before paging holder evidence. */
export async function getCountryMatchRecordHighlights(
  runId:string,branchId:string,countryCode:string,revisionId:string,
  opts:{fromSeason:number;fromWeek:number;toSeason:number;toWeek:number;
    recordKey:import('./types').CountryMatchRecordKey|null;offset:number;limit:number}
):Promise<import('./types').CountryMatchRecordHighlights>{
  const season=(n:number)=>Number.isInteger(n)&&n>=0&&n<=49
  const week=(n:number)=>Number.isInteger(n)&&n>=1&&n<=61
  if(!runId||!branchId||!revisionId.trim()||!/^[A-Z]{3}$/.test(countryCode)||
    !season(opts.fromSeason)||!season(opts.toSeason)||
    !week(opts.fromWeek)||!week(opts.toWeek)||
    opts.fromSeason*61+opts.fromWeek>opts.toSeason*61+opts.toWeek||
    (opts.recordKey!==null&&!['played_wins','played_matches'].includes(opts.recordKey))||
    !Number.isSafeInteger(opts.offset)||opts.offset<0||
    !Number.isSafeInteger(opts.limit)||opts.limit<1||opts.limit>50)
    throw Error('Country match record scope, period or evidence cursor is invalid')
  const q=new URLSearchParams({
    revision_id:revisionId,from_season:String(opts.fromSeason),from_week:String(opts.fromWeek),
    to_season:String(opts.toSeason),to_week:String(opts.toWeek),
    offset:String(opts.offset),limit:String(opts.limit),
  })
  if(opts.recordKey)q.set('record_key',opts.recordKey)
  const data=await request<import('./types').CountryMatchRecordHighlights>(
    '/admin/runs/'+encodeURIComponent(runId)+'/branches/'+encodeURIComponent(branchId)+
    '/country-match-record-highlights/'+encodeURIComponent(countryCode)+'?'+q.toString())
  const keys=['played_wins','played_matches'] as const
  const positive=(n:number)=>Number.isSafeInteger(n)&&n>=0
  const recordValid=(r:import('./types').CountryMatchRecordSummary)=>Boolean(
    keys.includes(r.key)&&positive(r.value)&&Array.isArray(r.holders)&&
    r.holders.every(x=>x.player_id&&x.player_name&&x.value===r.value&&r.value>0)&&
    (r.value>0||r.holders.length===0)&&
    (r.value===0||r.holders.length>0)&&
    new Set(r.holders.map(x=>x.player_id)).size===r.holders.length)
  const evidenceValid=(m:import('./types').CountrySavedMatch)=>Boolean(
    m.event_id&&m.match_id&&m.event_name&&m.scoreline&&
    m.winner_player_id&&m.winner_name&&m.loser_player_id&&m.loser_name&&
    m.winner_country&&m.loser_country&&m.host_country&&
    m.completion==='played'&&(m.winner_country===countryCode||m.loser_country===countryCode)&&
    m.season_week>=1&&m.season_week<=61&&
    Number.isInteger(m.round_number)&&m.round_number>=1&&
    (()=>{const match=/^(20\d{2})\/(20\d{2})$/.exec(m.season)
      if(!match||Number(match[2])!==Number(match[1])+1)return false
      const n=Number(match[1])-2000,time=n*61+m.season_week
      return n>=0&&n<50&&time>=opts.fromSeason*61+opts.fromWeek&&
        time<=opts.toSeason*61+opts.toWeek})())
  const selected=data.records.find(x=>x.key===opts.recordKey)
  const holders=new Set(selected?.holders.map(x=>x.player_id)??[])
  if(data.schema_version!=='country_match_record_highlights.v1'||
    data.source!=='reachable_saved_revision'||data.run_id!==runId||
    data.branch_id!==branchId||!data.revision_branch_id||
    data.saved_revision_id!==revisionId||data.country_code!==countryCode||
    data.from_season!==opts.fromSeason||data.from_week!==opts.fromWeek||
    data.to_season!==opts.toSeason||data.to_week!==opts.toWeek||
    data.selected_record!==opts.recordKey||data.offset!==opts.offset||
    data.limit!==opts.limit||
    ![data.period_country_matches,data.period_played_matches,data.period_walkovers,
      data.evidence_count].every(positive)||
    data.period_country_matches!==data.period_played_matches+data.period_walkovers||
    !Array.isArray(data.records)||data.records.length!==2||
    data.records.some((rec,i)=>rec.key!==keys[i]||!recordValid(rec))||
    !Array.isArray(data.evidence)||data.evidence.length>
      Math.min(opts.limit,Math.max(0,data.evidence_count-opts.offset))||
    data.evidence.length!==Math.max(0,Math.min(opts.limit,data.evidence_count-opts.offset))||
    data.has_more!==(opts.offset+opts.limit<data.evidence_count)||
    (opts.recordKey===null&&(data.evidence_count!==0||data.evidence.length!==0))||
    data.evidence.some(m=>!evidenceValid(m)||
      !(opts.recordKey==='played_wins'?
        m.winner_country===countryCode&&holders.has(m.winner_player_id):
        holders.has(m.winner_player_id)&&m.winner_country===countryCode||
        holders.has(m.loser_player_id)&&m.loser_country===countryCode))||
    new Set(data.evidence.map(m=>m.event_id+'\0'+m.match_id)).size!==data.evidence.length)
    throw Error('Country match record evidence differs from selected Saved Revision and period')
  return data
}

/** Exact-revision player leaderboard; validate rank order, scope and page before display. */
export async function getCountryPlayerStandings(
  runId:string,branchId:string,countryCode:string,revisionId:string,
  offset=0,limit=25
):Promise<import('./types').CountryPlayerStandings>{
  if(!runId||!branchId||!revisionId.trim()||!/^[A-Z]{3}$/.test(countryCode)||
    !Number.isSafeInteger(offset)||offset<0||
    !Number.isSafeInteger(limit)||limit<1||limit>50)
    throw new Error('Country player leaderboard request scope or page is invalid')
  const params=new URLSearchParams({
    revision_id:revisionId,offset:String(offset),limit:String(limit)
  })
  const data=await request<import('./types').CountryPlayerStandings>(
    '/admin/runs/'+encodeURIComponent(runId)+'/branches/'+encodeURIComponent(branchId)+
    '/country-player-standings/'+encodeURIComponent(countryCode)+'?'+params.toString()
  )
  const positive=(v:number)=>Number.isSafeInteger(v)&&v>=0
  const score=(p:import('./types').CountryPlayerStanding)=>[
    -p.titles,-p.final_appearances,-p.played_wins,p.played_losses,p.player_id
  ] as const
  const compare=(a:import('./types').CountryPlayerStanding,
    b:import('./types').CountryPlayerStanding)=>{
    const x=score(a),y=score(b)
    for(let i=0;i<4;i++){
      if(x[i]!==y[i])return (x[i] as number)-(y[i] as number)
    }
    return String(x[4]).localeCompare(String(y[4]),'en')
  }
  const rows=data.players
  const counts=[data.published_event_count,data.country_titles,
    data.country_runner_up_finishes,data.country_played_wins,
    data.country_played_losses,data.country_walkover_wins,
    data.country_walkover_losses,data.total_players]
  if(data.schema_version!=='country_player_standings.v1'||
    data.source!=='reachable_saved_revision'||data.run_id!==runId||
    data.branch_id!==branchId||data.saved_revision_id!==revisionId||
    !data.revision_branch_id||data.country_code!==countryCode||
    !['empty','ready'].includes(data.calendar_status)||
    counts.some(x=>!positive(x))||data.offset!==offset||data.limit!==limit||
    !Array.isArray(rows)||
    rows.length!==Math.max(0,Math.min(limit,data.total_players-offset))||
    data.has_more!==(offset+limit<data.total_players)||
    new Set(rows.map(p=>p.player_id)).size!==rows.length||
    rows.some((p,i)=>p.position!==offset+i+1||!p.player_id||!p.player_name||
      p.country_code!==countryCode||
      [p.titles,p.runner_up_finishes,p.final_appearances,p.played_wins,
        p.played_losses,p.walkover_wins,p.walkover_losses].some(x=>!positive(x))||
      p.final_appearances!==p.titles+p.runner_up_finishes||
      p.titles>data.country_titles||p.runner_up_finishes>data.country_runner_up_finishes||
      p.played_wins>data.country_played_wins||p.played_losses>data.country_played_losses||
      p.walkover_wins>data.country_walkover_wins||p.walkover_losses>data.country_walkover_losses||
      (i>0&&compare(rows[i-1],p)>0)))
    throw new Error('Country player leaderboard differs from selected Saved Revision or order')
  return data
}

/** Immutable, Branch-reachable Saved Revision Tour reads (never Working Draft). */
export function getSavedTourCalendar(
  runId:string,branchId:string,revisionId:string,seasonIndex:number
):Promise<import('./savedTour').SavedTourCalendar>{
  const prefix='/admin/runs/'+encodeURIComponent(runId)+'/branches/'+encodeURIComponent(branchId)
  const params=new URLSearchParams({revision_id:revisionId,season_index:String(seasonIndex)})
  return request(prefix+'/tour/calendar?'+params.toString())
}
export function getSavedTourEdition(
  runId:string,branchId:string,revisionId:string,seasonIndex:number,eventId:string
):Promise<import('./savedTour').SavedTourEdition>{
  const prefix='/admin/runs/'+encodeURIComponent(runId)+'/branches/'+encodeURIComponent(branchId)
  const params=new URLSearchParams({revision_id:revisionId,season_index:String(seasonIndex)})
  return request(prefix+'/tour/editions/'+encodeURIComponent(eventId)+'?'+params.toString())
}

/** Reachable, immutable Saved Revision Edition match; never the current player Saved HEAD. */
export async function getSavedTourMatchDetail(
  runId:string,branchId:string,revisionId:string,seasonIndex:number,
  eventId:string,matchId:string,offset=0,limit=25
):Promise<import('./savedTour').SavedTourMatchDetail>{
  if([runId,branchId,revisionId,eventId,matchId].some(id=>!id||id.length>128||id.trim()!==id)
    ||!Number.isInteger(seasonIndex)||seasonIndex<0||seasonIndex>49
    ||!Number.isInteger(offset)||offset<0
    ||!Number.isInteger(limit)||limit<1||limit>25){
    throw new Error('Invalid historical Edition match request.')
  }
  const q=new URLSearchParams({revision_id:revisionId,season_index:String(seasonIndex),
    offset:String(offset),limit:String(limit)})
  const data=await request<import('./savedTour').SavedTourMatchDetail>(
    '/admin/runs/'+encodeURIComponent(runId)+'/branches/'+encodeURIComponent(branchId)
      +'/tour/editions/'+encodeURIComponent(eventId)+'/matches/'+encodeURIComponent(matchId)
      +'?'+q.toString()
  )
  const {validSavedTourMatchDetail}=await import('./savedTour')
  if(!validSavedTourMatchDetail(data,runId,branchId,revisionId,seasonIndex,eventId,matchId,offset,limit))
    throw new Error('Historical Edition match does not match the selected Saved Revision.')
  return data
}

/** Real Admin season group rules — immutable once adopted. */
export async function getAdminGroupRules(
  runId:string,branchId:string,seasonIndex:number
):Promise<import('./tournamentGroupFormats').TournamentGroupRulesState>{
  const data=await request<import('./tournamentGroupFormats').TournamentGroupRulesState>(
    '/admin/runs/'+encodeURIComponent(runId)+'/branches/'+encodeURIComponent(branchId)
    +'/tournament-group-rules?target_season_index='+seasonIndex
  )
  if(data.schema_version!=='tournament_group_rules_state.v1'||data.run_id!==runId
    ||data.branch_id!==branchId||data.target_season_index!==seasonIndex
    ||(data.effective!==null&&(data.effective.run_id!==runId||data.effective.branch_id!==branchId
      ||data.effective.effective_from_season_index>seasonIndex
      ||![3,5].includes(data.effective.default_match_best_of))))
    throw new Error('Group Rules read does not match the active Run/Branch/season.')
  return data
}
export async function adoptAdminGroupRules(
  runId:string,branchId:string,seasonIndex:number,bestOf:3|5,commandId:string
):Promise<import('./tournamentGroupFormats').TournamentGroupRulesState['effective']>{
  const data=await request<NonNullable<import('./tournamentGroupFormats').TournamentGroupRulesState['effective']>>(
    '/admin/runs/'+encodeURIComponent(runId)+'/branches/'+encodeURIComponent(branchId)
    +'/tournament-group-rules/versions',{
      method:'POST',body:JSON.stringify({
        command_id:commandId,effective_from_season_index:seasonIndex,
        default_match_best_of:bestOf,
      })
    })
  if(data.schema_version!=='tournament_group_rules_policy.v1'
    ||data.run_id!==runId||data.branch_id!==branchId
    ||data.effective_from_season_index!==seasonIndex
    ||data.default_match_best_of!==bestOf
    ||!/^[0-9a-f]{64}$/.test(data.authority_fingerprint))
    throw new Error('Group Rules adoption returned the wrong authority.')
  return data
}
export async function configureAdminPureGroups(
  runId:string,branchId:string,eventId:string,
  payload:import('./tournamentGroupFormats').GroupSetupPayload
):Promise<import('./tournamentGroupFormats').TournamentGroupFormatAuthority>{
  const data=await request<import('./tournamentGroupFormats').TournamentGroupFormatAuthority>(
    '/admin/runs/'+encodeURIComponent(runId)+'/branches/'+encodeURIComponent(branchId)
    +'/tournaments/'+encodeURIComponent(eventId)+'/format/configure',{
      method:'POST',body:JSON.stringify(payload)
    })
  if(data.schema_version!=='tournament_format_authority.v1'||data.run_id!==runId
    ||data.branch_id!==branchId||data.event_id!==eventId
    ||data.configured_by_command_id!==payload.command_id
    ||data.format_kind!=='groups'
    ||data.group_configuration?.group_count!==payload.group_count
    ||data.group_configuration.group_size!==payload.group_size)
    throw new Error('Frozen group Format response has an unexpected scope or configuration.')
  return data
}
/** Immutable hybrid Format submission: inspect every explicit crossing and scope
 * before treating the production response as the adopted authority. */
export async function configureAdminHybridGroups(
  runId:string,branchId:string,eventId:string,
  payload:import('./tournamentGroupFormats').HybridGroupSetupPayload
):Promise<import('./tournamentGroupFormats').TournamentGroupFormatAuthority>{
  const data=await request<import('./tournamentGroupFormats').TournamentGroupFormatAuthority>(
    '/admin/runs/'+encodeURIComponent(runId)+'/branches/'+encodeURIComponent(branchId)
    +'/tournaments/'+encodeURIComponent(eventId)+'/format/configure',{
      method:'POST',body:JSON.stringify(payload)
    })
  const g=data.group_configuration
  if(data.schema_version!=='tournament_format_authority.v1'
    ||data.run_id!==runId||data.branch_id!==branchId||data.event_id!==eventId
    ||data.configured_by_command_id!==payload.command_id
    ||data.format_kind!=='groups_knockout'
    ||!g||g.group_count!==payload.group_count||g.group_size!==payload.group_size
    ||g.advancing_per_group!==payload.advancing_per_group
    ||g.seeded_slots_per_group!==0
    ||!Array.isArray(g.knockout_crossings)
    ||JSON.stringify(g.knockout_crossings)!==JSON.stringify(payload.knockout_crossings))
    throw new Error('Hybrid Format response differs from the reviewed immutable crossing configuration.')
  return data
}
export async function generateAdminGroupTopology(
  runId:string,branchId:string,eventId:string,commandId:string,topologySeed:number,
  formatKind:'groups'|'groups_knockout'='groups'
):Promise<import('./tournamentGroupFormats').TournamentGroupTopologyAuthority>{
  const data=await request<import('./tournamentGroupFormats').TournamentGroupTopologyAuthority>(
    '/admin/runs/'+encodeURIComponent(runId)+'/branches/'+encodeURIComponent(branchId)
    +'/tournaments/'+encodeURIComponent(eventId)+'/format/topology/generate',{
      method:'POST',body:JSON.stringify({command_id:commandId,topology_seed:topologySeed})
    })
  if(data.schema_version!=='tournament_topology_authority.v1'
    ||data.run_id!==runId||data.branch_id!==branchId||data.event_id!==eventId
    ||data.format_kind!==formatKind||data.generated_by_command_id!==commandId
    ||!/^[0-9a-f]{64}$/.test(data.format_authority_fingerprint))
    throw new Error('Group Topology generation returned an unrelated authority.')
  return data
}

/** No implicit qualification or seeding: exact canonical standings are mandatory. */
export async function getAdminHybridKnockoutEntrants(
  runId:string,branchId:string,eventId:string,
  standings:import('./tournamentGroupStandings').CompletedGroupStandings,
):Promise<import('./tournamentHybridKnockout').HybridKnockoutEntrants>{
  const data=await request<import('./tournamentHybridKnockout').HybridKnockoutEntrants>(
    '/admin/runs/'+encodeURIComponent(runId)+'/branches/'+encodeURIComponent(branchId)
    +'/tournaments/'+encodeURIComponent(eventId)+'/hybrid-knockout-entrants')
  const {exactHybridEntrants}=await import('./tournamentHybridKnockout')
  if(!exactHybridEntrants(data,runId,branchId,eventId,standings))
    throw new Error('Hybrid Knockout Entrants do not match exact frozen final Group Standings.')
  return data
}
export async function generateAdminHybridKnockoutEntrants(
  runId:string,branchId:string,eventId:string,
  standings:import('./tournamentGroupStandings').CompletedGroupStandings,commandId:string,
):Promise<import('./tournamentHybridKnockout').HybridKnockoutEntrants>{
  const data=await request<import('./tournamentHybridKnockout').HybridKnockoutEntrants>(
    '/admin/runs/'+encodeURIComponent(runId)+'/branches/'+encodeURIComponent(branchId)
    +'/tournaments/'+encodeURIComponent(eventId)+'/hybrid-knockout-entrants/generate',{
      method:'POST',body:JSON.stringify({command_id:commandId}),
    })
  const {exactHybridEntrants}=await import('./tournamentHybridKnockout')
  if(!exactHybridEntrants(data,runId,branchId,eventId,standings,commandId))
    throw new Error('Generated Hybrid Knockout Entrants do not match reviewed group positions.')
  return data
}
export async function getAdminHybridKnockoutBracket(
  runId:string,branchId:string,eventId:string,
  entrants:import('./tournamentHybridKnockout').HybridKnockoutEntrants,
):Promise<import('./tournamentHybridKnockout').HybridKnockoutBracket>{
  const data=await request<import('./tournamentHybridKnockout').HybridKnockoutBracket>(
    '/admin/runs/'+encodeURIComponent(runId)+'/branches/'+encodeURIComponent(branchId)
    +'/tournaments/'+encodeURIComponent(eventId)+'/hybrid-knockout-bracket')
  const {exactHybridBracket}=await import('./tournamentHybridKnockout')
  if(!exactHybridBracket(data,runId,branchId,eventId,entrants))
    throw new Error('Frozen Hybrid Knockout Bracket differs from immutable source entrants.')
  return data
}
export async function generateAdminHybridKnockoutBracket(
  runId:string,branchId:string,eventId:string,
  entrants:import('./tournamentHybridKnockout').HybridKnockoutEntrants,commandId:string,
):Promise<import('./tournamentHybridKnockout').HybridKnockoutBracket>{
  const data=await request<import('./tournamentHybridKnockout').HybridKnockoutBracket>(
    '/admin/runs/'+encodeURIComponent(runId)+'/branches/'+encodeURIComponent(branchId)
    +'/tournaments/'+encodeURIComponent(eventId)+'/hybrid-knockout-bracket/generate',{
      method:'POST',body:JSON.stringify({command_id:commandId}),
    })
  const {exactHybridBracket}=await import('./tournamentHybridKnockout')
  if(!exactHybridBracket(data,runId,branchId,eventId,entrants,commandId))
    throw new Error('Generated Hybrid Knockout Bracket does not replay from approved entrants.')
  return data
}

/** The immutable event-specific phase policy; no implicit number or Walkover reward. */
export async function getAdminHybridRankingPolicy(
  runId:string,branchId:string,eventId:string,
  bracket:import('./tournamentHybridKnockout').HybridKnockoutBracket
):Promise<import('./tournamentHybridRanking').HybridRankingPolicy>{
  const result=await request<import('./tournamentHybridRanking').HybridRankingPolicy>(
    '/admin/runs/'+encodeURIComponent(runId)+'/branches/'+encodeURIComponent(branchId)
    +'/tournaments/'+encodeURIComponent(eventId)+'/hybrid-ranking-policy'
  )
  const {exactHybridRankingPolicy}=await import('./tournamentHybridRanking')
  if(!exactHybridRankingPolicy(result,runId,branchId,eventId,bracket))
    throw new Error('Stored hybrid ranking policy is not an exact reviewed knockout stage policy.')
  return result
}
export async function configureAdminHybridRankingPolicy(
  runId:string,branchId:string,eventId:string,
  bracket:import('./tournamentHybridKnockout').HybridKnockoutBracket,
  payload:import('./tournamentHybridRanking').HybridRankingPayload,
):Promise<import('./tournamentHybridRanking').HybridRankingPolicy>{
  const result=await request<import('./tournamentHybridRanking').HybridRankingPolicy>(
    '/admin/runs/'+encodeURIComponent(runId)+'/branches/'+encodeURIComponent(branchId)
    +'/tournaments/'+encodeURIComponent(eventId)+'/hybrid-ranking-policy/configure',{
      method:'POST',body:JSON.stringify(payload)
    })
  const {exactHybridRankingPolicy}=await import('./tournamentHybridRanking')
  if(!exactHybridRankingPolicy(result,runId,branchId,eventId,bracket,payload))
    throw new Error('Configured hybrid phase award policy differs from explicitly reviewed values.')
  return result
}
export async function getAdminHybridRankingClosure(
  runId:string,branchId:string,eventId:string,
):Promise<import('./tournamentHybridRanking').HybridRankingClosure>{
  const result=await request<import('./tournamentHybridRanking').HybridRankingClosure>(
    '/admin/runs/'+encodeURIComponent(runId)+'/branches/'+encodeURIComponent(branchId)
    +'/tournaments/'+encodeURIComponent(eventId)+'/hybrid-ranking-close'
  )
  const {exactHybridRankingClosure}=await import('./tournamentHybridRanking')
  if(!exactHybridRankingClosure(result,runId,branchId,eventId))
    throw new Error('Completed Hybrid Tournament Ranking source is corrupt or out of scope.')
  return result
}
export async function closeAdminHybridRanking(
  runId:string,branchId:string,eventId:string,commandId:string,
):Promise<import('./tournamentHybridRanking').HybridRankingClosure>{
  const result=await request<import('./tournamentHybridRanking').HybridRankingClosure>(
    '/admin/runs/'+encodeURIComponent(runId)+'/branches/'+encodeURIComponent(branchId)
    +'/tournaments/'+encodeURIComponent(eventId)+'/hybrid-ranking-close',{
      method:'POST',body:JSON.stringify({command_id:commandId})
    })
  const {exactHybridRankingClosure}=await import('./tournamentHybridRanking')
  if(!exactHybridRankingClosure(result,runId,branchId,eventId))
    throw new Error('Completed Hybrid Tournament Ranking source is corrupt or out of scope.')
  return result
}

export async function getAdminCompletedGroupStandings(
  runId: string, branchId: string, eventId: string
): Promise<import('./tournamentGroupStandings').CompletedGroupStandings> {
  const data = await request<import('./tournamentGroupStandings').CompletedGroupStandings>(
    '/admin/runs/' + encodeURIComponent(runId) + '/branches/' + encodeURIComponent(branchId)
      + '/tournaments/' + encodeURIComponent(eventId) + '/group-standings'
  )
  const { isScopedCompletedGroupStandings } = await import('./tournamentGroupStandings')
  if (!isScopedCompletedGroupStandings(data, runId, branchId, eventId))
    throw new Error('Final Group Standings do not match the selected Run, Branch, Event and source authority.')
  return data
}

export async function generateAdminCompletedGroupStandings(
  runId: string, branchId: string, eventId: string, commandId: string
): Promise<import('./tournamentGroupStandings').CompletedGroupStandings> {
  const data = await request<import('./tournamentGroupStandings').CompletedGroupStandings>(
    '/admin/runs/' + encodeURIComponent(runId) + '/branches/' + encodeURIComponent(branchId)
      + '/tournaments/' + encodeURIComponent(eventId) + '/group-standings/generate',
    { method: 'POST', body: JSON.stringify({ command_id: commandId }) }
  )
  const { isScopedCompletedGroupStandings } = await import('./tournamentGroupStandings')
  if (!isScopedCompletedGroupStandings(data, runId, branchId, eventId)
    || data.generated_by_command_id !== commandId)
    throw new Error('Completed Group Standings generation returned an unrelated frozen authority.')
  return data
}

export async function getAdminGroupTieResolutionState(
  runId: string, branchId: string, eventId: string
): Promise<import('./tournamentGroupStandings').GroupStandingsTieState> {
  const data = await request<import('./tournamentGroupStandings').GroupStandingsTieState>(
    '/admin/runs/' + encodeURIComponent(runId) + '/branches/' + encodeURIComponent(branchId)
      + '/tournaments/' + encodeURIComponent(eventId) + '/group-standings/tie-resolution'
  )
  const { isScopedGroupTieState } = await import('./tournamentGroupStandings')
  if (!isScopedGroupTieState(data, runId, branchId, eventId))
    throw new Error('Group tie case does not belong to the selected Run, Branch and Event.')
  return data
}

/** Commit one explicitly reviewed ordering of the server's exact unresolved case. */
export async function resolveAdminGroupStandingsTie(
  runId: string, branchId: string, eventId: string,
  casePlayers: string[],
  payload: import('./tournamentGroupStandings').GroupTieResolutionPayload
): Promise<import('./tournamentGroupStandings').GroupTieResolutionAuthority> {
  const data = await request<import('./tournamentGroupStandings').GroupTieResolutionAuthority>(
    '/admin/runs/' + encodeURIComponent(runId) + '/branches/' + encodeURIComponent(branchId)
      + '/tournaments/' + encodeURIComponent(eventId) + '/group-standings/tie-resolution',
    { method: 'POST', body: JSON.stringify(payload) }
  )
  const { isExactGroupTieResolution } = await import('./tournamentGroupStandings')
  if (!isExactGroupTieResolution(data, runId, branchId, eventId, casePlayers, payload))
    throw new Error('Group tie-resolution authority does not match this Run, Branch, Event and explicit ordered case.')
  return data
}

export function getCalendarInitialHealth(runId:string,branchId:string):Promise<unknown> {
  return request(`/admin/runs/${encodeURIComponent(runId)}/branches/${encodeURIComponent(branchId)}/player-health/calendar-initial`)
}
export function reviewCalendarInitialHealth(runId:string,branchId:string,payload:import('./calendarInitialHealth').InitialHealthRequest):Promise<unknown> {
  return request(`/admin/runs/${encodeURIComponent(runId)}/branches/${encodeURIComponent(branchId)}/player-health/calendar-initial/preview`, {method:'POST',body:JSON.stringify(payload)})
}
export function confirmCalendarInitialHealth(runId:string,branchId:string,review:import('./calendarInitialHealth').InitialHealthRequest,fingerprint:string):Promise<unknown> {
  return request(`/admin/runs/${encodeURIComponent(runId)}/branches/${encodeURIComponent(branchId)}/player-health/calendar-initial`, {method:'POST',body:JSON.stringify({review,expected_health_fingerprint:fingerprint})})
}


/** Inspection only: no mutation, Save or sim task is permitted. */
export async function previewRunCalendarExtension(
  runId: string, branchId: string, newSeasonCount: number
): Promise<import('./runCalendarCreation').RunCalendarExtensionPreview> {
  if (!Number.isSafeInteger(newSeasonCount) || newSeasonCount < 1 || newSeasonCount > 2147483647) {
    throw Error('Invalid proposed season count')
  }
  const path = '/run-containers/' + encodeURIComponent(runId) + '/branches/'
    + encodeURIComponent(branchId) + '/calendar/extension-preview?new_season_count=' + newSeasonCount
  return validateExtensionPreview(await request<unknown>(path), runId, branchId, newSeasonCount)
}


/** Read-only, all-Branch review bound to immutable heads and monotone draft versions. */
export async function reviewRunCalendarExtension(
  runId: string, newSeasonCount: number
): Promise<import('./runCalendarExtension').CalendarExtensionReview> {
  if (!Number.isSafeInteger(newSeasonCount) || newSeasonCount < 1 || newSeasonCount > 2147483647) {
    throw Error('Invalid Run calendar extension horizon')
  }
  const { validateCalendarExtensionReview } = await import('./runCalendarExtension')
  const endpoint = '/run-containers/' + encodeURIComponent(runId)
    + '/calendar/extension-review?new_season_count=' + newSeasonCount
  return validateCalendarExtensionReview(await request<unknown>(endpoint), runId, newSeasonCount)
}

/** Explicitly confirmed manual Save; never starts Full Simulation. */
export async function saveRunCalendarExtension(
  runId: string, payload: import('./runCalendarExtension').CalendarExtensionSaveRequest,
): Promise<import('./runCalendarExtension').CalendarExtensionReceipt> {
  if (!payload.explicit_confirmation || !payload.review_fingerprint
    || !payload.command_id.trim() || !Number.isSafeInteger(payload.new_season_count)) {
    throw Error('Invalid explicit Run extension Save command')
  }
  const { validateCalendarExtensionReceipt } = await import('./runCalendarExtension')
  const endpoint = '/run-containers/' + encodeURIComponent(runId) + '/calendar/extension-save'
  return validateCalendarExtensionReceipt(
    await request<unknown>(endpoint, { method: 'POST', body: JSON.stringify(payload) }),
    runId, payload,
  )
}

/** Read-only, Saved HEAD-scoped Run Home guidance; never grants sporting execution. */
export async function getRunHomeReadiness(
  runId: string, branchId: string,
): Promise<import('./runHomeReadiness').RunHomeReadiness> {
  const { validateRunHomeReadiness } = await import('./runHomeReadiness')
  const path = '/admin/runs/' + encodeURIComponent(runId) + '/branches/'
    + encodeURIComponent(branchId) + '/home-readiness'
  return validateRunHomeReadiness(await request<unknown>(path), runId, branchId)
}

/** Calendar-native isolated match: only saved v2 initial population, no legacy W61 writer. */
function calendarMatchRoot(runId: string, branchId: string): string {
  return authoritativeSimulationRoot(runId, branchId) + '/calendar-standalone-match'
}

export function inspectCalendarStandaloneMatch(runId: string, branchId: string):
  Promise<import('./calendarStandaloneMatch').CalendarMatchView> {
  return request(calendarMatchRoot(runId, branchId))
}

export function simulateCalendarStandaloneMatch(runId: string, branchId: string,
  command: import('./calendarStandaloneMatch').CalendarMatchCommand):
  Promise<import('./calendarStandaloneMatch').CalendarMatchReceipt> {
  return request(calendarMatchRoot(runId, branchId) + '/simulate', {
    method: 'POST', body: JSON.stringify(command),
  })
}

export function replayCalendarStandaloneMatch(runId: string, branchId: string, matchId: string):
  Promise<import('./calendarStandaloneMatch').CalendarMatchReplay> {
  return request(calendarMatchRoot(runId, branchId) + '/' + encodeURIComponent(matchId) + '/replay')
}

export function previewCalendarStandaloneMatchSave(runId: string, branchId: string):
  Promise<import('./calendarStandaloneMatch').CalendarMatchSavePreview> {
  return request(calendarMatchRoot(runId, branchId) + '/save/preview')
}

export function saveCalendarStandaloneMatch(runId: string, branchId: string,
  expectedDraftVersion: number, expectedMatchFingerprint: string): Promise<unknown> {
  return request(calendarMatchRoot(runId, branchId) + '/save', {
    method: 'POST',
    body: JSON.stringify({
      expected_draft_version: expectedDraftVersion,
      expected_calendar_match_fingerprint: expectedMatchFingerprint,
    }),
  })
}


/** Run-calendar-native real four-player knockout, distinct from legacy W61 simulation. */
function knockoutRoot(runId: string, branchId: string): string {
  return authoritativeSimulationRoot(runId, branchId) + '/calendar-opening-knockout'
}

export function inspectCalendarOpeningKnockout(runId: string, branchId: string):
  Promise<import('./calendarOpeningKnockout').KnockoutInspection> {
  return request(knockoutRoot(runId, branchId))
}
export function simulateCalendarOpeningKnockout(runId: string, branchId: string,
  command: import('./calendarOpeningKnockout').KnockoutCommand):
  Promise<import('./calendarOpeningKnockout').KnockoutReceipt> {
  return request(knockoutRoot(runId, branchId) + '/simulate', {
    method: 'POST', body: JSON.stringify(command),
  })
}
export function replayCalendarOpeningKnockout(runId: string, branchId: string, matchId: string):
  Promise<import('./calendarOpeningKnockout').KnockoutReplay> {
  return request(knockoutRoot(runId, branchId) + '/' + encodeURIComponent(matchId) + '/replay')
}
export function previewCalendarOpeningKnockoutSave(runId: string, branchId: string):
  Promise<import('./calendarOpeningKnockout').KnockoutSavePreview> {
  return request(knockoutRoot(runId, branchId) + '/save/preview')
}
export function saveCalendarOpeningKnockout(runId: string, branchId: string,
  draftVersion: number, fingerprint: string): Promise<unknown> {
  return request(knockoutRoot(runId, branchId) + '/save', {
    method: 'POST', body: JSON.stringify({
      expected_draft_version: draftVersion,
      expected_calendar_match_fingerprint: fingerprint,
    }),
  })
}


/** Prepared, not Official, calendar knockout point evidence from Saved MatchEngine results. */
export function reviewCalendarKnockoutAwards(runId: string, branchId: string,
  proposal: import('./calendarOpeningKnockout').CalendarAwardProposal):
  Promise<import('./calendarOpeningKnockout').CalendarAwardReview> {
  return request(knockoutRoot(runId, branchId) + '/awards/review', {
    method: 'POST', body: JSON.stringify(proposal),
  })
}
export function applyCalendarKnockoutAwards(runId: string, branchId: string,
  command: import('./calendarOpeningKnockout').CalendarAwardApplyCommand):
  Promise<{ prepared: unknown; fingerprint: string }> {
  return request(knockoutRoot(runId, branchId) + '/awards/apply', {
    method: 'POST', body: JSON.stringify(command),
  })
}


/** Trusted Signed event standings, never a published Official Ranking. */
export function inspectSignedCalendarKnockoutStandings(
  runId: string, branchId: string, expectedSavedHead: string,
  seasonIndex: number, week: number,
): Promise<import('./calendarOpeningKnockout').SignedKnockoutStandings> {
  const params = new URLSearchParams({
    expected_saved_head: expectedSavedHead,
    season_index: String(seasonIndex), week: String(week),
  })
  return request(knockoutRoot(runId, branchId) + '/standings?' + params.toString())
}


export function previewCalendarCanonicalKnockout(runId: string, branchId: string,
  body: { expected_saved_head: string; expected_initial_world_fingerprint: string; entrant_ids: string[] }):
  Promise<import('./calendarOpeningKnockout').CanonicalKnockoutPreview> {
  return request(knockoutRoot(runId, branchId) + '/canonical-preview',
    { method: 'POST', body: JSON.stringify(body) })
}
