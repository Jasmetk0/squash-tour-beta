import { Link } from 'react-router-dom'

import type { RankingPreviewRow } from './rankingPayload'

function displayValue(value: number | string | null): string {
  return value === null ? '—' : String(value)
}

function playerLabel(row: RankingPreviewRow): string {
  return row.playerName ?? row.playerId ?? '—'
}

function movementLabel(row: RankingPreviewRow): string {
  if (row.movement !== null) return String(row.movement)
  if (row.previousRank !== null) return `Previous ${row.previousRank}`
  return '—'
}

type RankingPreviewTableProps = {
  rows: RankingPreviewRow[]
  ariaLabel?: string
  runId?: string
}

function playerCell(row: RankingPreviewRow, runId?: string): JSX.Element | string {
  const label = playerLabel(row)
  if (!runId || !row.playerId) return label

  return <Link to={`/viewer/runs/${encodeURIComponent(runId)}/players/${encodeURIComponent(row.playerId)}/career`}>{label}</Link>
}

function countryCell(row: RankingPreviewRow, runId?: string): JSX.Element | string {
  if (!row.country) return '—'
  if (!runId) return row.country

  return <Link to={`/viewer/runs/${encodeURIComponent(runId)}/countries/${encodeURIComponent(row.country)}`}>{row.country}</Link>
}

export function RankingPreviewTable({ rows, ariaLabel = 'Top 10 ranking preview table', runId }: RankingPreviewTableProps): JSX.Element {
  return (
    <table aria-label={ariaLabel}>
      <thead>
        <tr>
          <th scope="col">Rank</th>
          <th scope="col">Player</th>
          <th scope="col">Country</th>
          <th scope="col">Points</th>
          <th scope="col">Tournaments counted</th>
          <th scope="col">Movement</th>
        </tr>
      </thead>
      <tbody>
        {rows.map((row, index) => (
          <tr key={`${row.playerId ?? row.playerName ?? 'ranking-row'}-${row.rank ?? index}`}>
            <td>{displayValue(row.rank)}</td>
            <td>{playerCell(row, runId)}</td>
            <td>{countryCell(row, runId)}</td>
            <td>{displayValue(row.points)}</td>
            <td>{displayValue(row.tournamentsCounted)}</td>
            <td>{movementLabel(row)}</td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}
