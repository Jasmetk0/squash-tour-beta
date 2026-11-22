import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'

import { getViewerCountries } from '../../../api/client'
import type { ViewerCountries } from '../../../api/types'
import { ViewerEmptyState, ViewerSampleList } from '../../../components/viewer/ViewerLandingComponents'
import { ViewerShellPage } from '../../../components/viewer/ViewerShellPage'
import { useActiveViewerProductRunId } from '../../../viewer/useActiveViewerProductRunId'
import { useViewerOfficialRunContext } from '../../../viewer/useViewerOfficialRunContext'
import { viewerCountriesPath } from '../../../viewer/viewerRoutes'
import { renderCountrySampleMetadata } from './viewerPeopleRender'
import { playerViewerBranch } from './viewerPlayerDirectory'

// This page consumes the existing public viewer_countries.v1 Saved projection,
// never private Admin data or a current Working Draft. All displayed rows must
// belong to the verified saved Viewer Branch of the selected Product Run.
function validCountrySnapshot(value: unknown, runId: string, branchId: string): value is ViewerCountries {
  if (!value || typeof value !== 'object') return false
  const data = value as Partial<ViewerCountries>
  const natural = (n: unknown, max = Number.MAX_SAFE_INTEGER): n is number =>
    typeof n === 'number' && Number.isSafeInteger(n) && n >= 0 && n <= max
  const publicOvr = (n: unknown): boolean =>
    n === null || (typeof n === 'number' && Number.isFinite(n) && n >= 0 && n <= 200)
  if (
    data.schema_version !== 'viewer_countries.v1' ||
    data.product_run_id !== runId || data.viewer_branch_id !== branchId ||
    !natural(data.season_index) || !natural(data.week, 61) || data.week < 1 ||
    !natural(data.country_count) || !Array.isArray(data.countries) ||
    data.countries.length !== data.country_count
  ) return false

  const codes = new Set<string>()
  for (const item of data.countries) {
    if (!item || typeof item !== 'object') return false
    const code = item.country_code
    if (
      typeof code !== 'string' || !/^[A-Z]{3}$/.test(code) || codes.has(code) ||
      !natural(item.player_count) || !natural(item.active_player_count) ||
      !natural(item.retired_player_count) ||
      item.active_player_count + item.retired_player_count !== item.player_count ||
      !publicOvr(item.average_current_ovr) || !publicOvr(item.top_player_current_ovr) ||
      (item.top_player_id !== null && (typeof item.top_player_id !== 'string' || !item.top_player_id.trim())) ||
      (item.top_player_name !== null && (typeof item.top_player_name !== 'string' || !item.top_player_name.trim())) ||
      (item.top_player_id === null) !== (item.top_player_name === null) ||
      (item.player_count === 0 && item.top_player_id !== null) ||
      // The published v1 country summary has no private simulation fields.
      Object.keys(item).some(key => ![
        'country_code', 'player_count', 'active_player_count', 'retired_player_count',
        'average_current_ovr', 'top_player_id', 'top_player_name', 'top_player_current_ovr'
      ].includes(key))
    ) return false
    codes.add(code)
  }
  return true
}

export function ViewerCountriesPage(): JSX.Element {
  const productRunId = useActiveViewerProductRunId()?.trim() ?? ''
  const context = useViewerOfficialRunContext(productRunId)
  const branchId = playerViewerBranch(context.data, productRunId)
  const validContext = Boolean(branchId && !context.isPending && !context.isFetching && !context.isError)
  const countriesQuery = useQuery({
    queryKey: ['viewer-countries-hub-canonical', productRunId, branchId],
    queryFn: () => getViewerCountries(productRunId),
    enabled: validContext,
    retry: false,
    refetchOnWindowFocus: false
  })

  if (!productRunId) {
    return (
      <ViewerShellPage title="Countries" description="Read-only canonical country summaries in the selected Viewer Product Run.">
        <ViewerEmptyState>No Product Run is selected yet.</ViewerEmptyState>
      </ViewerShellPage>
    )
  }

  if (!validContext) {
    return (
      <ViewerShellPage title="Countries" description="Read-only canonical country summaries in the selected Viewer Product Run.">
        {context.isPending || context.isFetching
          ? <p className="status" role="status">Resolving the saved Viewer Branch…</p>
          : <div role="alert">
              <p>Viewer Branch could not be verified for the selected Product Run.</p>
              <button type="button" onClick={() => void context.refetch()}>Retry Viewer Branch read (GET)</button>
            </div>}
      </ViewerShellPage>
    )
  }

  if (countriesQuery.isPending || countriesQuery.isFetching) {
    return (
      <ViewerShellPage title="Countries" description="Read-only Saved-Revision country summaries for the selected Product Run.">
        <p className="status" role="status">Loading canonical country metadata…</p>
      </ViewerShellPage>
    )
  }
  const verified = !countriesQuery.isError && validCountrySnapshot(countriesQuery.data, productRunId, branchId)
    ? countriesQuery.data : null
  if (!verified) {
    return (
      <ViewerShellPage title="Countries" description="Read-only Saved-Revision country summaries for the selected Product Run.">
        <div role="alert">
          <p>{countriesQuery.isError
            ? 'Canonical country metadata is temporarily unavailable.'
            : 'Country summary does not match the saved source or contains invalid public data.'}</p>
          <button type="button" onClick={() => void countriesQuery.refetch()}>Retry country read (GET)</button>
        </div>
      </ViewerShellPage>
    )
  }
  const countries = verified.countries.slice(0, 5)

  return (
    <ViewerShellPage title="Countries" description="Read-only Saved-Revision country summaries for the selected Product Run.">
      <article className="viewer-active-run-card" aria-label="Countries canonical Product Run summary">
        <span className="eyebrow">Selected Product Run</span>
        <h3>Countries summary</h3>
        <dl className="metadata-list">
          <div><dt>Product Run</dt><dd>{productRunId}</dd></div>
          <div><dt>Viewer Branch</dt><dd>{verified.viewer_branch_id}</dd></div>
          <div><dt>Total country count</dt><dd>{verified.country_count}</dd></div>
        </dl>
        {countries.length === 0 ? <ViewerEmptyState>No canonical countries are available for this Product Run yet.</ViewerEmptyState> : null}
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
