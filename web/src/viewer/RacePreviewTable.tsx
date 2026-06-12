import { Link } from 'react-router-dom'

import type { RacePreviewRow } from './racePayload'
import { viewerCountryProfilePath, viewerPlayerProfilePath } from './viewerRoutes'

function displayValue(value: unknown): string {
  if (typeof value === 'number' && Number.isFinite(value)) return String(value)
  if (typeof value === 'string') {
    const trimmed = value.trim()
    return trimmed ? trimmed : '—'
  }
  return '—'
}

function playerLabel(row: RacePreviewRow): string {
  return displayValue(row.playerName ?? row.playerId)
}

type RacePreviewTableProps = {
  rows: RacePreviewRow[]
  ariaLabel?: string
  runId?: string
}

function playerCell(row: RacePreviewRow, runId?: string): JSX.Element | string {
  const label = playerLabel(row)
  const playerId = displayValue(row.playerId)
  if (!runId || playerId === '—') return label

  return <Link to={viewerPlayerProfilePath(runId, playerId)}>{label}</Link>
}

function countryCell(row: RacePreviewRow, runId?: string): JSX.Element | string {
  const country = displayValue(row.country)
  if (country === '—') return country
  if (!runId) return country

  return <Link to={viewerCountryProfilePath(runId, country)}>{country}</Link>
}

export function RacePreviewTable({ rows, ariaLabel = 'Top 10 race preview table', runId }: RacePreviewTableProps): JSX.Element {
  return (
    <table aria-label={ariaLabel}>
      <thead>
        <tr>
          <th scope="col">Rank</th>
          <th scope="col">Player</th>
          <th scope="col">Country</th>
          <th scope="col">Race points</th>
          <th scope="col">Tournaments counted</th>
          <th scope="col">Qualification</th>
          <th scope="col">Next max</th>
        </tr>
      </thead>
      <tbody>
        {rows.map((row, index) => (
          <tr key={`${row.playerId ?? row.playerName ?? 'race-row'}-${row.rank ?? index}`}>
            <td>{displayValue(row.rank)}</td>
            <td>{playerCell(row, runId)}</td>
            <td>{countryCell(row, runId)}</td>
            <td>{displayValue(row.racePoints)}</td>
            <td>{displayValue(row.tournamentsCounted)}</td>
            <td>{displayValue(row.qualificationStatus)}</td>
            <td>{displayValue(row.nextMaxPoints)}</td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}
