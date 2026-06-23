import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it, vi } from 'vitest'

import App from '../App'
import * as api from '../api/client'

vi.mock('../api/client', () => ({
  getHealth: vi.fn(),
  createRun: vi.fn(),
  getRun: vi.fn(),
  getRunStatusSummary: vi.fn(),
  listRuns: vi.fn(),
  listCountries: vi.fn(),
  getCountriesMetadata: vi.fn(),
  getTournamentTemplatesMetadata: vi.fn(),
  listEvents: vi.fn(),
  getRunActivity: vi.fn(),
  getEvent: vi.fn(),
  listRankingSnapshots: vi.fn(),
  listRaceSnapshots: vi.fn(),
  getFinalsSummary: vi.fn(),
  getFinalsQualification: vi.fn(),
  getFinalsResult: vi.fn(),
  simulateWorldTourFinals: vi.fn(),
  getLatestRollover: vi.fn(),
  getRolloverBySeason: vi.fn(),
  getPlayerTransitions: vi.fn(),
  getNextSeasonPlayers: vi.fn(),
  rolloverNextSeason: vi.fn(),
  getRunSource: vi.fn(),
  getRunLineage: vi.fn(),
  getRunTalentPlan: vi.fn(),
  listGeneratedPlayersProvenance: vi.fn(),
  bootstrapNextSeason: vi.fn(),
  getViewerRankingTable: vi.fn(),
  getAdminRankingTable: vi.fn(),
  getAdminRankingSnapshot: vi.fn(),
  getAdminPointBreakdown: vi.fn(),
  getTalentClassSummary: vi.fn(),
  getSeasonRegistry: vi.fn(),
  getSeasonActivePlayers: vi.fn(),
  getSeasonCalendar: vi.fn(),
  getSeasonTemplates: vi.fn(),
  getSeasonTemplateSlotValidation: vi.fn(),
  getSeasonTemplateSlotValidationIssueCodes: vi.fn(),
  getSeasonTemplateSlotConflicts: vi.fn(),
  getSeasonTemplateSlotConflictCodes: vi.fn(),
  getSeasonCalendarValidation: vi.fn(),
  getSeasonCalendarValidationIssueCodes: vi.fn(),
  getCategories: vi.fn(),
  getTournaments: vi.fn(),
  getTourSeasonsValidation: vi.fn(),
  postSeasonBuilderPreflight: vi.fn(),
  postSeasonBuilderDryRunBuild: vi.fn(),
  postSeasonBuilderApplyCommandContract: vi.fn(),
  postSeasonBuilderApplyCreateOnlyReadiness: vi.fn(),
  postSeasonBuilderApplyCreateOnlyCommand: vi.fn(),
  validateFutureApplyRequestPreview: vi.fn(),
  ApiError: class ApiError extends Error { status: number; constructor(message: string, status: number) { super(message); this.status = status } }
}))

function renderSandbox(): void {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={['/admin/tour-seasons/season-templates/draft-sandbox']}>
        <App />
      </MemoryRouter>
    </QueryClientProvider>
  )
}

