import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'

import { listViewerOfficialRankingHistory } from '../../../api/client'
import { EmptyState, RunScopedHeader, SectionCard } from '../../../components/RunScopedUi'
import { formatApiError } from '../../../utils/apiErrors'
import { useViewerProductRunRouteContext } from '../../../viewer/ViewerProductRunRouteContext'
import { viewerRankingSnapshotPath } from '../../../viewer/viewerRoutes'

export function ViewerOfficialRankingHistoryPage(): JSX.Element {
  const { productRunId } = useViewerProductRunRouteContext()
  const query = useQuery({
    queryKey: ['viewer-official-ranking-history', productRunId],
    queryFn: () => listViewerOfficialRankingHistory(productRunId)
  })

  const history = query.data
  return (
    <section className="panel">
      <RunScopedHeader
        title="MSA Rankings"
        runId={productRunId}
        subtitle="Historically faithful Official Ranking publications from the selected Viewer Branch."
      />
      <SectionCard title="Official Ranking publication timeline">
        {query.isLoading ? <p className="status">Loading Official Ranking history…</p> : null}
        {query.isError ? <p className="error">Failed to load Official Ranking history: {formatApiError(query.error)}</p> : null}
        {history && history.publication_count === 0 ? <EmptyState message="No published Official Rankings are available yet." /> : null}
        {history && history.publications.length > 0 ? (
          <table aria-label="Official Ranking publication history">
            <thead>
              <tr>
                <th>Season</th>
                <th>Week</th>
                <th>Players</th>
                <th>Best N</th>
                <th>Publication</th>
              </tr>
            </thead>
            <tbody>
              {history.publications.map((item) => (
                <tr key={item.week_ordinal}>
                  <td>{2000 + item.season_index}</td>
                  <td>{item.week}</td>
                  <td>{item.row_count}</td>
                  <td>{item.best_n}</td>
                  <td>
                    <Link to={viewerRankingSnapshotPath(productRunId, item.week_ordinal)}>
                      Open Week {item.week} ranking
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : null}
      </SectionCard>
    </section>
  )
}
