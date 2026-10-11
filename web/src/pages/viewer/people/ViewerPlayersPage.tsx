import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'

import { getViewerPlayers } from '../../../api/client'
import { ViewerEmptyState, ViewerSampleList } from '../../../components/viewer/ViewerLandingComponents'
import { ViewerShellPage } from '../../../components/viewer/ViewerShellPage'
import { useActiveViewerProductRunId } from '../../../viewer/useActiveViewerProductRunId'
import { viewerPlayersPath } from '../../../viewer/viewerRoutes'
import { renderPlayerSampleMetadata } from './viewerPeopleRender'

export function ViewerPlayersPage(): JSX.Element {
  const productRunId = useActiveViewerProductRunId()
  const playersQuery = useQuery({
    queryKey: ['viewer-players-hub-canonical', productRunId],
    queryFn: () => getViewerPlayers(productRunId ?? ''),
    enabled: Boolean(productRunId),
    retry: false
  })

  if (!productRunId) {
    return (
      <ViewerShellPage
        title="Players"
        description="Read-only canonical player profiles in the selected Viewer Product Run."
      >
        <ViewerEmptyState>No Product Run is selected yet.</ViewerEmptyState>
      </ViewerShellPage>
    )
  }

  const players = playersQuery.data?.players.slice(0, 5) ?? []

  return (
    <ViewerShellPage title="Players" description="Read-only Saved-Revision player profiles for the selected Product Run.">
      <article className="viewer-active-run-card" aria-label="Players canonical Product Run summary">
        <span className="eyebrow">Selected Product Run</span>
        <h3>Players summary</h3>
        {playersQuery.isLoading ? <p className="status">Loading canonical player metadata…</p> : null}
        {playersQuery.isError ? <ViewerEmptyState>Canonical player metadata is temporarily unavailable.</ViewerEmptyState> : null}
        <dl className="metadata-list">
          <div><dt>Product Run</dt><dd>{productRunId}</dd></div>
          <div><dt>Viewer Branch</dt><dd>{playersQuery.data?.viewer_branch_id ?? '—'}</dd></div>
          <div><dt>Total player count</dt><dd>{playersQuery.isLoading ? 'Loading…' : playersQuery.data?.player_count ?? '—'}</dd></div>
          <div><dt>Active players</dt><dd>{playersQuery.isLoading ? 'Loading…' : playersQuery.data?.active_player_count ?? '—'}</dd></div>
          <div><dt>Retired players</dt><dd>{playersQuery.isLoading ? 'Loading…' : playersQuery.data?.retired_player_count ?? '—'}</dd></div>
        </dl>
        {!playersQuery.isLoading && !playersQuery.isError && players.length === 0 ? <ViewerEmptyState>No canonical players are available for this Product Run yet.</ViewerEmptyState> : null}
        <ViewerSampleList
          title="Sample players"
          label="Sample canonical players"
          items={players}
          getKey={(player) => player.player_id}
          renderItem={(player) => renderPlayerSampleMetadata(player, productRunId)}
        />
        <p className="viewer-active-run-actions">
          <Link className="viewer-active-run-link" to={viewerPlayersPath(productRunId)}>Open Product Run players</Link>
        </p>
      </article>
    </ViewerShellPage>
  )
}
