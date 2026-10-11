import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it } from 'vitest'

import { LandingPage } from './LandingPage'

describe('LandingPage', () => {
  it('renders unchanged mode choice copy and links', () => {
    render(
      <MemoryRouter>
        <LandingPage />
      </MemoryRouter>,
    )

    expect(screen.getByRole('heading', { level: 2, name: 'Squash Tour Beta Engine' })).toBeInTheDocument()
    expect(screen.getByText('Choose how you want to use the deterministic FAX squash world.')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /Viewer \/ MSA Website Mode/ })).toHaveAttribute('href', '/viewer')
    expect(screen.getByText('Browse the generated squash world')).toBeInTheDocument()
    expect(screen.getByText('Rankings, tournaments, players, countries, history, and records in a public sports-site view.')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /Admin \/ Engine Mode/ })).toHaveAttribute('href', '/admin')
    expect(screen.getByText('Build, validate, and simulate the world')).toBeInTheDocument()
    expect(screen.getByText('World setup, generation, run control, simulation commands, diagnostics, and engine tools.')).toBeInTheDocument()
  })
})
