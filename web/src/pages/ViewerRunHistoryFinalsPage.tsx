import { useQuery } from '@tanstack/react-query'
import type { ReactNode } from 'react'
import { Link, useParams } from 'react-router-dom'

import { getFinalsQualification, getFinalsResult, getFinalsSummary, getRunActivity } from '../api/client'
import type { FinalsQualificationResponse, FinalsResultResponse, FinalsSummaryResponse, RunActivityItem } from '../api/types'
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
import {
  viewerFinalsPath,
  viewerFinalsQualificationPath,
  viewerFinalsResultPath,
  viewerPlannedEventPath,
  viewerPlayerProfilePath,
  viewerRacePath,
  viewerRaceSnapshotPath,
  viewerRankingsPath,
  viewerRankingSnapshotPath,
  viewerSeasonCalendarPath,
  viewerTournamentDetailPath,
  viewerTournamentsPath
} from '../viewer/viewerRoutes'


function formatFieldLabel(key: string): string {
  return key
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (letter) => letter.toUpperCase())
}

function collectPrimitivePayloadItems(payload: Record<string, unknown> | null | undefined, excludedKeys: Set<string> = new Set()): Array<{ label: string; value: string | number }> {
  const items: Array<{ label: string; value: string | number }> = []

  for (const [key, value] of Object.entries(payload ?? {})) {
    if (excludedKeys.has(key)) continue

    if (typeof value === 'string' || typeof value === 'number') {
      items.push({ label: formatFieldLabel(key), value })
    } else if (typeof value === 'boolean') {
      items.push({ label: formatFieldLabel(key), value: value ? 'Yes' : 'No' })
    }
  }

  return items
}

function collectArrayCountItems(payload: Record<string, unknown> | null | undefined): Array<{ label: string; value: number }> {
  const items: Array<{ label: string; value: number }> = []

  for (const [key, value] of Object.entries(payload ?? {})) {
    if (Array.isArray(value)) {
      items.push({ label: `${formatFieldLabel(key)} count`, value: value.length })
    }
  }

  return items
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return Boolean(value && typeof value === 'object' && !Array.isArray(value))
}

function collectPlayerIds(payload: Record<string, unknown> | null | undefined): string[] {
  const playerIds = new Set<string>()

  function visit(value: unknown, keyHint = ''): void {
    const normalizedKey = keyHint.toLowerCase()
    const keyLooksLikePlayerId = normalizedKey.includes('player') && normalizedKey.includes('id')

    if (keyLooksLikePlayerId && (typeof value === 'string' || typeof value === 'number') && String(value)) {
      playerIds.add(String(value))
      return
    }

    if (Array.isArray(value)) {
      value.forEach((item) => {
        if (keyLooksLikePlayerId && (typeof item === 'string' || typeof item === 'number') && String(item)) {
          playerIds.add(String(item))
        } else {
          visit(item, keyHint)
        }
      })
      return
    }

    if (isRecord(value)) {
      Object.entries(value).forEach(([childKey, childValue]) => visit(childValue, childKey))
    }
  }

  visit(payload)
  return [...playerIds]
}

function readNumberField(payload: Record<string, unknown> | null | undefined, key: string): number | null {
  const value = payload?.[key]
  return typeof value === 'number' ? value : null
}

function findSnapshotSequence(payload: Record<string, unknown> | null | undefined, kind: 'ranking' | 'race'): number | null {
  const candidates = kind === 'ranking'
    ? ['ranking_snapshot_sequence', 'source_ranking_snapshot_sequence', 'ranking_snapshot_seq', 'source_ranking_snapshot_seq']
    : ['race_snapshot_sequence', 'source_race_snapshot_sequence', 'race_snapshot_seq', 'source_race_snapshot_seq']
  for (const key of candidates) {
    const value = readNumberField(payload, key)
    if (value != null) return value
  }
  return null
}

function hasPayloadData(payload: Record<string, unknown> | null | undefined): boolean {
  return Object.keys(payload ?? {}).length > 0
}


function sourceSnapshotLabel(season: number | null | undefined, week: number | null | undefined): string {
  return typeof week === 'number' ? `${season ?? '—'} W${week}` : '—'
}

function renderPlayerLinks(runId: string, playerIds: string[]): JSX.Element | null {
  if (!playerIds.length) return null
  return (
    <ul className="item-list" aria-label="Finals player profile links">
      {playerIds.map((playerId) => (
        <li key={playerId}>
          <Link to={viewerPlayerProfilePath(runId, playerId)}>Player {playerId} profile</Link>
        </li>
      ))}
    </ul>
  )
}

