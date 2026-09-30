import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'

import { getViewerFinalsRace } from '../../../api/client'
import type { ViewerFinalsRacePublication, ViewerFinalsRaceRow } from '../../../api/types'
import {
  ViewerActiveRunLinks,
  ViewerEmptyState,
  ViewerMetadataList,
  ViewerSectionCard
} from '../../../components/viewer/ViewerLandingComponents'
import { formatApiError } from '../../../utils/apiErrors'
import { useActiveViewerProductRunId } from '../../../viewer/useActiveViewerProductRunId'
import { useViewerProductRunRouteContext } from '../../../viewer/ViewerProductRunRouteContext'
import { viewerPlayerProfilePath, viewerRacePath } from '../../../viewer/viewerRoutes'
import { findViewerTopLevelHubLink } from '../../../viewer/viewerHubLinks'

const VIEWER_RACE_HUB_LINK = findViewerTopLevelHubLink('Race to Finals')

function seasonLabel(index: number): string {
  const start = 2000 + index
  return `${start}/${String((start + 1) % 100).padStart(2, '0')}`
}

function qualificationLabel(row: ViewerFinalsRaceRow): string {
  if (row.finals_selected === null) return 'Selection pending'
  if (!row.finals_selected) return 'Not selected'
  if (row.qualification_source === 'direct_entry') {
    return row.finals_seed == null ? 'Direct entry' : `Direct entry · seed ${row.finals_seed}`
  }
  return row.finals_seed == null ? 'Race qualified' : `Race qualified · seed ${row.finals_seed}`
}

function countedResultsLabel(row: ViewerFinalsRaceRow): string {
  if (!row.counted_results.length) return 'None'
  return row.counted_results
    .map((result) => `${result.event_id}: ${result.race_points} pts (W${result.completed_week})`)
    .join(' · ')
}

function FinalsRaceTable({
  publication,
  productRunId
}: {
  publication: ViewerFinalsRacePublication
  productRunId: string
}): JSX.Element {
  return (
    <div className="table-wrap">
      <table aria-label="Canonical Finals Race standings">
        <thead>
          <tr>
            <th>Rank</th>
            <th>Player</th>
            <th>Race points</th>
            <th>Counted</th>
            <th>Finals status</th>
            <th>Counted results</th>
          </tr>
        </thead>
        <tbody>
          {publication.rows.map((row) => (
            <tr key={row.player_id}>
              <td>{row.rank}</td>
              <td>
                <Link to={viewerPlayerProfilePath(productRunId, row.player_id)}>
                  {row.player_id}
                </Link>
              </td>
              <td>{row.race_points}</td>
              <td>{row.tournaments_counted}</td>
              <td>{qualificationLabel(row)}</td>
              <td>{countedResultsLabel(row)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function ViewerFinalsRaceContent({
  productRunId,
  showRunLink
}: {
  productRunId: string | null
  showRunLink: boolean
}): JSX.Element {
  const query = useQuery({
    queryKey: ['viewer-canonical-finals-race', productRunId],
    queryFn: () => getViewerFinalsRace(productRunId ?? ''),
    enabled: Boolean(productRunId),
    retry: false
  })

  const publications = query.data?.publications ?? []
  const latest = publications.length ? publications[publications.length - 1] : null

  return (
    <section className="panel viewer-shell-page">
      <div className="page-intro">
        <span className="eyebrow">Read-only canonical Race</span>
        <h2>{VIEWER_RACE_HUB_LINK.label}</h2>
        <p className="subtitle">
          Frozen seasonal World Tour Finals Race from the selected Viewer Branch Saved Revision.
        </p>
      </div>

      {!productRunId ? (
        <ViewerEmptyState>Select a Product Run before opening Race to Finals.</ViewerEmptyState>
      ) : null}
      {query.isLoading ? <p className="status">Loading canonical Finals Race…</p> : null}
      {query.error ? <p className="error">Failed to load canonical Finals Race: {formatApiError(query.error)}</p> : null}
      {!query.isLoading && !query.error && productRunId && !latest ? (
        <ViewerEmptyState>No canonical Finals Race has been published for this Viewer Branch yet.</ViewerEmptyState>
      ) : null}

      {latest && productRunId ? (
        <>
          <ViewerSectionCard kicker="Latest saved season" title={`Race to Finals · ${seasonLabel(latest.target_season_index)}`} variant="hero">
            <ViewerMetadataList
              items={[
                { label: 'Viewer Branch', value: latest.viewer_branch_id },
                { label: 'Target season', value: seasonLabel(latest.target_season_index) },
                { label: 'Cutoff', value: `${seasonLabel(latest.cutoff_season_index)} · W${latest.cutoff_week}` },
                { label: 'Best N', value: latest.best_n },
                { label: 'Race players', value: latest.rows.length },
                { label: 'Finals selection', value: latest.selection_published ? 'Published' : 'Pending' },
                { label: 'Finals event', value: latest.finals_event_id ?? 'Not published yet' }
              ]}
            />
            <FinalsRaceTable publication={latest} productRunId={productRunId} />
            {showRunLink ? (
              <ViewerActiveRunLinks links={[{ label: 'Open run-scoped Race', to: viewerRacePath(productRunId) }]} />
            ) : null}
          </ViewerSectionCard>

          <ViewerSectionCard kicker="Saved history" title="Seasonal Race publications">
            <ul className="viewer-home-list" aria-label="Canonical Finals Race publication history">
              {[...publications].reverse().map((publication) => (
                <li key={publication.target_season_index}>
                  <strong>{seasonLabel(publication.target_season_index)}</strong>
                  {' · '}
                  cutoff W{publication.cutoff_week}
                  {' · '}
                  {publication.rows.length} players
                  {' · '}
                  {publication.selection_published
                    ? `${publication.rows.filter((row) => row.finals_selected).length} Finals participants`
                    : 'Finals selection pending'}
                </li>
              ))}
            </ul>
          </ViewerSectionCard>
        </>
      ) : null}
    </section>
  )
}

export function ViewerRacePage(): JSX.Element {
  const productRunId = useActiveViewerProductRunId()
  return <ViewerFinalsRaceContent productRunId={productRunId} showRunLink />
}

export function ViewerRunRacePage(): JSX.Element {
  const { productRunId } = useViewerProductRunRouteContext()
  return <ViewerFinalsRaceContent productRunId={productRunId} showRunLink={false} />
}
