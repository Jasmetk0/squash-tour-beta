import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it } from 'vitest'

import { VIEWER_CONTEXT_STORAGE_KEY, ViewerContextProvider, useViewerContext } from './ViewerContext'

function ViewerContextProbe(): JSX.Element {
  const context = useViewerContext()

  return (
    <section>
      <output aria-label="Selected season">{context.selectedSeason}</output>
      <output aria-label="Selected week">{context.selectedWeek}</output>
      <output aria-label="Calendar year">{context.calendarYear}</output>
      <output aria-label="Year week">{context.yearWeek}</output>
      <button type="button" onClick={() => context.setViewerContext('2005/06', 24)}>Set context</button>
      <button type="button" onClick={() => context.setSelectedSeason('  ')}>Blank season</button>
      <button type="button" onClick={() => context.setSelectedWeek(999)}>Large week</button>
    </section>
  )
}

function renderViewerContextProbe(): void {
  render(
    <ViewerContextProvider>
      <ViewerContextProbe />
    </ViewerContextProvider>
  )
}

describe('ViewerContextProvider', () => {
  beforeEach(() => {
    localStorage.clear()
  })

  it('provides the existing default Viewer season/week context', () => {
    renderViewerContextProbe()

    expect(screen.getByLabelText('Selected season')).toHaveTextContent('2004/05')
    expect(screen.getByLabelText('Selected week')).toHaveTextContent('10')
    expect(screen.getByLabelText('Calendar year')).toHaveTextContent('2004')
    expect(screen.getByLabelText('Year week')).toHaveTextContent('46')
  })

  it('updates and persists selected Viewer season/week context', async () => {
    const user = userEvent.setup()
    renderViewerContextProbe()

    await user.click(screen.getByRole('button', { name: 'Set context' }))

    expect(screen.getByLabelText('Selected season')).toHaveTextContent('2005/06')
    expect(screen.getByLabelText('Selected week')).toHaveTextContent('24')
    expect(localStorage.getItem(VIEWER_CONTEXT_STORAGE_KEY)).toBe(JSON.stringify({ selectedSeason: '2005/06', selectedWeek: 24 }))
  })

  it('falls back safely for invalid stored Viewer context payloads', () => {
    localStorage.setItem(VIEWER_CONTEXT_STORAGE_KEY, '{bad json')

    renderViewerContextProbe()

    expect(screen.getByLabelText('Selected season')).toHaveTextContent('2004/05')
    expect(screen.getByLabelText('Selected week')).toHaveTextContent('10')
  })

  it('normalizes blank seasons and clamps weeks without changing storage keys', async () => {
    const user = userEvent.setup()
    renderViewerContextProbe()

    await user.click(screen.getByRole('button', { name: 'Blank season' }))
    await user.click(screen.getByRole('button', { name: 'Large week' }))

    expect(screen.getByLabelText('Selected season')).toHaveTextContent('2004/05')
    expect(screen.getByLabelText('Selected week')).toHaveTextContent('61')
    expect(localStorage.getItem(VIEWER_CONTEXT_STORAGE_KEY)).toBe(JSON.stringify({ selectedSeason: '2004/05', selectedWeek: 61 }))
  })
})
