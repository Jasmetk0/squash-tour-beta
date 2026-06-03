type ViewerPathSegment = string | number

function encodePathSegment(segment: ViewerPathSegment): string {
  return encodeURIComponent(String(segment))
}

export function viewerHomePath(): string {
  return '/viewer'
}

export function viewerTopRankingsPath(): string {
  return '/viewer/rankings'
}

export function viewerTopRacePath(): string {
  return '/viewer/rankings/race'
}

export function viewerTopTourPath(): string {
  return '/viewer/tour'
}

export function viewerTopTourCalendarPath(): string {
  return '/viewer/tour/calendar'
}

export function viewerTopTourCurrentWeekPath(): string {
  return '/viewer/tour/current-week'
}

export function viewerTopTourTournamentsPath(): string {
  return '/viewer/tour/tournaments'
}

export function viewerTopTournamentsPath(): string {
  return '/viewer/tournaments'
}

export function viewerTopPlayersPath(): string {
  return '/viewer/players'
}

export function viewerTopCountriesPath(): string {
  return '/viewer/countries'
}

export function viewerTopCountryRankingPath(): string {
  return '/viewer/countries/ranking'
}

export function viewerTopStatsPath(): string {
  return '/viewer/stats'
}

export function viewerTopRecordsPath(): string {
  return '/viewer/records'
}

export function viewerTopPredictionsPath(): string {
  return '/viewer/predictions'
}

export function viewerTopSearchPath(): string {
  return '/viewer/search'
}

export function viewerTopHistoryPath(): string {
  return '/viewer/history'
}

export function viewerTopH2HPath(): string {
  return '/viewer/h2h'
}

export function viewerRunsPath(): string {
  return '/viewer/runs'
}

export function viewerPlayerProfilePath(runId: ViewerPathSegment, playerId: ViewerPathSegment): string {
  return `/viewer/runs/${encodePathSegment(runId)}/players/${encodePathSegment(playerId)}/career`
}

export function viewerCountryProfilePath(runId: ViewerPathSegment, countryCode: ViewerPathSegment): string {
  return `/viewer/runs/${encodePathSegment(runId)}/countries/${encodePathSegment(countryCode)}`
}

export function viewerTournamentDetailPath(runId: ViewerPathSegment, eventId: ViewerPathSegment): string {
  return `/viewer/runs/${encodePathSegment(runId)}/tournaments/${encodePathSegment(eventId)}`
}

export function viewerWeekDetailPath(runId: ViewerPathSegment, week: ViewerPathSegment): string {
  return `/viewer/runs/${encodePathSegment(runId)}/weeks/${encodePathSegment(week)}`
}

export function viewerRankingSnapshotPath(runId: ViewerPathSegment, snapshotSequence: ViewerPathSegment): string {
  return `/viewer/runs/${encodePathSegment(runId)}/rankings/${encodePathSegment(snapshotSequence)}`
}

export function viewerRaceSnapshotPath(runId: ViewerPathSegment, snapshotSequence: ViewerPathSegment): string {
  return `/viewer/runs/${encodePathSegment(runId)}/race/${encodePathSegment(snapshotSequence)}`
}

export function viewerSeasonCalendarPath(runId: ViewerPathSegment): string {
  return `/viewer/runs/${encodePathSegment(runId)}/calendar`
}

export function viewerHistoryPath(runId: ViewerPathSegment): string {
  return `/viewer/runs/${encodePathSegment(runId)}/history`
}

export function viewerFinalsPath(runId: ViewerPathSegment): string {
  return `/viewer/runs/${encodePathSegment(runId)}/finals`
}

export function viewerFinalsQualificationPath(runId: ViewerPathSegment): string {
  return `/viewer/runs/${encodePathSegment(runId)}/finals/qualification`
}

export function viewerFinalsResultPath(runId: ViewerPathSegment): string {
  return `/viewer/runs/${encodePathSegment(runId)}/finals/result`
}

export function viewerPlannedEventPath(runId: ViewerPathSegment, eventId: ViewerPathSegment): string {
  return `/viewer/runs/${encodePathSegment(runId)}/calendar/${encodePathSegment(eventId)}`
}

export function viewerPlayersPath(runId: ViewerPathSegment): string {
  return `/viewer/runs/${encodePathSegment(runId)}/players`
}

export function viewerCountriesPath(runId: ViewerPathSegment): string {
  return `/viewer/runs/${encodePathSegment(runId)}/countries`
}

export function viewerTournamentsPath(runId: ViewerPathSegment): string {
  return `/viewer/runs/${encodePathSegment(runId)}/tournaments`
}

export function viewerRankingsPath(runId: ViewerPathSegment): string {
  return `/viewer/runs/${encodePathSegment(runId)}/rankings`
}

export function viewerRacePath(runId: ViewerPathSegment): string {
  return `/viewer/runs/${encodePathSegment(runId)}/race`
}
