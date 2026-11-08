import type { TourCareerRecords, TourSeasonComparison } from './calendarTour'

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:8000'
const path = (runId: string) => API_BASE + '/viewer/runs/' + encodeURIComponent(runId) + '/calendar-tour'

async function read<T>(url: URL, signal?: AbortSignal): Promise<T> {
  const response = await fetch(url.toString(), { method: 'GET', signal })
  if (!response.ok) throw new Error('Signed Viewer season HTTP ' + response.status)
  return await response.json() as T
}

/** Determine real signed closed seasons; legacy calendar season count is not a substitute. */
export function listViewerSignedSeasons(runId: string, signal?: AbortSignal): Promise<TourCareerRecords> {
  const url = new URL(path(runId) + '/records')
  url.searchParams.set('from_season_index', '0')
  url.searchParams.set('leaderboard_limit', '20')
  return read<TourCareerRecords>(url, signal)
}

/** Public Saved Viewer Branch only; never an Admin Working Draft or simulated closure. */
export function readViewerSignedSeason(
  runId: string, seasonIndex: number, comparisonIndex: number | null, signal?: AbortSignal
): Promise<TourSeasonComparison> {
  const url = new URL(path(runId) + '/seasons/' + encodeURIComponent(String(seasonIndex)))
  if (comparisonIndex !== null) url.searchParams.set('compare_to', String(comparisonIndex))
  return read<TourSeasonComparison>(url, signal)
}
