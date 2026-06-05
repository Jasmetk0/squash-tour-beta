import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { AdminSettingsPage } from './AdminSettingsPage'

describe('AdminSettingsPage', () => {
  it('renders existing placeholder copy', () => {
    render(<AdminSettingsPage />)

    expect(screen.getByRole('heading', { level: 2, name: 'Settings' })).toBeInTheDocument()
    expect(screen.getByText('Engine settings placeholder for future config-version and environment controls.')).toBeInTheDocument()
    expect(screen.getByText('No settings editor is implemented in Phase 1.')).toBeInTheDocument()
  })
})
