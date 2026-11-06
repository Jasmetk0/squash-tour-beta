import type { TourCareerRecords } from './calendarTour'

export type ViewerSignedRecordsFilters = {
  asOfSeason: number | null
  fromSeason: number
  countryCode: string | null
}

const ROOT = import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:8000'

/** Public Viewer endpoint: never read a Working Draft or an Admin branch. */
export async function getViewerSignedTourRecords(
  runId: string,
  filters: ViewerSignedRecordsFilters = { asOfSeason: null, fromSeason: 0, countryCode: null },
  signal?: AbortSignal
): Promise<TourCareerRecords> {
  const url = new URL(ROOT + '/viewer/runs/' + encodeURIComponent(runId) + '/calendar-tour/records')
  if (filters.asOfSeason !== null) url.searchParams.set('as_of_season_index', String(filters.asOfSeason))
  url.searchParams.set('from_season_index', String(filters.fromSeason))
  url.searchParams.set('leaderboard_limit', '20')
  if (filters.countryCode !== null) url.searchParams.set('country_code', filters.countryCode)
  const response = await fetch(url.toString(), { signal })
  if (!response.ok) throw new Error('Viewer signed records HTTP ' + response.status)
  return await response.json() as TourCareerRecords
}
