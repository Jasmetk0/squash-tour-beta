import { describe, expect, it } from 'vitest'

import {
  FAX_REFERENCE_RUN_ID,
  faxReferenceRunContainer,
  makeFaxReferenceRunContainersResponse,
  makeFaxReferenceRunsResponse,
  makeFaxReferenceViewerContext,
  makeDisposableFaxRunContainer,
} from './faxReferenceFixture'

describe('canonical FAX reference fixture', () => {
  it('is a read-only built-in projection', () => {
    expect(Object.isFrozen(faxReferenceRunContainer)).toBe(true)
    expect(faxReferenceRunContainer).toMatchObject({
      run_id: FAX_REFERENCE_RUN_ID,
      world_id: 'official_fax_world',
      storage_kind: 'built_in',
      read_only: true,
    })
  })

  it('creates isolated editable identities without changing the reference', () => {
    const clone = makeDisposableFaxRunContainer('mutation-1')
    clone.display_name = 'Changed only in this test'
    expect(clone).toMatchObject({ storage_kind: 'custom_local', read_only: false })
    expect(faxReferenceRunContainer.display_name).toBe('FAX Reference v1')
  })

  it('returns isolated response graphs for every API mock', () => {
    const runsA = makeFaxReferenceRunsResponse()
    const runsB = makeFaxReferenceRunsResponse()
    runsA.runs[0].progress.total_events = 99

    const containersA = makeFaxReferenceRunContainersResponse()
    const containersB = makeFaxReferenceRunContainersResponse()
    containersA.run_containers[0].metadata_json.changed = true

    const viewerA = makeFaxReferenceViewerContext()
    const viewerB = makeFaxReferenceViewerContext()
    viewerA.product_run_display_name = 'Changed in one mock'

    expect(runsB.runs[0].progress.total_events).toBe(4)
    expect(containersB.run_containers[0].metadata_json).toEqual({ fixture_version: 'fax-reference-v1' })
    expect(faxReferenceRunContainer.metadata_json).toEqual({ fixture_version: 'fax-reference-v1' })
    expect(viewerB.product_run_display_name).toBe('FAX Reference v1')
  })
})
