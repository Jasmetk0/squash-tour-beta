import { useQuery } from '@tanstack/react-query'
import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'

import { listRaceSnapshots, listRankingSnapshots } from '../api/client'
import { JsonPayloadBlock, RunScopedHeader, SectionCard } from '../components/RunScopedUi'
import { SelectableHistoryList } from '../components/SelectableHistoryList'
import type { RankingSnapshot } from '../api/types'
import { formatApiError } from '../utils/apiErrors'

type Mode = 'ranking' | 'race'

export function SnapshotsPage({ mode }: { mode: Mode }): JSX.Element {
  const { runId = '' } = useParams()
  const [selectedSequence, setSelectedSequence] = useState<number | null>(null)

  const query = useQuery({
    queryKey: [`${mode}-snapshots`, runId],
    queryFn: () => (mode === 'ranking' ? listRankingSnapshots(runId) : listRaceSnapshots(runId)),
    enabled: Boolean(runId)
  })

  const snapshots = query.data?.snapshots ?? []

  useEffect(() => {
    if (!snapshots.length) {
      setSelectedSequence(null)
      return
    }

    if (!selectedSequence || !snapshots.some((snapshot) => snapshot.snapshot_sequence === selectedSequence)) {
      setSelectedSequence(snapshots[0].snapshot_sequence)
    }
  }, [snapshots, selectedSequence])

  const selected = snapshots.find((snapshot) => snapshot.snapshot_sequence === selectedSequence) ?? null

  const title = mode === 'ranking' ? 'Ranking snapshots' : 'Race snapshots'

  return (
    <section className="panel">
      <RunScopedHeader title={title} runId={runId} />

      <SectionCard title="Snapshot timeline">
        {query.isLoading && <p className="status">Loading snapshots history...</p>}
        {query.error && <p className="error">Failed to load snapshots history: {formatApiError(query.error)}</p>}
        {!query.isLoading && !query.error && snapshots.length === 0 && (
          <p className="status">No snapshots are available for this run yet.</p>
        )}

        {snapshots.length > 0 && (
          <SelectableHistoryList
            items={snapshots}
            getKey={(snapshot) => `${snapshot.snapshot_kind}-${snapshot.snapshot_sequence}`}
            getLabel={(snapshot) => `${snapshot.snapshot_sequence}. ${snapshot.snapshot_kind}`}
            getSubLabel={(snapshot) => (snapshot.source_event_id ? `Source ${snapshot.source_event_id}` : undefined)}
            isSelected={(snapshot) => snapshot.snapshot_sequence === selectedSequence}
            onSelect={(snapshot) => setSelectedSequence(snapshot.snapshot_sequence)}
            ariaLabel={`${title} list`}
          />
        )}
      </SectionCard>

      <SectionCard title="Selected snapshot detail">
        {selected ? (
          <SnapshotDetail snapshot={selected} />
        ) : (
          <p className="status">Select a snapshot to inspect details.</p>
        )}
      </SectionCard>
    </section>
  )
}

function SnapshotDetail({ snapshot }: { snapshot: RankingSnapshot }): JSX.Element {
  return (
    <>
      <dl className="kv-grid">
        <div>
          <dt>Sequence</dt>
          <dd>{snapshot.snapshot_sequence}</dd>
        </div>
        <div>
          <dt>Kind</dt>
          <dd>{snapshot.snapshot_kind}</dd>
        </div>
        <div>
          <dt>Source event ID</dt>
          <dd>{snapshot.source_event_id ?? '—'}</dd>
        </div>
      </dl>

      <JsonPayloadBlock title="Snapshot payload" emptyText="No snapshot payload is available for this item." payload={snapshot.payload} />
    </>
  )
}
