import { screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { useLocation, useNavigate } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { LanguageProvider, useLanguage } from '../../i18n/LanguageContext'
import {
  clearViewerStorage, expectNoForbiddenViewerActions, renderWithViewerProviders,
} from '../../test/viewerTestUtils'
import { normalizeRunBrowserRuns } from '../../viewer/runBrowserDisplay'
import { ViewerRunBrowserPage } from './ViewerRunBrowserPage'
import { filterViewerRuns, parseViewerRunPage } from './viewerRunBrowserBrowse'

const api = vi.hoisted(() => ({
  listRunContainers: vi.fn(),
  ApiError: class ApiError extends Error { status = 500 },
}))
vi.mock('../../api/client', () => api)

function run(runId: string, name = runId) {
  return {
    run_id: runId, display_name: name, storage_kind: 'custom_local',
    read_only: false, world_id: 'fax', world_package_fingerprint: 'world',
    config_version: 'v1', config_fingerprint: 'config',
    global_seed: 1, timeline_start_season: 2000, timeline_end_season: 2049,
    viewer_branch_id: 'viewer', official_branch_id: 'viewer',
    status: 'ready', metadata_json: {}, mapped_simulation_run_count: 0,
  }
}

function Navigation(): JSX.Element {
  const location = useLocation()
  const navigate = useNavigate()
  const { language, setLanguage } = useLanguage()
  return <>
    <output aria-label="Current URL">{location.pathname}{location.search}</output>
    <button type="button" onClick={() => navigate(-1)}>Back</button>
    <button type="button" onClick={() => navigate(1)}>Forward</button>
    <button type="button" onClick={() => setLanguage(language === 'cs' ? 'en' : 'cs')}>Toggle language</button>
  </>
}
function mount(route = '/viewer/runs') {
  return renderWithViewerProviders(
    <LanguageProvider><Navigation /><ViewerRunBrowserPage /></LanguageProvider>,
    { route },
  )
}
function currentUrl() {
  return screen.getByLabelText('Current URL').textContent ?? ''
}
function shownRunIds() {
  return screen.getAllByRole('heading', { level: 4 }).map(item => item.textContent)
}

describe('Viewer Run Browser URL browsing (local filtering over mocked GET only)', () => {
  beforeEach(() => {
    clearViewerStorage()
    localStorage.setItem('squash-engine-language-v1', 'en')
    vi.clearAllMocks()
    api.listRunContainers.mockResolvedValue({
      run_containers: [run('a/id #1', 'Brno Championship'), run('b id', 'Prague Tour')],
    })
  })

  it('matches case-insensitive ID/name tokens without expanding untrusted metadata', () => {
    const list = normalizeRunBrowserRuns([
      run('a/id #1', 'Brno Championship'),
      run('b-id', 'Prague Championship'),
      run('c', 'Brno league'),
    ])
    expect(filterViewerRuns(list, 'BRNO')).toHaveLength(2)
    expect(filterViewerRuns(list, 'championship brno').map(item => item.run_id))
      .toEqual(['a/id #1'])
    expect(filterViewerRuns(list, '  a/id   #1 ' ).map(item => item.run_id))
      .toEqual(['a/id #1'])
    expect(filterViewerRuns(list, '   ')).toHaveLength(3)
    expect(filterViewerRuns(list, 'not-present')).toEqual([])
    expect(filterViewerRuns(normalizeRunBrowserRuns([run('clean', { private: true } as unknown as string)]), 'private'))
      .toEqual([])
  })

  it('accepts canonical page numbers only and rejects out-of-range deep links', () => {
    expect(parseViewerRunPage(null, 3)).toBe(1)
    expect(parseViewerRunPage('1', 3)).toBe(1)
    expect(parseViewerRunPage('3', 3)).toBe(3)
    for (const bad of ['0', '-1', '01', '1.0', 'NaN', '4', '999999999999999999999', '']) {
      expect(parseViewerRunPage(bad, 3)).toBeNull()
    }
  })

  it('loads exact bookmarked search/page with URL-encoded links and preserved unrelated params', async () => {
    api.listRunContainers.mockResolvedValue({
      run_containers: Array.from({ length: 60 }, (_, i) => run('run/' + String(i).padStart(2, '0') + ' #',
        'Brno tour ' + i)),
    })
    mount('/viewer/runs?keep=one&keep=two&runQuery=Brno&runPage=2')
    expect(await screen.findByRole('heading', { level: 4, name: 'run/25 #' })).toBeInTheDocument()
    expect(shownRunIds()).toHaveLength(25)
    expect(screen.queryByRole('heading', { name: 'run/00 #' })).not.toBeInTheDocument()
    const card = screen.getByLabelText('Run run/25 #')
    expect(within(card).getByRole('link', { name: 'Season calendar' }))
      .toHaveAttribute('href', '/viewer/runs/run%2F25%20%23/calendar')
    expect(currentUrl()).toContain('keep=one&keep=two')
    expect(screen.getByRole('searchbox', { name: 'Search by Run name or ID' }))
      .toHaveValue('Brno')
    expectNoForbiddenViewerActions()
  })

  it('submits case-insensitive name search by Enter, clears it and never refetches for local filtering', async () => {
    const user = userEvent.setup()
    mount('/viewer/runs?keep=one&keep=two')
    expect(await screen.findByRole('heading', { name: 'a/id #1' })).toBeInTheDocument()
    const calls = api.listRunContainers.mock.calls.length
    const input = screen.getByRole('searchbox', { name: 'Search by Run name or ID' })
    await user.type(input, 'brno{enter}')
    expect(await screen.findByRole('heading', { name: 'a/id #1' })).toBeInTheDocument()
    await waitFor(() => expect(currentUrl()).toContain('runQuery=brno'))
    expect(screen.queryByRole('heading', { name: 'b id' })).not.toBeInTheDocument()
    expect(api.listRunContainers).toHaveBeenCalledTimes(calls)
    await user.click(screen.getByRole('button', { name: 'Clear filter' }))
    expect(await screen.findByRole('heading', { name: 'b id' })).toBeInTheDocument()
    expect(screen.getByRole('searchbox', { name: 'Search by Run name or ID' })).toHaveValue('')
    expect(currentUrl()).not.toContain('runQuery=')
    expect(currentUrl()).toContain('keep=one&keep=two')
    expect(api.listRunContainers).toHaveBeenCalledTimes(calls)
  })

  it('supports Back/Forward over submitted filters and resynchronizes the search input', async () => {
    const user = userEvent.setup()
    mount()
    expect(await screen.findByRole('heading', { name: 'a/id #1' })).toBeInTheDocument()
    const input = screen.getByRole('searchbox', { name: 'Search by Run name or ID' })
    await user.type(input, 'Brno{enter}')
    await waitFor(() => expect(currentUrl()).toContain('runQuery=Brno'))
    await user.clear(input)
    await user.type(input, 'Prague{enter}')
    expect(await screen.findByRole('heading', { name: 'b id' })).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Back' }))
    expect(await screen.findByRole('heading', { name: 'a/id #1' })).toBeInTheDocument()
    expect(input).toHaveValue('Brno')
    await user.click(screen.getByRole('button', { name: 'Forward' }))
    expect(await screen.findByRole('heading', { name: 'b id' })).toBeInTheDocument()
    expect(input).toHaveValue('Prague')
  })

  it('pages 61 Runs without changing the active Run or fetching new data', async () => {
    const user = userEvent.setup()
    api.listRunContainers.mockResolvedValue({
      run_containers: Array.from({ length: 61 }, (_, i) => run('run-' + i)),
    })
    mount()
    expect(await screen.findByRole('heading', { level: 4, name: 'run-0' })).toBeInTheDocument()
    expect(shownRunIds()).toHaveLength(25)
    const calls = api.listRunContainers.mock.calls.length
    await user.click(screen.getByRole('button', { name: 'Next' }))
    expect(await screen.findByRole('heading', { level: 4, name: 'run-25' })).toBeInTheDocument()
    expect(currentUrl()).toContain('runPage=2')
    expect(shownRunIds()).toHaveLength(25)
    await user.click(screen.getByRole('button', { name: 'Next' }))
    expect(await screen.findByRole('heading', { level: 4, name: 'run-50' })).toBeInTheDocument()
    expect(shownRunIds()).toHaveLength(11)
    expect(screen.getByRole('button', { name: 'Next' })).toBeDisabled()
    await user.click(screen.getByRole('button', { name: 'Previous' }))
    expect(await screen.findByRole('heading', { level: 4, name: 'run-25' })).toBeInTheDocument()
    expect(api.listRunContainers).toHaveBeenCalledTimes(calls)
  })

  it('does not silently redirect invalid/out-of-range bookmarked pages', async () => {
    mount('/viewer/runs?keep=two&runPage=99')
    expect(await screen.findByRole('alert')).toHaveTextContent('Requested page does not exist')
    expect(screen.queryByRole('heading', { level: 4, name: 'a/id #1' })).not.toBeInTheDocument()
    const user = userEvent.setup()
    await user.click(screen.getByRole('button', { name: 'First page' }))
    expect(await screen.findByRole('heading', { level: 4, name: 'a/id #1' })).toBeInTheDocument()
    expect(currentUrl()).toContain('keep=two')
    expect(currentUrl()).not.toContain('runPage')
  })

  it('distinguishes malformed catalog, legitimate empty list, and no search matches', async () => {
    api.listRunContainers.mockResolvedValue({ incorrect_key: [] })
    const first = mount()
    expect(await screen.findByRole('alert')).toHaveTextContent('invalid API format')
    expect(screen.queryByText('No Viewer runs are available yet.')).not.toBeInTheDocument()
    first.unmount()

    api.listRunContainers.mockResolvedValue({ run_containers: [] })
    const second = mount()
    expect(await screen.findByText('No Viewer runs are available yet.')).toBeInTheDocument()
    second.unmount()

    api.listRunContainers.mockResolvedValue({
      run_containers: [run('a/id #1', 'Brno Championship')],
    })
    mount('/viewer/runs?runQuery=Missing')
    expect(await screen.findByText('No Runs match this search.')).toBeInTheDocument()
    expect(screen.queryByText('No Viewer runs are available yet.')).not.toBeInTheDocument()
  })

  it('changes CS/EN copy without changing displayed Run identities or GET count', async () => {
    const user = userEvent.setup()
    mount('/viewer/runs?runQuery=Brno')
    expect(await screen.findByRole('heading', { level: 4, name: 'a/id #1' })).toBeInTheDocument()
    const calls = api.listRunContainers.mock.calls.length
    await user.click(screen.getByRole('button', { name: 'Toggle language' }))
    expect(screen.getByRole('heading', { name: 'Prohlížeč Runů' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Hledat' })).toBeInTheDocument()
    expect(screen.getByRole('searchbox', { name: 'Hledat podle názvu nebo ID Runu' }))
      .toHaveValue('Brno')
    const card = screen.getByLabelText('Run a/id #1')
    expect(within(card).getByRole('link', { name: 'Sezonní kalendář' }))
      .toHaveAttribute('href', '/viewer/runs/a%2Fid%20%231/calendar')
    expect(api.listRunContainers).toHaveBeenCalledTimes(calls)
    expectNoForbiddenViewerActions()
  })
})
