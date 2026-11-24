import { act, fireEvent, screen, waitFor, within } from '@testing-library/react'
import { QueryClient } from '@tanstack/react-query'
import { useLocation, useNavigate } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { LanguageProvider, useLanguage } from '../../../i18n/LanguageContext'
import { createTestQueryClient, expectNoForbiddenViewerActions, renderWithViewerProviders } from '../../../test/viewerTestUtils'
import { ViewerSignedSeasonComparison } from './ViewerSignedSeasonComparison'
import { signedSeasonComparisonFixture, signedSeasonListFixture } from './viewerSignedSeasonFixture'

const api = vi.hoisted(() => ({ getViewerOfficialRunContext: vi.fn() }))
const seasons = vi.hoisted(() => ({
  listViewerSignedSeasons: vi.fn(), readViewerSignedSeason: vi.fn(),
}))
vi.mock('../../../api/client', () => api)
vi.mock('../../../api/viewerSignedSeason', () => seasons)

function Navigation(): JSX.Element {
  const loc = useLocation(), nav = useNavigate()
  const { language, setLanguage } = useLanguage()
  return <>
    <output aria-label="Current URL">{loc.pathname}{loc.search}</output>
    <button type="button" onClick={() => nav(-1)}>Back</button>
    <button type="button" onClick={() => nav(1)}>Forward</button>
    <button type="button" onClick={() => setLanguage(language === 'cs' ? 'en' : 'cs')}>Toggle language</button>
  </>
}
const base = '/viewer/tour'
const prefix = 'signedRun=run+alpha&signedBranch=branch-tour&signedHead=rev-20'
function mount(search = '', client = createTestQueryClient()) {
  const view = renderWithViewerProviders(
    <LanguageProvider>
      <Navigation />
      <ViewerSignedSeasonComparison runId="run alpha" />
    </LanguageProvider>,
    { route: base + search, queryClient: client },
  )
  return { ...view, client }
}
function params() {
  const url = screen.getByLabelText('Current URL').textContent ?? ''
  return new URLSearchParams(url.split('?')[1] ?? '')
}
describe('Viewer signed-season source-scoped URL reports (mocked GET only)', () => {
  beforeEach(() => {
    localStorage.clear()
    localStorage.setItem('squash-engine-language-v1', 'en')
    vi.clearAllMocks()
    api.getViewerOfficialRunContext.mockResolvedValue({
      product_run_id: 'run alpha', official_branch_id: 'branch-tour',
    })
    seasons.listViewerSignedSeasons.mockResolvedValue(signedSeasonListFixture())
    seasons.readViewerSignedSeason.mockImplementation(async (_run, selected, compare) =>
      signedSeasonComparisonFixture(compare !== null))
  })

  it('does not request a report by default; submitting writes an exact deep link', async () => {
    mount('?keep=one&keep=two')
    expect(await screen.findByRole('button', { name: 'Show report' })).toBeInTheDocument()
    expect(seasons.readViewerSignedSeason).not.toHaveBeenCalled()
    fireEvent.click(screen.getByRole('button', { name: 'Show report' }))
    expect(await screen.findByText('Season summary: 2001/02')).toBeInTheDocument()
    expect(params().get('signedRun')).toBe('run alpha')
    expect(params().get('signedBranch')).toBe('branch-tour')
    expect(params().get('signedHead')).toBe('rev-20')
    expect(params().get('signedSeason')).toBe('1')
    expect(params().has('compareSeason')).toBe(false)
    expect(params().getAll('keep')).toEqual(['one', 'two'])
    expect(seasons.readViewerSignedSeason).toHaveBeenCalledWith('run alpha', 1, null, expect.anything())
    expectNoForbiddenViewerActions()
  })

  it('loads the exact requested closed seasons on a bookmarked URL and preserves original signed statistics', async () => {
    mount('?' + prefix + '&signedSeason=1&compareSeason=0&keep=x')
    const summary = await screen.findByRole('article', { name: 'Season summary' })
    expect(within(summary).getByText('2001/02 ↔ 2000/01')).toBeInTheDocument()
    expect(within(summary).getByText('rev-20')).toBeInTheDocument()
    expect(within(summary).getByRole('table', { name: 'Change versus comparison season' }))
      .toHaveTextContent('-40')
    expect(seasons.readViewerSignedSeason).toHaveBeenCalledWith('run alpha', 1, 0, expect.anything())
    expect(screen.getByLabelText('Selected season')).toHaveValue('1')
    expect(screen.getByLabelText('Comparison season')).toHaveValue('0')
    expect(params().get('keep')).toBe('x')
    expectNoForbiddenViewerActions()
  })

  it.each([
    '?' + prefix + '&signedSeason=01',
    '?' + prefix + '&signedSeason=1&compareSeason=1',
    '?' + prefix + '&signedSeason=1&compareSeason=-1',
    '?' + prefix + '&signedSeason=99',
    '?' + prefix.replace('rev-20', 'foreign-head') + '&signedSeason=1',
    '?' + prefix.replace('branch-tour', 'foreign') + '&signedSeason=1',
    '?signedSeason=1&compareSeason=0',
    '?' + prefix + '&signedSeason=1&signedSeason=0',
  ])('rejects invalid/foreign/unpublished deep link without silent latest fallback: %s', async url => {
    mount(url)
    expect(await screen.findByRole('alert')).toHaveTextContent('link is invalid or refers to another Viewer Branch')
    expect(seasons.readViewerSignedSeason).not.toHaveBeenCalled()
    expect(screen.queryByRole('article', { name: 'Season summary' })).not.toBeInTheDocument()
  })

  it('draft changes hide previous report until submission and Back/Forward restores exact pairs', async () => {
    mount('?' + prefix + '&signedSeason=1&keep=one&keep=two')
    expect(await screen.findByText('Season summary: 2001/02')).toBeInTheDocument()
    fireEvent.change(screen.getByLabelText('Comparison season'), { target: { value: '0' } })
    expect(screen.queryByRole('article', { name: 'Season summary' })).not.toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Show report' }))
    expect(await screen.findByText('2001/02 ↔ 2000/01')).toBeInTheDocument()
    expect(params().get('compareSeason')).toBe('0')
    expect(params().getAll('keep')).toEqual(['one', 'two'])
    fireEvent.click(screen.getByRole('button', { name: 'Back' }))
    expect(await screen.findByText('Season summary: 2001/02')).toBeInTheDocument()
    expect(screen.getByLabelText('Comparison season')).toHaveValue('')
    expect(params().has('compareSeason')).toBe(false)
    fireEvent.click(screen.getByRole('button', { name: 'Forward' }))
    expect(await screen.findByText('2001/02 ↔ 2000/01')).toBeInTheDocument()
    expect(screen.getByLabelText('Comparison season')).toHaveValue('0')
  })

  it('can recover from a foreign URL only by explicitly selecting an available report', async () => {
    mount('?' + prefix.replace('branch-tour', 'wrong-branch') + '&signedSeason=1&keep=untouched')
    expect(await screen.findByRole('alert')).toBeInTheDocument()
    expect(seasons.readViewerSignedSeason).not.toHaveBeenCalled()
    fireEvent.click(screen.getByRole('button', { name: 'Show report' }))
    expect(await screen.findByText('Season summary: 2001/02')).toBeInTheDocument()
    expect(params().get('signedBranch')).toBe('branch-tour')
    expect(params().get('signedHead')).toBe('rev-20')
    expect(params().get('keep')).toBe('untouched')
  })

  it('hides an already verified season report during a fresh signed GET', async () => {
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
    mount('?' + prefix + '&signedSeason=1', client)
    expect(await screen.findByText('Season summary: 2001/02')).toBeInTheDocument()
    let release!: (value: ReturnType<typeof signedSeasonComparisonFixture>) => void
    seasons.readViewerSignedSeason.mockImplementationOnce(() =>
      new Promise(resolve => { release = resolve })
    )
    const pending = client.invalidateQueries({ queryKey: ['viewer-signed-season-summary'] })
    await waitFor(() => expect(seasons.readViewerSignedSeason).toHaveBeenCalledTimes(2))
    expect(screen.queryByRole('article', { name: 'Season summary' })).not.toBeInTheDocument()
    await act(async () => { release(signedSeasonComparisonFixture()); await pending })
    expect(await screen.findByText('Season summary: 2001/02')).toBeInTheDocument()
  })

  it('switches CS/EN without a new HTTP GET or changed historical season pairing', async () => {
    mount('?' + prefix + '&signedSeason=1&compareSeason=0')
    expect(await screen.findByText('2001/02 ↔ 2000/01')).toBeInTheDocument()
    const reads = seasons.readViewerSignedSeason.mock.calls.length
    fireEvent.click(screen.getByRole('button', { name: 'Toggle language' }))
    expect(screen.getByText('Uzavřené sezony – výsledky a srovnání')).toBeInTheDocument()
    expect(screen.getByText('2001/02 ↔ 2000/01')).toBeInTheDocument()
    expect(seasons.readViewerSignedSeason).toHaveBeenCalledTimes(reads)
    expect(params().get('signedSeason')).toBe('1')
    expect(params().get('compareSeason')).toBe('0')
  })
})
