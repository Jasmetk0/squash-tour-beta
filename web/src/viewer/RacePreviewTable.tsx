import { Link } from 'react-router-dom'

import type { RacePreviewRow } from './racePayload'

function displayValue(value: number | string | null): string {
  return value === null ? '—' : String(value)
}

function playerLabel(row: RacePreviewRow): string {
  return row.playerName ?? row.playerId ?? '—'
}

type RacePreviewTableProps = {
  rows: RacePreviewRow[]
  ariaLabel?: string
  runId?: string
}

function playerCell(row: RacePreviewRow, runId?: string): JSX.Element | string {
  const label = playerLabel(row)
  if (!runId || !row.playerId) return label

  return <Link to={`/viewer/runs/${encodeURIComponent(runId)}/players/${encodeURIComponent(row.playerId)}/career`}>{label}</Link>
}

function countryCell(row: RacePreviewRow, runId?: string): JSX.Element | string {
  if (!row.country) return '—'
  if (!runId) return row.country

  return <Link to={`/viewer/runs/${encodeURIComponent(runId)}/countries/${encodeURIComponent(row.country)}`}>{row.country}</Link>
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
