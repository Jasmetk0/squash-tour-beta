import type { RunContainer, RunSummary } from '../api/types'
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

function formatSafeRunOptionValue(value: unknown): string {
  if (typeof value === 'string') return value
  if (typeof value === 'number') return String(value)
  if (typeof value === 'boolean') return String(value)
  return '—'
}

export type ViewerActiveRunQuickLink = {
  label: string
  to: string
}

export function formatViewerRunOptionLabel(run: ViewerRunOptionSummary): string {
  return `${formatSafeRunOptionValue(run.run_id)} — season ${formatSafeRunOptionValue(run.season)}, seed ${formatSafeRunOptionValue(run.seed)}`
}

export function formatViewerCompactRunOptionLabel(run: ViewerRunOptionSummary): string {
  return `${formatSafeRunOptionValue(run.run_id)} · S${formatSafeRunOptionValue(run.season)} · seed ${formatSafeRunOptionValue(run.seed)}`
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

export function formatViewerProductRunOptionLabel(run: RunContainer, compact = false): string {
  const name = formatSafeRunOptionValue(run.display_name) === '—' ? run.run_id : formatSafeRunOptionValue(run.display_name)
  const suffix = `${formatSafeRunOptionValue(run.run_id)} · ${formatSafeRunOptionValue(run.status)} · ${formatSafeRunOptionValue(run.storage_kind)}${run.read_only === true ? ' · read-only' : ''}`
  return compact ? `${name} · ${suffix}` : `${name} — Product Run ${suffix}`
}
