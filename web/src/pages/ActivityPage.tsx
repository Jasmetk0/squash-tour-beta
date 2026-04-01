import { useQuery } from '@tanstack/react-query'
import { Link, useParams } from 'react-router-dom'

import { getRunActivity } from '../api/client'
import { type RunActivityItem } from '../api/types'
import { CurrentContextStrip, EmptyState, MetadataList, RunScopedHeader, SectionCard } from '../components/RunScopedUi'
import { formatApiError } from '../utils/apiErrors'

function activityLink(runId: string, item: RunActivityItem): JSX.Element | string {
  if (item.kind === 'event' && item.event_id) {
    return <Link to={`/runs/${runId}/events/${encodeURIComponent(item.event_id)}`}>Open event detail</Link>
  }
  if (item.kind === 'ranking_snapshot' && item.snapshot_sequence !== null) {
    return <Link to={`/runs/${runId}/snapshots/ranking/${item.snapshot_sequence}`}>Open ranking snapshot</Link>
  }
  if (item.kind === 'race_snapshot' && item.snapshot_sequence !== null) {
    return <Link to={`/runs/${runId}/snapshots/race/${item.snapshot_sequence}`}>Open race snapshot</Link>
  }
  if (item.kind === 'rollover') {
    if (item.season !== null) {
      return <Link to={`/runs/${runId}/rollover/${item.season}`}>Open rollover season detail</Link>
    }
    return <Link to={`/runs/${runId}/rollover`}>Open rollover page</Link>
  }
  if (item.kind === 'finals_qualification' || item.kind === 'finals_result') {
    return <Link to={`/runs/${runId}/finals`}>Open finals page</Link>
  }
  if (item.kind === 'bootstrap_child' && item.related_run_id) {
    return <Link to={`/runs/${item.related_run_id}`}>Open child run</Link>
  }
  return 'No direct link'
}

export function ActivityPage(): JSX.Element {
  const { runId = '' } = useParams()
  const activityQuery = useQuery({
    queryKey: ['run-activity', runId],
    queryFn: () => getRunActivity(runId),
    enabled: Boolean(runId),
    retry: false
  })

  return (
    <section className="panel">
      <RunScopedHeader title="Run activity" runId={runId} subtitle="Deterministic feed of persisted run artifacts." />
      <CurrentContextStrip
        items={[
          { label: 'Run', value: runId || 'unknown' },
          { label: 'Items', value: activityQuery.data?.items.length ?? '—' }
        ]}
      />

      <SectionCard title="Activity feed">
        {activityQuery.isLoading ? <p className="status">Loading activity feed...</p> : null}
        {activityQuery.error ? <p className="error">Failed to load activity feed: {formatApiError(activityQuery.error)}</p> : null}
        {activityQuery.data && activityQuery.data.items.length === 0 ? (
          <EmptyState message="No activity has been persisted for this run yet." />
        ) : null}
        {activityQuery.data && activityQuery.data.items.length > 0 ? (
          <ul className="item-list" aria-label="Run activity feed list">
            {activityQuery.data.items.map((item, index) => (
              <li key={`${item.kind}-${item.sequence ?? 'none'}-${item.related_run_id ?? item.event_id ?? index}`}>
                <strong>{item.label}</strong>
                <MetadataList
                  items={[
                    { label: 'Kind', value: item.kind },
                    { label: 'Season', value: item.season ?? '—' },
                    { label: 'Week', value: item.week ?? '—' },
                    { label: 'Sequence', value: item.sequence ?? '—' },
                    { label: 'Link', value: activityLink(runId, item) }
                  ]}
                />
              </li>
            ))}
          </ul>
        ) : null}
      </SectionCard>
    </section>
  )
}
