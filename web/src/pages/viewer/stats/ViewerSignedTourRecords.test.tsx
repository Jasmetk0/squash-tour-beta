import { fireEvent, screen, within } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { LanguageProvider } from '../../../i18n/LanguageContext'
import { renderWithViewerProviders } from '../../../test/viewerTestUtils'
import { ViewerSignedTourRecords } from './ViewerSignedTourRecords'
import { signedRecordFixture } from './viewerSignedTourRecordsFixture'

const client = vi.hoisted(() => ({ getViewerOfficialRunContext: vi.fn() }))
const records = vi.hoisted(() => ({ getViewerSignedTourRecords: vi.fn() }))

vi.mock('../../../api/client', () => client)
vi.mock('../../../api/viewerSignedTourRecords', () => records)

function renderRecords(): void {
  renderWithViewerProviders(<LanguageProvider><ViewerSignedTourRecords runId="record run" /></LanguageProvider>)
}

describe('Viewer signed native Tour record browser (mocked GET contract)', () => {
  beforeEach(() => {
    localStorage.setItem('squash-engine-language-v1', 'en')
    vi.clearAllMocks()
    client.getViewerOfficialRunContext.mockResolvedValue({
      product_run_id: 'record run', official_branch_id: 'viewer-a'
    })
    records.getViewerSignedTourRecords.mockResolvedValue(signedRecordFixture())
  })

  it('renders exactly six signed record summaries and bounded provenance with no writes', async () => {
    renderRecords()
    expect(await screen.findByText('2000/01 – 2001/02')).toBeInTheDocument()
    expect(screen.getByText('revision-7')).toBeInTheDocument()
    expect(screen.getByText('Confirmed tournaments')).toBeInTheDocument()
    const summaries = [...document.querySelectorAll('summary')].map(element => element.textContent ?? '')
    expect(summaries.filter(text => text.startsWith('Titles: 1'))).toHaveLength(2)
    expect(summaries.filter(text => text.startsWith('Finals: 2'))).toHaveLength(2)
    expect(summaries.filter(text => text.startsWith('Awarded points: 150'))).toHaveLength(2)
    expect(records.getViewerSignedTourRecords).toHaveBeenCalledWith(
      'record run', { asOfSeason: null, fromSeason: 0, countryCode: null }, expect.anything()
    )
    const playerSection = screen.getByRole('region', { name: 'Players' })
    fireEvent.click(within(playerSection).getAllByText((_, element) =>
      element?.tagName === 'SUMMARY' && element.textContent?.startsWith('Titles: 1') === true)[0])
    expect(within(playerSection).getAllByRole('link', { name: 'Player One' })[0]).toHaveAttribute(
      'href', '/viewer/runs/record%20run/players/p-1/career'
    )
    expect(screen.queryByRole('button', { name: /Save|Simulate|Publish/i })).not.toBeInTheDocument()
  })

  it('requires explicit filter submission and reads only the requested Signed period/country', async () => {
    records.getViewerSignedTourRecords.mockImplementation(async (_run, filter) => {
      const base = signedRecordFixture()
      return filter?.countryCode === 'CZE' ? { ...base, country_code: 'CZE' } : base
    })
    renderRecords()
    await screen.findByText('2000/01 – 2001/02')
    fireEvent.change(screen.getByLabelText('ISO-3 country (optional)'), { target: { value: 'cze' } })
    expect(records.getViewerSignedTourRecords).toHaveBeenCalledTimes(1)
    fireEvent.click(screen.getByRole('button', { name: 'Show selected records' }))
    expect(await screen.findByText('CZE', { selector: 'dd' })).toBeInTheDocument()
    expect(records.getViewerSignedTourRecords).toHaveBeenCalledWith(
      'record run', { asOfSeason: 1, fromSeason: 0, countryCode: 'CZE' }, expect.anything()
    )
    fireEvent.click(screen.getByRole('button', { name: 'Default period' }))
    expect(screen.getByLabelText('ISO-3 country (optional)')).toHaveValue('')
  })

  it('refuses a mismatched Saved response without showing forged records', async () => {
    records.getViewerSignedTourRecords.mockResolvedValue({
      ...signedRecordFixture(), branch_id: 'viewer-other'
    })
    renderRecords()
    expect(await screen.findByText(/historical evidence failed validation/)).toBeInTheDocument()
    expect(screen.queryByText('2000/01 – 2001/02')).not.toBeInTheDocument()
  })

  it.each(['saved_head_revision_id', 'source_tour_fingerprint'] as const)(
    'rejects a filtered response from a different %s than its season inventory', async field => {
      records.getViewerSignedTourRecords.mockImplementation(async (_run, filter) => {
        const base = signedRecordFixture()
        return filter?.countryCode === 'CZE'
          ? { ...base, country_code: 'CZE', [field]: field === 'source_tour_fingerprint' ? 'f'.repeat(64) : 'new-head' }
          : base
      })
      renderRecords()
      await screen.findByText('2000/01 – 2001/02')
      fireEvent.change(screen.getByLabelText('ISO-3 country (optional)'), { target: { value: 'CZE' } })
      fireEvent.click(screen.getByRole('button', { name: 'Show selected records' }))
      expect(await screen.findByText(/historical evidence failed validation/)).toBeInTheDocument()
      expect(screen.queryByText('2000/01 – 2001/02')).not.toBeInTheDocument()
    })

  it('refuses a foreign Viewer context before issuing a records request', async () => {
    client.getViewerOfficialRunContext.mockResolvedValue({
      product_run_id: 'other run', official_branch_id: 'viewer-a'
    })
    renderRecords()
    expect(await screen.findByText(/historical evidence failed validation/)).toBeInTheDocument()
    expect(records.getViewerSignedTourRecords).not.toHaveBeenCalled()
  })

  it('does not mislabel a rejected or unavailable record source as a zero-record season', async () => {
    records.getViewerSignedTourRecords.mockRejectedValue(new Error('HTTP 409'))
    renderRecords()
    expect(await screen.findByText(/Records are unavailable/)).toBeInTheDocument()
    expect(screen.queryByText('No record holder yet.')).not.toBeInTheDocument()
  })
})
