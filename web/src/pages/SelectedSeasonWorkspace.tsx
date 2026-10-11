import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'

import { getAdminPointBreakdown, getAdminRankingSnapshot, getAdminRankingTable, getSeasonActivePlayers, getSeasonCalendar, getSeasonRegistry } from '../api/client'
import { DetailFieldGrid, DetailList } from '../components/DetailUi'
import { SectionCard, SummaryPills } from '../components/RunScopedUi'
import { formatApiError } from '../utils/apiErrors'
import { safeToCompactSeasonLabel, safeToLongSeasonLabel } from '../utils/seasonLabels'

type Props = {
  selectedSeasonRaw: string | null
}

type ReadOnlyStatusCardProps = {
  title: string
  status: string
  details?: string
  error?: string
}

function ReadOnlyStatusCard({ title, status, details, error }: ReadOnlyStatusCardProps): JSX.Element {
  const suffix = error ? ` (${error})` : ''
  return <SummaryPills items={[{ label: title, value: `${status}${suffix}` }, ...(details ? [{ label: `${title} detail`, value: details }] : [])]} />
}

export function SelectedSeasonWorkspace({ selectedSeasonRaw }: Props): JSX.Element | null {
  const selectedCompactSeason = selectedSeasonRaw ? safeToCompactSeasonLabel(selectedSeasonRaw) : null
  const selectedLongSeason = selectedSeasonRaw ? safeToLongSeasonLabel(selectedSeasonRaw) : null
  const selectedSeasonIsValid = selectedSeasonRaw ? Boolean(selectedCompactSeason) : false

  const selectedSeasonRegistryQuery = useQuery({ queryKey: ['selected-season-registry'], queryFn: getSeasonRegistry, enabled: selectedSeasonIsValid, retry: false })
  const selectedSeasonPlayersQuery = useQuery({ queryKey: ['selected-season-players', selectedCompactSeason], queryFn: () => getSeasonActivePlayers(selectedCompactSeason ?? ''), enabled: selectedSeasonIsValid, retry: false })
  const selectedSeasonCalendarQuery = useQuery({ queryKey: ['selected-season-calendar', selectedCompactSeason], queryFn: () => getSeasonCalendar(selectedCompactSeason ?? ''), enabled: selectedSeasonIsValid, retry: false })
  const selectedSeasonRankingQuery = useQuery({ queryKey: ['selected-season-ranking', selectedCompactSeason], queryFn: () => getAdminRankingTable(selectedCompactSeason ?? '', { limit: 5 }), enabled: selectedSeasonIsValid, retry: false })
  const selectedSeasonRankingSnapshotQuery = useQuery({ queryKey: ['selected-season-ranking-snapshot', selectedCompactSeason, 1], queryFn: () => getAdminRankingSnapshot(selectedCompactSeason ?? '', 1), enabled: selectedSeasonIsValid, retry: false })
  const selectedSeasonPointBreakdownQuery = useQuery({
    queryKey: ['selected-season-point-breakdown', selectedCompactSeason],
    queryFn: () => getAdminPointBreakdown(selectedCompactSeason ?? '', { limit: 5, applied_only: true, include_zero_point_awards: false }),
    enabled: selectedSeasonIsValid,
    retry: false
  })

  const selectedRegistryEntry = selectedCompactSeason
    ? (selectedSeasonRegistryQuery.data?.seasons ?? []).find((entry) => entry.label === selectedCompactSeason) ?? null
    : null

  if (!selectedSeasonRaw) {
    return null
  }

  return (
    <SectionCard title="Selected Season Workspace">
      {!selectedSeasonIsValid ? (
        <>
          <p className="error">Selected season label is invalid.</p>
          <h3>Selected Season Identity</h3>
          <DetailFieldGrid fields={[
            { label: 'Raw label', value: selectedSeasonRaw },
            { label: 'Validity status', value: 'Invalid label format' }
          ]} />
        </>
      ) : (
        <>
          <h3>Selected Season Identity</h3>
          <DetailFieldGrid fields={[
            { label: 'Compact label', value: selectedCompactSeason ?? 'Unavailable' },
            { label: 'Legacy label', value: selectedLongSeason ?? 'Unavailable' },
            { label: 'Raw label', value: selectedSeasonRaw },
            { label: 'Validity status', value: 'Valid label format' }
          ]} />

          <h3>Registry Metadata</h3>
          {!selectedRegistryEntry ? <p className="status">This season label is valid but not present in the fixed registry.</p> : null}
          <DetailFieldGrid fields={[
            { label: 'Registry status', value: selectedRegistryEntry?.status ?? 'Unavailable (valid label not in fixed registry)' },
            { label: 'Start year', value: selectedRegistryEntry?.season_start_year ?? 'Unavailable' },
            { label: 'Season index', value: selectedRegistryEntry?.season_index ?? 'Unavailable' },
            { label: 'Week count', value: selectedRegistryEntry?.week_count ?? 'Unavailable' },
            { label: 'Season week range', value: selectedRegistryEntry ? `SW${selectedRegistryEntry.season_week_start}–SW${selectedRegistryEntry.season_week_end}` : 'Unavailable' },
            { label: 'Year week range', value: selectedRegistryEntry ? `YW${selectedRegistryEntry.year_week_start}–YW${selectedRegistryEntry.year_week_end}` : 'Unavailable' },
            { label: 'SW1 year week', value: selectedRegistryEntry ? String(selectedSeasonRegistryQuery.data?.season_week_1_year_week ?? 'Unavailable') : 'Unavailable' }
          ]} />

          <h3>Operational Read-only Preview</h3>
          <ReadOnlyStatusCard title="Active players" status={selectedSeasonPlayersQuery.data ? `Loaded (${selectedSeasonPlayersQuery.data.summary.total_active_players})` : 'Unavailable'} error={selectedSeasonPlayersQuery.error ? formatApiError(selectedSeasonPlayersQuery.error) : undefined} />
          <ReadOnlyStatusCard title="Calendar" status={selectedSeasonCalendarQuery.data?.summary ? `Loaded (${selectedSeasonCalendarQuery.data.summary.event_count})` : 'Unavailable'} error={selectedSeasonCalendarQuery.error ? formatApiError(selectedSeasonCalendarQuery.error) : undefined} />
          <ReadOnlyStatusCard title="Ranking table" status={selectedSeasonRankingQuery.data ? `Loaded (${selectedSeasonRankingQuery.data.rows.length})` : 'Unavailable'} error={selectedSeasonRankingQuery.error ? formatApiError(selectedSeasonRankingQuery.error) : undefined} />
          <ReadOnlyStatusCard title="Ranking snapshot W1" status={selectedSeasonRankingSnapshotQuery.data?.summary ? `Loaded (${selectedSeasonRankingSnapshotQuery.data.summary.ranking.player_count})` : 'Unavailable'} error={selectedSeasonRankingSnapshotQuery.error ? formatApiError(selectedSeasonRankingSnapshotQuery.error) : undefined} />
          <ReadOnlyStatusCard title="Point breakdowns" status={selectedSeasonPointBreakdownQuery.data ? `Loaded (${selectedSeasonPointBreakdownQuery.data.summary_rows.length})` : 'Unavailable'} error={selectedSeasonPointBreakdownQuery.error ? formatApiError(selectedSeasonPointBreakdownQuery.error) : undefined} />

          <h3>Navigation / Planned Workflows</h3>
          <DetailList
            items={[
              <Link key="back-registry" to="/admin/tour-seasons/season-registry">Back to Season Registry</Link>,
              <Link key="open-registry" to="/admin/tour-seasons/season-registry">Open Season Registry</Link>,
              <Link key="open-validation" to="/admin/tour-seasons/validation">Open Calendar Validation</Link>,
              <Link key="open-compare" to="/admin/tour-seasons/compare">Open Calendar Compare / Apply</Link>,
              ...(selectedCompactSeason ? [<Link key="open-concrete-detail" to={`/admin/seasons/detail/${encodeURIComponent(selectedCompactSeason)}`}>Open concrete season detail</Link>] : []),
              'Season editor — planned.',
              'Build from template — planned.',
              'Compare/apply — planned.'
            ]}
            emptyLabel="No links."
          />
        </>
      )}
    </SectionCard>
  )
}