function finalsSummaryItems(summary: FinalsSummaryResponse | undefined, runId: string): Array<{ label: string; value: ReactNode }> {
  const qualification = summary?.qualification ?? null
  const result = summary?.result ?? null
  const qualificationPayload = qualification?.qualification ?? null
  const resultPayload = result?.result ?? null
  return [
    { label: 'Active run ID', value: summary?.run_id ?? (runId || 'unknown') },
    { label: 'Qualification availability', value: qualification ? 'Available' : 'Unavailable' },
    { label: 'Result availability', value: result ? 'Available' : 'Unavailable' },
    { label: 'Season', value: summary?.season ?? qualification?.season ?? result?.season ?? '—' },
    { label: 'Source event ID', value: result?.event_id ? <Link to={viewerPlannedEventPath(runId, result.event_id)}>{result.event_id}</Link> : '—' },
    { label: 'Qualification source snapshot', value: qualification?.source_as_of_week != null ? `${qualification.source_as_of_season} W${qualification.source_as_of_week}` : '—' },
    { label: 'Result source snapshot', value: result?.source_as_of_week != null ? `${result.source_as_of_season} W${result.source_as_of_week}` : '—' },
    ...collectArrayCountItems(qualificationPayload).map((item) => ({ label: `Qualification ${item.label}`, value: item.value })),
    ...collectArrayCountItems(resultPayload).map((item) => ({ label: `Result ${item.label}`, value: item.value }))
  ]
}

function qualificationPrimitiveMetadataItems(payload: Record<string, unknown> | null | undefined): Array<{ label: string; value: string | number }> {
  const excluded = new Set([
    'ranking_snapshot_sequence',
    'source_ranking_snapshot_sequence',
    'ranking_snapshot_seq',
    'source_ranking_snapshot_seq',
    'race_snapshot_sequence',
    'source_race_snapshot_sequence',
    'race_snapshot_seq',
    'source_race_snapshot_seq'
  ])
  return collectPrimitivePayloadItems(payload, excluded).filter((item) => {
    const label = item.label.toLowerCase()
    return label.includes('cutoff') || label.includes('ranking') || label.includes('race') || label.includes('qualification')
  })
}

function subpageQualificationMetadataItems(qualification: FinalsQualificationResponse, runId: string): Array<{ label: string; value: ReactNode }> {
  const payload = qualification.qualification
  const rankingSequence = findSnapshotSequence(payload, 'ranking')
  const raceSequence = findSnapshotSequence(payload, 'race')
  const qualifiedPlayersCount = readArrayFieldLength(payload, 'qualified_player_ids')
  const groupCount = readArrayFieldLength(payload, 'groups')
  const items: Array<{ label: string; value: ReactNode }> = [
    { label: 'Active run ID', value: qualification.run_id },
    { label: 'Season', value: qualification.season },
    { label: 'Source season', value: qualification.source_as_of_season },
    { label: 'Source week', value: formatWeek(qualification.source_as_of_week) },
    { label: 'Qualification availability', value: hasPayloadData(payload) ? 'Available' : 'Unavailable' }
  ]

  if (qualifiedPlayersCount != null) items.push({ label: 'Qualified player count', value: qualifiedPlayersCount })
  if (groupCount != null) items.push({ label: 'Group count', value: groupCount })
  if (rankingSequence != null) items.push({ label: 'Ranking snapshot sequence', value: <Link to={viewerRankingSnapshotPath(runId, rankingSequence)}>Ranking snapshot {rankingSequence}</Link> })
  if (raceSequence != null) items.push({ label: 'Race snapshot sequence', value: <Link to={viewerRaceSnapshotPath(runId, raceSequence)}>Race snapshot {raceSequence}</Link> })
  items.push(...qualificationPrimitiveMetadataItems(payload))

  return items
}

