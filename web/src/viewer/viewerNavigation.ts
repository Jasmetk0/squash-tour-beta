import {
  viewerTopActivePlayersPath,
  viewerTopAllCountriesPath,
  viewerTopAllPlayersPath,
  viewerTopCountriesPath,
  viewerTopCountryRankingPath,
  viewerTopCountryRecordsPath,
  viewerTopEloRankingPath,
  viewerTopFinalsQualificationPredictionPath,
  viewerTopFormRankingPath,
  viewerTopFuturesPath,
  viewerTopH2HFinalsRivalriesPath,
  viewerTopH2HMostPlayedPath,
  viewerTopH2HPath,
  viewerTopH2HRivalriesPath,
  viewerTopHostingCountriesPath,
  viewerTopMatchOddsPath,
  viewerTopMatchPredictorPath,
  viewerTopNextGenPlayersPath,
  viewerTopNextGenRankingPath,
  viewerTopNo1HistoryPath,
  viewerTopPlayerComparePath,
  viewerTopPlayersPath,
  viewerTopPowerRankingPath,
  viewerTopPredictionsPath,
  viewerTopRacePath,
  viewerTopRankingsPath,
  viewerTopRecordsPath,
  viewerTopRetiredPlayersPath,
  viewerTopSeasonEndNo1PredictionPath,
  viewerTopStatsAwardsPath,
  viewerTopStatsBestSeasonsPath,
  viewerTopStatsCountryStatsPath,
  viewerTopStatsEraRankingsPath,
  viewerTopStatsHallOfFamePath,
  viewerTopStatsNo1WeeksPath,
  viewerTopStatsPath,
  viewerTopStatsPlayerStatsPath,
  viewerTopStatsStreaksPath,
  viewerTopStatsTitleLeadersPath,
  viewerTopStatsTournamentStatsPath,
  viewerTopStatsUpsetsPath,
  viewerTopTalentPipelineCountriesPath,
  viewerTopTourCalendarPath,
  viewerTopTourCategoriesPath,
  viewerTopTourChampionsPath,
  viewerTopTourCurrentWeekPath,
  viewerTopTourMatchesPath,
  viewerTopTourPath,
  viewerTopTourTournamentsPath,
  viewerTopTournamentOddsPath,
  viewerTopTournamentsPath,
  viewerTopUpsetWatchPath
} from './viewerRoutes'

export type ViewerNavItem = {
  to: string
  label: string
}

export type ViewerDropdown = {
  label: string
  to: string
  routePrefixes: string[]
  items: ViewerNavItem[]
}

