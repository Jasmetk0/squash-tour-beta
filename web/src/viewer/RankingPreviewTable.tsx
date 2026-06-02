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

export function RankingPreviewTable({ rows, ariaLabel = 'Top 10 ranking preview table' }: { rows: RankingPreviewRow[]; ariaLabel?: string }): JSX.Element {
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
            <td>{playerLabel(row)}</td>
            <td>{displayValue(row.country)}</td>
            <td>{displayValue(row.points)}</td>
            <td>{displayValue(row.tournamentsCounted)}</td>
            <td>{movementLabel(row)}</td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}