function subpageResultMetadataItems(result: FinalsResultResponse, runId: string): Array<{ label: string; value: ReactNode }> {
  const payload = result.result
  const playerIds = collectPlayerIds(payload)
  return [
    { label: 'Active run ID', value: result.run_id },
    { label: 'Season', value: result.season },
    { label: 'Source season', value: result.source_as_of_season },
    { label: 'Source week', value: formatWeek(result.source_as_of_week) },
    { label: 'Source event ID', value: result.event_id ? <Link to={viewerPlannedEventPath(runId, result.event_id)}>{result.event_id}</Link> : '—' },
    ...collectArrayCountItems(payload),
    ...collectPrimitivePayloadItems(payload),
    ...playerIds.map((playerId) => ({ label: `Player ${playerId}`, value: <Link to={viewerPlayerProfilePath(runId, playerId)}>Player Profile</Link> }))
  ]
}

function qualificationMetadataItems(qualification: FinalsQualificationResponse, runId: string): Array<{ label: string; value: ReactNode }> {
  const payload = qualification.qualification
  const rankingSequence = findSnapshotSequence(payload, 'ranking')
  const raceSequence = findSnapshotSequence(payload, 'race')
  return [
    { label: 'Run ID', value: qualification.run_id },
    { label: 'Season', value: qualification.season },
    { label: 'Source season', value: qualification.source_as_of_season },
    { label: 'Source week', value: `W${qualification.source_as_of_week}` },
    { label: 'Ranking snapshot', value: rankingSequence != null ? <Link to={viewerRankingSnapshotPath(runId, rankingSequence)}>Ranking snapshot {rankingSequence}</Link> : '—' },
    { label: 'Race snapshot', value: raceSequence != null ? <Link to={viewerRaceSnapshotPath(runId, raceSequence)}>Race snapshot {raceSequence}</Link> : '—' },
    ...collectArrayCountItems(payload),
    ...collectPrimitivePayloadItems(payload, new Set(['ranking_snapshot_sequence', 'source_ranking_snapshot_sequence', 'ranking_snapshot_seq', 'source_ranking_snapshot_seq', 'race_snapshot_sequence', 'source_race_snapshot_sequence', 'race_snapshot_seq', 'source_race_snapshot_seq']))
  ]
}

function resultMetadataItems(result: FinalsResultResponse, runId: string): Array<{ label: string; value: ReactNode }> {
  const payload = result.result
  const playerIds = collectPlayerIds(payload)
  return [
    { label: 'Run ID', value: result.run_id },
    { label: 'Season', value: result.season },
    { label: 'Source event ID', value: result.event_id ? <Link to={viewerPlannedEventPath(runId, result.event_id)}>{result.event_id}</Link> : '—' },
    { label: 'Source season', value: result.source_as_of_season },
    { label: 'Source week', value: `W${result.source_as_of_week}` },
    ...collectArrayCountItems(payload),
    ...collectPrimitivePayloadItems(payload),
    ...playerIds.map((playerId) => ({ label: `Player ${playerId}`, value: <Link to={viewerPlayerProfilePath(runId, playerId)}>Player Profile</Link> }))
  ]
}

function hasQualificationPreviewData(payload: Record<string, unknown> | null | undefined): boolean {
  return hasPayloadData(payload) && (
    collectPlayerIds(payload).length > 0 ||
    readArrayFieldLength(payload, 'qualified_player_ids') != null ||
    readArrayFieldLength(payload, 'groups') != null ||
    findSnapshotSequence(payload, 'ranking') != null ||
    findSnapshotSequence(payload, 'race') != null ||
    qualificationPrimitiveMetadataItems(payload).length > 0
  )
}

function hasResultPreviewData(payload: Record<string, unknown> | null | undefined): boolean {
  return hasPayloadData(payload) && (
    collectPlayerIds(payload).length > 0 ||
    collectArrayCountItems(payload).length > 0 ||
    collectPrimitivePayloadItems(payload).length > 0
  )
}

