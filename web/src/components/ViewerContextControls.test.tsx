import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it } from 'vitest'

import { VIEWER_CONTEXT_STORAGE_KEY, ViewerContextProvider } from '../viewer/ViewerContext'
import { ViewerJumpToWeekButton, ViewerSeasonWeekSelector } from './ViewerContextControls'

function renderViewerContextControls(): void {
  render(
    <ViewerContextProvider>
      <ViewerSeasonWeekSelector />
      <ViewerJumpToWeekButton week={24} />
    </ViewerContextProvider>
  )
}

describe('ViewerContextControls', () => {
  beforeEach(() => {
    localStorage.clear()
  })

  it('renders the collapsed Season/Week selector with a compact visible label and full accessible label', () => {
    renderViewerContextControls()

    const selector = screen.getByRole('button', { name: 'Season 2004/05 · W10' })

    expect(selector).toHaveTextContent('Week W10')
    expect(selector).toHaveAttribute('aria-expanded', 'false')
  })

  it('expands the selector with existing fields, update button, and metadata', async () => {
    const user = userEvent.setup()
    renderViewerContextControls()

    const selector = screen.getByRole('button', { name: 'Season 2004/05 · W10' })
    await user.click(selector)

    expect(selector).toHaveAttribute('aria-expanded', 'true')
    expect(screen.getByLabelText('Selected season')).toHaveValue('2004/05')
    expect(screen.getByLabelText('Selected week')).toHaveValue(10)
    expect(screen.getByRole('button', { name: 'Set Viewer Week' })).toBeInTheDocument()
    expect(screen.getByText('Season Week: 10 / 61')).toBeInTheDocument()
    expect(screen.getByText('Calendar Year: 2004')).toBeInTheDocument()
    expect(screen.getByText('Year Week: 46')).toBeInTheDocument()
    expect(screen.getByText('Status: selected viewer context; stored locally in this browser.')).toBeInTheDocument()
  })

  it('updates season/week context and preserves the compact collapsed display format', async () => {
    const user = userEvent.setup()
    renderViewerContextControls()

    await user.click(screen.getByRole('button', { name: 'Season 2004/05 · W10' }))
    await user.clear(screen.getByLabelText('Selected season'))
    await user.type(screen.getByLabelText('Selected season'), '2005/06')
    await user.clear(screen.getByLabelText('Selected week'))
    await user.type(screen.getByLabelText('Selected week'), '24')
    await user.click(screen.getByRole('button', { name: 'Set Viewer Week' }))

    expect(screen.getByRole('button', { name: 'Season 2005/06 · W24' })).toHaveTextContent('Week W24')
    expect(screen.getByText('Season Week: 24 / 61')).toBeInTheDocument()
    expect(localStorage.getItem(VIEWER_CONTEXT_STORAGE_KEY)).toBe(JSON.stringify({ selectedSeason: '2005/06', selectedWeek: 24 }))
  })

  it('keeps Jump to Week updating the shared Viewer context', async () => {
    const user = userEvent.setup()
    renderViewerContextControls()

    await user.click(screen.getByRole('button', { name: 'Jump to W24' }))

    expect(screen.getByRole('button', { name: 'Season 2004/05 · W24' })).toHaveTextContent('Week W24')
    expect(localStorage.getItem(VIEWER_CONTEXT_STORAGE_KEY)).toBe(JSON.stringify({ selectedSeason: '2004/05', selectedWeek: 24 }))
  })
})
