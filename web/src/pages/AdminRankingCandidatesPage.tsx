import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link, useParams } from 'react-router-dom'
import { getRankingCandidates, getRankingCandidateSources } from '../api/client'
import type { CandidateWeek } from '../api/rankingCandidates'
import { EmptyState, PageIntro, SectionCard } from '../components/RunScopedUi'
import { formatApiError } from '../utils/apiErrors'

function label(w: CandidateWeek): string {
  return `${2000 + w.season_index}/${String(2001 + w.season_index).slice(-2)} · Week ${w.week}`
}
export function AdminRankingCandidatesPage(): JSX.Element {
  const { runId = '', branchId = '', seasonIndex, week } = useParams()
  const base = `/admin/runs/${encodeURIComponent(runId)}/branches/${encodeURIComponent(branchId)}/ranking-candidates`
  const valid = (seasonIndex === undefined && week === undefined) || (seasonIndex !== undefined && week !== undefined && /^\d+$/.test(seasonIndex) && /^\d+$/.test(week) && Number(seasonIndex) < 50 && Number(week) >= 1 && Number(week) <= 61)
  const query = useQuery({ queryKey: ['ranking-candidates', runId, branchId], queryFn: () => getRankingCandidates(runId, branchId), enabled: Boolean(runId && branchId && valid), retry: false })
  const selected = query.data?.candidates.find(c => c.snapshot.week.season_index === Number(seasonIndex) && c.snapshot.week.week === Number(week))
  return <main>
    <PageIntro title="Ranking candidates" subtitle="Unpublished preparation history. Viewing does not publish rankings or advance time." meta={`Run: ${runId} · Branch: ${branchId}`} />
    <Link to={`/admin/runs/${encodeURIComponent(runId)}/branches`}>Back to Branches</Link>
    {!valid ? <p role="alert">Invalid season or week.</p> : query.isPending ? <p role="status">Loading ranking history…</p> : query.isError ? <div role="alert"><p>{formatApiError(query.error)}</p><button type="button" onClick={() => void query.refetch()}>Retry loading</button></div> : query.data && <>
      <SectionCard title="Candidate weeks">
        {query.data.candidates.length === 0 ? <EmptyState message="No ranking candidates have been prepared for this Branch." /> : <ul>{query.data.candidates.map(c => <li key={c.fingerprint}><Link to={`${base}/${c.snapshot.week.season_index}/${c.snapshot.week.week}`} aria-current={selected?.fingerprint === c.fingerprint ? 'page' : undefined}>{label(c.snapshot.week)}</Link> — {c.snapshot.rows.length} players · Best {c.snapshot.policy.best_n} · Unpublished candidate</li>)}</ul>}
      </SectionCard>
      {seasonIndex !== undefined && !selected ? <p role="alert">No candidate is stored for this week.</p> : selected ? <SectionCard title={label(selected.snapshot.week)}>
        <p>Unpublished candidate · Best {selected.snapshot.policy.best_n}</p>
        {selected.snapshot.rows.length === 0 ? <EmptyState message="This candidate contains no ranked players." /> : <div className="table-scroll" role="region" aria-label="Candidate ranking table" tabIndex={0}><table><thead><tr><th>Rank</th><th>Player ID</th><th>Points</th><th>Counted results</th></tr></thead><tbody>{selected.snapshot.rows.map(row => <tr key={row.player_id}>
          <td>{row.rank}</td><td>{row.player_id}</td><td>{row.points}</td><td>{row.counted_results.length === 0 ? 'No counted results' : <details><summary>{row.counted_results.length} counted results for {row.player_id}</summary><ul>{row.counted_results.map(r => <li key={r.edition_id}><strong>{r.edition_id}</strong>: {r.qualification_points + r.main_points} points ({r.qualification_points} qualification + {r.main_points} main). Completed {label(r.completed_week)}; first publication {label(r.first_publication_week)}; validity {r.validity_weeks} weeks.</li>)}</ul></details>}</td>
        </tr>)}</tbody></table></div>}
        <RankingSources key={`${runId}/${branchId}/${selected.fingerprint}`} runId={runId} branchId={branchId} week={selected.snapshot.week} fingerprint={selected.fingerprint} />
        <details><summary>Technical provenance</summary><p>Policy: {selected.snapshot.policy.policy_id}</p><p style={{ overflowWrap: 'anywhere' }}>Fingerprint: {selected.fingerprint}</p><p>Commands: {selected.command_ids.join(', ') || 'No command receipt'}</p></details>
      </SectionCard> : query.data.candidates.length > 0 && <p>Select a week to inspect its ranking.</p>}
    </>}
  </main>
}

function RankingSources({ runId, branchId, week, fingerprint }: { runId: string; branchId: string; week: CandidateWeek; fingerprint: string }): JSX.Element {
  const [opened, setOpened] = useState(false)
  const query = useQuery({
    queryKey: ['ranking-sources', runId, branchId, week.season_index, week.week, fingerprint],
    queryFn: async () => {
      const data = await getRankingCandidateSources(runId, branchId, week.season_index, week.week)
      if (data.candidate_fingerprint !== fingerprint) throw new Error('Source history does not match this candidate.')
      return data
    },
    enabled: opened, retry: false,
  })
  return <section aria-label="Historical ranking sources">
    <h3>Source results</h3>
    <p>Results effective for this candidate week, including results outside Best N. Later corrections are excluded.</p>
    {!opened ? <button type="button" onClick={() => setOpened(true)}>Load source results</button>
      : query.isPending ? <p role="status">Loading source results…</p>
      : query.isError ? <div role="alert"><p>{formatApiError(query.error)}</p><button type="button" onClick={() => void query.refetch()}>Retry source results</button></div>
      : query.data && (query.data.sources.length === 0 ? <p>No source results at this boundary.</p> : <ul>{query.data.sources.map(source => {
        const v = source.version
        return <li key={source.fingerprint}>
          <strong>{v.result.player_id} · {v.result.edition_id}</strong>: {v.result.qualification_points + v.result.main_points} points · {source.counted ? 'Counted' : 'Not counted in this candidate'}
          <p>Effective {label(v.effective_week)} · First publication {label(v.result.first_publication_week)} · Validity {v.result.validity_weeks} weeks</p>
          <details><summary>Source provenance</summary><p style={{ overflowWrap: 'anywhere' }}>Source: {v.result.source_fingerprint}<br />Version: {source.fingerprint}<br />Previous version: {v.previous_fingerprint || 'Initial result'}</p></details>
        </li>
      })}</ul>)}
  </section>
}