function readArrayFieldLength(payload: Record<string, unknown> | null | undefined, key: string): number | null {
  const value = payload?.[key]
  return Array.isArray(value) ? value.length : null
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

export function ViewerRunFinalsPage(): JSX.Element {
  const { runId = '' } = useParams()
  const summaryQuery = useQuery({
    queryKey: ['finals-summary', runId],
    queryFn: () => getFinalsSummary(runId),
    enabled: Boolean(runId),
    retry: false
  })

  const summary = summaryQuery.data
  const qualification = summary?.qualification ?? null
  const result = summary?.result ?? null
  const qualificationPayload = qualification?.qualification ?? null
  const resultPayload = result?.result ?? null
  const qualificationPlayerIds = collectPlayerIds(qualificationPayload)
  const resultPlayerIds = collectPlayerIds(resultPayload)

  return (
    <section className="panel">
      <RunScopedHeader title="World Tour Finals" runId={runId} subtitle="Read-only Finals summary, qualification, and result metadata from existing run data only." />
      <CurrentContextStrip
        items={[
          { label: 'Active run', value: runId || 'unknown' },
          { label: 'Qualification', value: qualification ? 'Available' : 'Unavailable' },
          { label: 'Result', value: result ? 'Available' : 'Unavailable' },
          { label: 'Season', value: summary?.season ?? qualification?.season ?? result?.season ?? '—' }
        ]}
      />

      <SectionCard title="Finals Summary">
        {summaryQuery.isLoading ? <p className="status">Loading Finals summary…</p> : null}
        {summaryQuery.error ? <p className="error">Failed to load Finals summary: {formatApiError(summaryQuery.error)}</p> : null}
        {summary ? <MetadataList items={finalsSummaryItems(summary, runId)} /> : null}
      </SectionCard>

      <SectionCard title="Qualification">
        {summaryQuery.isLoading ? <p className="status">Loading Finals qualification metadata…</p> : null}
        {qualification ? (
          hasPayloadData(qualificationPayload) ? (
            <>
              <MetadataList items={qualificationMetadataItems(qualification, runId)} />
              {renderPlayerLinks(runId, qualificationPlayerIds)}
            </>
          ) : (
            <EmptyState message="This preview is not connected for this data shape yet." />
          )
        ) : summaryQuery.data ? (
          <EmptyState message="This preview is not connected for this data shape yet." />
        ) : null}
      </SectionCard>

      <SectionCard title="Result">
        {summaryQuery.isLoading ? <p className="status">Loading Finals result metadata…</p> : null}
        {result ? (
          hasPayloadData(resultPayload) ? (
            <>
              <MetadataList items={resultMetadataItems(result, runId)} />
              {renderPlayerLinks(runId, resultPlayerIds)}
            </>
          ) : (
            <EmptyState message="This preview is not connected for this data shape yet." />
          )
        ) : summaryQuery.data ? (
          <EmptyState message="This preview is not connected for this data shape yet." />
        ) : null}
      </SectionCard>

      <SectionCard title="Links">
        <p className="viewer-active-run-actions">
          <Link className="viewer-active-run-link" to={viewerSeasonCalendarPath(runId)}>Back to Season Calendar</Link>{' '}
          <Link className="viewer-active-run-link" to={viewerFinalsQualificationPath(runId)}>Open Finals qualification</Link>{' '}
          <Link className="viewer-active-run-link" to={viewerFinalsResultPath(runId)}>Open Finals result</Link>{' '}
          <Link className="viewer-active-run-link" to={viewerRankingsPath(runId)}>Open rankings</Link>{' '}
          <Link className="viewer-active-run-link" to={viewerRacePath(runId)}>Open race</Link>{' '}
          <Link className="viewer-active-run-link" to={viewerTournamentsPath(runId)}>Open tournaments</Link>
        </p>
      </SectionCard>

      {summary ? (
        <SectionCard title="Read-only data">
          <TechnicalData
            summary="Show technical finals data"
            title="Technical Finals data"
            payload={summary}
            emptyText="No technical Finals data is available."
          />
        </SectionCard>
      ) : null}
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
  const qualification = qualificationQuery.data
  const payload = isRecord(qualification?.qualification) ? qualification.qualification : null
  const playerIds = collectPlayerIds(payload)
  const hasSafePreview = Boolean(qualification && hasQualificationPreviewData(payload))

  return (
    <section className="panel">
      <RunScopedHeader title="Finals Qualification" runId={runId} subtitle="Read-only Finals qualification for the selected run." />
      <CurrentContextStrip
        items={[
          { label: 'Active run', value: runId || 'unknown' },
          { label: 'Season', value: qualification?.season ?? '—' },
          { label: 'Source snapshot', value: qualification ? sourceSnapshotLabel(qualification.source_as_of_season, qualification.source_as_of_week) : '—' },
          { label: 'Qualification', value: payload ? 'Available' : notFound ? 'Unavailable' : 'Loading' }
        ]}
      />

      <SectionCard title="Qualification Summary">
        {qualificationQuery.isLoading ? <p className="status">Loading Finals qualification…</p> : null}
        {qualificationQuery.error && !notFound ? <p className="error">Failed to load Finals qualification: {formatApiError(qualificationQuery.error)}</p> : null}
        {notFound ? <EmptyState message="No data is available for this run yet." /> : null}
        {qualification ? (
          hasSafePreview ? (
            <MetadataList items={subpageQualificationMetadataItems(qualification, runId)} />
          ) : (
            <EmptyState message="This preview is not connected for this data shape yet." />
          )
        ) : null}
      </SectionCard>

      <SectionCard title="Qualified Players / Links">
        {hasSafePreview && playerIds.length > 0 ? renderPlayerLinks(runId, playerIds) : <EmptyState message="This preview is not connected for this data shape yet." />}
      </SectionCard>

      <SectionCard title="Links">
        <p className="viewer-active-run-actions">
          <Link className="viewer-active-run-link" to={viewerFinalsPath(runId)}>Back to Finals Summary</Link>{' '}
          <Link className="viewer-active-run-link" to={viewerRankingsPath(runId)}>Open rankings</Link>{' '}
          <Link className="viewer-active-run-link" to={viewerRacePath(runId)}>Open race</Link>{' '}
          <Link className="viewer-active-run-link" to={viewerTournamentsPath(runId)}>Open tournaments</Link>
        </p>
      </SectionCard>

      {payload ? (
        <SectionCard title="Read-only data">
          <TechnicalData
            summary="Show technical finals qualification data"
            title="Technical qualification data"
            payload={qualification}
            emptyText="No technical Finals qualification data is available."
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
  const result = resultQuery.data
  const payload = isRecord(result?.result) ? result.result : null
  const playerIds = collectPlayerIds(payload)
  const hasSafePreview = Boolean(result && hasResultPreviewData(payload))

  return (
    <section className="panel">
      <RunScopedHeader title="Finals Result" runId={runId} subtitle="Read-only Finals result for the selected run." />
      <CurrentContextStrip
        items={[
          { label: 'Active run', value: runId || 'unknown' },
          { label: 'Season', value: result?.season ?? '—' },
          { label: 'Source snapshot', value: result ? sourceSnapshotLabel(result.source_as_of_season, result.source_as_of_week) : '—' },
          { label: 'Result', value: payload ? 'Available' : notFound ? 'Unavailable' : 'Loading' }
        ]}
      />

      <SectionCard title="Result Summary">
        {resultQuery.isLoading ? <p className="status">Loading Finals result…</p> : null}
        {resultQuery.error && !notFound ? <p className="error">Failed to load Finals result: {formatApiError(resultQuery.error)}</p> : null}
        {notFound ? <EmptyState message="No data is available for this run yet." /> : null}
        {result ? (
          hasSafePreview ? (
            <MetadataList items={subpageResultMetadataItems(result, runId)} />
          ) : (
            <EmptyState message="This preview is not connected for this data shape yet." />
          )
        ) : null}
      </SectionCard>

      <SectionCard title="Player Links">
        {hasSafePreview && playerIds.length > 0 ? renderPlayerLinks(runId, playerIds) : <EmptyState message="This preview is not connected for this data shape yet." />}
      </SectionCard>

      <SectionCard title="Source Links">
        {hasSafePreview && result?.event_id ? (
          <ul className="item-list" aria-label="Finals source event links">
            <li><Link to={viewerPlannedEventPath(runId, result.event_id)}>Planned event {result.event_id}</Link></li>
            <li><Link to={viewerTournamentDetailPath(runId, result.event_id)}>Tournament detail {result.event_id}</Link></li>
          </ul>
        ) : (
          <EmptyState message="This preview is not connected for this data shape yet." />
        )}
      </SectionCard>

      <SectionCard title="Links">
        <p className="viewer-active-run-actions">
          <Link className="viewer-active-run-link" to={viewerFinalsPath(runId)}>Back to Finals Summary</Link>{' '}
          <Link className="viewer-active-run-link" to={viewerRankingsPath(runId)}>Open rankings</Link>{' '}
          <Link className="viewer-active-run-link" to={viewerRacePath(runId)}>Open race</Link>{' '}
          <Link className="viewer-active-run-link" to={viewerTournamentsPath(runId)}>Open tournaments</Link>
        </p>
      </SectionCard>

      {payload ? (
        <SectionCard title="Read-only data">
          <TechnicalData
            summary="Show technical finals result data"
            title="Technical result data"
            payload={result}
            emptyText="No technical Finals result data is available."
          />
        </SectionCard>
      ) : null}
    </section>
  )
}
