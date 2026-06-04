import type { ReactNode } from 'react'
import { Link } from 'react-router-dom'

import type { EventRecord } from '../../../api/types'
import {
  viewerRaceSnapshotPath,
  viewerRankingSnapshotPath,
  viewerTournamentDetailPath
} from '../../../viewer/viewerRoutes'
import type { OrderedSeasonEvent } from '../tour/viewerTourDisplay'
import { renderLinkedEventId, renderLinkedWeek } from '../tour/viewerTourEventRender'
import type { RunActivityItem } from '../../../api/types'

export type ActivityLinkContext = {
  plannedEvents: Map<string, OrderedSeasonEvent>
  persistedEvents: Map<string, EventRecord>
}

export function renderActivityItem(item: RunActivityItem, runId: string, context: ActivityLinkContext): ReactNode {
  const eventId = item.event_id
  const plannedEvent = eventId ? context.plannedEvents.get(eventId) : null
  const persistedEvent = eventId ? context.persistedEvents.get(eventId) : null
  const resolvedWeek = plannedEvent?.week ?? persistedEvent?.week ?? null

  const parts: ReactNode[] = [item.label]
  if (item.season != null) parts.push(`Season ${item.season}`)
  if (resolvedWeek != null) {
    parts.push(renderLinkedWeek(runId, resolvedWeek))
  } else if (item.week != null) {
    parts.push(`W${item.week}`)
  }
  if (eventId) {
    parts.push(plannedEvent ? renderLinkedEventId(runId, eventId) : eventId)
    if (persistedEvent) {
      parts.push(<Link to={viewerTournamentDetailPath(runId, eventId)}>Tournament detail {eventId}</Link>)
    }
  }
  if (item.snapshot_sequence != null) {
    if (item.kind === 'ranking_snapshot') {
      parts.push(<Link to={viewerRankingSnapshotPath(runId, item.snapshot_sequence)}>Ranking snapshot #{item.snapshot_sequence}</Link>)
    } else if (item.kind === 'race_snapshot') {
      parts.push(<Link to={viewerRaceSnapshotPath(runId, item.snapshot_sequence)}>Race snapshot #{item.snapshot_sequence}</Link>)
    }
  }

  return parts.map((part, index) => (
    <span key={index}>
      {index > 0 ? ' · ' : null}
      {part}
    </span>
  ))
}
