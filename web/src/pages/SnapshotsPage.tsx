import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { useParams } from 'react-router-dom'

import { listRaceSnapshots, listRankingSnapshots } from '../api/client'
import type { RankingSnapshot } from '../api/types'

type Mode = 'ranking' | 'race'

export function SnapshotsPage({ mode }: { mode: Mode }): JSX.Element {
  const { runId = '' } = useParams()
  const [selected, setSelected] = useState<RankingSnapshot | null>(null)

  const query = useQuery({
    queryKey: [`${mode}-snapshots`, runId],
    queryFn: () => (mode === 'ranking' ? listRankingSnapshots(runId) : listRaceSnapshots(runId)),
    enabled: Boolean(runId)
  })

  return (
    <section className="panel">
      <h2>{mode === 'ranking' ? 'Ranking snapshots' : 'Race snapshots'}</h2>
      {query.error && <p className="error">Failed to load snapshots: {String(query.error)}</p>}
      <ul className="item-list">
        {query.data?.snapshots.map((snapshot) => (
          <li key={snapshot.snapshot_sequence}>
            <button className="linkish" onClick={() => setSelected(snapshot)}>
              Seq {snapshot.snapshot_sequence} · {snapshot.snapshot_kind} · {snapshot.source_event_id ?? 'season_rollup'}
            </button>
          </li>
        ))}
      </ul>

      {selected && (
        <>
          <h3>Snapshot payload</h3>
          <pre className="json-block">{JSON.stringify(selected.payload, null, 2)}</pre>
        </>
      )}
    </section>
  )
}
