import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { MemoryRouter } from 'react-router-dom'

import { ModeSwitcher } from './ModeSwitcher'

function renderModeSwitcher(route: string): void {
  render(
    <MemoryRouter initialEntries={[route]}>
      <ModeSwitcher pathname={route} />
    </MemoryRouter>
  )
}

describe('ModeSwitcher', () => {
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

  it('preserves unknown Admin paths as the Admin target with Viewer home fallback', () => {
    renderModeSwitcher('/admin/runs/run-a/finals')

    expect(screen.getByRole('link', { name: 'Viewer / MSA' })).toHaveAttribute('href', '/viewer')
    expect(screen.getByRole('link', { name: 'Admin / Engine' })).toHaveAttribute('href', '/admin/runs/run-a/finals')
    expect(screen.getByRole('link', { name: 'Admin / Engine' })).toHaveClass('active')
  })

  it('keeps run-scoped calendar targets mapped between Viewer and Admin', () => {
    renderModeSwitcher('/viewer/runs/run-a/calendar')

    expect(screen.getByRole('link', { name: 'Viewer / MSA' })).toHaveAttribute('href', '/viewer/runs/run-a/calendar')
    expect(screen.getByRole('link', { name: 'Admin / Engine' })).toHaveAttribute('href', '/admin/runs/run-a/calendar')
  })

  it('keeps run-scoped players targets mapped between Viewer and Admin', () => {
    renderModeSwitcher('/admin/runs/run-a/players')

    expect(screen.getByRole('link', { name: 'Viewer / MSA' })).toHaveAttribute('href', '/viewer/runs/run-a/players')
    expect(screen.getByRole('link', { name: 'Admin / Engine' })).toHaveAttribute('href', '/admin/runs/run-a/players')
  })
})
