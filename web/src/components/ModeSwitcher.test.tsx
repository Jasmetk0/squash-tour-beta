import { act, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it } from 'vitest'
import { MemoryRouter } from 'react-router-dom'

import { ModeSwitcher } from './ModeSwitcher'
import { writeViewerActiveProductRunId } from '../viewer/activeProductRun'
import { writeViewerActiveRunId } from '../viewer/activeRun'

function renderModeSwitcher(route: string): void {
  render(
    <MemoryRouter initialEntries={[route]}>
      <ModeSwitcher pathname={route} />
    </MemoryRouter>
  )
}

describe('ModeSwitcher', () => {
  beforeEach(() => localStorage.clear())
  it('keeps Viewer mode switch target and active link stable on Viewer home', () => {
    renderModeSwitcher('/viewer')

    expect(screen.getByLabelText('Mode switcher')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Viewer / MSA' })).toHaveAttribute('href', '/viewer')
    expect(screen.getByRole('link', { name: 'Viewer / MSA' })).toHaveClass('active')
    expect(screen.getByRole('link', { name: 'Admin / Engine' })).toHaveAttribute('href', '/admin')
  })

  it('keeps Admin mode switch target and active link stable on Admin home', () => {
    renderModeSwitcher('/admin')

    expect(screen.getByRole('link', { name: 'Viewer / MSA' })).toHaveAttribute('href', '/viewer')
    expect(screen.getByRole('link', { name: 'Admin / Engine' })).toHaveAttribute('href', '/admin')
    expect(screen.getByRole('link', { name: 'Admin / Engine' })).toHaveClass('active')
  })

  it('never inserts an unmatched legacy Admin route ID into a Viewer URL', () => {
    writeViewerActiveProductRunId('product-a')
    writeViewerActiveRunId('legacy-a')
    renderModeSwitcher('/admin/runs/run-a/finals')

    expect(screen.getByRole('link', { name: 'Viewer / MSA' })).toHaveAttribute('href', '/viewer/runs')
    expect(screen.getByRole('link', { name: 'Admin / Engine' })).toHaveAttribute('href', '/admin/runs/run-a/finals')
    expect(screen.getByRole('link', { name: 'Admin / Engine' })).toHaveClass('active')
  })

  it('maps Viewer Product Runs to Admin Branch management', () => {
    renderModeSwitcher('/viewer/runs/run-a/calendar')

    expect(screen.getByRole('link', { name: 'Viewer / MSA' })).toHaveAttribute('href', '/viewer/runs/run-a/calendar')
    expect(screen.getByRole('link', { name: 'Admin / Engine' })).toHaveAttribute('href', '/admin/runs/run-a/branches')
  })

  it('uses separately stored Product and legacy identities for a matching Admin route', () => {
    writeViewerActiveProductRunId('product-a')
    writeViewerActiveRunId('legacy-a')
    renderModeSwitcher('/admin/runs/legacy-a/players')

    expect(screen.getByRole('link', { name: 'Viewer / MSA' })).toHaveAttribute('href', '/viewer/runs/product-a/rankings')
    expect(screen.getByRole('link', { name: 'Viewer / MSA' })).not.toHaveAttribute('href', '/viewer/runs/legacy-a/rankings')
  })

  it('updates an exact legacy compatibility target after active Viewer identity storage events', async () => {
    writeViewerActiveProductRunId('product-a')
    writeViewerActiveRunId('legacy-a')
    renderModeSwitcher('/admin/runs/legacy-a/calendar')
    expect(screen.getByRole('link', { name: 'Viewer / MSA' })).toHaveAttribute('href', '/viewer/runs/product-a/rankings')

    act(() => writeViewerActiveProductRunId('product-b'))
    await waitFor(() => expect(screen.getByRole('link', { name: 'Viewer / MSA' })).toHaveAttribute('href', '/viewer/runs/product-b/rankings'))
  })
})