describe('SeasonTemplateDraftSandboxPage', () => {
  it('renders the route, local-only disclaimer, initial events, and planned copy/apply text', () => {
    renderSandbox()

    expect(screen.getByRole('heading', { name: 'Draft Template Sandbox' })).toBeInTheDocument()
    expect(screen.getByText('Local sandbox only — not persisted, not played, not visible in Viewer.')).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Default World Tour Skeleton Sandbox' })).toBeInTheDocument()
    expect(screen.getByText('Némarque Open')).toBeInTheDocument()
    expect(screen.getByText('Ameriga Open')).toBeInTheDocument()
    expect(screen.getByText('World Championship')).toBeInTheDocument()
    expect(screen.getByText('World Tour Finals')).toBeInTheDocument()
    expect(screen.getByText('Qualifying W5 · Main W6–W7')).toBeInTheDocument()
    expect(screen.getByText('Qualifying W43 · Main W44–W45')).toBeInTheDocument()
    expect(screen.getByText('Qualifying W48 · Main W49–W50')).toBeInTheDocument()
    expect(screen.getByText('Main W55')).toBeInTheDocument()
    expect(screen.getByText('Copy to canonical season — planned.')).toBeInTheDocument()
    expect(screen.getByText('Two-pane compare/copy workspace — planned.')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /copy|apply|create|save/i })).not.toBeInTheDocument()
  })

  it('uses the category catalog in the add form', () => {
    renderSandbox()

    const categorySelect = screen.getByLabelText('Category')
    expect(within(categorySelect).getByRole('option', { name: 'Diamond (DIAMOND)' })).toBeInTheDocument()
    expect(within(categorySelect).getByRole('option', { name: 'World Tour Finals (WORLD_TOUR_FINALS)' })).toBeInTheDocument()
  })

  it('adds valid events locally without calling backend API functions', async () => {
    const user = userEvent.setup()
    renderSandbox()

    await user.type(screen.getByLabelText('Name'), 'Cobalt Test Open')
    await user.selectOptions(screen.getByLabelText('Category'), 'COBALT')
    await user.type(screen.getByLabelText('weeks'), '12,13')
    await user.type(screen.getByLabelText('qualificationWeeks'), '11')
    await user.type(screen.getByLabelText('Notes (optional)'), 'local note')
    await user.click(screen.getByRole('button', { name: 'Add Local Draft Event' }))

    expect(screen.getByText('Cobalt Test Open')).toBeInTheDocument()
    expect(screen.getByText('COBALT')).toBeInTheDocument()
    expect(screen.getByText('Qualifying W11 · Main W12–W13')).toBeInTheDocument()
    expect(screen.getByText('local note')).toBeInTheDocument()
    expectNoBackendCalls()
  })

  it('shows validation errors for invalid and duplicate weeks without adding the event', async () => {
    const user = userEvent.setup()
    renderSandbox()

    await user.type(screen.getByLabelText('Name'), 'Invalid Week Open')
    await user.type(screen.getByLabelText('weeks'), '6,6,62')
    await user.type(screen.getByLabelText('qualificationWeeks'), 'abc')
    await user.click(screen.getByRole('button', { name: 'Add Local Draft Event' }))

    expect(screen.getByText('weeks: Week 6 is duplicated.')).toBeInTheDocument()
    expect(screen.getByText('weeks: Week 62 must be between 1 and 61.')).toBeInTheDocument()
    expect(screen.getByText('qualificationWeeks value at position 1 must be an integer.')).toBeInTheDocument()
    expect(screen.queryByText('Invalid Week Open')).not.toBeInTheDocument()
  })

  it('prevents locked deletion until a local unlock', async () => {
    const user = userEvent.setup()
    renderSandbox()

    const nemarqueRow = screen.getByText('Némarque Open').closest('tr') as HTMLElement
    expect(within(nemarqueRow).getByText('Locked')).toBeInTheDocument()
    expect(within(nemarqueRow).queryByRole('button', { name: 'Delete' })).not.toBeInTheDocument()

    await user.click(within(nemarqueRow).getByRole('button', { name: 'Unlock' }))
    const unlockedNemarqueRow = screen.getByText('Némarque Open').closest('tr') as HTMLElement
    expect(within(unlockedNemarqueRow).getByText('Unlocked')).toBeInTheDocument()
    await user.click(within(unlockedNemarqueRow).getByRole('button', { name: 'Delete' }))
    expect(screen.queryByText('Némarque Open')).not.toBeInTheDocument()
    expectNoBackendCalls()
  })
})

function expectNoBackendCalls(): void {
  for (const value of Object.values(api)) {
    if (vi.isMockFunction(value)) expect(value).not.toHaveBeenCalled()
  }
}
