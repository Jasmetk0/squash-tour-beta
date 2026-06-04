import {
  viewerCountriesPath,
  viewerFinalsPath,
  viewerHistoryPath,
  viewerPlayersPath,
  viewerRacePath,
  viewerRankingsPath,
  viewerRunsPath,
  viewerSeasonCalendarPath,
  viewerTopCountriesPath,
  viewerTopH2HPath,
  viewerTopMatchPredictorPath,
  viewerTopPlayersPath,
  viewerTopPredictionsPath,
  viewerTopRacePath,
  viewerTopRankingsPath,
  viewerTopRecordsPath,
  viewerTopSearchPath,
  viewerTopStatsPath,
  viewerTopTourPath,
  viewerTopTournamentsPath,
  viewerTournamentsPath
} from './viewerRoutes'

export type ViewerHubLink = {
  label: string
  to: string
  description?: string
}

export type ActiveRunHubLinkDefinition = {
  label: string
  href: (runId: string) => string
}

export const activeRunHubLinkDefinitions: ActiveRunHubLinkDefinition[] = [
  { label: 'Active Run Rankings', href: (runId: string) => viewerRankingsPath(runId) },
  { label: 'Active Run Race', href: (runId: string) => viewerRacePath(runId) },
  { label: 'Active Run Tournaments', href: (runId: string) => viewerTournamentsPath(runId) },
  { label: 'Active Run Calendar', href: (runId: string) => viewerSeasonCalendarPath(runId) },
  { label: 'Active Run Players', href: (runId: string) => viewerPlayersPath(runId) },
  { label: 'Active Run Countries', href: (runId: string) => viewerCountriesPath(runId) },
  { label: 'Active Run History', href: (runId: string) => viewerHistoryPath(runId) },
  { label: 'Active Run Finals', href: (runId: string) => viewerFinalsPath(runId) }
]

export function buildActiveRunHubLinks(runId: string): ViewerHubLink[] {
  return activeRunHubLinkDefinitions.map((link) => ({ label: link.label, to: link.href(runId) }))
}

export const viewerTopLevelHubLinks: ViewerHubLink[] = [
  {
    label: 'MSA Rankings',
    to: viewerTopRankingsPath(),
    description: 'Read-only rankings publication for the selected season and week context.'
  },
  {
    label: 'Race to Finals',
    to: viewerTopRacePath(),
    description: 'Read-only Race to Finals publication for the selected Viewer run.'
  },
  {
    label: 'Season Hub',
    to: viewerTopTourPath(),
    description: 'Read-only season hub for the selected Viewer run.'
  },
  {
    label: 'All Tournaments',
    to: viewerTopTournamentsPath(),
    description: 'Read-only tournament hub for active-run tournament and calendar sources.'
  },
  {
    label: 'Players Hub',
    to: viewerTopPlayersPath(),
    description: 'Read-only player hub using active-run player data when available.'
  },
  {
    label: 'Countries Hub',
    to: viewerTopCountriesPath(),
    description: 'Read-only country hub using active-run country and player data when available.'
  },
  {
    label: 'H2H Explorer',
    to: viewerTopH2HPath(),
    description: 'Read-only head-to-head explorer shell backed by active-run player source data.'
  },
  {
    label: 'Stats Hub',
    to: viewerTopStatsPath(),
    description: 'Read-only stats hub for deferred records and statistics groups.'
  },
  {
    label: 'Records',
    to: viewerTopRecordsPath(),
    description: 'Read-only records hub for deferred historical records groups.'
  },
  {
    label: 'Predictions',
    to: viewerTopPredictionsPath(),
    description: 'Read-only predictions hub with deferred forecast outputs.'
  },
  {
    label: 'Match Predictor',
    to: viewerTopMatchPredictorPath(),
    description: 'Read-only match predictor shell using selected player inputs only.'
  },
  {
    label: 'Search',
    to: viewerTopSearchPath(),
    description: 'Read-only Viewer search across safe active-run source data.'
  },
  {
    label: 'Run Browser',
    to: viewerRunsPath(),
    description: 'Browse available generated runs and open run-scoped Viewer pages using existing run list metadata only.'
  }
]
