import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'

import { listRunPlayers } from '../../../api/client'
import { ViewerEmptyState, ViewerSampleList } from '../../../components/viewer/ViewerLandingComponents'
import { ViewerShellPage } from '../../../components/viewer/ViewerShellPage'
import { useActiveViewerRunId } from '../../../viewer/useActiveViewerRunId'
import { viewerPlayersPath } from '../../../viewer/viewerRoutes'
import { renderPlayerSampleMetadata } from './viewerPeopleRender'

export function ViewerPlayersPage(): JSX.Element {
  const activeRunId = useActiveViewerRunId()
  const playersQuery = useQuery({
    queryKey: ['viewer-players-hub-run-players', activeRunId],
    queryFn: () => listRunPlayers(activeRunId ?? '', { limit: 5, offset: 0 }),
    enabled: Boolean(activeRunId),
    retry: false
  })

  if (!activeRunId) {
    return (
      <ViewerShellPage
        title="Players"
        description="Read-only player profiles and browsing in the selected Viewer context."
      >
        <ViewerEmptyState>No data is available for this run yet.</ViewerEmptyState>
      </ViewerShellPage>
    )
  }

  const players = playersQuery.data?.players ?? []

  return (
    <ViewerShellPage title="Players" description="Read-only player profiles using existing active-run player data.">
      <article className="viewer-active-run-card" aria-label="Players active run summary">
        <span className="eyebrow">Active Viewer run</span>
        <h3>Players summary</h3>
        {playersQuery.isLoading ? <p className="status">Loading active run player metadata…</p> : null}
        {playersQuery.isError ? <ViewerEmptyState>Player metadata is temporarily unavailable for this run.</ViewerEmptyState> : null}
        <dl className="metadata-list">
          <div><dt>Active run ID</dt><dd>{activeRunId}</dd></div>
          <div><dt>Total player count</dt><dd>{playersQuery.isLoading ? 'Loading…' : playersQuery.data?.total ?? '—'}</dd></div>
          <div><dt>Returned player count</dt><dd>{playersQuery.isLoading ? 'Loading…' : players.length}</dd></div>
        </dl>
        {!playersQuery.isLoading && !playersQuery.isError && players.length === 0 ? <ViewerEmptyState>No data is available for this run yet.</ViewerEmptyState> : null}
        <ViewerSampleList
          title="Sample players"
          label="Sample active run players"
          items={players}
          getKey={(player) => player.player_id || player.name || 'unknown-player'}
          renderItem={(player) => renderPlayerSampleMetadata(player, activeRunId)}
        />
        <p className="viewer-active-run-actions">
          <Link className="viewer-active-run-link" to={viewerPlayersPath(activeRunId)}>Open active run players</Link>
        </p>
      </article>
    </ViewerShellPage>
  )
}
