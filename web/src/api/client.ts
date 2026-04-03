import type {
  BootstrapNextSeasonPayload,
  BootstrapNextSeasonResponse,
  AssignWildcardsPayload,
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
  PlayerTransitionsResponse,
  RunLineageApiResponse,
  RunStatusSummary,
  RunSourceApiResponse,
  RunsIndexResponse,
  SeasonRolloverExecutionResponse,
  SeasonRolloverSummaryApiResponse,
  RunSummary,
  SeasonStateResponse,
  SimulateResponse,
  WildcardCandidatesResponse,
  WildcardActionHistoryResponse,
  WildcardStateResponse
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

  return (await response.json()) as T
}

export function getHealth(): Promise<HealthResponse> {
  return request('/health')
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
