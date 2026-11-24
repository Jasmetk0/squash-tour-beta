import { act, fireEvent, screen, waitFor } from '@testing-library/react'
import { useLocation, useNavigate } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { LanguageProvider, useLanguage } from '../../../i18n/LanguageContext'
import { createTestQueryClient, expectNoForbiddenViewerActions, renderWithViewerProviders } from '../../../test/viewerTestUtils'
import { ViewerSignedTourRecords } from './ViewerSignedTourRecords'
import { signedRecordFixture } from './viewerSignedTourRecordsFixture'

const client = vi.hoisted(() => ({ getViewerOfficialRunContext: vi.fn() }))
const records = vi.hoisted(() => ({ getViewerSignedTourRecords: vi.fn() }))
vi.mock('../../../api/client', () => client)
vi.mock('../../../api/viewerSignedTourRecords', () => records)

const scope = 'recordsRun=record+run&recordsBranch=viewer-a&recordsHead=revision-7&recordsFingerprint='
  + 'a'.repeat(64) + '&recordsAsOf=1&recordsFrom=0'
function Navigation(): JSX.Element {
  const { language, setLanguage } = useLanguage()
  const loc = useLocation(), nav = useNavigate()
  return <>
    <output aria-label="Current URL">{loc.pathname}{loc.search}</output>
    <button type="button" onClick={() => nav(-1)}>Back</button>
    <button type="button" onClick={() => nav(1)}>Forward</button>
    <button type="button" onClick={() => setLanguage(language === 'cs' ? 'en' : 'cs')}>Switch language</button>
  </>
}
function url(): URLSearchParams {
  return new URLSearchParams((screen.getByLabelText('Current URL').textContent ?? '').split('?')[1] ?? '')
}
function mount(search = '') {
  const queryClient = createTestQueryClient()
  const view = renderWithViewerProviders(<LanguageProvider>
    <Navigation />
    <ViewerSignedTourRecords runId="record run" />
  </LanguageProvider>, { route: '/viewer/records' + search, queryClient })
  return { ...view, queryClient }
}

