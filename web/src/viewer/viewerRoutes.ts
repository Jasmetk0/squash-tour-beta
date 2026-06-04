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

export function viewerTopNextGenRankingPath(): string {
  return '/viewer/rankings/next-gen'
}

export function viewerTopEloRankingPath(): string {
  return '/viewer/rankings/elo'
}

export function viewerTopPowerRankingPath(): string {
  return '/viewer/rankings/power'
}

export function viewerTopFormRankingPath(): string {
  return '/viewer/rankings/form'
}

export function viewerTopNo1HistoryPath(): string {
  return '/viewer/rankings/no1-history'
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

export function viewerTopTourMatchesPath(): string {
  return '/viewer/tour/matches'
}

export function viewerTopTourCategoriesPath(): string {
  return '/viewer/tour/categories'
}

export function viewerTopTourChampionsPath(): string {
  return '/viewer/tour/champions'
}

export function viewerTopTournamentsPath(): string {
  return '/viewer/tournaments'
}

export function viewerTopPlayersPath(): string {
  return '/viewer/players'
}

export function viewerTopAllPlayersPath(): string {
  return '/viewer/players/all'
}

export function viewerTopActivePlayersPath(): string {
  return '/viewer/players/active'
}

export function viewerTopNextGenPlayersPath(): string {
  return '/viewer/players/next-gen'
}

export function viewerTopRetiredPlayersPath(): string {
  return '/viewer/players/retired'
}

export function viewerTopPlayerComparePath(): string {
  return '/viewer/players/compare'
}

export function viewerTopCountriesPath(): string {
  return '/viewer/countries'
}

export function viewerTopCountryRankingPath(): string {
  return '/viewer/countries/ranking'
}

export function viewerTopAllCountriesPath(): string {
  return '/viewer/countries/all'
}

export function viewerTopHostingCountriesPath(): string {
  return '/viewer/countries/hosting'
}

export function viewerTopTalentPipelineCountriesPath(): string {
  return '/viewer/countries/talent-pipeline'
}

export function viewerTopCountryRecordsPath(): string {
  return '/viewer/countries/records'
}

export function viewerTopStatsPath(): string {
  return '/viewer/stats'
}

export function viewerTopStatsTitleLeadersPath(): string {
  return '/viewer/stats/title-leaders'
}

export function viewerTopStatsNo1WeeksPath(): string {
  return '/viewer/stats/no1-weeks'
}

export function viewerTopStatsStreaksPath(): string {
  return '/viewer/stats/streaks'
}

export function viewerTopStatsUpsetsPath(): string {
  return '/viewer/stats/upsets'
}

export function viewerTopStatsBestSeasonsPath(): string {
  return '/viewer/stats/best-seasons'
}

export function viewerTopStatsPlayerStatsPath(): string {
  return '/viewer/stats/player-stats'
}

export function viewerTopStatsTournamentStatsPath(): string {
  return '/viewer/stats/tournament-stats'
}

export function viewerTopStatsCountryStatsPath(): string {
  return '/viewer/stats/country-stats'
}

export function viewerTopStatsAwardsPath(): string {
  return '/viewer/stats/awards'
}

export function viewerTopStatsHallOfFamePath(): string {
  return '/viewer/stats/hall-of-fame'
}

export function viewerTopStatsEraRankingsPath(): string {
  return '/viewer/stats/era-rankings'
}

export function viewerTopRecordsPath(): string {
  return '/viewer/records'
}

export function viewerTopPredictionsPath(): string {
  return '/viewer/predictions'
}

export function viewerTopMatchPredictorPath(): string {
  return '/viewer/predictions/match-predictor'
}

export function viewerTopMatchOddsPath(): string {
  return '/viewer/predictions/match-odds'
}

export function viewerTopTournamentOddsPath(): string {
  return '/viewer/predictions/tournament-odds'
}

export function viewerTopFinalsQualificationPredictionPath(): string {
  return '/viewer/predictions/finals-qualification'
}

export function viewerTopSeasonEndNo1PredictionPath(): string {
  return '/viewer/predictions/season-end-no1'
}

export function viewerTopUpsetWatchPath(): string {
  return '/viewer/predictions/upset-watch'
}

export function viewerTopFuturesPath(): string {
  return '/viewer/predictions/futures'
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

export function viewerTopH2HRivalriesPath(): string {
  return '/viewer/h2h/rivalries'
}

export function viewerTopH2HMostPlayedPath(): string {
  return '/viewer/h2h/most-played'
}

export function viewerTopH2HFinalsRivalriesPath(): string {
  return '/viewer/h2h/finals-rivalries'
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
