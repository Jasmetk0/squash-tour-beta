import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it } from 'vitest'

import { ViewerContextProvider } from '../../../viewer/ViewerContext'
import { ViewerPlannedEventReadOnlyPage } from './ViewerReadOnlyPages'

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
  'Overwrite',
]

describe('ViewerReadOnlyPages', () => {
  it('renders planned event placeholder without forbidden Viewer actions', () => {
    render(
      <MemoryRouter>
        <ViewerContextProvider>
          <ViewerPlannedEventReadOnlyPage />
        </ViewerContextProvider>
      </MemoryRouter>,
    )

    expect(screen.getByRole('heading', { level: 2, name: 'Planned Event' })).toBeInTheDocument()
    expect(screen.getByText('Read-only schedule event destination. Event context can be surfaced here without commissioner controls.')).toBeInTheDocument()

    for (const label of forbiddenViewerActionLabels) {
      expect(screen.queryByText(label, { exact: true })).not.toBeInTheDocument()
    }
  })
})
