import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'

import { listRunNations } from '../../../api/client'
import { ViewerEmptyState, ViewerSampleList } from '../../../components/viewer/ViewerLandingComponents'
import { ViewerShellPage } from '../../../components/viewer/ViewerShellPage'
import { useActiveViewerRunId } from '../../../viewer/useActiveViewerRunId'
import { viewerCountriesPath } from '../../../viewer/viewerRoutes'
import { renderCountrySampleMetadata } from './viewerPeopleRender'

export function ViewerCountriesPage(): JSX.Element {
  const activeRunId = useActiveViewerRunId()
  const nationsQuery = useQuery({
    queryKey: ['viewer-countries-hub-run-nations', activeRunId],
    queryFn: () => listRunNations(activeRunId ?? '', { limit: 5, offset: 0 }),
    enabled: Boolean(activeRunId),
    retry: false
  })

  if (!activeRunId) {
    return (
      <ViewerShellPage title="Countries" description="Read-only country profiles and national summaries in the selected Viewer context.">
        <ViewerEmptyState>No data is available for this run yet.</ViewerEmptyState>
      </ViewerShellPage>
    )
  }

  const nations = nationsQuery.data?.nations ?? []

  return (
    <ViewerShellPage title="Countries" description="Read-only country profiles using existing active-run country data.">
      <article className="viewer-active-run-card" aria-label="Countries active run summary">
        <span className="eyebrow">Active Viewer run</span>
        <h3>Countries summary</h3>
        {nationsQuery.isLoading ? <p className="status">Loading active run country metadata…</p> : null}
        {nationsQuery.isError ? <ViewerEmptyState>Country metadata is temporarily unavailable for this run.</ViewerEmptyState> : null}
        <dl className="metadata-list">
          <div><dt>Active run ID</dt><dd>{activeRunId}</dd></div>
          <div><dt>Total country count</dt><dd>{nationsQuery.isLoading ? 'Loading…' : nationsQuery.data?.total ?? '—'}</dd></div>
          <div><dt>Returned country count</dt><dd>{nationsQuery.isLoading ? 'Loading…' : nations.length}</dd></div>
        </dl>
        {!nationsQuery.isLoading && !nationsQuery.isError && nations.length === 0 ? <ViewerEmptyState>No data is available for this run yet.</ViewerEmptyState> : null}
        <ViewerSampleList
          title="Sample countries"
          label="Sample active run countries"
          items={nations}
          getKey={(nation) => nation.country_code}
          renderItem={(nation) => renderCountrySampleMetadata(nation, activeRunId)}
        />
        <p className="viewer-active-run-actions">
          <Link className="viewer-active-run-link" to={viewerCountriesPath(activeRunId)}>Open active run countries</Link>
        </p>
      </article>
    </ViewerShellPage>
  )
}
