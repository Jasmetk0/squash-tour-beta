import { useQuery } from '@tanstack/react-query'
import { Link, useParams } from 'react-router-dom'

import { getRaceSnapshot, getRankingSnapshot, listRaceSnapshots, listRankingSnapshots } from '../api/client'
import { CompactSummaryCard, CurrentContextStrip, EmptyState, JsonPayloadBlock, RunScopedHeader, SectionCard } from '../components/RunScopedUi'
import type { RankingSnapshot } from '../api/types'
import { formatApiError, isApiNotFound } from '../utils/apiErrors'

type SnapshotMode = 'ranking' | 'race'

export function SnapshotDetailPage({ mode }: { mode: SnapshotMode }): JSX.Element {
  const { runId = '', snapshotSequence = '' } = useParams()
  const parsedSequence = Number.parseInt(snapshotSequence, 10)
  const isValidSequence = Number.isInteger(parsedSequence) && parsedSequence > 0

  const snapshotQuery = useQuery({
    queryKey: [`${mode}-snapshot`, runId, parsedSequence],
    queryFn: () => (mode === 'ranking' ? getRankingSnapshot(runId, parsedSequence) : getRaceSnapshot(runId, parsedSequence)),
    enabled: Boolean(runId && isValidSequence),
    retry: false
  })

  const snapshotsQuery = useQuery({
    queryKey: [`${mode}-snapshots`, runId],
    queryFn: () => (mode === 'ranking' ? listRankingSnapshots(runId) : listRaceSnapshots(runId)),
    enabled: Boolean(runId && isValidSequence)
  })

  const snapshot = snapshotQuery.data ?? null
  const neighboringSnapshots = snapshotsQuery.data?.snapshots ?? []
  const currentSnapshotIndex = neighboringSnapshots.findIndex((item) => item.snapshot_sequence === parsedSequence)
  const previousSnapshot = currentSnapshotIndex > 0 ? neighboringSnapshots[currentSnapshotIndex - 1] : null
  const nextSnapshot =
    currentSnapshotIndex >= 0 && currentSnapshotIndex < neighboringSnapshots.length - 1
      ? neighboringSnapshots[currentSnapshotIndex + 1]
      : null
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
        {isValidSequence && (
          <p>
            Previous:{' '}
            {previousSnapshot ? (
              <Link to={`/runs/${runId}/snapshots/${mode}/${previousSnapshot.snapshot_sequence}`}>
                #{previousSnapshot.snapshot_sequence}
              </Link>
            ) : (
              <span>None</span>
            )}{' '}
            · Next:{' '}
            {nextSnapshot ? (
              <Link to={`/runs/${runId}/snapshots/${mode}/${nextSnapshot.snapshot_sequence}`}>#{nextSnapshot.snapshot_sequence}</Link>
            ) : (
              <span>None</span>
            )}
          </p>
        )}
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
            {snapshotQuery.isLoading && <p className="status">Loading snapshot details...</p>}
            {snapshotQuery.error && !isApiNotFound(snapshotQuery.error) && (
              <p className="error">Failed to load snapshot details: {formatApiError(snapshotQuery.error)}</p>
            )}
            {isApiNotFound(snapshotQuery.error) && (
              <EmptyState message={`Snapshot sequence ${snapshotSequence} was not found for this run.`} />
            )}
            {snapshot && <SnapshotSummary mode={mode} snapshot={snapshot} runId={runId} />}
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
