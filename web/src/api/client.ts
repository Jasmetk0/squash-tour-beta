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
  AssignWildcardsPayload,
  ApplyPreDrawWithdrawalPayload,
  ApplyLateReplacementPayload,
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
  LateReplacementCandidatesResponse,
  LateReplacementResultResponse,
  LateReplacementStateResponse,
  PlayerTransitionsResponse,
  PreDrawWithdrawalActionHistoryResponse,
  PreDrawWithdrawalResultResponse,
  PreDrawWithdrawalStateResponse,
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
  RunBranch,
  RunBranchListResponse,
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
  SimulateResponse,
  WildcardCandidatesResponse,
  WildcardActionHistoryResponse,
  WildcardStateResponse,
  WorldPackage,
  WorldPackageClonePayload,
  WorldPackageCloneResponse,
  WorldPackageCountriesResponse,
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

export function listRunBranches(runId?: string): Promise<RunBranchListResponse> {
  const suffix = runId === undefined ? '' : `?${new URLSearchParams({ run_id: runId }).toString()}`
  return request(`/run-branches${suffix}`)
}

export function getRunBranch(branchId: string): Promise<RunBranch> {
  return request(`/run-branches/${encodeURIComponent(branchId)}`)
}

export function listBranchCheckpoints(params?: { branch_id?: string; run_id?: string }): Promise<BranchCheckpointListResponse> {
  const query = new URLSearchParams()
  if (params?.branch_id) query.set('branch_id', params.branch_id)
  if (params?.run_id) query.set('run_id', params.run_id)
  return request(`/branch-checkpoints${query.size ? `?${query}` : ''}`)
}
export function getBranchCheckpoint(checkpointId: string): Promise<BranchCheckpoint> { return request(`/branch-checkpoints/${encodeURIComponent(checkpointId)}`) }
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

export function getEventWildcards(runId: string, eventId: string): Promise<WildcardStateResponse> {
  return request(`/runs/${encodeURIComponent(runId)}/events/${encodeURIComponent(eventId)}/wildcards`)
}

export function getEventWildcardCandidates(runId: string, eventId: string): Promise<WildcardCandidatesResponse> {
  return request(`/runs/${encodeURIComponent(runId)}/events/${encodeURIComponent(eventId)}/wildcard-candidates`)
}

export function getEventWildcardActions(runId: string, eventId: string): Promise<WildcardActionHistoryResponse> {
  return request(`/runs/${encodeURIComponent(runId)}/events/${encodeURIComponent(eventId)}/wildcard-actions`)
}

export function assignEventWildcards(
  runId: string,
  eventId: string,
  payload: AssignWildcardsPayload
): Promise<WildcardStateResponse> {
  return request(`/runs/${encodeURIComponent(runId)}/events/${encodeURIComponent(eventId)}/wildcards`, {
    method: 'POST',
    body: JSON.stringify(payload)
  })
}

export function getEventPreDrawWithdrawalState(runId: string, eventId: string): Promise<PreDrawWithdrawalStateResponse> {
  return request(`/runs/${encodeURIComponent(runId)}/events/${encodeURIComponent(eventId)}/pre-draw-withdrawal`)
}

export function applyEventPreDrawWithdrawal(
  runId: string,
  eventId: string,
  payload: ApplyPreDrawWithdrawalPayload
): Promise<PreDrawWithdrawalResultResponse> {
  return request(`/runs/${encodeURIComponent(runId)}/events/${encodeURIComponent(eventId)}/pre-draw-withdrawal`, {
    method: 'POST',
    body: JSON.stringify(payload)
  })
}

export function getEventPreDrawWithdrawalActions(
  runId: string,
  eventId: string
): Promise<PreDrawWithdrawalActionHistoryResponse> {
  return request(`/runs/${encodeURIComponent(runId)}/events/${encodeURIComponent(eventId)}/pre-draw-withdrawal-actions`)
}

export function getEventLateReplacementState(runId: string, eventId: string): Promise<LateReplacementStateResponse> {
  return request(`/runs/${encodeURIComponent(runId)}/events/${encodeURIComponent(eventId)}/late-replacement`)
}

export function getEventLateReplacementCandidates(
  runId: string,
  eventId: string
): Promise<LateReplacementCandidatesResponse> {
  return request(`/runs/${encodeURIComponent(runId)}/events/${encodeURIComponent(eventId)}/late-replacement-candidates`)
}

export function applyEventLateReplacement(
  runId: string,
  eventId: string,
  payload: ApplyLateReplacementPayload
): Promise<LateReplacementResultResponse> {
  return request(`/runs/${encodeURIComponent(runId)}/events/${encodeURIComponent(eventId)}/late-replacement`, {
    method: 'POST',
    body: JSON.stringify(payload)
  })
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
