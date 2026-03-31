import { useQuery } from '@tanstack/react-query'
import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'

import { listRaceSnapshots, listRankingSnapshots } from '../api/client'
import { EmptyState, JsonPayloadBlock, MetadataList, RunScopedHeader, SectionCard } from '../components/RunScopedUi'
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
      <RunScopedHeader
        title={title}
        runId={runId}
        subtitle="Browse stored snapshot history and inspect payload details by sequence."
      />

      <SectionCard title="Snapshot timeline">
        {query.isLoading && <p className="status">Loading snapshots history...</p>}
        {query.error && <p className="error">Failed to load snapshots history: {formatApiError(query.error)}</p>}
        {!query.isLoading && !query.error && snapshots.length === 0 && (
          <EmptyState message="No snapshots are available for this run yet." />
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
          <EmptyState message="Select a snapshot to inspect details." />
        )}
      </SectionCard>
    </section>
  )
}

function SnapshotDetail({ snapshot }: { snapshot: RankingSnapshot }): JSX.Element {
  return (
    <>
      <MetadataList
        items={[
          { label: 'Sequence', value: snapshot.snapshot_sequence },
          { label: 'Kind', value: snapshot.snapshot_kind },
          { label: 'Source event ID', value: snapshot.source_event_id ?? '—' }
        ]}
      />

      <JsonPayloadBlock title="Snapshot payload" emptyText="No snapshot payload is available for this item." payload={snapshot.payload} />
    </>
  )
}
