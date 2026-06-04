import type { RunSummary } from '../api/types'
import {
  viewerCountriesPath,
  viewerFinalsPath,
  viewerHistoryPath,
  viewerPlayersPath,
  viewerRacePath,
  viewerRankingsPath,
  viewerSeasonCalendarPath,
  viewerTournamentsPath
} from './viewerRoutes'

type ViewerRunOptionSummary = Pick<RunSummary, 'run_id' | 'season' | 'seed'>

export type ViewerActiveRunQuickLink = {
  label: string
  to: string
}

export function formatViewerRunOptionLabel(run: ViewerRunOptionSummary): string {
  return `${run.run_id} — season ${run.season}, seed ${run.seed}`
}

export function formatViewerCompactRunOptionLabel(run: ViewerRunOptionSummary): string {
  return `${run.run_id} · S${run.season} · seed ${run.seed}`
}

export function formatViewerActiveRunLabel(runId: string | null | undefined): string {
  return runId ?? 'None'
}

export function buildViewerActiveRunQuickLinks(runId: string): ViewerActiveRunQuickLink[] {
  return [
    { label: 'Open calendar', to: viewerSeasonCalendarPath(runId) },
    { label: 'Open rankings', to: viewerRankingsPath(runId) },
    { label: 'Open race', to: viewerRacePath(runId) },
    { label: 'Open tournaments', to: viewerTournamentsPath(runId) },
    { label: 'Open players', to: viewerPlayersPath(runId) },
    { label: 'Open countries', to: viewerCountriesPath(runId) },
    { label: 'Open history', to: viewerHistoryPath(runId) },
    { label: 'Open finals', to: viewerFinalsPath(runId) }
  ]
}
