import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'

import { getAdminPointBreakdown, getAdminRankingSnapshot, getAdminRankingTable, getSeasonActivePlayers, getSeasonCalendar, getSeasonRegistry } from '../api/client'
import { DetailList } from '../components/DetailUi'
import { formatApiError } from '../utils/apiErrors'
import { safeToCompactSeasonLabel } from '../utils/seasonLabels'

type Props = { seasonLabelRaw: string | null }

type HealthSeverity = 'OK' | 'Info' | 'Warning'

type HealthCheck = {
  name: string
  severity: HealthSeverity
  message: string
  relatedLink?: { label: string, to: string }
}

export function SeasonHealthPreview({ seasonLabelRaw }: Props): JSX.Element {
  const compactLabel = seasonLabelRaw ? safeToCompactSeasonLabel(seasonLabelRaw) : null
  const enabled = Boolean(compactLabel)

  const registryQuery = useQuery({ queryKey: ['selected-season-registry'], queryFn: getSeasonRegistry, enabled, retry: false })
  const calendarQuery = useQuery({ queryKey: ['selected-season-calendar', compactLabel], queryFn: () => getSeasonCalendar(compactLabel ?? ''), enabled, retry: false })
  const playersQuery = useQuery({ queryKey: ['selected-season-players', compactLabel], queryFn: () => getSeasonActivePlayers(compactLabel ?? ''), enabled, retry: false })
  const rankingQuery = useQuery({ queryKey: ['selected-season-ranking', compactLabel], queryFn: () => getAdminRankingTable(compactLabel ?? '', { limit: 5 }), enabled, retry: false })
  const snapshotQuery = useQuery({ queryKey: ['selected-season-ranking-snapshot', compactLabel, 1], queryFn: () => getAdminRankingSnapshot(compactLabel ?? '', 1), enabled, retry: false })
  const pointsQuery = useQuery({
    queryKey: ['selected-season-point-breakdown', compactLabel],
    queryFn: () => getAdminPointBreakdown(compactLabel ?? '', { limit: 5, applied_only: true, include_zero_point_awards: false }),
    enabled,
    retry: false
  })

  if (!compactLabel) {
    return <p className="status">Season health preview unavailable for invalid season label.</p>
  }

  const registryEntry = (registryQuery.data?.seasons ?? []).find((entry) => entry.label === compactLabel)
  const calendarWarnings = calendarQuery.data?.validation_warnings.length ?? 0
  const calendarErrors = calendarQuery.data?.validation_errors.length ?? 0

  const checks: HealthCheck[] = [
    {
      name: 'Registry check',
      severity: registryEntry ? 'OK' : (registryQuery.error ? 'Warning' : 'Info'),
      message: registryQuery.error
        ? `Registry lookup unavailable: ${formatApiError(registryQuery.error)}`
        : registryEntry
          ? `Season ${compactLabel} exists in fixed registry.`
          : 'Valid season label, but no matching fixed-registry entry was found.',
      relatedLink: { label: 'Open Season Registry', to: '/admin/tour-seasons/season-registry' }
    },
    {
      name: 'Calendar check',
      severity: calendarQuery.error ? 'Warning' : (calendarQuery.data?.calendar ? 'OK' : 'Info'),
      message: calendarQuery.error
        ? `Calendar preview unavailable: ${formatApiError(calendarQuery.error)}`
        : calendarQuery.data?.calendar
          ? `Calendar exists (${calendarQuery.data.summary.event_count} events). Warnings: ${calendarWarnings}. Errors: ${calendarErrors}.`
          : 'No calendar currently exists for this season.',
      relatedLink: { label: 'Open Calendar preview section', to: '#calendar-preview' }
    },
    {
      name: 'Active players check',
      severity: playersQuery.error ? 'Warning' : ((playersQuery.data?.summary.total_active_players ?? 0) > 0 ? 'OK' : 'Info'),
      message: playersQuery.error
        ? `Active players unavailable: ${formatApiError(playersQuery.error)}`
        : `Active players loaded: ${playersQuery.data?.summary.total_active_players ?? 0}.`,
      relatedLink: { label: 'Open Seasons', to: '/admin/seasons' }
    },
    {
      name: 'Ranking table check',
      severity: rankingQuery.error ? 'Warning' : ((rankingQuery.data?.summary.player_count ?? 0) > 0 ? 'OK' : 'Info'),
      message: rankingQuery.error
        ? `Ranking table unavailable: ${formatApiError(rankingQuery.error)}`
        : `Ranking rows available: ${rankingQuery.data?.rows.length ?? 0}; players in summary: ${rankingQuery.data?.summary.player_count ?? 0}.`,
      relatedLink: { label: 'Open Ranking & points preview section', to: '#ranking-points-preview' }
    },
    {
      name: 'Ranking snapshot W1 check',
      severity: snapshotQuery.error ? 'Info' : (snapshotQuery.data?.snapshot_exists ? 'OK' : 'Info'),
      message: snapshotQuery.error
        ? 'Ranking snapshot W1 not available in this read-only preview.'
        : snapshotQuery.data?.snapshot_exists
          ? `Snapshot W1 exists with ${snapshotQuery.data.summary?.ranking.player_count ?? 0} rows.`
          : 'No ranking snapshot W1 is currently available.',
      relatedLink: { label: 'Open Ranking & points preview section', to: '#ranking-points-preview' }
    },
    {
      name: 'Point breakdown check',
      severity: pointsQuery.error ? 'Info' : (pointsQuery.data ? 'OK' : 'Info'),
      message: pointsQuery.error
        ? `Point breakdown unavailable: ${formatApiError(pointsQuery.error)}`
        : `Point breakdown loaded with ${pointsQuery.data?.summary_rows.length ?? 0} summary rows.`,
      relatedLink: { label: 'Open Ranking & points preview section', to: '#ranking-points-preview' }
    }
  ]

  return (
    <>
      <p className="status">Read-only health preview. Not an authoritative simulation readiness gate yet.</p>
      <table>
        <thead>
          <tr><th>Check</th><th>Severity</th><th>Message</th><th>Related link</th></tr>
        </thead>
        <tbody>
          {checks.map((check) => (
            <tr key={check.name}>
              <td>{check.name}</td>
              <td>{check.severity}</td>
              <td>{check.message}</td>
              <td>{check.relatedLink ? <Link to={check.relatedLink.to}>{check.relatedLink.label}</Link> : '—'}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <DetailList items={[
        'Authoritative readiness gates are planned for a later phase.',
        'Build/simulate/apply workflows remain disabled in this page.'
      ]} emptyLabel="No notes." />
    </>
  )
}
