import { Link, useParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'

import { getSeasonCalendar } from '../api/client'
import { DetailFieldGrid, DetailList } from '../components/DetailUi'
import { PageIntro, SectionCard } from '../components/RunScopedUi'
import { formatApiError } from '../utils/apiErrors'
import { safeToCompactSeasonLabel, safeToLongSeasonLabel } from '../utils/seasonLabels'
import { SelectedSeasonWorkspace } from './SelectedSeasonWorkspace'

type SeasonCalendarPreviewProps = {
  selectedSeasonRaw: string
}

function SeasonCalendarPreview({ selectedSeasonRaw }: SeasonCalendarPreviewProps): JSX.Element {
  const compactLabel = safeToCompactSeasonLabel(selectedSeasonRaw)
  const calendarQuery = useQuery({
    queryKey: ['season-detail-calendar-preview', compactLabel],
    queryFn: () => getSeasonCalendar(compactLabel ?? ''),
    enabled: Boolean(compactLabel),
    retry: false
  })

  if (!compactLabel) {
    return <p className="status">Calendar preview unavailable: invalid season label.</p>
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

export function AdminSeasonDetailPage(): JSX.Element {
  const { seasonLabel: seasonLabelParam = '' } = useParams()
  const seasonLabel = decodeURIComponent(seasonLabelParam)
  const compactLabel = safeToCompactSeasonLabel(seasonLabel)
  const legacyLabel = safeToLongSeasonLabel(seasonLabel)
  const canonicalDetailRoute = compactLabel ? `/admin/seasons/detail/${encodeURIComponent(compactLabel)}` : null

  return (
    <section className="panel">
      <PageIntro
        title="Concrete Season"
        subtitle="Read-only season profile and operational status preview."
      />

      <SectionCard title="Read-only concrete season profile">
        <p>This page does not create, build, simulate, or edit the season.</p>
        <p>Concrete season editor is planned.</p>
        <p>Build from template is planned.</p>
        <p>Compare/apply workflow is planned.</p>
        <DetailFieldGrid fields={[
          { label: 'Raw route label', value: seasonLabelParam },
          { label: 'Decoded route label', value: seasonLabel || 'Unavailable' },
          ...(compactLabel ? [{ label: 'Compact label', value: compactLabel }] : []),
          ...(legacyLabel ? [{ label: 'Legacy label', value: legacyLabel }] : [])
        ]} />
      </SectionCard>

      <SectionCard title="Navigation">
        <DetailList items={[
          <Link key="tour-seasons" to="/admin/tour-seasons">Tour &amp; Seasons</Link>,
          <Link key="season-registry" to="/admin/tour-seasons/season-registry">Season Registry</Link>,
          <Link key="seasons" to="/admin/seasons">Seasons</Link>,
          <Link key="validation" to="/admin/tour-seasons/validation">Calendar Validation</Link>,
          <Link key="compare-apply" to="/admin/tour-seasons/compare">Calendar Compare / Apply</Link>
        ]} emptyLabel="No links." />
      </SectionCard>

      {canonicalDetailRoute ? (
        <SectionCard title="Canonical route">
          <p>Canonical compact detail route: <Link to={canonicalDetailRoute}>{canonicalDetailRoute}</Link></p>
        </SectionCard>
      ) : null}

      <SectionCard title="Related links">
        <p><Link to="/admin/seasons">Back to Seasons</Link></p>
        <p><Link to="/admin/tour-seasons/season-registry">Open Season Registry</Link></p>
        <p><Link to="/admin/tour-seasons/validation">Open Calendar Validation</Link></p>
        <p><Link to="/admin/tour-seasons/compare">Open Calendar Compare / Apply</Link></p>
      </SectionCard>

      <SectionCard title="Calendar preview (read-only)">
        <SeasonCalendarPreview selectedSeasonRaw={seasonLabel} />
      </SectionCard>

      <SelectedSeasonWorkspace selectedSeasonRaw={seasonLabel} />
    </section>
  )
}
