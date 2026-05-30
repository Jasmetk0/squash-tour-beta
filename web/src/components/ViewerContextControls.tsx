import { useState } from 'react'

import { useViewerContext } from '../viewer/ViewerContext'

export function ViewerSeasonWeekSelector(): JSX.Element {
  const context = useViewerContext()
  const [expanded, setExpanded] = useState(false)

  return (
    <div className="viewer-context-selector">
      <button
        type="button"
        className="viewer-context-selector__button"
        aria-expanded={expanded}
        aria-controls="viewer-context-selector-panel"
        onClick={() => setExpanded((current) => !current)}
      >
        Season {context.selectedSeason} · W{context.selectedWeek}
      </button>
      {expanded ? (
        <div id="viewer-context-selector-panel" className="viewer-context-selector__panel" role="status">
          <p>Season: {context.selectedSeason}</p>
          <p>
            Season Week: {context.selectedWeek} / {context.seasonWeekCount}
          </p>
          <p>Calendar Year: {context.calendarYear}</p>
          <p>Year Week: {context.yearWeek}</p>
          <p>Status: selected viewer context</p>
        </div>
      ) : null}
    </div>
  )
}

export function ViewerJumpToWeekButton({ week }: { week: number }): JSX.Element {
  const { setSelectedWeek } = useViewerContext()

  return (
    <button type="button" className="viewer-jump-button" onClick={() => setSelectedWeek(week)}>
      Jump to W{week}
    </button>
  )
}
