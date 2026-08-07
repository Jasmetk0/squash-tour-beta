import type {
  RunContainer,
  RunContainerListResponse,
  RunsIndexResponse,
  ViewerOfficialRunContext,
} from '../api/types'

/**
 * Versioned FAX API contract projection used by component tests with a mocked API boundary.
 * Keep this deliberately small: it describes stable identities and API contracts, while
 * the authoritative world content remains in config/worlds/official_fax_world.
 */
export const FAX_REFERENCE_VERSION = 'fax-reference-v1' as const
export const FAX_REFERENCE_RUN_ID = 'fax-reference-v1' as const
export const FAX_REFERENCE_LEGACY_RUN_ID = 'fax-reference-v1-main' as const
export const FAX_REFERENCE_BRANCH_ID = 'fax-reference-v1-viewer' as const

export const faxReferenceRunContainer = Object.freeze({
  run_id: FAX_REFERENCE_RUN_ID,
  display_name: 'FAX Reference v1',
  storage_kind: 'built_in',
  read_only: true,
  world_id: 'official_fax_world',
  world_package_fingerprint: null,
  config_version: null,
  config_fingerprint: null,
  global_seed: 20270807,
  timeline_start_season: 2000,
  timeline_end_season: 2049,
  official_branch_id: FAX_REFERENCE_BRANCH_ID,
  status: 'active',
  metadata_json: Object.freeze({ fixture_version: FAX_REFERENCE_VERSION }),
  mapped_simulation_run_count: 1,
} satisfies RunContainer)

const faxReferenceViewerContext = Object.freeze({
  product_run_id: FAX_REFERENCE_RUN_ID,
  product_run_display_name: 'FAX Reference v1',
  product_run_status: 'active',
  product_run_storage_kind: 'built_in',
  product_run_read_only: true,
  official_branch_id: FAX_REFERENCE_BRANCH_ID,
  official_branch_display_name: 'Viewer Branch',
  official_branch_status: 'active',
  official_branch_read_only: true,
  official_branch_seed: 20270807,
  legacy_simulation_run_id: FAX_REFERENCE_LEGACY_RUN_ID,
  head_checkpoint_id: 'fax-reference-v1-initial',
  head_checkpoint_kind: 'initial',
  current_season: 2027,
  current_week: 1,
  current_event_id: null,
  current_event_sequence: null,
  resolution_version: 'viewer_official_branch_v1',
} satisfies ViewerOfficialRunContext)

/** Returns an isolated Viewer API response so mocks cannot leak mutations between tests. */
export function makeFaxReferenceViewerContext(): ViewerOfficialRunContext {
  return { ...faxReferenceViewerContext }
}

export function makeFaxReferenceRunsResponse(): RunsIndexResponse {
  return {
    runs: [{
      run_id: FAX_REFERENCE_LEGACY_RUN_ID,
      season: 2027,
      seed: 20270807,
      progress: { next_event_index: 0, total_events: 4, completed_event_count: 0 },
      source_type: 'fresh_seed',
      parent_run_id: null,
      child_run_count: 0,
      world_id: 'official_fax_world',
    }],
  } satisfies RunsIndexResponse
}

export function makeFaxReferenceRunContainersResponse(): RunContainerListResponse {
  return {
    run_containers: [{ ...faxReferenceRunContainer, metadata_json: { ...faxReferenceRunContainer.metadata_json } }],
  } satisfies RunContainerListResponse
}

/** Returns an in-memory editable contract projection, never a persisted Run. */
export function makeDisposableFaxRunContainer(suffix: string): RunContainer {
  const runId = `${FAX_REFERENCE_RUN_ID}-${suffix}`
  return {
    ...faxReferenceRunContainer,
    run_id: runId,
    display_name: `FAX test ${suffix}`,
    storage_kind: 'custom_local' as const,
    read_only: false,
    official_branch_id: `${runId}-branch`,
    metadata_json: { derived_from: FAX_REFERENCE_VERSION },
  }
}
