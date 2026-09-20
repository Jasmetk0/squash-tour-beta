import { useQuery } from '@tanstack/react-query'

import { getViewerVisibleProspects } from '../../../api/client'
import {
  ViewerEmptyState,
  ViewerMetadataList,
  ViewerStatusMessage,
} from '../../../components/viewer/ViewerLandingComponents'
import { formatApiError } from '../../../utils/apiErrors'
import { useActiveViewerProductRunId } from '../../../viewer/useActiveViewerProductRunId'

function weekLabel(seasonIndex: number, week: number): string {
  const start = 2000 + seasonIndex
  return `${start}/${String((start + 1) % 100).padStart(2, '0')} · W${week}`
}

export function ViewerNextGenPlayersPage(): JSX.Element {
  const productRunId = useActiveViewerProductRunId()
  const query = useQuery({
    queryKey: ['viewer-visible-pre-tour-prospects', productRunId],
    queryFn: () => getViewerVisibleProspects(productRunId ?? ''),
    enabled: Boolean(productRunId),
    retry: false,
  })

  return (
    <section className="panel viewer-shell-page">
      <div className="page-intro">
        <span className="eyebrow">Read-only Viewer section</span>
        <h2>Prospects / Next Gen</h2>
        <p className="subtitle">
          Players are shown only after their canonical birth-week lifecycle
          visibility begins on the selected Viewer Branch. Future pregenerated
          cohorts are not public Viewer data.
        </p>
      </div>

      {!productRunId ? (
        <ViewerEmptyState>
          Select a Product Run before opening the historical prospect list.
        </ViewerEmptyState>
      ) : null}

      {productRunId && query.isLoading ? (
        <ViewerStatusMessage>Loading visible prospects…</ViewerStatusMessage>
      ) : null}

      {productRunId && query.isError ? (
        <ViewerEmptyState>
          Canonical prospect visibility is unavailable: {formatApiError(query.error)}
        </ViewerEmptyState>
      ) : null}

      {query.data ? (
        <>
          <article
            className="viewer-active-run-card viewer-active-run-card--summary"
            aria-label="Visible prospect read model context"
          >
            <span className="eyebrow">Canonical Viewer Branch</span>
            <h3>Historical visibility</h3>
            <ViewerMetadataList
              items={[
                { label: 'Product Run', value: query.data.run_id },
                { label: 'Viewer Branch', value: query.data.branch_id },
                {
                  label: 'Current canonical week',
                  value: weekLabel(
                    query.data.week.season_index,
                    query.data.week.week
                  ),
                },
                { label: 'Visible pre-Tour prospects', value: query.data.total },
              ]}
            />
          </article>

          {query.data.prospects.length === 0 ? (
            <ViewerEmptyState>
              No pre-Tour prospects are historically visible in this Viewer Branch
              at the current canonical week.
            </ViewerEmptyState>
          ) : (
            <div className="viewer-sample-list-block">
              <h3>Visible prospects</h3>
              <ul
                className="viewer-home-list viewer-sample-list"
                aria-label="Visible pre-Tour prospects"
              >
                {query.data.prospects.map((prospect) => (
                  <li key={prospect.player_id}>
                    <strong>{prospect.display_name}</strong>
                    {' · '}
                    {prospect.country_code}
                    {' · age '}
                    {prospect.age}
                    {' · pre-Tour · visible since '}
                    {weekLabel(
                      prospect.visible_since_week.season_index,
                      prospect.visible_since_week.week
                    )}
                  </li>
                ))}
              </ul>
              <ViewerStatusMessage>
                Birth-week visibility is not MSA Tour entry. These players remain
                outside the normal pro/Tour list until a later authoritative Tour-entry
                event exists.
              </ViewerStatusMessage>
            </div>
          )}
        </>
      ) : null}
    </section>
  )
}
