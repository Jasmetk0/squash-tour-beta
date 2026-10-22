import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import type { RunHomeRankingChanges } from '../api/types'

import { RunHomeRankingPanel } from './RunHomeRankingPanel'
import { RunHomeProgress, runHomeClock } from './RunHomeProgress'

const data: RunHomeRankingChanges = {
  schema_version: 'run_home_ranking_changes.v1',
  run_id: 'run-1', branch_id: 'timeline-1', saved_revision_id: 'saved-1',
  source: 'selected_branch_saved_revision',
  status: 'ready', previous_week_ordinal: 51, current_week_ordinal: 52,
  current_row_count: 0, total_change_count: 0, moved_count: 0,
  entered_count: 0, exited_count: 0, points_only_count: 0, changes: [],
}

const earth = { weeks_per_year: 52, season_count: 3, start_year: 2030, season_start_year_week: 1 }
const fax = { weeks_per_year: 61, season_count: 50, start_year: 2000, season_start_year_week: 37 }
const extended = { weeks_per_year: 80, season_count: 3, start_year: 2040, season_start_year_week: 37 }

describe('Run-local Saved Ranking movement week labels', () => {
  it('uses 52 weeks and calendar years for Earth instead of legacy FAX 61', () => {
    render(<RunHomeRankingPanel data={data} locale="en" clock={earth} />)
    expect(screen.getByText(/2030 · W52 → 2031 · W1/)).toBeInTheDocument()
    expect(screen.queryByText(/2000\/01 · W52/)).not.toBeInTheDocument()
  })

  it('preserves reference FAX week labels at the 61-week season boundary', () => {
    render(<RunHomeRankingPanel data={{ ...data, previous_week_ordinal: 60, current_week_ordinal: 61 }}
      locale="cs" clock={fax} />)
    expect(screen.getByText(/2000\/01 · W61 → 2001\/02 · W1/)).toBeInTheDocument()
  })

  it('uses a custom 80-week Run with its own season start year and cross-season boundary', () => {
    render(<RunHomeRankingPanel data={{ ...data, previous_week_ordinal: 79, current_week_ordinal: 80 }}
      locale="en" clock={extended} />)
    expect(screen.getByText(/2040\/41 · W80 → 2041\/42 · W1/)).toBeInTheDocument()
  })

  it('shows first publication using W80 rather than inventing a 61-week date', () => {
    render(<RunHomeRankingPanel data={{ ...data, status: 'first_publication', previous_week_ordinal: null,
      current_week_ordinal: 100 }} locale="en" clock={extended} />)
    expect(screen.getByText(/2041\/42 · W21/)).toBeInTheDocument()
  })

  it('does not invent a week when the calendar is corrupt or the ordinal exceeds the Run horizon', () => {
    const { unmount } = render(<RunHomeRankingPanel data={data} locale="en" clock={null} />)
    expect(screen.getByText(/Run calendar is unavailable; ranking week labels are not inferred/)).toBeInTheDocument()
    expect(screen.getByText(/— → —/)).toBeInTheDocument()
    unmount()
    render(<RunHomeRankingPanel data={{ ...data, current_week_ordinal: 104 }}
      locale="en" clock={{ ...earth, season_count: 1 }} />)
    expect(screen.getByText(/2030 · W52 → —/)).toBeInTheDocument()
  })

  it('uses the same year naming convention as the Run Home timeline', () => {
    render(<RunHomeProgress season={1} week={1} loading={false} unavailable={false}
      historical={false} locale="en" clock={runHomeClock({
        run_calendar: { schema_version: 'run_calendar.v1', ...earth },
      })} />)
    expect(screen.getByTitle('2031')).toBeInTheDocument()
  })
})
