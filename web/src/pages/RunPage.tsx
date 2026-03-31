import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Link, useParams } from 'react-router-dom'

import { getRun, simulateFullSeason, simulateNextTournament, simulateNextWeek } from '../api/client'

export function RunPage(): JSX.Element {
  const { runId = '' } = useParams()
  const queryClient = useQueryClient()

  const runQuery = useQuery({ queryKey: ['run', runId], queryFn: () => getRun(runId), enabled: Boolean(runId) })

  const simulator = useMutation({
    mutationFn: async (mode: 'next-tournament' | 'next-week' | 'full-season') => {
      if (mode === 'next-tournament') return simulateNextTournament(runId)
      if (mode === 'next-week') return simulateNextWeek(runId)
      return simulateFullSeason(runId)
    },
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['run', runId] }),
        queryClient.invalidateQueries({ queryKey: ['events', runId] }),
        queryClient.invalidateQueries({ queryKey: ['ranking-snapshots', runId] }),
        queryClient.invalidateQueries({ queryKey: ['race-snapshots', runId] })
      ])
    }
  })

  return (
    <section className="panel">
      <h2>Run detail</h2>
      {runQuery.isLoading && <p>Loading run...</p>}
      {runQuery.error && <p className="error">Failed to load run: {String(runQuery.error)}</p>}
      {runQuery.data && (
        <>
          <dl className="kv-grid">
            <div>
              <dt>Run ID</dt>
              <dd>{runQuery.data.run.run_id}</dd>
            </div>
            <div>
              <dt>Season</dt>
              <dd>{runQuery.data.run.season}</dd>
            </div>
            <div>
              <dt>Seed</dt>
              <dd>{runQuery.data.run.seed}</dd>
            </div>
            <div>
              <dt>Progress</dt>
              <dd>
                {runQuery.data.run.next_event_index} / {runQuery.data.run.total_events}
              </dd>
            </div>
            <div>
              <dt>Completed event IDs</dt>
              <dd>{runQuery.data.run.completed_event_ids.length}</dd>
            </div>
          </dl>

          <h3>Simulation controls</h3>
          <div className="actions">
            <button onClick={() => simulator.mutate('next-tournament')}>Simulate next tournament</button>
            <button onClick={() => simulator.mutate('next-week')}>Simulate next week</button>
            <button onClick={() => simulator.mutate('full-season')}>Simulate full season</button>
          </div>
          {simulator.error && <p className="error">Simulation failed: {String(simulator.error)}</p>}
          <p>
            <Link to={`/runs/${runId}/finals`}>View World Tour Finals</Link>
          </p>
          {simulator.data && (
            <pre className="json-block" aria-label="simulation-result">
              {JSON.stringify(simulator.data.step, null, 2)}
            </pre>
          )}
        </>
      )}
    </section>
  )
}