describe('Source-locked URL filters for signed native Tour records (mocked GET)', () => {
  beforeEach(() => {
    localStorage.clear()
    localStorage.setItem('squash-engine-language-v1', 'en')
    vi.clearAllMocks()
    client.getViewerOfficialRunContext.mockResolvedValue({
      product_run_id: 'record run', official_branch_id: 'viewer-a',
    })
    records.getViewerSignedTourRecords.mockImplementation(async (_run, filters) => ({
      ...signedRecordFixture(), country_code: filters.countryCode,
    }))
  })

  it('keeps default baseline until a form is submitted; writes scope-locked filters and preserves extras', async () => {
    mount('?keep=one&keep=two')
    expect(await screen.findByText('2000/01 – 2001/02')).toBeInTheDocument()
    expect(records.getViewerSignedTourRecords).toHaveBeenCalledTimes(1)
    fireEvent.change(screen.getByLabelText('ISO-3 country (optional)'), { target: { value: 'cze' } })
    expect(records.getViewerSignedTourRecords).toHaveBeenCalledTimes(1)
    expect(screen.queryByText('2000/01 – 2001/02')).not.toBeInTheDocument()
    expect(screen.getByText('Filters were edited. Submit the new period to load records.')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Show selected records' }))
    expect(await screen.findByText('CZE', { selector: 'dd' })).toBeInTheDocument()
    expect(records.getViewerSignedTourRecords).toHaveBeenCalledWith(
      'record run', { asOfSeason: 1, fromSeason: 0, countryCode: 'CZE' }, expect.anything())
    expect(url().get('recordsRun')).toBe('record run')
    expect(url().get('recordsBranch')).toBe('viewer-a')
    expect(url().get('recordsHead')).toBe('revision-7')
    expect(url().get('recordsFingerprint')).toBe('a'.repeat(64))
    expect(url().get('recordsCountry')).toBe('CZE')
    expect(url().getAll('keep')).toEqual(['one', 'two'])
    expectNoForbiddenViewerActions()
  })

  it('loads a bookmarked exact signed period and country on direct URL', async () => {
    mount('?' + scope + '&recordsCountry=CZE&keep=one')
    expect(await screen.findByText('CZE', { selector: 'dd' })).toBeInTheDocument()
    expect(screen.getByLabelText('As of season')).toHaveValue('1')
    expect(screen.getByLabelText('From season')).toHaveValue('0')
    expect(screen.getByLabelText('ISO-3 country (optional)')).toHaveValue('CZE')
    expect(records.getViewerSignedTourRecords).toHaveBeenCalledWith(
      'record run', { asOfSeason: 1, fromSeason: 0, countryCode: 'CZE' }, expect.anything())
    expect(url().get('keep')).toBe('one')
    expect(screen.getByText('revision-7')).toBeInTheDocument()
    expectNoForbiddenViewerActions()
  })

  it('restores exact source-bound reports with Back/Forward, including country scope', async () => {
    mount('?' + scope + '&keep=one&keep=two')
    expect(await screen.findByText('2000/01 – 2001/02')).toBeInTheDocument()
    fireEvent.change(screen.getByLabelText('ISO-3 country (optional)'), { target: { value: 'cze' } })
    fireEvent.click(screen.getByRole('button', { name: 'Show selected records' }))
    expect(await screen.findByText('CZE', { selector: 'dd' })).toBeInTheDocument()
    expect(url().get('recordsCountry')).toBe('CZE')
    fireEvent.click(screen.getByRole('button', { name: 'Back' }))
    await waitFor(() => expect(screen.getByLabelText('ISO-3 country (optional)')).toHaveValue(''))
    expect(await screen.findByText('2000/01 – 2001/02')).toBeInTheDocument()
    expect(url().get('recordsCountry')).toBeNull()
    fireEvent.click(screen.getByRole('button', { name: 'Forward' }))
    await waitFor(() => expect(screen.getByLabelText('ISO-3 country (optional)')).toHaveValue('CZE'))
    expect(await screen.findByText('CZE', { selector: 'dd' })).toBeInTheDocument()
    expect(url().get('recordsCountry')).toBe('CZE')
  })

  it.each([
    '?' + scope.replace('revision-7', 'older-head'),
    '?' + scope.replace('viewer-a', 'foreign-branch'),
    '?' + scope.replace('a'.repeat(64), 'b'.repeat(64)),
    '?' + scope.replace('recordsAsOf=1', 'recordsAsOf=99'),
    '?' + scope.replace('recordsFrom=0', 'recordsFrom=99'),
    '?' + scope + '&recordsAsOf=0',
    '?' + scope + '&recordsCountry=cze',
    '?recordsCountry=CZE',
  ])('rejects foreign/expired/unpublished or malformed bookmark without a filtered GET: %s', async search => {
    mount(search)
    expect(await screen.findByRole('alert')).toHaveTextContent('link does not match this Run')
    expect(screen.queryByText('2000/01 – 2001/02')).not.toBeInTheDocument()
    expect(records.getViewerSignedTourRecords).toHaveBeenCalledTimes(1)
    fireEvent.click(screen.getByRole('button', { name: 'Default period' }))
    expect(await screen.findByText('2000/01 – 2001/02')).toBeInTheDocument()
    expect(url().has('recordsHead')).toBe(false)
  })

  it('refuses a stale saved revision even if a cached filter report names the old HEAD', async () => {
    const view = mount('?' + scope + '&recordsCountry=CZE')
    expect(await screen.findByText('CZE', { selector: 'dd' })).toBeInTheDocument()
    let release!: (value: ReturnType<typeof signedRecordFixture>) => void
    records.getViewerSignedTourRecords.mockImplementationOnce(() =>
      new Promise(resolve => { release = resolve }))
    const refresh = view.queryClient.invalidateQueries({
      queryKey: ['viewer-signed-tour-records', 'record run', 'viewer-a', 'baseline'],
    })
    await waitFor(() => expect(records.getViewerSignedTourRecords).toHaveBeenCalledTimes(3))
    expect(screen.queryByText('CZE', { selector: 'dd' })).not.toBeInTheDocument()
    await act(async () => { release({ ...signedRecordFixture(), saved_head_revision_id: 'revision-8' }); await refresh })
    expect(await screen.findByRole('alert')).toHaveTextContent('link does not match this Run')
    expect(screen.queryByText('2000/01 – 2001/02')).not.toBeInTheDocument()
  })

  it('switches CS/EN labels but preserves the selected historical period and country', async () => {
    mount('?' + scope + '&recordsCountry=CZE')
    expect(await screen.findByText('CZE', { selector: 'dd' })).toBeInTheDocument()
    const calls = records.getViewerSignedTourRecords.mock.calls.length
    fireEvent.click(screen.getByRole('button', { name: 'Switch language' }))
    expect(screen.getByText('Historické rekordy dokončených sezon')).toBeInTheDocument()
    expect(screen.getByLabelText('Země ISO-3 (nepovinné)')).toHaveValue('CZE')
    expect(screen.getByText('revision-7')).toBeInTheDocument()
    expect(records.getViewerSignedTourRecords).toHaveBeenCalledTimes(calls)
    expect(url().get('recordsCountry')).toBe('CZE')
  })
})
