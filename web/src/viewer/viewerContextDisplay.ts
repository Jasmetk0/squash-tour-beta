export type ViewerContextDisplayInput = {
  selectedSeason: string
  selectedWeek: number
  seasonWeekCount: number
  calendarYear: number
  yearWeek: number
}

export type ViewerContextSummaryItem = {
  label: 'Season Week' | 'Calendar Year' | 'Year Week' | 'Status'
  value: string
}

export function formatViewerSeasonLabel(season: string): string {
  return `Season ${season}`
}

export function formatViewerWeekLabel(week: number): string {
  return `W${week}`
}

export function formatViewerContextButtonLabel(context: Pick<ViewerContextDisplayInput, 'selectedSeason' | 'selectedWeek'>): string {
  return `Week ${formatViewerWeekLabel(context.selectedWeek)}`
}

export function formatViewerContextFullLabel(context: Pick<ViewerContextDisplayInput, 'selectedSeason' | 'selectedWeek'>): string {
  return `${formatViewerSeasonLabel(context.selectedSeason)} · ${formatViewerWeekLabel(context.selectedWeek)}`
}

export function formatViewerContextStatus(): string {
  return 'selected viewer context; stored locally in this browser.'
}

export function normalizeViewerWeekInput(week: string): number {
  return Number(week)
}

export function buildViewerContextSummaryItems(context: ViewerContextDisplayInput): ViewerContextSummaryItem[] {
  return [
    { label: 'Season Week', value: `${context.selectedWeek} / ${context.seasonWeekCount}` },
    { label: 'Calendar Year', value: String(context.calendarYear) },
    { label: 'Year Week', value: String(context.yearWeek) },
    { label: 'Status', value: formatViewerContextStatus() }
  ]
}
