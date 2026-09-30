import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'

import { getViewerCountries } from '../../../api/client'
import { ViewerEmptyState, ViewerSampleList } from '../../../components/viewer/ViewerLandingComponents'
import { ViewerShellPage } from '../../../components/viewer/ViewerShellPage'
import { useActiveViewerProductRunId } from '../../../viewer/useActiveViewerProductRunId'
import { viewerCountriesPath } from '../../../viewer/viewerRoutes'
import { renderCountrySampleMetadata } from './viewerPeopleRender'

export function ViewerCountriesPage(): JSX.Element {
  const productRunId = useActiveViewerProductRunId()
  const countriesQuery = useQuery({
    queryKey: ['viewer-countries-hub-canonical', productRunId],
    queryFn: () => getViewerCountries(productRunId ?? ''),
    enabled: Boolean(productRunId),
    retry: false
  })

  if (!productRunId) {
    return (
      <ViewerShellPage title="Countries" description="Read-only canonical country summaries in the selected Viewer Product Run.">
        <ViewerEmptyState>No Product Run is selected yet.</ViewerEmptyState>
      </ViewerShellPage>
    )
  }

  const countries = countriesQuery.data?.countries.slice(0, 5) ?? []

  return (
    <ViewerShellPage title="Countries" description="Read-only Saved-Revision country summaries for the selected Product Run.">
      <article className="viewer-active-run-card" aria-label="Countries canonical Product Run summary">
        <span className="eyebrow">Selected Product Run</span>
        <h3>Countries summary</h3>
        {countriesQuery.isLoading ? <p className="status">Loading canonical country metadata…</p> : null}
        {countriesQuery.isError ? <ViewerEmptyState>Canonical country metadata is temporarily unavailable.</ViewerEmptyState> : null}
        <dl className="metadata-list">
          <div><dt>Product Run</dt><dd>{productRunId}</dd></div>
          <div><dt>Viewer Branch</dt><dd>{countriesQuery.data?.viewer_branch_id ?? '—'}</dd></div>
          <div><dt>Total country count</dt><dd>{countriesQuery.isLoading ? 'Loading…' : countriesQuery.data?.country_count ?? '—'}</dd></div>
        </dl>
        {!countriesQuery.isLoading && !countriesQuery.isError && countries.length === 0 ? <ViewerEmptyState>No canonical countries are available for this Product Run yet.</ViewerEmptyState> : null}
        <ViewerSampleList
          title="Sample countries"
          label="Sample canonical countries"
          items={countries}
          getKey={(country) => country.country_code}
          renderItem={(country) => renderCountrySampleMetadata(country, productRunId)}
        />
        <p className="viewer-active-run-actions">
          <Link className="viewer-active-run-link" to={viewerCountriesPath(productRunId)}>Open Product Run countries</Link>
        </p>
      </article>
    </ViewerShellPage>
  )
}
