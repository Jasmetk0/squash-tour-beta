import type { ViewerLandingLink } from '../../../components/viewer/ViewerLandingComponents'
import {
  viewerCountriesPath,
  viewerPlayersPath,
  viewerRacePath,
  viewerRankingsPath,
  viewerRunsPath,
  viewerSeasonCalendarPath,
  viewerTopMatchPredictorPath,
  viewerTopRecordsPath,
  viewerTopSearchPath,
  viewerTopStatsPath,
  viewerTournamentsPath,
} from '../../../viewer/viewerRoutes'

export function buildRankingDeferredSourceLinks(
  activeRunId: string,
): ViewerLandingLink[] {
  return [
    { label: 'Open active run rankings', to: viewerRankingsPath(activeRunId) },
    { label: 'Open active run race', to: viewerRacePath(activeRunId) },
    {
      label: 'Open active run tournaments',
      to: viewerTournamentsPath(activeRunId),
    },
    {
      label: 'Open active run calendar',
      to: viewerSeasonCalendarPath(activeRunId),
    },
    { label: 'Open run browser', to: viewerRunsPath() },
  ]
}

export function buildTourDeferredSourceLinks(
  activeRunId: string,
): ViewerLandingLink[] {
  return [
    {
      label: 'Open active run calendar',
      to: viewerSeasonCalendarPath(activeRunId),
    },
    {
      label: 'Open active run tournaments',
      to: viewerTournamentsPath(activeRunId),
    },
    { label: 'Open active run rankings', to: viewerRankingsPath(activeRunId) },
    { label: 'Open active run race', to: viewerRacePath(activeRunId) },
    { label: 'Open run browser', to: viewerRunsPath() },
  ]
}

export function buildPredictionDeferredSourceLinks(
  activeRunId: string,
): ViewerLandingLink[] {
  return [
    { label: 'Open match predictor', to: viewerTopMatchPredictorPath() },
    {
      label: 'Open active run tournaments',
      to: viewerTournamentsPath(activeRunId),
    },
    { label: 'Open active run rankings', to: viewerRankingsPath(activeRunId) },
    { label: 'Open active run race', to: viewerRacePath(activeRunId) },
    { label: 'Open run browser', to: viewerRunsPath() },
  ]
}

export function buildStatsDeferredSourceLinks(
  activeRunId: string,
): ViewerLandingLink[] {
  return [
    { label: 'Open records', to: viewerTopRecordsPath() },
    { label: 'Open stats', to: viewerTopStatsPath() },
    {
      label: 'Open active run tournaments',
      to: viewerTournamentsPath(activeRunId),
    },
    { label: 'Open active run rankings', to: viewerRankingsPath(activeRunId) },
    { label: 'Open active run race', to: viewerRacePath(activeRunId) },
    { label: 'Open run browser', to: viewerRunsPath() },
  ]
}

export function buildPlayersDeferredSourceLinks(
  activeRunId: string,
): ViewerLandingLink[] {
  return [
    { label: 'Open active run players', to: viewerPlayersPath(activeRunId) },
    { label: 'Open active run countries', to: viewerCountriesPath(activeRunId) },
    { label: 'Open active run rankings', to: viewerRankingsPath(activeRunId) },
    {
      label: 'Open active run tournaments',
      to: viewerTournamentsPath(activeRunId),
    },
    { label: 'Open Viewer search', to: viewerTopSearchPath() },
    { label: 'Open run browser', to: viewerRunsPath() },
  ]
}

export function buildCountriesDeferredSourceLinks(
  activeRunId: string,
): ViewerLandingLink[] {
  return [
    { label: 'Open active run countries', to: viewerCountriesPath(activeRunId) },
    { label: 'Open active run players', to: viewerPlayersPath(activeRunId) },
    { label: 'Open active run rankings', to: viewerRankingsPath(activeRunId) },
    {
      label: 'Open active run tournaments',
      to: viewerTournamentsPath(activeRunId),
    },
    { label: 'Open Viewer search', to: viewerTopSearchPath() },
    { label: 'Open run browser', to: viewerRunsPath() },
  ]
}
