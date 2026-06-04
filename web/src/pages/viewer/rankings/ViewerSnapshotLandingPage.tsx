import { useQuery } from '@tanstack/react-query'

import { listRaceSnapshots, listRankingSnapshots } from '../../../api/client'
import { ViewerActiveRunCard, ViewerActiveRunLinks, ViewerEmptyState, ViewerMetadataList } from '../../../components/viewer/ViewerLandingComponents'
import { ViewerShellPage } from '../../../components/viewer/ViewerShellPage'
import { RacePreviewTable } from '../../../viewer/RacePreviewTable'
import { RankingPreviewTable } from '../../../viewer/RankingPreviewTable'
import { parseRacePreviewPayload } from '../../../viewer/racePayload'
import { parseRankingPreviewPayload } from '../../../viewer/rankingPayload'
import { useActiveViewerRunId } from '../../../viewer/useActiveViewerRunId'
import { latestSnapshot } from './viewerSnapshotDisplay'

export type ViewerSnapshotLandingMode = 'ranking' | 'race'

export type ViewerSnapshotLandingConfig = {
  mode: ViewerSnapshotLandingMode
  title: string
  description: string
  emptyMessage: string
  noSnapshotsMessage: string
  countLabel: string
  openLabel: string
  latestLabel: string
  runScopedPath: (runId: string) => string
  detailPath: (runId: string, snapshotSequence: number) => string
}

export function ViewerSnapshotLandingPage({ config }: { config: ViewerSnapshotLandingConfig }): JSX.Element {
  const activeRunId = useActiveViewerRunId()
  const snapshotsQuery = useQuery({
    queryKey: ['viewer-top-level-snapshots', config.mode, activeRunId],
    queryFn: () => (config.mode === 'ranking' ? listRankingSnapshots(activeRunId ?? '') : listRaceSnapshots(activeRunId ?? '')),
    enabled: Boolean(activeRunId),
    retry: false
  })

  if (!activeRunId) {
    return (
      <ViewerShellPage title={config.title} description={config.description}>
        <ViewerEmptyState>{config.emptyMessage}</ViewerEmptyState>
      </ViewerShellPage>
    )
  }

  const snapshots = snapshotsQuery.data?.snapshots ?? []
  const latest = latestSnapshot(snapshots)
  const rankingPreview = config.mode === 'ranking' && latest ? parseRankingPreviewPayload(latest.payload) : null
  const racePreview = config.mode === 'race' && latest ? parseRacePreviewPayload(latest.payload) : null

  return (
    <ViewerShellPage title={config.title} description={config.description}>
      <ViewerActiveRunCard ariaLabel={`${config.title} active run snapshot summary`} title={`${config.title} snapshot landing`}>
        <ViewerMetadataList
          items={[
            { label: 'Active run ID', value: activeRunId },
            { label: config.countLabel, value: snapshotsQuery.isLoading ? 'Loading…' : snapshots.length },
            { label: 'Latest snapshot sequence', value: latest ? latest.snapshot_sequence : '—' },
            { label: 'Latest source event ID', value: latest?.source_event_id ?? '—' },
            { label: 'Latest snapshot kind', value: latest?.snapshot_kind ?? '—' }
          ]}
        />

        {snapshotsQuery.isError ? <ViewerEmptyState>Snapshot metadata is temporarily unavailable for this run.</ViewerEmptyState> : null}
        {!snapshotsQuery.isLoading && !snapshotsQuery.isError && !latest ? <ViewerEmptyState>{config.noSnapshotsMessage}</ViewerEmptyState> : null}
        {rankingPreview?.rows.length ? (
          <div>
            <h4>Top 10 Ranking Preview</h4>
            <RankingPreviewTable rows={rankingPreview.rows} ariaLabel="Latest Top 10 ranking preview table" runId={activeRunId} />
          </div>
        ) : null}
        {racePreview?.rows.length ? (
          <div>
            <h4>Top 10 Race Preview</h4>
            <RacePreviewTable rows={racePreview.rows} ariaLabel="Latest Top 10 race preview table" runId={activeRunId} />
          </div>
        ) : null}

        <ViewerActiveRunLinks
          links={[
            { label: config.openLabel, to: config.runScopedPath(activeRunId) },
            ...(latest ? [{ label: config.latestLabel, to: config.detailPath(activeRunId, latest.snapshot_sequence) }] : [])
          ]}
        />
      </ViewerActiveRunCard>
    </ViewerShellPage>
  )
}
