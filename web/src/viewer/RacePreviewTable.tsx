import type { RacePreviewRow } from './racePayload'

function displayValue(value: number | string | null): string {
  return value === null ? '—' : String(value)
}

function playerLabel(row: RacePreviewRow): string {
  return row.playerName ?? row.playerId ?? '—'
}

export function RacePreviewTable({ rows, ariaLabel = 'Top 10 race preview table' }: { rows: RacePreviewRow[]; ariaLabel?: string }): JSX.Element {
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
            <td>{playerLabel(row)}</td>
            <td>{displayValue(row.country)}</td>
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
