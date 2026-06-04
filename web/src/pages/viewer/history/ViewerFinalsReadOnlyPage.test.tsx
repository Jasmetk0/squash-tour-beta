import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it } from 'vitest'

import { ViewerContextProvider } from '../../../viewer/ViewerContext'
import { ViewerFinalsReadOnlyPage } from './ViewerFinalsReadOnlyPage'

const forbiddenViewerActionLabels = [
  'Simulate',
  'Generate',
  'Persist',
  'Apply',
  'Execute',
  'Delete',
  'Edit',
  'Import',
  'Rollover',
  'Rebuild',
  'Override',
  'Save changes',
  'Commit',
  'Regenerate',
  'Repair',
  'Merge',
  'Overwrite'
]

describe('ViewerFinalsReadOnlyPage', () => {
  it('renders the existing read-only World Tour Finals shell', () => {
    render(
      <MemoryRouter>
        <ViewerContextProvider>
          <ViewerFinalsReadOnlyPage />
        </ViewerContextProvider>
      </MemoryRouter>
    )

    expect(screen.getByRole('heading', { name: 'World Tour Finals' })).toBeInTheDocument()
    expect(screen.getByText('Read-only World Tour Finals destination for qualification and results.')).toBeInTheDocument()

    for (const label of forbiddenViewerActionLabels) {
      expect(screen.queryByText(label, { exact: true })).not.toBeInTheDocument()
    }
  })
})
