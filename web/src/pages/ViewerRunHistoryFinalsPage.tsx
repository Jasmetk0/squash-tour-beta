import { useQuery } from '@tanstack/react-query'
import type { ReactNode } from 'react'

import { getRunActivity } from '../api/client'
import type { RunActivityItem } from '../api/types'
import {
  CurrentContextStrip,
  EmptyState,
  JsonPayloadBlock,
  MetadataList,
  RunScopedHeader,
  SectionCard,
  SummaryPills
} from '../components/RunScopedUi'
import { formatApiError } from '../utils/apiErrors'
import { useViewerProductRunRouteContext } from '../viewer/ViewerProductRunRouteContext'

function isScalar(value: unknown): value is string | number | boolean {
  return typeof value === 'string' || typeof value === 'number' || typeof value === 'boolean'
}

function safeScalarValue(value: unknown, fallback: string | number = '—'): string | number {
  if (typeof value === 'string' || typeof value === 'number') return value
  if (typeof value === 'boolean') return value ? 'Yes' : 'No'
  return fallback
}

function formatWeek(week: number | null | undefined): string {
  return typeof week === 'number' ? `W${week}` : '—'
}

function formatSeason(season: number | null | undefined): string | number {
  return typeof season === 'number' ? season : '—'
}

function isPreviewableActivityItem(item: RunActivityItem | undefined): item is RunActivityItem {
  return Boolean(item && isScalar(item.label) && isScalar(item.kind))
}

function TechnicalData({
  summary,
  title,
  payload,
  emptyText
}: {
  summary: string
  title: string
  payload: unknown
  emptyText: string
}): JSX.Element {
  return (
    <details>
      <summary>{summary}</summary>
      <JsonPayloadBlock title={title} payload={payload} emptyText={emptyText} />
    </details>
  )
}

export function ViewerRunHistoryPage(): JSX.Element {
  const { productRunId: runId, legacySimulationRunId } = useViewerProductRunRouteContext()
  const activityQuery = useQuery({
    queryKey: ['run-activity', runId, legacySimulationRunId],
    queryFn: () => getRunActivity(legacySimulationRunId),
    enabled: Boolean(runId),
    retry: false
  })

  const items = Array.isArray(activityQuery.data?.items) ? activityQuery.data.items : []
  const latestItem = items[0]
  const canPreviewLatest = isPreviewableActivityItem(latestItem)

  return (
    <section className="panel">
      <RunScopedHeader title="History" runId={runId} subtitle="Read-only run activity and season timeline." />
      <CurrentContextStrip
        items={[
          { label: 'Active run', value: runId || 'unknown' },
          { label: 'Activity count', value: activityQuery.data ? items.length : '—' },
          { label: 'Latest activity', value: canPreviewLatest ? latestItem.label : items.length > 0 ? 'Preview deferred' : '—' }
        ]}
      />

      <SectionCard title="Season timeline">
        {activityQuery.isLoading ? <p className="status">Loading history…</p> : null}
        {activityQuery.error ? <p className="error">Failed to load run activity: {formatApiError(activityQuery.error)}</p> : null}
        {activityQuery.data && items.length === 0 ? <EmptyState message="No data is available for this run yet." /> : null}
        {activityQuery.data && items.length > 0 ? (
          canPreviewLatest ? (
            <>
              <SummaryPills
                items={[
                  { label: 'Activity count', value: items.length },
                  { label: 'Latest kind', value: safeScalarValue(latestItem.kind) },
                  { label: 'Latest season', value: formatSeason(latestItem.season) },
                  { label: 'Latest week', value: formatWeek(latestItem.week) }
                ]}
              />
              <MetadataList
                items={[
                  { label: 'Latest label', value: safeScalarValue(latestItem.label) },
                  { label: 'Sequence', value: safeScalarValue(latestItem.sequence) },
                  { label: 'Event ID', value: safeScalarValue(latestItem.event_id) },
                  { label: 'Snapshot sequence', value: safeScalarValue(latestItem.snapshot_sequence) },
                  { label: 'Source event', value: safeScalarValue(latestItem.source_event_id) },
                  { label: 'Related run', value: safeScalarValue(latestItem.related_run_id) }
                ]}
              />
            </>
          ) : (
            <EmptyState message="This preview is not connected for this data shape yet." />
          )
        ) : null}
      </SectionCard>

      {activityQuery.data ? (
        <SectionCard title="Read-only data">
          <TechnicalData
            summary="Show technical history data"
            title="Technical activity data"
            payload={activityQuery.data}
            emptyText="No technical history data is available."
          />
        </SectionCard>
      ) : null}
    </section>
  )
}
