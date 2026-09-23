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
  LateReplacementActionHistoryResponse,
  PlayerTransitionsResponse,
  PreDrawWithdrawalActionHistoryResponse,
  CanonicalTournamentEntryFieldState,
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
  RunProspectListResponse,
  RunSummary,
  RunContainer,
  RunContainerListResponse,
  ViewerOfficialRunContext,
  ViewerTournamentEntryField,
  ViewerTournamentDraw,
  ViewerTournamentWildCards,
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
  AuthoritativeWeekScheduleProposal,
  AuthoritativeWeekScheduleManualPreview,
  PreviewAuthoritativeWeekSchedulePayload,
  AdoptAuthoritativeWeekSchedulePayload,
  AdoptAuthoritativeWeekScheduleProposalPayload,
  AuthoritativeWeekScheduleAdoptionResult,
  AuthoritativeSimulationCommandPayload,
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
  AuthoritativeFullSimulationAbandonPayload,
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
  PlayerCareerHistoryResponse,
  PlayerCareerPerformanceResponse,
  PlayerTournamentResultsTimelineResponse,
  RunPlayersListResponse,
  RunNationDetail,
  RunNationsSummaryResponse,
  SeasonStateResponse,
  HistoricalBranchSeasonStateResponse,
  SimulateResponse,
  WildcardActionHistoryResponse,
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
  SeasonBootstrapPayload,
  SeasonCalendarBuildPayload,
  SeasonCalendarBuildResponse,
  SeasonCalendarEvent,
  SeasonBootstrapResponse,
  EntryListGeneratePayload,
  DrawGeneratePayload,
  MatchGeneratePayload,
  MatchSimulatePayload,
  ProgressionCommandPayload,
  ProgressionCommandResult,
  SimulateDrawPayload,
  SimulateRoundPayload,
  TournamentProgressionStatus,
  SeasonEventDrawPackageResult,
  SeasonEventMatchPackageResult,
  MatchReplayResponse,
  SeasonEventResultPackageResult,
  EventPointAwardPackageResult,
  PointAwardGeneratePayload,
  PointAwardApplyPayload,
  PointAwardApplyResult,
  PlayerPointBreakdownQueryParams,
  PlayerPointBreakdownResponse,
  RankingTableQueryParams,
  RankingTableResponse,
  WeeklyRankingSnapshotGeneratePayload,
  WeeklyRankingSnapshotResult,
  EventResultExtractPayload,
  SeasonEventEntryListResult,
  SeasonLifecycleResponse,
  EventLifecycleResponse,
  SimulateOneEventRequest,
  SimulateOneEventResult,
  SimulateSeasonWeekPreflightRequest,
  SimulateSeasonWeekPreflightResult,
  RunSeasonWeekRequest,
  RunSeasonWeekResult,
  SeasonWeekRecoveryRequest,
  SeasonWeekRecoveryResult,
  SeasonReadinessRequest,
  SeasonReadinessResult,
  SeasonRangePreflightRequest,
  SeasonRangePreflightResult,
  RunSeasonRangeRequest,
  RunSeasonRangeResult,
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
    headers: { 'Content-Type': 'application/json', ...(init?.headers ?? {}) },
    ...init
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

