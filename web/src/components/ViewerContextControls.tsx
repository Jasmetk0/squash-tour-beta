import { useEffect, useState } from 'react'

import { useViewerContext } from '../viewer/ViewerContext'
import {
  buildViewerContextSummaryItems,
  formatViewerContextButtonLabel,
  formatViewerContextFullLabel,
  formatViewerWeekLabel,
  normalizeViewerWeekInput
} from '../viewer/viewerContextDisplay'

export function ViewerSeasonWeekSelector(): JSX.Element {
  const context = useViewerContext()
  const [expanded, setExpanded] = useState(false)
  const [draftSeason, setDraftSeason] = useState(context.selectedSeason)
  const [draftWeek, setDraftWeek] = useState(String(context.selectedWeek))

  useEffect(() => {
    setDraftSeason(context.selectedSeason)
    setDraftWeek(String(context.selectedWeek))
  }, [context.selectedSeason, context.selectedWeek])

  const contextSummaryItems = buildViewerContextSummaryItems(context)
  const fullContextLabel = formatViewerContextFullLabel(context)

  function updateViewerContext(): void {
    context.setViewerContext(draftSeason, normalizeViewerWeekInput(draftWeek))
  }

  return (
    <div className="viewer-context-selector">
      <button
        type="button"
        className="viewer-context-selector__button"
        aria-expanded={expanded}
        aria-controls="viewer-context-selector-panel"
        aria-label={fullContextLabel}
        title={fullContextLabel}
        onClick={() => setExpanded((current) => !current)}
      >
        {formatViewerContextButtonLabel(context)}
      </button>
      {expanded ? (
        <div id="viewer-context-selector-panel" className="viewer-context-selector__panel" role="region" aria-label="Viewer season and week context controls">
          <p className="viewer-context-selector__summary">{fullContextLabel}</p>
          <label className="field-label" htmlFor="viewer-season-input">Selected season</label>
          <input
            id="viewer-season-input"
            aria-label="Selected season"
            value={draftSeason}
            onChange={(event) => setDraftSeason(event.target.value)}
          />
          <label className="field-label" htmlFor="viewer-week-input">Selected week</label>
          <input
            id="viewer-week-input"
            aria-label="Selected week"
            type="number"
            min="1"
            max={context.seasonWeekCount}
            value={draftWeek}
            onChange={(event) => setDraftWeek(event.target.value)}
          />
          <button type="button" className="viewer-context-selector__update" onClick={updateViewerContext}>
            Set Viewer Week
          </button>
          {contextSummaryItems.map((item) => (
            <p key={item.label}>{item.label}: {item.value}</p>
          ))}
        </div>
      ) : null}
    </div>
  )
}

export function ViewerJumpToWeekButton({ week }: { week: number }): JSX.Element {
  const { setSelectedWeek } = useViewerContext()

  return (
    <button type="button" className="viewer-jump-button" onClick={() => setSelectedWeek(week)}>
      Jump to {formatViewerWeekLabel(week)}
    </button>
  )
}
