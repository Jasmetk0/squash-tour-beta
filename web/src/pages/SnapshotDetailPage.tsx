import { useQuery } from '@tanstack/react-query'
import { Link, useParams } from 'react-router-dom'

import { listRaceSnapshots, listRankingSnapshots } from '../api/client'
import { CompactSummaryCard, CurrentContextStrip, EmptyState, JsonPayloadBlock, RunScopedHeader, SectionCard } from '../components/RunScopedUi'
import type { RankingSnapshot } from '../api/types'
import { formatApiError } from '../utils/apiErrors'

type SnapshotMode = 'ranking' | 'race'

export function SnapshotDetailPage({ mode }: { mode: SnapshotMode }): JSX.Element {
  const { runId = '', snapshotSequence = '' } = useParams()
  const parsedSequence = Number.parseInt(snapshotSequence, 10)
  const isValidSequence = Number.isInteger(parsedSequence) && parsedSequence > 0

  const snapshotsQuery = useQuery({
    queryKey: [`${mode}-snapshots`, runId],
    queryFn: () => (mode === 'ranking' ? listRankingSnapshots(runId) : listRaceSnapshots(runId)),
    enabled: Boolean(runId && isValidSequence)
  })

  const snapshot = snapshotsQuery.data?.snapshots.find((item) => item.snapshot_sequence === parsedSequence) ?? null
  const title = mode === 'ranking' ? 'Ranking snapshot detail' : 'Race snapshot detail'

  return (
    <section className="panel">
      <RunScopedHeader
        title={title}
        runId={runId}
        subtitle="Inspect snapshot metadata and payload for a single history snapshot sequence."
      />

      <CurrentContextStrip
        items={[
          { label: 'Run', value: runId || 'unknown' },
          { label: 'Mode', value: mode },
          { label: 'Sequence', value: snapshotSequence || 'unknown' },
          { label: 'Status', value: snapshot ? 'Loaded' : 'Pending' }
        ]}
      />

      <SectionCard title="Snapshot context">
        <p>
          <Link to={`/runs/${runId}/snapshots/${mode}`}>Back to {mode} snapshots history</Link>
        </p>
      </SectionCard>

      {!snapshotSequence && (
        <SectionCard title="Snapshot lookup">
          <EmptyState message="No snapshot sequence was provided in the URL." />
        </SectionCard>
      )}

      {snapshotSequence && !isValidSequence && (
        <SectionCard title="Snapshot lookup">
          <EmptyState message={`Snapshot sequence "${snapshotSequence}" is invalid. Use a positive integer sequence.`} />
        </SectionCard>
      )}

      {snapshotSequence && isValidSequence && (
        <>
          <SectionCard title="Snapshot summary">
            {snapshotsQuery.isLoading && <p className="status">Loading snapshot details...</p>}
            {snapshotsQuery.error && (
              <p className="error">Failed to load snapshot details: {formatApiError(snapshotsQuery.error)}</p>
            )}
            {snapshot && <SnapshotSummary mode={mode} snapshot={snapshot} runId={runId} />}
            {!snapshotsQuery.isLoading && !snapshotsQuery.error && !snapshot && (
              <EmptyState message={`Snapshot sequence ${snapshotSequence} was not found for this run.`} />
            )}
          </SectionCard>

          <SectionCard title="Raw snapshot payload">
            {snapshot && (
              <JsonPayloadBlock
                title="Snapshot record"
                emptyText="No snapshot payload is available for this snapshot."
                payload={snapshot.payload}
              />
            )}
          </SectionCard>
        </>
      )}
    </section>
  )
}

function SnapshotSummary({ mode, snapshot, runId }: { mode: SnapshotMode; snapshot: RankingSnapshot; runId: string }): JSX.Element {
  return (
    <>
      <CompactSummaryCard
        items={[
          { label: 'Sequence', value: snapshot.snapshot_sequence },
          { label: 'Kind', value: snapshot.snapshot_kind },
          { label: 'Mode', value: mode },
          { label: 'Source event ID', value: snapshot.source_event_id ?? '—' }
        ]}
      />
      {snapshot.source_event_id ? (
        <p>
          <Link to={`/runs/${runId}/events/${encodeURIComponent(snapshot.source_event_id)}`}>Open source event detail page</Link>
        </p>
      ) : null}
    </>
  )
}