export function bootstrapSeasonFromInitialPool(season: string, payload: SeasonBootstrapPayload): Promise<SeasonBootstrapResponse> {
  return request(`/admin/seasons/${encodeURIComponent(season)}/bootstrap-from-initial-pool`, { method: 'POST', body: JSON.stringify(payload) })
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

export function getEventLifecycle(eventId: string): Promise<EventLifecycleResponse> {
  return request(`/admin/lifecycle/event/${encodeURIComponent(eventId)}`)
}

export function simulateOneEvent(eventId: string, payload: SimulateOneEventRequest): Promise<SimulateOneEventResult> {
  return request(`/admin/events/${encodeURIComponent(eventId)}/simulate`, { method: 'POST', body: JSON.stringify(payload) })
}

export function preflightSeasonWeek(payload: SimulateSeasonWeekPreflightRequest): Promise<SimulateSeasonWeekPreflightResult> {
  return request(`/admin/weeks/preflight`, { method: 'POST', body: JSON.stringify(payload) })
}

export function runSeasonWeek(payload: RunSeasonWeekRequest): Promise<RunSeasonWeekResult> {
  return request(`/admin/weeks/run`, { method: 'POST', body: JSON.stringify(payload) })
}

export function recoverSeasonWeek(payload: SeasonWeekRecoveryRequest): Promise<SeasonWeekRecoveryResult> {
  return request(`/admin/weeks/recovery`, { method: 'POST', body: JSON.stringify(payload) })
}

export function getSeasonReadiness(payload: SeasonReadinessRequest): Promise<SeasonReadinessResult> {
  return request(`/admin/seasons/readiness`, { method: 'POST', body: JSON.stringify(payload) })
}

export function preflightSeasonRange(payload: SeasonRangePreflightRequest): Promise<SeasonRangePreflightResult> {
  return request(`/admin/seasons/range-preflight`, { method: 'POST', body: JSON.stringify(payload) })
}

export function runSeasonRange(payload: RunSeasonRangeRequest): Promise<RunSeasonRangeResult> {
  return request(`/admin/seasons/range-run`, { method: 'POST', body: JSON.stringify(payload) })
}

export function buildSeasonCalendar(season: string, payload: SeasonCalendarBuildPayload): Promise<SeasonCalendarBuildResponse> {
  return request(`/admin/seasons/${encodeURIComponent(season)}/calendar/build`, { method: 'POST', body: JSON.stringify(payload) })
}

export function getEventEntryList(eventId: string): Promise<SeasonEventEntryListResult> {
  return request(`/admin/entries/${encodeURIComponent(eventId)}`)
}

export function generateEventEntryList(eventId: string, payload: EntryListGeneratePayload): Promise<SeasonEventEntryListResult> {
  return request(`/admin/entries/${encodeURIComponent(eventId)}/generate`, { method: 'POST', body: JSON.stringify(payload) })
}

export function getEventDrawPackage(eventId: string): Promise<SeasonEventDrawPackageResult> {
  return request(`/admin/draws/${encodeURIComponent(eventId)}`)
}

export function generateEventDrawPackage(eventId: string, payload: DrawGeneratePayload): Promise<SeasonEventDrawPackageResult> {
  return request(`/admin/draws/${encodeURIComponent(eventId)}/generate`, { method: 'POST', body: JSON.stringify(payload) })
}

export function getEventMatchPackage(eventId: string): Promise<SeasonEventMatchPackageResult> {
  return request(`/admin/matches/${encodeURIComponent(eventId)}`)
}

export function generateEventMatchPackage(eventId: string, payload: MatchGeneratePayload): Promise<SeasonEventMatchPackageResult> {
  return request(`/admin/matches/${encodeURIComponent(eventId)}/generate`, { method: 'POST', body: JSON.stringify(payload) })
}

export function simulateNextEventMatch(eventId: string, payload: MatchSimulatePayload): Promise<SeasonEventMatchPackageResult> {
  return request(`/admin/matches/${encodeURIComponent(eventId)}/simulate-next`, { method: 'POST', body: JSON.stringify(payload) })
}

export function simulateEventMatch(eventId: string, matchId: string, payload: MatchSimulatePayload): Promise<SeasonEventMatchPackageResult> {
  return request(`/admin/matches/${encodeURIComponent(eventId)}/simulate/${encodeURIComponent(matchId)}`, { method: 'POST', body: JSON.stringify(payload) })
}

export function getEventMatchReplay(eventId: string, matchId: string): Promise<MatchReplayResponse> {
  return request(`/admin/matches/${encodeURIComponent(eventId)}/replay/${encodeURIComponent(matchId)}`)
}

export function getEventProgressionStatus(eventId: string): Promise<TournamentProgressionStatus> {
  return request(`/admin/matches/${encodeURIComponent(eventId)}/progression`)
}

export function processEventByes(eventId: string, payload: ProgressionCommandPayload): Promise<ProgressionCommandResult> {
  return request(`/admin/matches/${encodeURIComponent(eventId)}/process-byes`, { method: 'POST', body: JSON.stringify(payload) })
}

export function refreshEventProgression(eventId: string, payload: ProgressionCommandPayload): Promise<ProgressionCommandResult> {
  return request(`/admin/matches/${encodeURIComponent(eventId)}/refresh-progression`, { method: 'POST', body: JSON.stringify(payload) })
}

export function promoteEventQualifiers(eventId: string, payload: ProgressionCommandPayload): Promise<ProgressionCommandResult> {
  return request(`/admin/matches/${encodeURIComponent(eventId)}/promote-qualifiers`, { method: 'POST', body: JSON.stringify(payload) })
}

export function simulateEventRound(eventId: string, payload: SimulateRoundPayload): Promise<ProgressionCommandResult> {
  return request(`/admin/matches/${encodeURIComponent(eventId)}/simulate-round`, { method: 'POST', body: JSON.stringify(payload) })
}

export function simulateEventDraw(eventId: string, payload: SimulateDrawPayload): Promise<ProgressionCommandResult> {
  return request(`/admin/matches/${encodeURIComponent(eventId)}/simulate-draw`, { method: 'POST', body: JSON.stringify(payload) })
}

export function getEventResultPackage(eventId: string): Promise<SeasonEventResultPackageResult> {
  return request(`/admin/results/${encodeURIComponent(eventId)}`)
}

export function extractEventResultPackage(eventId: string, payload: EventResultExtractPayload): Promise<SeasonEventResultPackageResult> {
  return request(`/admin/results/${encodeURIComponent(eventId)}/extract`, { method: 'POST', body: JSON.stringify(payload) })
}

export function getEventPointAwards(eventId: string): Promise<EventPointAwardPackageResult> {
  return request(`/admin/points/${encodeURIComponent(eventId)}`)
}

export function generateEventPointAwards(eventId: string, payload: PointAwardGeneratePayload): Promise<EventPointAwardPackageResult> {
  return request(`/admin/points/${encodeURIComponent(eventId)}/generate`, { method: 'POST', body: JSON.stringify(payload) })
}

export function applyEventPointAwards(eventId: string, payload: PointAwardApplyPayload): Promise<PointAwardApplyResult> {
  return request(`/admin/points/${encodeURIComponent(eventId)}/apply`, { method: 'POST', body: JSON.stringify(payload) })
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

export function cloneOfficialWorldPackage(payload: WorldPackageClonePayload): Promise<WorldPackageCloneResponse> {
  return request('/world/packages/official_fax_world/clone', { method: 'POST', body: JSON.stringify(payload) })
}

export function createRun(payload: CreateRunPayload): Promise<RunSummary> {
  return request('/runs', { method: 'POST', body: JSON.stringify(payload) })
}

export function listRuns(): Promise<RunsIndexResponse> {
  return request('/runs')
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
    !/^[0-9a-f]{64}$/.test(data.player_sporting_fingerprint)
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
      operation.command.expected_preview_fingerprint !==
        operation.review.preview_fingerprint ||
      operation.command.expected_position_fingerprint !==
        operation.review.expected_position_fingerprint ||
      operation.command.expected_revision_id !==
        operation.review.expected_revision_id ||
      operation.completed_season_count !== operation.completed_seasons.length ||
      operation.final_completed_week_count !==
        operation.final_completed_weeks.length
    ) {
      throw new Error('Pending Full Simulation operation is invalid.')
    }
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
      data.status !== 'blocked' ||
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
    data.result.player_sporting_fingerprint !== preview.result.player_sporting_fingerprint
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


export function materializeRunProspects(
  runId: string,
  payload: MaterializeRunProspectsRequest = {}
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

export function getEventWildcardActions(runId: string, eventId: string): Promise<WildcardActionHistoryResponse> {
  return request(`/runs/${encodeURIComponent(runId)}/events/${encodeURIComponent(eventId)}/wildcard-actions`)
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

export function getEventPreDrawWithdrawalActions(
  runId: string,
  eventId: string
): Promise<PreDrawWithdrawalActionHistoryResponse> {
  return request(`/runs/${encodeURIComponent(runId)}/events/${encodeURIComponent(eventId)}/pre-draw-withdrawal-actions`)
}

export function getEventLateReplacementActions(
  runId: string,
  eventId: string
): Promise<LateReplacementActionHistoryResponse> {
  return request(`/runs/${encodeURIComponent(runId)}/events/${encodeURIComponent(eventId)}/late-replacement-actions`)
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
