import type { EventRecord, RunPlayerListItem, SeasonStateResponse } from '../../../api/types'

export const comparisonStatFields = [
  { key: 'overall', label: 'Power Rating difference' },
  { key: 'technique', label: 'Technique difference' },
  { key: 'movement', label: 'Movement difference' },
  { key: 'physical', label: 'Physical difference' },
  { key: 'mental', label: 'Mental difference' },
  { key: 'age', label: 'Age difference' }
] as const

export type ComparisonStatFieldKey = typeof comparisonStatFields[number]['key']

export function playerNumericField(player: RunPlayerListItem, field: ComparisonStatFieldKey): number | null {
  const value = player[field]
  return typeof value === 'number' && Number.isFinite(value) ? value : null
}

export function formatComparisonDifference(playerA: RunPlayerListItem, playerB: RunPlayerListItem, field: ComparisonStatFieldKey): string {
  const valueA = playerNumericField(playerA, field)
  const valueB = playerNumericField(playerB, field)
  if (valueA === null || valueB === null) return '—'
  const difference = valueA - valueB
  return difference > 0 ? `+${difference}` : String(difference)
}

export type ViewerComparisonQueryParams = {
  playerAParam: string
  playerBParam: string
  hasPlayerParams: boolean
}

export type ViewerSelectedComparisonPlayers = ViewerComparisonQueryParams & {
  playerA: RunPlayerListItem | null
  playerB: RunPlayerListItem | null
  hasMissingRequestedPlayer: boolean
}

export function readViewerComparisonQueryParams(searchParams: URLSearchParams): ViewerComparisonQueryParams {
  const playerAParam = searchParams.get('playerA') || searchParams.get('player_a') || searchParams.get('a') || ''
  const playerBParam = searchParams.get('playerB') || searchParams.get('player_b') || searchParams.get('b') || ''
  return {
    playerAParam,
    playerBParam,
    hasPlayerParams: Boolean(playerAParam || playerBParam)
  }
}

export function selectViewerComparisonPlayers(players: RunPlayerListItem[], searchParams: URLSearchParams): ViewerSelectedComparisonPlayers {
  const params = readViewerComparisonQueryParams(searchParams)
  const playerA = params.playerAParam ? players.find((player) => player.player_id === params.playerAParam) ?? null : null
  const playerB = params.playerBParam ? players.find((player) => player.player_id === params.playerBParam) ?? null : null
  return {
    ...params,
    playerA,
    playerB,
    hasMissingRequestedPlayer: params.hasPlayerParams && (!params.playerAParam || !params.playerBParam || !playerA || !playerB)
  }
}

export function selectedComparisonPlayers(selection: Pick<ViewerSelectedComparisonPlayers, 'playerA' | 'playerB'>): RunPlayerListItem[] {
  return [selection.playerA, selection.playerB].filter((player): player is RunPlayerListItem => Boolean(player))
}

export type ViewerSearchPlannedEvent = SeasonStateResponse['season_state']['ordered_events'][number]

export type ViewerSearchTournamentResult = {
  eventId: string
  season: number | null
  week: number | null
  tour: string | null
  category: string | null
  templateId: string | null
  hasPlannedEvent: boolean
  hasPersistedEvent: boolean
}

export function normalizeViewerSearchQuery(searchParams: URLSearchParams): string {
  return (searchParams.get('q') ?? searchParams.get('query') ?? searchParams.get('search') ?? '').trim()
}

export function searchTextMatches(query: string, values: Array<string | number | null | undefined>): boolean {
  const normalizedQuery = query.toLowerCase()
  return values.some((value) => String(value ?? '').toLowerCase().includes(normalizedQuery))
}

export function buildSearchTournamentResults(plannedEvents: ViewerSearchPlannedEvent[], persistedEvents: EventRecord[], query: string): ViewerSearchTournamentResult[] {
  const plannedById = new Map(plannedEvents.map((event) => [event.event_id, event]))
  const persistedById = new Map(persistedEvents.map((event) => [event.event_id, event]))
  const eventIds = Array.from(new Set([...plannedById.keys(), ...persistedById.keys()]))

  return eventIds
    .map((eventId) => {
      const planned = plannedById.get(eventId)
      const persisted = persistedById.get(eventId)
      return {
        eventId,
        season: planned?.season ?? persisted?.season ?? null,
        week: planned?.week ?? persisted?.week ?? null,
        tour: planned?.tour ?? null,
        category: planned?.category ?? null,
        templateId: planned?.template_id ?? persisted?.template_id ?? null,
        hasPlannedEvent: Boolean(planned),
        hasPersistedEvent: Boolean(persisted)
      }
    })
    .filter((event) => searchTextMatches(query, [event.eventId, event.tour, event.category, event.templateId, event.week]))
}
