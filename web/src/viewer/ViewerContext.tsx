import { createContext, useContext, useMemo, useState } from 'react'
import type { ReactNode } from 'react'

export type ViewerSeasonWeekContext = {
  selectedSeason: string
  selectedWeek: number
  seasonWeekCount: number
  calendarYear: number
  yearWeek: number
  setSelectedSeason: (season: string) => void
  setSelectedWeek: (week: number) => void
  setViewerContext: (season: string, week: number) => void
}

export const VIEWER_CONTEXT_STORAGE_KEY = 'beta_engine:viewer_context'

const DEFAULT_SEASON = '2004/05'
const DEFAULT_WEEK = 10
const SEASON_WEEK_COUNT = 61

function clampWeek(week: number): number {
  if (!Number.isFinite(week)) return DEFAULT_WEEK
  return Math.min(Math.max(Math.trunc(week), 1), SEASON_WEEK_COUNT)
}


function normalizeSeason(season: string): string {
  const trimmed = season.trim()
  return trimmed || DEFAULT_SEASON
}

type StoredViewerContext = {
  selectedSeason?: unknown
  selectedWeek?: unknown
}

function readStoredViewerContext(): { selectedSeason: string; selectedWeek: number } {
  if (typeof window === 'undefined') {
    return { selectedSeason: DEFAULT_SEASON, selectedWeek: DEFAULT_WEEK }
  }

  const raw = window.localStorage.getItem(VIEWER_CONTEXT_STORAGE_KEY)
  if (!raw) {
    return { selectedSeason: DEFAULT_SEASON, selectedWeek: DEFAULT_WEEK }
  }

  try {
    const parsed = JSON.parse(raw) as StoredViewerContext
    return {
      selectedSeason: typeof parsed.selectedSeason === 'string' ? normalizeSeason(parsed.selectedSeason) : DEFAULT_SEASON,
      selectedWeek: clampWeek(Number(parsed.selectedWeek))
    }
  } catch {
    return { selectedSeason: DEFAULT_SEASON, selectedWeek: DEFAULT_WEEK }
  }
}

function writeStoredViewerContext(selectedSeason: string, selectedWeek: number): void {
  if (typeof window === 'undefined') return
  window.localStorage.setItem(
    VIEWER_CONTEXT_STORAGE_KEY,
    JSON.stringify({ selectedSeason: normalizeSeason(selectedSeason), selectedWeek: clampWeek(selectedWeek) })
  )
}

function deriveCalendarYear(season: string, seasonWeek: number): number {
  const secondYear = Number.parseInt(season.split('/')[1] ?? '05', 10)
  const fullSecondYear = Number.isFinite(secondYear) ? 2000 + secondYear : 2005
  return seasonWeek <= 17 ? fullSecondYear - 1 : fullSecondYear
}

function deriveYearWeek(seasonWeek: number): number {
  return seasonWeek <= 17 ? seasonWeek + 36 : seasonWeek - 17
}

const ViewerContext = createContext<ViewerSeasonWeekContext | null>(null)

export function ViewerContextProvider({ children }: { children: ReactNode }): JSX.Element {
  const [selectedContext, setSelectedContext] = useState(() => readStoredViewerContext())

  const value = useMemo<ViewerSeasonWeekContext>(() => {
    const selectedSeason = normalizeSeason(selectedContext.selectedSeason)
    const selectedWeek = clampWeek(selectedContext.selectedWeek)

    function updateContext(nextSeason: string, nextWeek: number): void {
      const normalizedSeason = normalizeSeason(nextSeason)
      const normalizedWeek = clampWeek(nextWeek)
      writeStoredViewerContext(normalizedSeason, normalizedWeek)
      setSelectedContext({ selectedSeason: normalizedSeason, selectedWeek: normalizedWeek })
    }

    return {
      selectedSeason,
      selectedWeek,
      seasonWeekCount: SEASON_WEEK_COUNT,
      calendarYear: deriveCalendarYear(selectedSeason, selectedWeek),
      yearWeek: deriveYearWeek(selectedWeek),
      setSelectedSeason: (season: string) => updateContext(season, selectedWeek),
      setSelectedWeek: (week: number) => updateContext(selectedSeason, week),
      setViewerContext: updateContext
    }
  }, [selectedContext])

  return <ViewerContext.Provider value={value}>{children}</ViewerContext.Provider>
}

export function useViewerContext(): ViewerSeasonWeekContext {
  const value = useContext(ViewerContext)
  if (!value) {
    throw new Error('useViewerContext must be used within ViewerContextProvider')
  }
  return value
}
