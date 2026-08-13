import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'

import { getSeasonCalendar } from '../api/client'
import { DetailFieldGrid, DetailList } from '../components/DetailUi'
import { formatApiError } from '../utils/apiErrors'
import { safeToCompactSeasonLabel } from '../utils/seasonLabels'

type Props = {
  seasonLabelRaw: string | null
}

import { normalizeEditionRanking } from './seasonEditionRanking'

export function SeasonCalendarPreview({ seasonLabelRaw }: Props): JSX.Element {
  const compactLabel = seasonLabelRaw ? safeToCompactSeasonLabel(seasonLabelRaw) : null
  const calendarQuery = useQuery({
    queryKey: ['season-detail-calendar-preview', compactLabel],
    queryFn: () => getSeasonCalendar(compactLabel ?? ''),
    enabled: Boolean(compactLabel),
    retry: false
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

  const events = (calendar.events ?? []).map((event) => normalizeEditionRanking(event))
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
                  <p><strong>{event.ranking_status === 'ranked' ? 'Ranked' : 'Unranked'}</strong></p>
                  {event.ranking_status === 'ranked' ? <><p className={event.points_table_complete ? 'status' : 'error'}>{event.points_table_complete ? 'Points table complete.' : `Points table incomplete. Missing: ${event.missing_required_point_stages.join(', ')}`}</p><details><summary>Effective points table</summary><pre>{JSON.stringify(event.ranking_points_table, null, 2)}</pre></details></> : <p>Unranked: awards no MSA points or Best N result; tournament history remains.</p>}
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
