import { fireEvent, screen, waitFor } from '@testing-library/react'
import { QueryClient } from '@tanstack/react-query'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { RunCreatePage } from './RunCreatePage'
import { LanguageProvider } from '../i18n/LanguageContext'
import type { RunCalendarCreationInput } from '../api/runCalendarCreation'
import { renderWithRoute } from '../test/testUtils'

const navigate = vi.fn()
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual<typeof import('react-router-dom')>('react-router-dom')
  return { ...actual, useNavigate: () => navigate }
})
const api = vi.hoisted(() => {
  class ApiError extends Error {
    status: number
    constructor(message: string, status: number) {
      super(message)
      this.status = status
    }
  }
  return { ApiError, createEmptyRunContainer: vi.fn(), previewRunCalendarCreation: vi.fn(), listRunContainers: vi.fn() }
})
vi.mock('../api/client', () => api)

const renderPage = () => renderWithRoute(<LanguageProvider><RunCreatePage /></LanguageProvider>, '/admin/runs/new')
const preview = (input: RunCalendarCreationInput) => {
  const count = input.season_count ?? input.last_season_start_year! - input.start_year + 1
  const clock = {schema_version: 'run_calendar.v1', weeks_per_year: input.weeks_per_year,
    season_start_year_week: input.season_start_year_week, start_year: input.start_year, season_count: count}
  const position = (i: number, week: number) => {
    const elapsed = input.season_start_year_week + week - 2
    const year = input.start_year + i
    return {season_index: i, season_week: week, calendar_year: year + Math.floor(elapsed / input.weeks_per_year),
      year_week: elapsed % input.weeks_per_year + 1, week_ordinal: i * input.weeks_per_year + week - 1,
      season_label: input.season_start_year_week === 1 ? String(year) : `${year}/${year + 1}`}
  }
  return {schema_version: 'run_calendar_configuration_preview.v1', run_created: false, read_only: true,
    run_calendar: clock, first_week: position(0, 1), last_week: position(count - 1, input.weeks_per_year),
    sporting_calendar_supported: false, limitations: ['sporting_calendar_execution_not_supported_yet']}
}

