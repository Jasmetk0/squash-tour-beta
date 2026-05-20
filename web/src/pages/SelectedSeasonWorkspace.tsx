import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'

import { getAdminPointBreakdown, getAdminRankingSnapshot, getAdminRankingTable, getSeasonActivePlayers, getSeasonCalendar, getSeasonRegistry } from '../api/client'
import { SectionCard, SummaryPills } from '../components/RunScopedUi'
import { formatApiError } from '../utils/apiErrors'
import { safeToCompactSeasonLabel, safeToLongSeasonLabel } from '../utils/seasonLabels'

type Props = {
  selectedSeasonRaw: string | null
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
          <p className="status">Raw label: {selectedSeasonRaw}</p>
        </>
      ) : (
        <>
          <SummaryPills items={[
            { label: 'Compact label', value: selectedCompactSeason ?? 'Unavailable' },
            { label: 'Legacy label', value: selectedLongSeason ?? 'Unavailable' },
            { label: 'Registry status', value: selectedRegistryEntry?.status ?? 'Valid label; not in fixed registry' },
            { label: 'Start year', value: selectedRegistryEntry?.season_start_year ?? 'Unknown' },
            { label: 'Season index', value: selectedRegistryEntry?.season_index ?? 'Unknown' },
            { label: 'Week count', value: selectedRegistryEntry?.week_count ?? 'Unknown' },
            { label: 'Season week range', value: selectedRegistryEntry ? `SW${selectedRegistryEntry.season_week_start}–SW${selectedRegistryEntry.season_week_end}` : 'Unknown' },
            { label: 'Year week range', value: selectedRegistryEntry ? `YW${selectedRegistryEntry.year_week_start}–YW${selectedRegistryEntry.year_week_end}` : 'Unknown' },
            { label: 'SW1 year week', value: selectedSeasonRegistryQuery.data?.season_week_1_year_week ?? 'Unknown' }
          ]} />
          {!selectedRegistryEntry ? <p className="status">This season label is valid but not present in the fixed registry.</p> : null}
          <h3>Operational status preview</h3>
          <SummaryPills items={[
            { label: 'Active players', value: selectedSeasonPlayersQuery.data ? `Loaded (${selectedSeasonPlayersQuery.data.summary.total_active_players})` : `Unavailable${selectedSeasonPlayersQuery.error ? ` (${formatApiError(selectedSeasonPlayersQuery.error)})` : ''}` },
            { label: 'Calendar', value: selectedSeasonCalendarQuery.data?.summary ? `Loaded (${selectedSeasonCalendarQuery.data.summary.event_count})` : `Unavailable${selectedSeasonCalendarQuery.error ? ` (${formatApiError(selectedSeasonCalendarQuery.error)})` : ''}` },
            { label: 'Ranking table', value: selectedSeasonRankingQuery.data ? `Loaded (${selectedSeasonRankingQuery.data.rows.length})` : `Unavailable${selectedSeasonRankingQuery.error ? ` (${formatApiError(selectedSeasonRankingQuery.error)})` : ''}` },
            { label: 'Ranking snapshot W1', value: selectedSeasonRankingSnapshotQuery.data?.summary ? `Loaded (${selectedSeasonRankingSnapshotQuery.data.summary.ranking.player_count})` : `Unavailable${selectedSeasonRankingSnapshotQuery.error ? ` (${formatApiError(selectedSeasonRankingSnapshotQuery.error)})` : ''}` },
            { label: 'Point breakdowns', value: selectedSeasonPointBreakdownQuery.data ? `Loaded (${selectedSeasonPointBreakdownQuery.data.summary_rows.length})` : `Unavailable${selectedSeasonPointBreakdownQuery.error ? ` (${formatApiError(selectedSeasonPointBreakdownQuery.error)})` : ''}` }
          ]} />
          <h3>Selected season navigation</h3>
          <ul className="dashboard-help-list">
            <li><Link to="/admin/tour-seasons/season-registry">Back to Season Registry</Link></li>
            <li><Link to="/admin/tour-seasons/season-registry">Open Season Registry</Link></li>
            <li><Link to="/admin/tour-seasons/validation">Open Calendar Validation</Link></li>
            <li><Link to="/admin/tour-seasons/compare">Open Calendar Compare / Apply</Link></li>
            <li>Concrete season detail page — planned.</li>
            <li>Season editor — planned.</li>
            <li>Build from template — planned.</li>
            <li>Compare/apply — planned.</li>
          </ul>
        </>
      )}
    </SectionCard>
  )
}
