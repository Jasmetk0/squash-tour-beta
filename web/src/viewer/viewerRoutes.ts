type ViewerPathSegment = string | number

function encodePathSegment(segment: ViewerPathSegment): string {
  return encodeURIComponent(String(segment))
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