describe('canonical Product Run creation', () => {
  beforeEach(() => {
    localStorage.clear()
    localStorage.setItem('squash-engine-language-v1', 'en')
    vi.clearAllMocks()
    api.createEmptyRunContainer.mockResolvedValue({
      run_id: 'new-run-1', display_name: 'My test Run',
      storage_kind: 'custom_local', read_only: false,
      official_branch_id: 'timeline-1', status: 'active'
    })
    api.previewRunCalendarCreation.mockImplementation(async input => preview(input))
    api.listRunContainers.mockResolvedValue({ run_containers: [] })
  })

  it('creates an isolated empty Product Run using only its display name and opens the saved identity', async () => {
    renderPage()
    expect(screen.queryByLabelText('Seed')).not.toBeInTheDocument()
    expect(screen.queryByLabelText('World Package')).not.toBeInTheDocument()
    expect(screen.getByText(/own Timeline 1, initial Saved Revision/)).toBeInTheDocument()

    await userEvent.type(screen.getByLabelText('Unique Run name'), ' My test Run ')
    await userEvent.click(screen.getByRole('button', { name: 'Create isolated Run' }))
    await waitFor(() => expect(api.createEmptyRunContainer).toHaveBeenCalledWith('My test Run'))
    await waitFor(() => expect(navigate).toHaveBeenCalledWith('/admin/runs/new-run-1'))
    expect(localStorage.getItem('beta_engine:last_run_id')).toBe('new-run-1')
  })

  it('rejects a duplicate name without navigating or recording a guessed Run ID', async () => {
    api.createEmptyRunContainer.mockRejectedValueOnce(new Error('Display name already exists'))
    renderPage()
    await userEvent.type(screen.getByLabelText('Unique Run name'), 'My test Run')
    await userEvent.click(screen.getByRole('button', { name: 'Create isolated Run' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('Display name already exists')
    expect(navigate).not.toHaveBeenCalled()
    expect(localStorage.getItem('beta_engine:last_run_id')).toBeNull()
  })

  it('fails closed if the create response does not match the requested Run name', async () => {
    api.createEmptyRunContainer.mockResolvedValueOnce({
      run_id: 'other-run', display_name: 'Somebody else', storage_kind: 'custom_local', read_only: false
    })
    renderPage()
    await userEvent.type(screen.getByLabelText('Unique Run name'), 'My test Run')
    await userEvent.click(screen.getByRole('button', { name: 'Create isolated Run' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('unexpected Run identity')
    expect(navigate).not.toHaveBeenCalled()
  })

  it('reviews Earth and creates exactly that calendar, without claiming sporting execution (mock HTTP)', async () => {
    renderPage()
    await userEvent.type(screen.getByLabelText('Unique Run name'), 'My test Run')
    await userEvent.click(screen.getByLabelText('Choose calendar and range'))
    expect(screen.getByRole('button', {name: 'Create isolated Run'})).toBeDisabled()
    await userEvent.selectOptions(screen.getByLabelText('Calendar preset'), 'earth')
    await userEvent.clear(screen.getByLabelText('Start year'))
    await userEvent.type(screen.getByLabelText('Start year'), '2030')
    await userEvent.clear(screen.getByLabelText('Number of seasons'))
    await userEvent.type(screen.getByLabelText('Number of seasons'), '3')
    await userEvent.click(screen.getByRole('button', {name: 'Review calendar'}))
    expect(await screen.findByText(/Sporting simulation is not available/)).toBeVisible()
    expect(screen.getByText('2030', {selector:'strong'})).toBeVisible()
    expect(screen.getByText('2032', {selector:'strong'})).toBeVisible()
    const input = {weeks_per_year:52, season_start_year_week:1, start_year:2030, season_count:3}
    expect(api.previewRunCalendarCreation).toHaveBeenCalledWith(input)
    expect(api.createEmptyRunContainer).not.toHaveBeenCalled()
    api.createEmptyRunContainer.mockResolvedValueOnce({
      run_id:'new-run-1', display_name:'My test Run', storage_kind:'custom_local', read_only:false,
      metadata_json:{run_calendar:preview(input).run_calendar}
    })
    await userEvent.click(screen.getByRole('button', {name: 'Create isolated Run'}))
    await waitFor(() => expect(api.createEmptyRunContainer).toHaveBeenCalledWith('My test Run', input))
    expect(navigate).toHaveBeenCalledWith('/admin/runs/new-run-1')
  })

  it('revokes preview on edits and discards an in-flight response for old inputs', async () => {
    renderPage()
    await userEvent.type(screen.getByLabelText('Unique Run name'), 'My test Run')
    await userEvent.click(screen.getByLabelText('Choose calendar and range'))
    let resolve!: (value: unknown) => void
    api.previewRunCalendarCreation.mockImplementationOnce(() => new Promise(done => {resolve=done}))
    await userEvent.click(screen.getByRole('button', {name:'Review calendar'}))
    await userEvent.clear(screen.getByLabelText('Start year'))
    await userEvent.type(screen.getByLabelText('Start year'), '2030')
    resolve(preview({weeks_per_year:61, season_start_year_week:37, start_year:2000, season_count:50}))
    await waitFor(() => expect(screen.getByRole('button', {name:'Review calendar'})).toBeEnabled())
    expect(screen.queryByText(/Sporting simulation is not available/)).toBeNull()
    expect(screen.getByRole('button', {name:'Create isolated Run'})).toBeDisabled()
    await userEvent.click(screen.getByRole('button', {name:'Review calendar'}))
    await screen.findByText(/Sporting simulation is not available/)
    expect(screen.getByRole('button', {name:'Create isolated Run'})).toBeEnabled()
    await userEvent.selectOptions(screen.getByLabelText('Specify the end using'), 'last')
    expect(screen.getByLabelText('Starting year of last season')).toHaveValue(2079)
    expect(screen.getByRole('button', {name:'Create isolated Run'})).toBeDisabled()
  })

  it('rejects a different saved calendar and never navigates on that response', async () => {
    renderPage()
    await userEvent.type(screen.getByLabelText('Unique Run name'), 'My test Run')
    await userEvent.click(screen.getByLabelText('Choose calendar and range'))
    await userEvent.selectOptions(screen.getByLabelText('Calendar preset'), 'earth')
    await userEvent.click(screen.getByRole('button', {name:'Review calendar'}))
    await screen.findByText(/Sporting simulation is not available/)
    await userEvent.click(screen.getByRole('button', {name:'Create isolated Run'}))
    expect(await screen.findByRole('alert')).toHaveTextContent('does not match the reviewed request')
    expect(screen.getByRole('link', { name: 'Open the created Run' }))
      .toHaveAttribute('href', '/admin/runs/new-run-1')
    expect(screen.getByRole('button', { name: 'Create isolated Run' })).toBeDisabled()
    expect(navigate).not.toHaveBeenCalled()
  })

  it('uses Czech and accepts the last-season starting year as the horizon input', async () => {
    localStorage.setItem('squash-engine-language-v1', 'cs')
    renderPage()
    await userEvent.click(screen.getByLabelText('Zvolit kalendář a rozsah'))
    await userEvent.selectOptions(screen.getByLabelText('Předvolba kalendáře'), 'earth')
    await userEvent.selectOptions(screen.getByLabelText('Konec zadat pomocí'), 'last')
    await userEvent.clear(screen.getByLabelText('Rok začátku poslední sezony'))
    await userEvent.type(screen.getByLabelText('Rok začátku poslední sezony'), '2002')
    await userEvent.click(screen.getByRole('button', {name:'Prověřit kalendář'}))
    expect(await screen.findByText(/Sportovní simulace pro něj zatím není dostupná/)).toBeVisible()
    expect(api.previewRunCalendarCreation).toHaveBeenCalledWith({
      weeks_per_year:52, season_start_year_week:1, start_year:2000, last_season_start_year:2002
    })
    expect(screen.getByText('2002', {selector:'strong'})).toBeVisible()
  })

  it('sends only one authoritative create command for two submissions in the same render turn', async () => {
    let resolveCreate!: (value: unknown) => void
    api.createEmptyRunContainer.mockImplementationOnce(() => new Promise(done => { resolveCreate = done }))
    renderPage()
    await userEvent.type(screen.getByLabelText('Unique Run name'), 'My test Run')
    const form = screen.getByRole('button', { name: 'Create isolated Run' }).closest('form')!
    fireEvent.submit(form)
    fireEvent.submit(form)
    expect(api.createEmptyRunContainer).toHaveBeenCalledTimes(1)
    resolveCreate({ run_id: 'new-run-1', display_name: 'My test Run',
      storage_kind: 'custom_local', read_only: false })
    await waitFor(() => expect(navigate).toHaveBeenCalledWith('/admin/runs/new-run-1'))
  })

  it('navigates after a validated create even when the inventory cache refresh fails', async () => {
    const refresh = vi.spyOn(QueryClient.prototype, 'invalidateQueries')
      .mockRejectedValueOnce(new Error('inventory refresh failed'))
    try {
      renderPage()
      await userEvent.type(screen.getByLabelText('Unique Run name'), 'My test Run')
      await userEvent.click(screen.getByRole('button', { name: 'Create isolated Run' }))
      await waitFor(() => expect(navigate).toHaveBeenCalledWith('/admin/runs/new-run-1'))
      expect(screen.queryByRole('alert')).not.toBeInTheDocument()
      expect(api.createEmptyRunContainer).toHaveBeenCalledTimes(1)
    } finally {
      refresh.mockRestore()
    }
  })

  it('explains that a validated Run exists if navigating to it fails, avoiding duplicate retries', async () => {
    navigate.mockImplementationOnce(() => { throw new Error('router unavailable') })
    renderPage()
    await userEvent.type(screen.getByLabelText('Unique Run name'), 'My test Run')
    await userEvent.click(screen.getByRole('button', { name: 'Create isolated Run' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('The Run was created')
    expect(screen.getByRole('alert')).toHaveTextContent('do not create it again')
    expect(screen.getByRole('alert')).not.toHaveTextContent('Run creation was not confirmed')
    expect(screen.getByRole('link', { name: 'Open the created Run' }))
      .toHaveAttribute('href', '/admin/runs/new-run-1')
    expect(screen.getByRole('button', { name: 'Create isolated Run' })).toBeDisabled()
    // Even an explicit second submit on the still-mounted form cannot create a duplicate.
    fireEvent.submit(screen.getByRole('button', { name: 'Create isolated Run' }).closest('form')!)
    expect(api.createEmptyRunContainer).toHaveBeenCalledTimes(1)
  })

  it('creates a Run even if the browser denies localStorage writes', async () => {
    renderPage()
    await userEvent.type(screen.getByLabelText('Unique Run name'), 'My test Run')
    const storage = vi.spyOn(Storage.prototype, 'setItem')
      .mockImplementation(() => { throw new Error('storage unavailable') })
    try {
      await userEvent.click(screen.getByRole('button', { name: 'Create isolated Run' }))
      await waitFor(() => expect(navigate).toHaveBeenCalledWith('/admin/runs/new-run-1'))
      expect(screen.queryByRole('alert')).not.toBeInTheDocument()
    } finally {
      storage.mockRestore()
    }
  })

  it('allows retry only when a create request was not confirmed', async () => {
    api.createEmptyRunContainer.mockRejectedValueOnce(new Error('connection interrupted'))
    renderPage()
    await userEvent.type(screen.getByLabelText('Unique Run name'), 'My test Run')
    await userEvent.click(screen.getByRole('button', { name: 'Create isolated Run' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('Check the Run inventory before retrying')
    expect(screen.getByRole('button', { name: 'Create isolated Run' })).toBeDisabled()
    await userEvent.click(screen.getByRole('button', { name: 'Check saved Runs for this name' }))
    expect(api.listRunContainers).toHaveBeenCalledTimes(1)
    expect(screen.getByText(/No Run with this name is in the current inventory/)).toBeVisible()
    expect(screen.getByRole('button', { name: 'Create isolated Run' })).toBeEnabled()
    expect(api.createEmptyRunContainer).toHaveBeenCalledTimes(1)
    await userEvent.click(screen.getByRole('button', { name: 'Create isolated Run' }))
    await waitFor(() => expect(navigate).toHaveBeenCalledWith('/admin/runs/new-run-1'))
    expect(api.createEmptyRunContainer).toHaveBeenCalledTimes(2)
  })

  it('encodes a server-confirmed Run ID in the navigation path without altering its identity', async () => {
    api.createEmptyRunContainer.mockResolvedValueOnce({
      run_id: 'run/č 1', display_name: 'My test Run', storage_kind: 'custom_local', read_only: false
    })
    renderPage()
    await userEvent.type(screen.getByLabelText('Unique Run name'), 'My test Run')
    await userEvent.click(screen.getByRole('button', { name: 'Create isolated Run' }))
    await waitFor(() => expect(navigate).toHaveBeenCalledWith('/admin/runs/run%2F%C4%8D%201'))
    expect(localStorage.getItem('beta_engine:last_run_id')).toBe('run/č 1')
  })

  it('resolves a lost create reply to a matching saved Run without repeating POST', async () => {
    api.createEmptyRunContainer.mockRejectedValueOnce(new Error('connection lost after commit'))
    api.listRunContainers.mockResolvedValueOnce({ run_containers: [{
      run_id: 'saved/č', display_name: 'My test Run', read_only: false,
      storage_kind: 'custom_local'
    }] })
    renderPage()
    await userEvent.type(screen.getByLabelText('Unique Run name'), 'My test Run')
    await userEvent.click(screen.getByRole('button', { name: 'Create isolated Run' }))
    expect(await screen.findByRole('button', { name: 'Check saved Runs for this name' })).toBeVisible()
    expect(screen.getByRole('button', { name: 'Create isolated Run' })).toBeDisabled()
    await userEvent.click(screen.getByRole('button', { name: 'Check saved Runs for this name' }))
    expect(await screen.findByRole('link', { name: 'Open Run with this name' }))
      .toHaveAttribute('href', '/admin/runs/saved%2F%C4%8D')
    expect(screen.getByText(/A Run with this exact name exists/)).toBeVisible()
    expect(screen.getByRole('button', { name: 'Create isolated Run' })).toBeDisabled()
    fireEvent.submit(screen.getByRole('button', { name: 'Create isolated Run' }).closest('form')!)
    expect(api.createEmptyRunContainer).toHaveBeenCalledTimes(1)
    expect(navigate).not.toHaveBeenCalled()
    expect(localStorage.getItem('beta_engine:last_run_id')).toBeNull()
  })

  it('fails closed if the fresh inventory is unavailable and permits an explicit recheck', async () => {
    api.createEmptyRunContainer.mockRejectedValueOnce(new Error('network interrupted'))
    api.listRunContainers.mockRejectedValueOnce(new Error('offline'))
    renderPage()
    await userEvent.type(screen.getByLabelText('Unique Run name'), 'My test Run')
    await userEvent.click(screen.getByRole('button', { name: 'Create isolated Run' }))
    await userEvent.click(await screen.findByRole('button', { name: 'Check saved Runs for this name' }))
    expect(await screen.findByText(/Could not verify the Run inventory/)).toHaveTextContent('offline')
    expect(screen.getByRole('button', { name: 'Create isolated Run' })).toBeDisabled()
    expect(api.createEmptyRunContainer).toHaveBeenCalledTimes(1)
    await userEvent.click(screen.getByRole('button', { name: 'Check saved Runs for this name' }))
    expect(await screen.findByText(/No Run with this name is in the current inventory/)).toBeVisible()
    expect(screen.getByRole('button', { name: 'Create isolated Run' })).toBeEnabled()
  })

  it('rejects malformed or ambiguous inventory data instead of authorizing an unsafe retry', async () => {
    api.createEmptyRunContainer.mockRejectedValueOnce(new Error('unknown outcome'))
    api.listRunContainers.mockResolvedValueOnce({ run_containers: [{
      display_name: 'My test Run', run_id: ' '
    }] })
    renderPage()
    await userEvent.type(screen.getByLabelText('Unique Run name'), 'My test Run')
    await userEvent.click(screen.getByRole('button', { name: 'Create isolated Run' }))
    await userEvent.click(await screen.findByRole('button', { name: 'Check saved Runs for this name' }))
    expect(await screen.findByText(/Invalid Run inventory/)).toBeVisible()
    expect(screen.getByRole('button', { name: 'Create isolated Run' })).toBeDisabled()
    expect(api.createEmptyRunContainer).toHaveBeenCalledTimes(1)
  })

  it('ignores unrelated inventory rows and does not infer ownership of their Run IDs', async () => {
    api.createEmptyRunContainer.mockRejectedValueOnce(new Error('timeout'))
    api.listRunContainers.mockResolvedValueOnce({ run_containers: [{
      run_id: 'other', display_name: 'Other name', storage_kind: 'custom_local', read_only: false
    }] })
    renderPage()
    await userEvent.type(screen.getByLabelText('Unique Run name'), 'My test Run')
    await userEvent.click(screen.getByRole('button', { name: 'Create isolated Run' }))
    await userEvent.click(await screen.findByRole('button', { name: 'Check saved Runs for this name' }))
    expect(await screen.findByText(/No Run with this name is in the current inventory/)).toBeVisible()
    expect(screen.queryByRole('link', { name: 'Open Run with this name' })).toBeNull()
    expect(localStorage.getItem('beta_engine:last_run_id')).toBeNull()
  })

  it('does not issue duplicate inventory checks when its check is already in flight', async () => {
    let resolve!: (value: unknown) => void
    api.createEmptyRunContainer.mockRejectedValueOnce(new Error('timeout'))
    api.listRunContainers.mockImplementationOnce(() => new Promise(done => { resolve = done }))
    renderPage()
    await userEvent.type(screen.getByLabelText('Unique Run name'), 'My test Run')
    await userEvent.click(screen.getByRole('button', { name: 'Create isolated Run' }))
    const check = await screen.findByRole('button', { name: 'Check saved Runs for this name' })
    fireEvent.click(check)
    fireEvent.click(check)
    expect(api.listRunContainers).toHaveBeenCalledTimes(1)
    expect(screen.getByRole('button', { name: 'Create isolated Run' })).toBeDisabled()
    resolve({ run_containers: [] })
    expect(await screen.findByText(/No Run with this name is in the current inventory/)).toBeVisible()
  })

  it('does not trust an invalid server-confirmed ID or save it in local navigation hints', async () => {
    api.createEmptyRunContainer.mockResolvedValueOnce({
      run_id: ' ', display_name: 'My test Run', read_only: false,
      storage_kind: 'custom_local'
    })
    renderPage()
    await userEvent.type(screen.getByLabelText('Unique Run name'), 'My test Run')
    await userEvent.click(screen.getByRole('button', { name: 'Create isolated Run' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('unexpected Run identity')
    expect(screen.getByRole('button', { name: 'Create isolated Run' })).toBeDisabled()
    expect(screen.getByRole('button', { name: 'Check saved Runs for this name' })).toBeVisible()
    expect(localStorage.getItem('beta_engine:last_run_id')).toBeNull()
    expect(navigate).not.toHaveBeenCalled()
  })

  it('rejects a malformed unrelated inventory row instead of falsely concluding no matching Run exists', async () => {
    api.createEmptyRunContainer.mockRejectedValueOnce(new Error('timeout'))
    api.listRunContainers.mockResolvedValueOnce({ run_containers: [
      null,
      { run_id: 'other', display_name: 'Different Run' }
    ] })
    renderPage()
    await userEvent.type(screen.getByLabelText('Unique Run name'), 'My test Run')
    await userEvent.click(screen.getByRole('button', { name: 'Create isolated Run' }))
    expect(screen.getByLabelText('Unique Run name')).toBeDisabled()
    await userEvent.click(await screen.findByRole('button', { name: 'Check saved Runs for this name' }))
    expect(await screen.findByText(/Invalid Run inventory/)).toBeVisible()
    expect(screen.getByRole('button', { name: 'Create isolated Run' })).toBeDisabled()
  })

  it('rejects multiple exact-name Run matches as ambiguous without guessing which was created', async () => {
    api.createEmptyRunContainer.mockRejectedValueOnce(new Error('request timed out'))
    api.listRunContainers.mockResolvedValueOnce({ run_containers: [
      { run_id: 'one', display_name: 'My test Run' },
      { run_id: 'two', display_name: 'My test Run' }
    ] })
    renderPage()
    await userEvent.type(screen.getByLabelText('Unique Run name'), 'My test Run')
    await userEvent.click(screen.getByRole('button', { name: 'Create isolated Run' }))
    await userEvent.click(await screen.findByRole('button', { name: 'Check saved Runs for this name' }))
    expect(await screen.findByText(/Ambiguous Run inventory/)).toBeVisible()
    expect(screen.queryByRole('link', { name: 'Open Run with this name' })).toBeNull()
    expect(screen.getByRole('button', { name: 'Create isolated Run' })).toBeDisabled()
  })
})
