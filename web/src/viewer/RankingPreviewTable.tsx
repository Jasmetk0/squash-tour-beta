import { Link } from 'react-router-dom'

import type { RankingPreviewRow } from './rankingPayload'
import { viewerCountryProfilePath, viewerPlayerProfilePath } from './viewerRoutes'

function displayValue(value: unknown): string {
  if (typeof value === 'number' && Number.isFinite(value)) return String(value)
  if (typeof value === 'string') {
    const trimmed = value.trim()
    return trimmed ? trimmed : '—'
  }
  return '—'
}

function playerLabel(row: RankingPreviewRow): string {
  return displayValue(row.playerName ?? row.playerId)
}

function movementLabel(row: RankingPreviewRow): string {
  if (row.movement !== null) return displayValue(row.movement)
  if (row.previousRank !== null) return `Previous ${displayValue(row.previousRank)}`
  return '—'
}

type RankingPreviewTableProps = {
  rows: RankingPreviewRow[]
  ariaLabel?: string
  runId?: string
}

function playerCell(row: RankingPreviewRow, runId?: string): JSX.Element | string {
  const label = playerLabel(row)
  const playerId = displayValue(row.playerId)
  if (!runId || playerId === '—') return label

  return <Link to={viewerPlayerProfilePath(runId, playerId)}>{label}</Link>
}

function countryCell(row: RankingPreviewRow, runId?: string): JSX.Element | string {
  const country = displayValue(row.country)
  if (country === '—') return country
  if (!runId) return country

  return <Link to={viewerCountryProfilePath(runId, country)}>{country}</Link>
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
