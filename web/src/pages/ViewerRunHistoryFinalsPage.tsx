import { useQuery } from '@tanstack/react-query'
import { Link, useParams } from 'react-router-dom'

import { getFinalsQualification, getFinalsResult, getFinalsSummary, getRunActivity } from '../api/client'
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
import { formatApiError, isApiNotFound } from '../utils/apiErrors'

function readArrayFieldLength(payload: Record<string, unknown> | null | undefined, key: string): number | null {
  const value = payload?.[key]
  return Array.isArray(value) ? value.length : null
}

function readStringField(payload: Record<string, unknown> | null | undefined, key: string): string | null {
  const value = payload?.[key]
  return typeof value === 'string' ? value : null
}

function formatWeek(week: number | null | undefined): string {
  return typeof week === 'number' ? `W${week}` : '—'
}

function formatSeason(season: number | null | undefined): string | number {
  return typeof season === 'number' ? season : '—'
}

function isPreviewableActivityItem(item: RunActivityItem | undefined): item is RunActivityItem {
  return Boolean(item && typeof item.label === 'string' && typeof item.kind === 'string')
}

function TechnicalData({ summary, title, payload, emptyText }: { summary: string; title: string; payload: unknown; emptyText: string }): JSX.Element {
  return (
    <details>
      <summary>{summary}</summary>
      <JsonPayloadBlock title={title} payload={payload} emptyText={emptyText} />
    </details>
  )
}

export function ViewerRunHistoryPage(): JSX.Element {
  const { runId = '' } = useParams()
  const activityQuery = useQuery({
    queryKey: ['run-activity', runId],
    queryFn: () => getRunActivity(runId),
    enabled: Boolean(runId),
    retry: false
  })

  const items = activityQuery.data?.items ?? []
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

      <SectionCard title="Activity metadata">
        {activityQuery.isLoading ? <p className="status">Loading history…</p> : null}
        {activityQuery.error ? <p className="error">Failed to load run activity: {formatApiError(activityQuery.error)}</p> : null}
        {activityQuery.data && items.length === 0 ? <EmptyState message="No activity metadata is available for this run yet." /> : null}
        {activityQuery.data && items.length > 0 ? (
          canPreviewLatest ? (
            <>
              <SummaryPills
                items={[
                  { label: 'Activity count', value: items.length },
                  { label: 'Latest kind', value: latestItem.kind },
                  { label: 'Latest season', value: formatSeason(latestItem.season) },
                  { label: 'Latest week', value: formatWeek(latestItem.week) }
                ]}
              />
              <MetadataList
                items={[
                  { label: 'Latest label', value: latestItem.label },
                  { label: 'Sequence', value: latestItem.sequence ?? '—' },
                  { label: 'Event ID', value: latestItem.event_id ?? '—' },
                  { label: 'Snapshot sequence', value: latestItem.snapshot_sequence ?? '—' },
                  { label: 'Source event', value: latestItem.source_event_id ?? '—' },
                  { label: 'Related run', value: latestItem.related_run_id ?? '—' }
                ]}
              />
            </>
          ) : (
            <EmptyState message="History preview is not connected for this activity shape yet." />
          )
        ) : null}
      </SectionCard>

      {activityQuery.data ? (
        <SectionCard title="Technical history data">
          <TechnicalData
            summary="Show technical history data"
            title="Activity payload"
            payload={activityQuery.data}
            emptyText="No technical history payload is available."
          />
        </SectionCard>
      ) : null}
    </section>
  )
}

export function ViewerRunFinalsPage(): JSX.Element {
  const { runId = '' } = useParams()
  const summaryQuery = useQuery({
    queryKey: ['finals-summary', runId],
    queryFn: () => getFinalsSummary(runId),
    enabled: Boolean(runId),
    retry: false
  })

  const qualification = summaryQuery.data?.qualification ?? null
  const result = summaryQuery.data?.result ?? null
  const sourceSeason = qualification?.source_as_of_season ?? result?.source_as_of_season ?? summaryQuery.data?.season ?? null
  const sourceWeek = qualification?.source_as_of_week ?? result?.source_as_of_week ?? null

  return (
    <section className="panel">
      <RunScopedHeader title="World Tour Finals" runId={runId} subtitle="Read-only Finals availability for the selected run." />
      <CurrentContextStrip
        items={[
          { label: 'Active run', value: runId || 'unknown' },
          { label: 'Qualification', value: qualification ? 'Available' : 'Unavailable' },
          { label: 'Result', value: result ? 'Available' : 'Unavailable' },
          { label: 'Source season', value: sourceSeason ?? '—' },
          { label: 'Source week', value: sourceWeek != null ? `W${sourceWeek}` : '—' }
        ]}
      />

      <SectionCard title="Finals availability">
        {summaryQuery.isLoading ? <p className="status">Loading Finals summary…</p> : null}
        {summaryQuery.error ? <p className="error">Failed to load Finals summary: {formatApiError(summaryQuery.error)}</p> : null}
        {summaryQuery.data ? (
          <>
            <SummaryPills
              items={[
                { label: 'Qualification availability', value: qualification ? 'Available' : 'Unavailable' },
                { label: 'Result availability', value: result ? 'Available' : 'Unavailable' },
                { label: 'Season', value: summaryQuery.data.season }
              ]}
            />
            <p>
              <Link to={`/viewer/runs/${runId}/finals/qualification`}>Open Finals qualification</Link>
              {result ? (
                <>
                  {' · '}
                  <Link to={`/viewer/runs/${runId}/finals/result`}>Open Finals result</Link>
                </>
              ) : null}
            </p>
          </>
        ) : null}
      </SectionCard>
    </section>
  )
}

