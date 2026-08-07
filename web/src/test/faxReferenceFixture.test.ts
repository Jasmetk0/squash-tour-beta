import { describe, expect, it } from 'vitest'

import {
  FAX_REFERENCE_RUN_ID,
  faxReferenceRunContainer,
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
})
