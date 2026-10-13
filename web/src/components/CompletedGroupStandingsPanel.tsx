import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'

import {
  generateAdminCompletedGroupStandings, getAdminCompletedGroupStandings,
  getAdminGroupTieResolutionState,
} from '../api/client'
import { newCommandId } from '../admin/branchSimulation'
import { formatApiError, isApiNotFound } from '../utils/apiErrors'

type Props = { runId: string; branchId: string; eventId: string; enabled: boolean }

/**
 * Never derives positions from current matches or fabricated scorelines:
 * renders only immutable production Group Standings authority.
 */
export function CompletedGroupStandingsPanel({
  runId, branchId, eventId, enabled,
}: Props): JSX.Element {
  const client = useQueryClient()
  const [confirmed, setConfirmed] = useState(false)
  const [commandId, setCommandId] = useState(() => newCommandId())
  const key = ['admin-completed-group-standings', runId, branchId, eventId]
  const standings = useQuery({
    queryKey: key,
    queryFn: () => getAdminCompletedGroupStandings(runId, branchId, eventId),
    enabled: enabled && Boolean(runId && branchId && eventId),
    retry: false,
  })
  const absent = isApiNotFound(standings.error)
  const tieState = useQuery({
    queryKey: ['admin-group-tie-resolution', runId, branchId, eventId],
    queryFn: () => getAdminGroupTieResolutionState(runId, branchId, eventId),
    enabled: enabled && absent && Boolean(runId && branchId && eventId),
    retry: false,
  })
  const unresolved = tieState.data?.unresolved_case
  const generate = useMutation({
    mutationFn: () => generateAdminCompletedGroupStandings(runId, branchId, eventId, commandId),
    onSuccess: async (data) => {
      client.setQueryData(key, data)
      setConfirmed(false)
      setCommandId(newCommandId())
      await Promise.all([
        client.invalidateQueries({ queryKey: ['canonical-tournament-preparation', runId, branchId, eventId] }),
        client.invalidateQueries({ queryKey: ['admin-group-tie-resolution', runId, branchId, eventId] }),
      ])
    },
    onError: async () => {
      await tieState.refetch()
    },
  })

  useEffect(() => {
    setConfirmed(false)
    setCommandId(newCommandId())
  }, [runId, branchId, eventId])

  return <section className="panel" aria-label="Canonical completed group standings">
    <h3>Completed group standings</h3>
    <p>
      This is a final, immutable table derived from authoritative played match
      results and explicit tie decisions, never an estimate from the Match Schedule.
    </p>
    {standings.isPending && enabled ? <p role="status">Loading frozen group tables…</p> : null}
    {standings.error && !absent ? (
      <p role="alert">Frozen Group Standings could not be verified: {formatApiError(standings.error)}</p>
    ) : null}
    {standings.data ? (
      <>
        <p role="status">Frozen authority: <code>{standings.data.authority_fingerprint}</code></p>
        {standings.data.groups.map(group => (
          <div key={group.group_index}>
            <h4>Group {group.group_index}</h4>
            <table aria-label={`Canonical group ${group.group_index} standings`}>
              <thead><tr><th>Pos.</th><th>Player ID</th><th>W</th><th>L</th><th>Group pts</th><th>Games</th><th>Points</th></tr></thead>
              <tbody>{group.rows.map(row => (
                <tr key={row.player_id}>
                  <td>{row.position}</td>
                  <td><code>{row.player_id}</code></td>
                  <td>{row.wins}</td><td>{row.losses}</td><td>{row.group_points}</td>
                  <td>{row.games_won}–{row.games_lost}</td>
                  <td>{row.points_won}–{row.points_lost}</td>
                </tr>
              ))}</tbody>
            </table>
          </div>
        ))}
        <p className="status">This table is not a Saved Revision until Simulation Save succeeds.</p>
      </>
    ) : null}
    {absent && !standings.data ? (
      <div className="grid">
        <p role="status">No completed group-table authority is stored. The Match Schedule alone is not a result.</p>
        <p><Link to={`/admin/runs/${encodeURIComponent(runId)}/simulate?branch=${encodeURIComponent(branchId)}`}>
          Open authoritative Simulation to play all group Match Days
        </Link></p>
        {unresolved ? <p role="alert">
          Group {unresolved.group_index} has an unresolved tie among
          {' '}{unresolved.player_ids.join(', ')} ({unresolved.reason}).
          An explicit audited Admin ordering is required; no automatic ordering is permitted.
        </p> : null}
        {tieState.error && !isApiNotFound(tieState.error) &&
          (tieState.error as { status?: number }).status !== 409 ? (
          <p role="alert">Tie-resolution status unavailable: {formatApiError(tieState.error)}</p>
        ) : null}
        <label><input type="checkbox" checked={confirmed}
          onChange={e => setConfirmed(e.target.checked)}/>
          Confirm generation from all completed canonical group matches
        </label>
        <button type="button"
          disabled={!confirmed || !enabled || Boolean(unresolved) || generate.isPending ||
            (tieState.isPending && !tieState.isError)}
          onClick={() => generate.mutate()}>
          Generate canonical group standings
        </button>
        {generate.error ? <p role="alert">Group Standings generation blocked:
          {' '}{formatApiError(generate.error)}</p> : null}
      </div>
    ) : null}
  </section>
}