export const viewerDropdowns: ViewerDropdown[] = [
  {
    label: 'Rankings',
    to: viewerTopRankingsPath(),
    routePrefixes: [viewerTopRankingsPath()],
    items: [
      { to: viewerTopRankingsPath(), label: 'MSA Rankings' },
      { to: viewerTopRacePath(), label: 'Race to Finals' },
      { to: viewerTopNextGenRankingPath(), label: 'Next Gen Race' },
      { to: viewerTopEloRankingPath(), label: 'Elo Ranking' },
      { to: viewerTopPowerRankingPath(), label: 'Power Rating' },
      { to: viewerTopFormRankingPath(), label: 'Form Ranking' },
      { to: viewerTopNo1HistoryPath(), label: 'No.1 History' }
    ]
  },
  {
    label: 'Tour',
    to: viewerTopTourPath(),
    routePrefixes: [viewerTopTourPath(), viewerTopTournamentsPath()],
    items: [
      { to: viewerTopTourPath(), label: 'Season Hub' },
      { to: viewerTopTourCalendarPath(), label: 'Season Calendar' },
      { to: viewerTopTourCurrentWeekPath(), label: 'Current Week' },
      { to: viewerTopTourTournamentsPath(), label: 'All Tournaments' },
      { to: viewerTopTourMatchesPath(), label: 'Match Center' },
      { to: viewerTopTourCategoriesPath(), label: 'Tournament Categories' },
      { to: viewerTopTourChampionsPath(), label: 'Past Champions' }
    ]
  },
  {
    label: 'Players',
    to: viewerTopPlayersPath(),
    routePrefixes: [viewerTopPlayersPath()],
    items: [
      { to: viewerTopPlayersPath(), label: 'Players Hub' },
      { to: viewerTopAllPlayersPath(), label: 'All Players' },
      { to: viewerTopActivePlayersPath(), label: 'Active Players' },
      { to: viewerTopNextGenPlayersPath(), label: 'Prospects / Next Gen' },
      { to: viewerTopRetiredPlayersPath(), label: 'Retired Players' },
      { to: viewerTopPlayerComparePath(), label: 'Compare Players' }
    ]
  },
  {
    label: 'Countries',
    to: viewerTopCountriesPath(),
    routePrefixes: [viewerTopCountriesPath()],
    items: [
      { to: viewerTopCountriesPath(), label: 'Countries Hub' },
      { to: viewerTopCountryRankingPath(), label: 'Country Ranking' },
      { to: viewerTopAllCountriesPath(), label: 'All Countries' },
      { to: viewerTopHostingCountriesPath(), label: 'Hosting Nations' },
      { to: viewerTopTalentPipelineCountriesPath(), label: 'Talent Pipeline' },
      { to: viewerTopCountryRecordsPath(), label: 'Country Records' }
    ]
  },
  {
    label: 'H2H',
    to: viewerTopH2HPath(),
    routePrefixes: [viewerTopH2HPath()],
    items: [
      { to: viewerTopH2HPath(), label: 'H2H Explorer' },
      { to: viewerTopH2HRivalriesPath(), label: 'Rivalry Rankings' },
      { to: viewerTopH2HMostPlayedPath(), label: 'Most Played Matchups' },
      { to: viewerTopH2HFinalsRivalriesPath(), label: 'Finals Rivalries' },
      { to: viewerTopPlayerComparePath(), label: 'Player Comparison' },
      { to: viewerTopMatchPredictorPath(), label: 'Predict Matchup' }
    ]
  },
  {
    label: 'Stats',
    to: viewerTopStatsPath(),
    routePrefixes: [viewerTopStatsPath(), viewerTopRecordsPath()],
    items: [
      { to: viewerTopStatsPath(), label: 'Stats Hub' },
      { to: viewerTopRecordsPath(), label: 'Records' },
      { to: viewerTopStatsTitleLeadersPath(), label: 'Title Leaders' },
      { to: viewerTopStatsNo1WeeksPath(), label: 'Weeks at No.1' },
      { to: viewerTopStatsStreaksPath(), label: 'Streaks' },
      { to: viewerTopStatsUpsetsPath(), label: 'Biggest Upsets' },
      { to: viewerTopStatsBestSeasonsPath(), label: 'Best Seasons' },
      { to: viewerTopStatsPlayerStatsPath(), label: 'Player Stats' },
      { to: viewerTopStatsTournamentStatsPath(), label: 'Tournament Stats' },
      { to: viewerTopStatsCountryStatsPath(), label: 'Country Stats' },
      { to: viewerTopStatsAwardsPath(), label: 'Awards' },
      { to: viewerTopStatsHallOfFamePath(), label: 'Hall of Fame' },
      { to: viewerTopStatsEraRankingsPath(), label: 'Era Rankings' }
    ]
  },
  {
    label: 'Predictions',
    to: viewerTopPredictionsPath(),
    routePrefixes: [viewerTopPredictionsPath()],
    items: [
      { to: viewerTopMatchPredictorPath(), label: 'Match Predictor' },
      { to: viewerTopMatchOddsPath(), label: 'Match Odds' },
      { to: viewerTopTournamentOddsPath(), label: 'Tournament Odds' },
      { to: viewerTopFinalsQualificationPredictionPath(), label: 'Finals Qualification' },
      { to: viewerTopSeasonEndNo1PredictionPath(), label: 'Season-End No.1' },
      { to: viewerTopUpsetWatchPath(), label: 'Upset Watch' },
      { to: viewerTopFuturesPath(), label: 'Futures Markets' }
    ]
  }
]
