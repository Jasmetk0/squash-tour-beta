import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { FormEvent, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'

import { getSeasonCalendar, updateTournamentEditionRanking } from '../api/client'
import type { SeasonCalendarEvent } from '../api/types'
import { DetailFieldGrid, DetailList } from '../components/DetailUi'
import { formatApiError } from '../utils/apiErrors'
import { safeToCompactSeasonLabel } from '../utils/seasonLabels'

type Props = {
  seasonLabelRaw: string | null
}

type RankingEditorProps = {
  event: SeasonCalendarEvent
  saving: boolean
  save: (status: 'ranked' | 'unranked', table: Record<string, unknown>) => void
}

function RankingEditor({ event, saving, save }: RankingEditorProps): JSX.Element {
  const [status, setStatus] = useState(event.ranking_status)
  const [values, setValues] = useState<Record<string, string>>({})
  const editable = event.status === 'planned' && !saving

  useEffect(() => {
    setStatus(event.ranking_status)
    setValues(Object.fromEntries(event.required_ranking_point_stages.map((stage) => [stage, event.ranking_points_table[stage]?.toString() ?? ''])))
  }, [event])

  function submit(change: FormEvent<HTMLFormElement>): void {
    change.preventDefault()
    const table = { ...event.ranking_points_table }
    for (const stage of event.required_ranking_point_stages) {
      const raw = values[stage]
      if (raw === '' || !/^\d+$/.test(raw)) delete table[stage]
      else table[stage] = Number(raw)
    }
    save(status, table)
  }

  return (
    <form onSubmit={submit}>
      <label>
        <span className="sr-only">Ranking status for {event.event_name}</span>
        <select aria-label={`Ranking status for ${event.event_name}`} value={status} disabled={!editable} onChange={(change) => setStatus(change.target.value as 'ranked' | 'unranked')}>
          <option value="ranked">Ranked</option>
          <option value="unranked">Unranked</option>
        </select>
      </label>
      {status === 'ranked' ? (
        <>
          {event.points_table_complete ? <p>Points table complete.</p> : <p className="error">Points table incomplete. Publication and simulation are blocked. Missing: {event.missing_required_point_stages.join(', ')}</p>}
          <fieldset disabled={!editable}>
            <legend>Required ranking points</legend>
            {event.required_ranking_point_stages.map((stage) => {
              const missing = event.missing_required_point_stages.includes(stage)
              return <label key={stage}>{stage}<input aria-label={`Points for ${stage}`} type="number" min="0" step="1" required value={values[stage] ?? ''} aria-invalid={missing} onChange={(change) => setValues((current) => ({ ...current, [stage]: change.target.value }))} /></label>
            })}
          </fieldset>
          <button type="submit" disabled={!editable}>Save ranking configuration</button>
        </>
      ) : (
        <><p>Unranked: awards no MSA points or Best N result; matches and tournament history are still recorded.</p><button type="submit" disabled={!editable}>Save ranking configuration</button></>
      )}
    </form>
  )
}

export function SeasonCalendarPreview({ seasonLabelRaw }: Props): JSX.Element {
  const queryClient = useQueryClient()
  const compactLabel = seasonLabelRaw ? safeToCompactSeasonLabel(seasonLabelRaw) : null
  const calendarQuery = useQuery({
    queryKey: ['season-detail-calendar-preview', compactLabel],
    queryFn: () => getSeasonCalendar(compactLabel ?? ''),
    enabled: Boolean(compactLabel),
    retry: false
  })
  const rankingMutation = useMutation({
    mutationFn: ({ eventId, status, table }: { eventId: string; status: 'ranked' | 'unranked'; table: Record<string, unknown> }) =>
      updateTournamentEditionRanking(compactLabel ?? '', eventId, { ranking_status: status, ranking_points_table: table }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['season-detail-calendar-preview', compactLabel] })
  })

  if (!compactLabel) {
    return <p className="status">Calendar preview unavailable for invalid season label.</p>
  }
  if (calendarQuery.isLoading) {
    return <p className="status">Loading calendar preview…</p>
  }
  if (calendarQuery.error) {
    return <p className="error">Calendar preview unavailable: {formatApiError(calendarQuery.error)}</p>
  }

  const calendarResponse = calendarQuery.data
  const calendar = calendarResponse?.calendar
  if (!calendarResponse || !calendar) {
    return <p className="status">No calendar exists yet for this season.</p>
  }

  const events = calendar.events ?? []
  const firstTenEvents = events.slice(0, 10)
  const distinctCategories = Array.from(new Set(events.map((event) => event.category).filter(Boolean)))
  const distinctHosts = Array.from(new Set(events.map((event) => event.host_country).filter(Boolean)))
  const distinctRegions = Array.from(new Set(events.map((event) => event.region).filter(Boolean)))

  return (
    <>
      <p className="status">Calendar loaded.</p>
      <DetailFieldGrid fields={[
        { label: 'Event count', value: calendarResponse.summary.event_count },
        { label: 'Persisted status', value: String(calendarResponse.summary.persisted) },
        { label: 'Validation warnings', value: calendarResponse.validation_warnings.length },
        { label: 'First event week', value: calendarResponse.summary.first_event_week ?? '—' },
        { label: 'Last event week', value: calendarResponse.summary.last_event_week ?? '—' },
        { label: 'Distinct categories', value: distinctCategories.length > 0 ? distinctCategories.join(', ') : '—' },
        { label: 'Distinct hosts', value: distinctHosts.length > 0 ? distinctHosts.join(', ') : '—' },
        { label: 'Distinct regions', value: distinctRegions.length > 0 ? distinctRegions.join(', ') : '—' }
      ]} />
      {firstTenEvents.length > 0 ? (
        <table>
          <thead>
            <tr>
              <th>Week block / season week</th>
              <th>Event</th>
              <th>Category</th>
              <th>Host</th>
              <th>Region</th>
              <th>Source template / template id</th>
              <th>Status</th>
              <th>Ranking status</th>
            </tr>
          </thead>
          <tbody>
            {firstTenEvents.map((event) => (
              <tr key={event.event_id}>
                <td>{event.start_season_week ?? event.season_week ?? '—'}</td>
                <td>{event.event_name ?? '—'}</td>
                <td>{event.category ?? '—'}</td>
                <td>{event.host_country ?? '—'}</td>
                <td>{event.region ?? '—'}</td>
                <td>{event.template_id ?? '—'}</td>
                <td>{event.status ?? '—'}</td>
                <td>
                  <RankingEditor event={event} saving={rankingMutation.isPending} save={(status, table) => rankingMutation.mutate({ eventId: event.event_id, status, table })} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      ) : null}
      <p>Showing first 10 events only. Full calendar tooling remains in Seasons.</p>
      <DetailList items={[
        <Link key="open-seasons-tooling" to="/admin/seasons">Open Seasons tooling</Link>,
        <Link key="open-compare-apply" to="/admin/tour-seasons/compare">Open Calendar Compare / Apply</Link>,
        <Link key="open-calendar-validation" to="/admin/tour-seasons/validation">Open Calendar Validation</Link>
      ]} emptyLabel="No links." />
    </>
  )
}
