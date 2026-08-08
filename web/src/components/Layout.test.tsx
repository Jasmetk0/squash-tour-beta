import { fireEvent, screen, waitFor, within } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { Layout } from './Layout'
import { forbiddenViewerActionLabels, expectNoForbiddenViewerActions } from '../test/viewerTestUtils'
import { renderWithRoute } from '../test/testUtils'
import {
  makeFaxReferenceViewerContext,
  FAX_REFERENCE_RUN_ID,
  makeDisposableFaxRunContainer,
  makeFaxReferenceRunContainersResponse,
  makeFaxReferenceRunsResponse,
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
    const disposable = makeDisposableFaxRunContainer('layout-switch')
    const referenceRuns = makeFaxReferenceRunsResponse()
    const referenceContainers = makeFaxReferenceRunContainersResponse()
    localStorage.clear()
    vi.clearAllMocks()
    api.listRuns.mockResolvedValue({
      runs: [...referenceRuns.runs, {
        run_id: disposable.run_id,
        season: 2027,
        seed: disposable.global_seed ?? 20270807,
        progress: { next_event_index: 0, total_events: 4, completed_event_count: 0 },
        source_type: 'fresh_seed',
        parent_run_id: null,
        child_run_count: 0,
        world_id: disposable.world_id,
      }],
    })
    api.listRunContainers.mockResolvedValue({
      run_containers: [...referenceContainers.run_containers, disposable],
    })
    api.getViewerOfficialRunContext.mockResolvedValue(makeFaxReferenceViewerContext())
  })

  it('renders only Global Admin navigation on a global route', async () => {
    renderWithRoute(<Layout />, '/admin/world')

    expect(await screen.findByText('Admin / Engine Mode')).toBeInTheDocument()
    const nav = screen.getByRole('navigation', { name: 'Global Admin navigation' })
    expect(within(nav).getByRole('link', { name: 'World' })).toHaveAttribute('href', '/admin/world')
    expect(within(nav).getByRole('link', { name: 'Runs' })).toHaveAttribute('href', '/admin/runs')
    expect(screen.queryByRole('navigation', { name: 'Run Admin navigation' })).not.toBeInTheDocument()
    expect(screen.queryByText(/Current run context:/)).not.toBeInTheDocument()
    expect(screen.queryByRole('combobox', { name: 'Admin active Run' })).not.toBeInTheDocument()
  })

  it('renders only Run Admin navigation at a Run root', async () => {
    renderWithRoute(<Layout />, `/admin/runs/${FAX_REFERENCE_RUN_ID}`)

    expect(await screen.findByText('Admin / Engine Mode')).toBeInTheDocument()
    const nav = screen.getByRole('navigation', { name: 'Run Admin navigation' })
    expect(within(nav).getByRole('link', { name: 'Back to Global' })).toHaveAttribute('href', '/admin')
    expect(within(nav).getByRole('link', { name: 'Home' })).toHaveAttribute('href', `/admin/runs/${FAX_REFERENCE_RUN_ID}`)
    expect(within(nav).getByRole('link', { name: 'Events' })).toHaveAttribute('href', `/admin/runs/${FAX_REFERENCE_RUN_ID}/events`)
    expect(within(nav).getByRole('link', { name: 'Season Calendar' })).toHaveAttribute('href', `/admin/runs/${FAX_REFERENCE_RUN_ID}/calendar`)
    expect(screen.queryByRole('navigation', { name: 'Global Admin navigation' })).not.toBeInTheDocument()
    expect(within(nav).queryByRole('link', { name: 'Tour & Seasons' })).not.toBeInTheDocument()
    expect(screen.getByText(`Current run context: ${FAX_REFERENCE_RUN_ID}`)).toBeInTheDocument()
    const runSelector = await screen.findByRole('combobox', { name: 'Admin active Run' })
    expect(runSelector).toHaveValue(FAX_REFERENCE_RUN_ID)
    expect(screen.getByText('FAX Reference v1', { selector: '.admin-active-run-compact__status strong' })).toBeInTheDocument()
  })

  it('keeps nested Run routes in Run Admin scope', async () => {
    renderWithRoute(<Layout />, `/admin/runs/${FAX_REFERENCE_RUN_ID}/finals`)

    expect(await screen.findByText('Admin / Engine Mode')).toBeInTheDocument()
    const nav = screen.getByRole('navigation', { name: 'Run Admin navigation' })
    expect(within(nav).getByRole('link', { name: 'World Tour Finals' })).toHaveAttribute('href', `/admin/runs/${FAX_REFERENCE_RUN_ID}/finals`)
    expect(screen.queryByRole('navigation', { name: 'Global Admin navigation' })).not.toBeInTheDocument()
  })

  it('switches a generic Run route without changing Viewer selection', async () => {
    localStorage.setItem('beta_engine:viewer_active_product_run_id', 'viewer-run')
    const nextRunId = `${FAX_REFERENCE_RUN_ID}-layout-switch`
    renderWithRoute(<Layout />, `/admin/runs/${FAX_REFERENCE_RUN_ID}/branches`)

    await screen.findByRole('option', { name: 'FAX test layout-switch' })
    fireEvent.change(screen.getByRole('combobox', { name: 'Admin active Run' }), { target: { value: nextRunId } })

    await waitFor(() => expect(screen.getByRole('combobox', { name: 'Admin active Run' })).toHaveValue(nextRunId))
    expect(screen.getByRole('link', { name: 'Admin / Engine' })).toHaveAttribute('href', `/admin/runs/${nextRunId}/branches`)
    expect(localStorage.getItem('beta_engine:viewer_active_product_run_id')).toBe('viewer-run')
  })

  it('falls back to destination Run Home when switching from an object-specific route', async () => {
    const nextRunId = `${FAX_REFERENCE_RUN_ID}-layout-switch`
    renderWithRoute(<Layout />, `/admin/runs/${FAX_REFERENCE_RUN_ID}/events/E123`)

    await screen.findByRole('option', { name: 'FAX test layout-switch' })
    fireEvent.change(screen.getByRole('combobox', { name: 'Admin active Run' }), { target: { value: nextRunId } })

    await waitFor(() => expect(screen.getByRole('combobox', { name: 'Admin active Run' })).toHaveValue(nextRunId))
    expect(screen.getByRole('link', { name: 'Admin / Engine' })).toHaveAttribute('href', `/admin/runs/${nextRunId}`)
    expect(screen.getByRole('link', { name: 'Admin / Engine' })).not.toHaveAttribute('href', `/admin/runs/${nextRunId}/events/E123`)
  })

  it('keeps the Run creation route in Global Admin scope', async () => {
    renderWithRoute(<Layout />, '/admin/runs/new')

    expect(await screen.findByText('Admin / Engine Mode')).toBeInTheDocument()
    expect(screen.getByRole('navigation', { name: 'Global Admin navigation' })).toBeInTheDocument()
    expect(screen.queryByRole('navigation', { name: 'Run Admin navigation' })).not.toBeInTheDocument()
    expect(screen.queryByText('Current run context: new')).not.toBeInTheDocument()
    expect(screen.queryByRole('combobox', { name: 'Admin active Run' })).not.toBeInTheDocument()
  })

  it('keeps the route Run usable as a fallback when metadata loading fails', async () => {
    api.listRunContainers.mockRejectedValueOnce(new Error('temporarily unavailable'))

    renderWithRoute(<Layout />, '/admin/runs/run-metadata-fallback')

    const selector = await screen.findByRole('combobox', { name: 'Admin active Run' })
    expect(selector).toHaveValue('run-metadata-fallback')
    expect(screen.getByText('run-metadata-fallback', { selector: '.admin-active-run-compact__status strong' })).toBeInTheDocument()
    expect(await screen.findByText(/Run metadata unavailable: temporarily unavailable/)).toBeInTheDocument()
  })

  it('shows one Viewer primary nav in Viewer mode', async () => {
    renderWithRoute(<Layout />, `/viewer/runs/${FAX_REFERENCE_RUN_ID}/rankings`)

    expect(await screen.findByText('Viewer / MSA Website Mode')).toBeInTheDocument()
    expect(screen.getAllByTestId('viewer-primary-nav')).toHaveLength(1)
    expect(screen.queryByRole('navigation', { name: 'Global Admin navigation' })).not.toBeInTheDocument()
    expect(screen.queryByRole('navigation', { name: 'Run Admin navigation' })).not.toBeInTheDocument()
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
    const disposableRunId = `${FAX_REFERENCE_RUN_ID}-layout-switch`
    expect(await screen.findByRole('option', { name: /FAX test layout-switch/i })).toHaveAttribute('value', disposableRunId)
    fireEvent.change(screen.getByLabelText('Viewer active Product Run'), { target: { value: disposableRunId } })
    await waitFor(() => expect(localStorage.getItem('beta_engine:viewer_active_product_run_id')).toBe(disposableRunId))
    expect(screen.getByLabelText('Viewer header context controls')).toBeInTheDocument()
    expectNoForbiddenViewerActions(within(nav))
    for (const label of forbiddenViewerActionLabels) {
      expect(within(nav).queryByRole('button', { name: label })).not.toBeInTheDocument()
      expect(within(nav).queryByRole('link', { name: label })).not.toBeInTheDocument()
    }
  })
})