export function ViewerRunFinalsQualificationPage(): JSX.Element {
  const { runId = '' } = useParams()
  const qualificationQuery = useQuery({
    queryKey: ['finals-qualification', runId],
    queryFn: () => getFinalsQualification(runId),
    enabled: Boolean(runId),
    retry: false
  })

  const notFound = isApiNotFound(qualificationQuery.error)
  const payload = qualificationQuery.data?.qualification
  const qualifiedPlayersCount = readArrayFieldLength(payload, 'qualified_player_ids')
  const groupCount = readArrayFieldLength(payload, 'groups')
  const hasSafePreview = qualifiedPlayersCount != null || groupCount != null

  return (
    <section className="panel">
      <RunScopedHeader title="Finals Qualification" runId={runId} subtitle="Read-only qualification metadata for the selected run." />
      <CurrentContextStrip
        items={[
          { label: 'Active run', value: runId || 'unknown' },
          { label: 'Source season', value: qualificationQuery.data?.source_as_of_season ?? '—' },
          { label: 'Source week', value: qualificationQuery.data?.source_as_of_week != null ? `W${qualificationQuery.data.source_as_of_week}` : '—' }
        ]}
      />

      <SectionCard title="Qualification metadata">
        {qualificationQuery.isLoading ? <p className="status">Loading Finals qualification…</p> : null}
        {qualificationQuery.error && !notFound ? <p className="error">Failed to load Finals qualification: {formatApiError(qualificationQuery.error)}</p> : null}
        {notFound ? <EmptyState message="No Finals qualification is available for this run yet." /> : null}
        {qualificationQuery.data ? (
          hasSafePreview ? (
            <SummaryPills
              items={[
                { label: 'Qualified players', value: qualifiedPlayersCount ?? 'Unknown' },
                { label: 'Groups', value: groupCount ?? 'Unknown' },
                { label: 'Season', value: qualificationQuery.data.season ?? '—' }
              ]}
            />
          ) : (
            <EmptyState message="Finals qualification preview is not connected for this payload shape yet." />
          )
        ) : null}
      </SectionCard>

      {qualificationQuery.data ? (
        <SectionCard title="Technical finals qualification data">
          <TechnicalData
            summary="Show technical finals qualification data"
            title="Qualification payload"
            payload={qualificationQuery.data}
            emptyText="No technical Finals qualification payload is available."
          />
        </SectionCard>
      ) : null}
    </section>
  )
}

export function ViewerRunFinalsResultPage(): JSX.Element {
  const { runId = '' } = useParams()
  const resultQuery = useQuery({
    queryKey: ['finals-result', runId],
    queryFn: () => getFinalsResult(runId),
    enabled: Boolean(runId),
    retry: false
  })

  const notFound = isApiNotFound(resultQuery.error)
  const payload = resultQuery.data?.result
  const championPlayerId = readStringField(payload, 'champion_player_id')
  const runnerUpPlayerId = readStringField(payload, 'runner_up_player_id')
  const hasSafePreview = championPlayerId != null || runnerUpPlayerId != null

  return (
    <section className="panel">
      <RunScopedHeader title="Finals Result" runId={runId} subtitle="Read-only Finals result metadata for the selected run." />
      <CurrentContextStrip
        items={[
          { label: 'Active run', value: runId || 'unknown' },
          { label: 'Result', value: resultQuery.data ? 'Available' : notFound ? 'Unavailable' : 'Loading' },
          { label: 'Source season', value: resultQuery.data?.source_as_of_season ?? '—' },
          { label: 'Source week', value: resultQuery.data?.source_as_of_week != null ? `W${resultQuery.data.source_as_of_week}` : '—' }
        ]}
      />

      <SectionCard title="Result metadata">
        {resultQuery.isLoading ? <p className="status">Loading Finals result…</p> : null}
        {resultQuery.error && !notFound ? <p className="error">Failed to load Finals result: {formatApiError(resultQuery.error)}</p> : null}
        {notFound ? <EmptyState message="Finals result has not been recorded for this run yet." /> : null}
        {resultQuery.data ? (
          hasSafePreview ? (
            <SummaryPills
              items={[
                { label: 'Event', value: resultQuery.data.event_id ?? '—' },
                { label: 'Champion', value: championPlayerId ?? 'Unknown' },
                { label: 'Runner-up', value: runnerUpPlayerId ?? 'Unknown' },
                { label: 'Season', value: resultQuery.data.season ?? '—' }
              ]}
            />
          ) : (
            <EmptyState message="Finals result preview is not connected for this payload shape yet." />
          )
        ) : null}
      </SectionCard>

      {resultQuery.data ? (
        <SectionCard title="Technical finals result data">
          <TechnicalData
            summary="Show technical finals result data"
            title="Result payload"
            payload={resultQuery.data}
            emptyText="No technical Finals result payload is available."
          />
        </SectionCard>
      ) : null}
    </section>
  )
}
