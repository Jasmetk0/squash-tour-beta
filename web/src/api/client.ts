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
  RunSummary,
  RunPlayerDetail,
  PlayerCareerHistoryResponse,
  RunPlayersListResponse,
  RunNationDetail,
  RunNationsSummaryResponse,
  SeasonStateResponse,
  SimulateResponse,
  WildcardCandidatesResponse,
  WildcardActionHistoryResponse,
  WildcardStateResponse,
  WorldPackageImportPayload,
  WorldPackageImportResponse
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

export function createRun(payload: CreateRunPayload): Promise<RunSummary> {
  return request('/runs', { method: 'POST', body: JSON.stringify(payload) })
}

export function listRuns(): Promise<RunsIndexResponse> {
  return request('/runs')
}

export function getRun(runId: string): Promise<SeasonStateResponse> {
  return request(`/runs/${encodeURIComponent(runId)}`)
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
