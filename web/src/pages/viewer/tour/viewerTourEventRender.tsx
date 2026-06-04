import type { ReactNode } from 'react'
import { Link } from 'react-router-dom'

import type { EventRecord } from '../../../api/types'
import { viewerPlannedEventPath, viewerWeekDetailPath } from '../../../viewer/viewerRoutes'
import type { OrderedSeasonEvent } from './viewerTourDisplay'

export function renderLinkedEventId(runId: string, eventId: string | null | undefined): ReactNode {
  if (!eventId) return '—'
  return <Link to={viewerPlannedEventPath(runId, eventId)}>{eventId}</Link>
}

export function renderLinkedWeek(runId: string, week: number | string | null | undefined): ReactNode {
  if (week == null || week === '') return '—'
  return <Link to={viewerWeekDetailPath(runId, week)}>W{week}</Link>
}

export function renderOrderedEventMetadata(event: OrderedSeasonEvent, runId?: string): JSX.Element {
  const eventId = runId ? renderLinkedEventId(runId, event.event_id) : event.event_id
  const week = runId ? renderLinkedWeek(runId, event.week) : event.week

  return (
    <dl className="metadata-list">
      <div><dt>Event ID</dt><dd>{eventId}</dd></div>
      <div><dt>Week</dt><dd>{week}</dd></div>
      <div><dt>Category</dt><dd>{event.category}</dd></div>
      <div><dt>Tour</dt><dd>{event.tour}</dd></div>
      <div><dt>Template ID</dt><dd>{event.template_id}</dd></div>
    </dl>
  )
}

export function renderEventSummary(event: OrderedSeasonEvent, runId: string): ReactNode {
  return <>{renderLinkedEventId(runId, event.event_id)} · {renderLinkedWeek(runId, event.week)} · {event.category} · {event.tour} · {event.template_id}</>
}

export function renderPersistedEventSummary(event: EventRecord | null, plannedMap: Map<string, OrderedSeasonEvent>, runId?: string): ReactNode {
  if (!event) return '—'
  const planned = plannedMap.get(event.event_id)
  const week = event.week ?? planned?.week ?? null
  const templateId = event.template_id ?? planned?.template_id ?? '—'
  const category = planned?.category ?? '—'
  const tour = planned?.tour ?? '—'
  const eventId = runId ? renderLinkedEventId(runId, event.event_id) : event.event_id
  const weekValue = runId ? renderLinkedWeek(runId, week) : week != null ? `W${week}` : 'W—'
  return <>{eventId} · {weekValue} · {category} · {tour} · {templateId}</>
}
