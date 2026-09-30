import { useQuery } from '@tanstack/react-query'
import type { ReactNode } from 'react'
import { Link, useParams } from 'react-router-dom'
import { useViewerProductRunRouteContext } from '../viewer/ViewerProductRunRouteContext'

import { getFinalsResult, getRunActivity, getViewerFinalsRace } from '../api/client'
import type { FinalsResultResponse, RunActivityItem, ViewerFinalsRaceHistory, ViewerFinalsRacePublication, ViewerFinalsRaceRow } from '../api/types'
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
  viewerRankingsPath,
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

function isScalar(value: unknown): value is string | number | boolean {
  return typeof value === 'string' || typeof value === 'number' || typeof value === 'boolean'
}

function safeScalarValue(value: unknown, fallback: string | number = '—'): string | number {
  if (typeof value === 'string' || typeof value === 'number') return value
  if (typeof value === 'boolean') return value ? 'Yes' : 'No'
  return fallback
}

function safeLinkId(value: unknown): string | null {
  if (typeof value !== 'string' && typeof value !== 'number') return null
  const id = String(value)
  return id.length > 0 ? id : null
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

function subpageResultMetadataItems(result: FinalsResultResponse, runId: string): Array<{ label: string; value: ReactNode }> {
  const payload = result.result
  const playerIds = collectPlayerIds(payload)
  const eventId = safeLinkId(result.event_id)
  return [
    { label: 'Active run ID', value: safeScalarValue(result.run_id) },
    { label: 'Season', value: safeScalarValue(result.season) },
    { label: 'Source season', value: safeScalarValue(result.source_as_of_season) },
    { label: 'Source week', value: formatWeek(result.source_as_of_week) },
    { label: 'Source event ID', value: eventId ? <Link to={viewerPlannedEventPath(runId, eventId)}>{eventId}</Link> : '—' },
    ...collectArrayCountItems(payload),
    ...collectPrimitivePayloadItems(payload),
    ...playerIds.map((playerId) => ({ label: `Player ${playerId}`, value: <Link to={viewerPlayerProfilePath(runId, playerId)}>Player Profile</Link> }))
  ]
}

function resultMetadataItems(result: FinalsResultResponse, runId: string): Array<{ label: string; value: ReactNode }> {
  const payload = result.result
  const playerIds = collectPlayerIds(payload)
  const eventId = safeLinkId(result.event_id)
  return [
    { label: 'Run ID', value: safeScalarValue(result.run_id) },
    { label: 'Season', value: safeScalarValue(result.season) },
    { label: 'Source event ID', value: eventId ? <Link to={viewerPlannedEventPath(runId, eventId)}>{eventId}</Link> : '—' },
    { label: 'Source season', value: safeScalarValue(result.source_as_of_season) },
    { label: 'Source week', value: `W${result.source_as_of_week}` },
    ...collectArrayCountItems(payload),
    ...collectPrimitivePayloadItems(payload),
    ...playerIds.map((playerId) => ({ label: `Player ${playerId}`, value: <Link to={viewerPlayerProfilePath(runId, playerId)}>Player Profile</Link> }))
  ]
}

function hasResultPreviewData(payload: Record<string, unknown> | null | undefined): boolean {
  return hasPayloadData(payload) && (
    collectPlayerIds(payload).length > 0 ||
    collectArrayCountItems(payload).length > 0 ||
    collectPrimitivePayloadItems(payload).length > 0
  )
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

function latestFinalsPublication(history: ViewerFinalsRaceHistory | undefined): ViewerFinalsRacePublication | null {
  if (!history || history.latest_target_season_index == null) return null
  return history.publications.find(
    (publication) => publication.target_season_index === history.latest_target_season_index
  ) ?? null
}

function confirmedFinalsParticipants(publication: ViewerFinalsRacePublication | null): ViewerFinalsRaceRow[] {
  if (!publication?.selection_published) return []
  return publication.rows
    .filter((row) => row.finals_selected === true)
    .sort((a, b) => (a.finals_seed ?? Number.MAX_SAFE_INTEGER) - (b.finals_seed ?? Number.MAX_SAFE_INTEGER))
}

function FinalsParticipantList({ runId, rows }: { runId: string; rows: ViewerFinalsRaceRow[] }): JSX.Element {
  if (!rows.length) return <EmptyState message="Confirmed World Tour Finals participants are not published yet." />
  return (
    <div className="table-wrap">
      <table aria-label="Canonical World Tour Finals participants">
        <thead>
          <tr>
            <th>Seed</th>
            <th>Player</th>
            <th>Race rank</th>
            <th>Race points</th>
            <th>Qualification</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.player_id}>
              <td>{row.finals_seed ?? '—'}</td>
              <td><Link to={viewerPlayerProfilePath(runId, row.player_id)}>{row.player_id}</Link></td>
              <td>#{row.rank}</td>
              <td>{row.race_points}</td>
              <td>{row.qualification_source === 'direct_entry' ? 'Direct entry' : row.qualification_source === 'race' ? 'Race' : '—'}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
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

export function ViewerRunFinalsPage(): JSX.Element {
  const { productRunId: runId } = useViewerProductRunRouteContext()
  const raceQuery = useQuery({
    queryKey: ['viewer-finals-race', runId],
    queryFn: () => getViewerFinalsRace(runId),
    enabled: Boolean(runId),
    retry: false
  })
  const publication = latestFinalsPublication(raceQuery.data)
  const participants = confirmedFinalsParticipants(publication)

  return (
    <section className="panel">
      <RunScopedHeader
        title="World Tour Finals"
        runId={runId}
        subtitle="Canonical confirmed Finals field from the selected Viewer Branch's Saved Revision."
      />
      <CurrentContextStrip
        items={[
          { label: 'Active run', value: runId || 'unknown' },
          { label: 'Qualification', value: publication?.selection_published ? 'Published' : publication ? 'Pending' : 'Unavailable' },
          { label: 'Target season index', value: publication?.target_season_index ?? '—' },
          { label: 'Confirmed players', value: participants.length }
        ]}
      />

      <SectionCard title="Finals Summary">
        {raceQuery.isLoading ? <p className="status">Loading canonical Finals publication…</p> : null}
        {raceQuery.error ? <p className="error">Failed to load canonical Finals publication: {formatApiError(raceQuery.error)}</p> : null}
        {publication ? (
          <MetadataList
            items={[
              { label: 'Viewer Branch', value: publication.viewer_branch_id },
              { label: 'Finals event ID', value: publication.finals_event_id ?? 'Not selected yet' },
              { label: 'Race cutoff', value: `season ${publication.cutoff_season_index}, W${publication.cutoff_week}` },
              { label: 'Best-N', value: publication.best_n },
              { label: 'Selection published', value: publication.selection_published ? 'Yes' : 'No' },
              { label: 'Confirmed participants', value: participants.length }
            ]}
          />
        ) : raceQuery.data ? (
          <EmptyState message="No canonical World Tour Finals Race publication exists yet." />
        ) : null}
      </SectionCard>

      <SectionCard title="Confirmed Finals Participants">
        <FinalsParticipantList runId={runId} rows={participants} />
      </SectionCard>

      <SectionCard title="Finals Result">
        <p className="status">
          Finals result publication remains a separate migration. The confirmed participant field above is canonical;
          the existing result page remains read-only compatibility until it is bound to canonical Tournament Result history.
        </p>
        <p><Link to={viewerFinalsResultPath(runId)}>Open Finals result</Link></p>
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
    </section>
  )
}

export function ViewerRunFinalsQualificationPage(): JSX.Element {
  const { productRunId: runId } = useViewerProductRunRouteContext()
  const raceQuery = useQuery({
    queryKey: ['viewer-finals-race', runId],
    queryFn: () => getViewerFinalsRace(runId),
    enabled: Boolean(runId),
    retry: false
  })
  const publication = latestFinalsPublication(raceQuery.data)
  const participants = confirmedFinalsParticipants(publication)

  return (
    <section className="panel">
      <RunScopedHeader
        title="Finals Qualification"
        runId={runId}
        subtitle="Canonical confirmed World Tour Finals participant field from Saved Revision authority."
      />
      <CurrentContextStrip
        items={[
          { label: 'Active run', value: runId || 'unknown' },
          { label: 'Target season index', value: publication?.target_season_index ?? '—' },
          { label: 'Race cutoff', value: publication ? `W${publication.cutoff_week}` : '—' },
          { label: 'Qualification', value: publication?.selection_published ? 'Published' : publication ? 'Pending' : 'Unavailable' }
        ]}
      />

      <SectionCard title="Qualification Summary">
        {raceQuery.isLoading ? <p className="status">Loading canonical Finals qualification…</p> : null}
        {raceQuery.error ? <p className="error">Failed to load canonical Finals qualification: {formatApiError(raceQuery.error)}</p> : null}
        {publication ? (
          <MetadataList
            items={[
              { label: 'Viewer Branch', value: publication.viewer_branch_id },
              { label: 'Finals event ID', value: publication.finals_event_id ?? 'Not selected yet' },
              { label: 'Target season index', value: publication.target_season_index },
              { label: 'Cutoff season index', value: publication.cutoff_season_index },
              { label: 'Cutoff week', value: `W${publication.cutoff_week}` },
              { label: 'Best-N', value: publication.best_n },
              { label: 'Confirmed players', value: participants.length }
            ]}
          />
        ) : raceQuery.data ? (
          <EmptyState message="No canonical World Tour Finals Race publication exists yet." />
        ) : null}
      </SectionCard>

      <SectionCard title="Confirmed Participants">
        <FinalsParticipantList runId={runId} rows={participants} />
      </SectionCard>

      <SectionCard title="Links">
        <p className="viewer-active-run-actions">
          <Link className="viewer-active-run-link" to={viewerFinalsPath(runId)}>Back to Finals Summary</Link>{' '}
          <Link className="viewer-active-run-link" to={viewerRankingsPath(runId)}>Open rankings</Link>{' '}
          <Link className="viewer-active-run-link" to={viewerRacePath(runId)}>Open race</Link>{' '}
          <Link className="viewer-active-run-link" to={viewerTournamentsPath(runId)}>Open tournaments</Link>
        </p>
      </SectionCard>
    </section>
  )
}

export function ViewerRunFinalsResultPage(): JSX.Element {
  const { productRunId: runId, legacySimulationRunId } = useViewerProductRunRouteContext()
  const resultQuery = useQuery({
    queryKey: ['finals-result', runId, legacySimulationRunId],
    queryFn: () => getFinalsResult(legacySimulationRunId),
    enabled: Boolean(runId),
    retry: false
  })

  const notFound = isApiNotFound(resultQuery.error)
  const result = resultQuery.data
  const payload = isRecord(result?.result) ? result.result : null
  const playerIds = collectPlayerIds(payload)
  const hasSafePreview = Boolean(result && hasResultPreviewData(payload))
  const eventId = safeLinkId(result?.event_id)

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
        {hasSafePreview && eventId ? (
          <ul className="item-list" aria-label="Finals source event links">
            <li><Link to={viewerPlannedEventPath(runId, eventId)}>Planned event {eventId}</Link></li>
            <li><Link to={viewerTournamentDetailPath(runId, eventId)}>Tournament detail {eventId}</Link></li>
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
