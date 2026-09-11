import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { getRankingCandidateInputs } from '../api/client'
import type { CandidateWeek } from '../api/rankingCandidates'
import { formatApiError } from '../utils/apiErrors'

function weekLabel(week: CandidateWeek): string {
  return `${2000 + week.season_index}/${String(2001 + week.season_index).slice(-2)} · Week ${week.week}`
}

export function RankingCandidateInputsPanel({ runId, branchId, week, fingerprint }: {
  runId: string; branchId: string; week: CandidateWeek; fingerprint: string
}): JSX.Element {
  const [opened, setOpened] = useState(false)
  const query = useQuery({
    queryKey: ['ranking-inputs', runId, branchId, week.season_index, week.week, fingerprint],
    queryFn: async () => {
      const data = await getRankingCandidateInputs(runId, branchId, week.season_index, week.week)
      if (data.candidate_fingerprint !== fingerprint) throw new Error('Stored inputs do not match this candidate.')
      return data
    },
    enabled: opened, retry: false,
  })
  return <section aria-label="Stored calculation inputs">
    <h3>Stored calculation inputs</h3>
    <p>Frozen roster and results supplied to this calculation, including players and results absent from the ranking.</p>
    {!opened ? <button type="button" onClick={() => setOpened(true)}>Inspect stored inputs</button>
      : query.isPending ? <p role="status">Loading stored inputs…</p>
      : query.isError ? <div role="alert"><p>{formatApiError(query.error)}</p><button type="button" onClick={() => void query.refetch()}>Retry stored inputs</button></div>
      : query.data?.verification_status === 'legacy_without_manifest' ? <p>Legacy candidate: complete calculation inputs were not stored. They cannot be reconstructed from current data.</p>
      : query.data?.manifest && <>
        <p>Verified: stored inputs reproduce this candidate. This does not verify completeness against the entire world.</p>
        <h4>Why equal-point players are ordered this way</h4>
        {query.data.tie_explanations === undefined ? <p>Tie explanations are unavailable from this server.</p>
          : query.data.tie_explanations.length === 0 ? <p>No adjacent players have equal points.</p>
          : <ul>{query.data.tie_explanations.map(tie => {
            const reason = { result_profile: 'Counted points at result slot', completion_age: 'Newer completion at result slot', previous_position: 'Previous Official position', stored_token: 'Stored tie-break token' }[tie.reason]
            const value = (v: number | string | null): string => v === null ? 'None' : tie.reason === 'completion_age' && typeof v === 'number' ? weekLabel({season_index: Math.floor(v / 61), week: v % 61 + 1}) : String(v)
            return <li key={`${tie.higher_rank}/${tie.lower_rank}`}>
              {tie.higher_rank}. {tie.higher_player_id} precedes {tie.lower_rank}. {tie.lower_player_id} at {tie.points} points.
              {' '}{reason}{tie.result_slot === null ? '' : ` ${tie.result_slot}`}: {value(tie.higher_value)} versus {value(tie.lower_value)}.
            </li>
          })}</ul>}
        <h4>Stored roster ({query.data.manifest.players.length})</h4>
        {query.data.manifest.players.length === 0 ? <p>The stored roster is empty.</p> : <ul>{query.data.manifest.players.map(player => <li key={player.player_id}>
          <strong>{player.player_id}</strong> · Entry {weekLabel(player.tour_entry_week)} · {player.retired ? 'Retired at this boundary' : 'Not retired at this boundary'}
          <details><summary>Stored tie-break token</summary><p style={{ overflowWrap: 'anywhere' }}>{player.tie_break_token}</p></details>
        </li>)}</ul>}
        {Boolean(query.data.manifest.disciplinary_zeros?.length) && <>
          <h4>Resolved disciplinary zero inputs</h4>
          <p>Each active zero reserves one Best N slot. These are stored inputs, not an automatic sanction decision.</p>
          <ul>{query.data.manifest.disciplinary_zeros?.map(z => <li key={z.zero_id}>{z.player_id} · {z.zero_id} · Effective {weekLabel(z.effective_week)} for {z.duration_weeks} weeks.<details><summary>Disciplinary source</summary>{z.source_fingerprint}</details></li>)}</ul>
        </>}
        <h4>Stored result inputs ({query.data.manifest.results.length})</h4>
        {query.data.manifest.results.length === 0 ? <p>No result inputs were supplied.</p> : <ul>{query.data.manifest.results.map(result => <li key={JSON.stringify([result.edition_id, result.player_id])}>
          <strong>{result.player_id} · {result.edition_id}</strong> · Award {result.qualification_points + result.main_points} points · {result.ranked ? 'Ranked result' : 'Unranked result'}
          <p>First publication {weekLabel(result.first_publication_week)} · Validity {result.validity_weeks} weeks</p>
          <details><summary>Stored source fingerprint</summary><p style={{ overflowWrap: 'anywhere' }}>{result.source_fingerprint}</p></details>
        </li>)}</ul>}
      </>}
  </section>
}
