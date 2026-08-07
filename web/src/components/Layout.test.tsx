import { fireEvent, screen, waitFor, within } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { Layout } from './Layout'
import { forbiddenViewerActionLabels, expectNoForbiddenViewerActions } from '../test/viewerTestUtils'
import { renderWithRoute } from '../test/testUtils'
import {
  faxReferenceRunContainersResponse,
  faxReferenceRunsResponse,
  faxReferenceViewerContext,
  FAX_REFERENCE_RUN_ID,
} from '../test/faxReferenceFixture'

const api = vi.hoisted(() => ({
  listRuns: vi.fn(),
  listRunContainers: vi.fn(),
  getViewerOfficialRunContext: vi.fn(),
  ApiError: class ApiError extends Error { status = 500 }
}))

vi.mock('../api/client', () => api)

function viewerNav(): HTMLElement {
  return screen.getByTestId('viewer-primary-nav')
}

describe('Layout mode navigation', () => {
  beforeEach(() => {
    localStorage.clear()
    vi.clearAllMocks()
    api.listRuns.mockResolvedValue(faxReferenceRunsResponse)
    api.listRunContainers.mockResolvedValue(faxReferenceRunContainersResponse)
    api.getViewerOfficialRunContext.mockResolvedValue(faxReferenceViewerContext)
  })

  it('keeps Admin / Engine mode navigation and run-scoped admin links stable', async () => {
    renderWithRoute(<Layout />, `/admin/runs/${FAX_REFERENCE_RUN_ID}/finals`)

    expect(await screen.findByText('Admin / Engine Mode')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Viewer / MSA' })).toHaveAttribute('href', '/viewer/runs')
    expect(screen.getByRole('link', { name: 'Admin / Engine' })).toHaveAttribute('href', `/admin/runs/${FAX_REFERENCE_RUN_ID}/finals`)
    expect(screen.getByRole('link', { name: 'World' })).toHaveAttribute('href', '/admin/world')
    expect(screen.getByRole('link', { name: 'Tour & Seasons' })).toHaveAttribute('href', '/admin/tour-seasons')
    expect(screen.getByRole('link', { name: 'Simulate' })).toHaveAttribute('href', '/admin/simulate')
    expect(screen.getByRole('link', { name: 'Runs' })).toHaveAttribute('href', '/admin/runs')
    expect(screen.getByRole('link', { name: 'Home' })).toHaveAttribute('href', `/admin/runs/${FAX_REFERENCE_RUN_ID}`)
    expect(screen.getByRole('link', { name: 'Events' })).toHaveAttribute('href', `/admin/runs/${FAX_REFERENCE_RUN_ID}/events`)
    expect(screen.getByRole('link', { name: 'Season Calendar' })).toHaveAttribute('href', `/admin/runs/${FAX_REFERENCE_RUN_ID}/calendar`)
    expect(screen.getAllByRole('link', { name: 'Diagnostics' })[1]).toHaveAttribute('href', `/admin/runs/${FAX_REFERENCE_RUN_ID}/diagnostics`)
    expect(screen.getByRole('link', { name: 'World Generation' })).toHaveAttribute('href', `/admin/runs/${FAX_REFERENCE_RUN_ID}/world-generation`)
    expect(screen.getByRole('link', { name: 'Ranking Snapshots' })).toHaveAttribute('href', `/admin/runs/${FAX_REFERENCE_RUN_ID}/snapshots/ranking`)
    expect(screen.getByRole('link', { name: 'Race Snapshots' })).toHaveAttribute('href', `/admin/runs/${FAX_REFERENCE_RUN_ID}/snapshots/race`)
    expect(screen.getByText(`Current run context: ${FAX_REFERENCE_RUN_ID}`)).toBeInTheDocument()
  })

  it('shows one Viewer primary nav in Viewer mode', async () => {
    renderWithRoute(<Layout />, `/viewer/runs/${FAX_REFERENCE_RUN_ID}/rankings`)

    expect(await screen.findByText('Viewer / MSA Website Mode')).toBeInTheDocument()
    expect(screen.getAllByTestId('viewer-primary-nav')).toHaveLength(1)
  })

  it('renders Viewer topbar links as Viewer-only links without Admin shell controls in the Viewer nav', async () => {
    renderWithRoute(<Layout />, '/viewer/rankings')

    expect(await screen.findByText('Viewer / MSA Website Mode')).toBeInTheDocument()
    const nav = viewerNav()
    const links = within(nav).getAllByRole('link')
    expect(links.length).toBeGreaterThan(0)
    for (const link of links) {
      const href = link.getAttribute('href') ?? ''
      expect(href).toMatch(/^\/viewer(?:\/|$)/)
      expect(href).not.toMatch(/^\/admin(?:\/|$)/)
    }
    expect(within(nav).queryByText(/Admin|Commissioner|Engine Mode|Engine/i)).not.toBeInTheDocument()
  })

  it('registers Viewer dropdown links as Viewer-only destinations without fake result labels', async () => {
    renderWithRoute(<Layout />, '/viewer/tour')

    expect(await screen.findByText('Viewer / MSA Website Mode')).toBeInTheDocument()
    const nav = viewerNav()
    const dropdownMenus = within(nav).getAllByLabelText(/ menu$/)
    expect(dropdownMenus.length).toBeGreaterThan(0)
    for (const menu of dropdownMenus) {
      for (const link of within(menu).getAllByRole('link')) {
        const href = link.getAttribute('href') ?? ''
        expect(href).toMatch(/^\/viewer(?:\/|$)/)
        expect(href).not.toMatch(/^\/admin(?:\/|$)/)
      }
    }
    expect(within(nav).queryByText(/Winner|Top 100|standings table/i)).not.toBeInTheDocument()
    expect(document.body).not.toHaveTextContent('[object Object]')
  })

  it('keeps Viewer nav free of backend mutation controls while allowing local selectors', async () => {
    renderWithRoute(<Layout />, '/viewer')

    expect(await screen.findByText('Viewer / MSA Website Mode')).toBeInTheDocument()
    const nav = viewerNav()
    expect(within(nav).getByRole('search', { name: 'Viewer search' })).toBeInTheDocument()
    expect(within(nav).queryByLabelText('Viewer active run')).not.toBeInTheDocument()
    expect(within(nav).getByRole('button', { name: 'Season 2004/05 · W10' })).toHaveTextContent('Week W10')
    expect(await screen.findByRole('option', { name: /FAX Reference v1/i })).toHaveAttribute('value', FAX_REFERENCE_RUN_ID)
    fireEvent.change(screen.getByLabelText('Viewer active Product Run'), { target: { value: FAX_REFERENCE_RUN_ID } })
    await waitFor(() => expect(localStorage.getItem('beta_engine:viewer_active_product_run_id')).toBe(FAX_REFERENCE_RUN_ID))
    expect(screen.getByLabelText('Viewer header context controls')).toBeInTheDocument()
    expectNoForbiddenViewerActions(within(nav))
    for (const label of forbiddenViewerActionLabels) {
      expect(within(nav).queryByRole('button', { name: label })).not.toBeInTheDocument()
      expect(within(nav).queryByRole('link', { name: label })).not.toBeInTheDocument()
    }
  })
})
