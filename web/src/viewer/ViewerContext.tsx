import { createContext, useContext, useMemo, useState } from 'react'
import type { ReactNode } from 'react'

export type ViewerSeasonWeekContext = {
  selectedSeason: string
  selectedWeek: number
  seasonWeekCount: number
  calendarYear: number
  yearWeek: number
  setSelectedWeek: (week: number) => void
}

const DEFAULT_SEASON = '2004/05'
const DEFAULT_WEEK = 10
const SEASON_WEEK_COUNT = 61

function clampWeek(week: number): number {
  if (!Number.isFinite(week)) return DEFAULT_WEEK
  return Math.min(Math.max(Math.trunc(week), 1), SEASON_WEEK_COUNT)
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
  const [selectedWeekState, setSelectedWeekState] = useState(DEFAULT_WEEK)

  const value = useMemo<ViewerSeasonWeekContext>(() => {
    const selectedWeek = clampWeek(selectedWeekState)
    return {
      selectedSeason: DEFAULT_SEASON,
      selectedWeek,
      seasonWeekCount: SEASON_WEEK_COUNT,
      calendarYear: deriveCalendarYear(DEFAULT_SEASON, selectedWeek),
      yearWeek: deriveYearWeek(selectedWeek),
      setSelectedWeek: (week: number) => setSelectedWeekState(clampWeek(week))
    }
  }, [selectedWeekState])

  return <ViewerContext.Provider value={value}>{children}</ViewerContext.Provider>
}

export function useViewerContext(): ViewerSeasonWeekContext {
  const value = useContext(ViewerContext)
  if (!value) {
    throw new Error('useViewerContext must be used within ViewerContextProvider')
  }
  return value
}
