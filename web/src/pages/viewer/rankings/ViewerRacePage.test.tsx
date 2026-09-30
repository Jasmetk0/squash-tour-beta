import { screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import {
  clearViewerStorage,
  expectNoForbiddenViewerActions,
  renderWithViewerProviders,
  setViewerActiveProductRunId
} from '../../../test/viewerTestUtils'
import { ViewerRacePage, ViewerRunRacePage } from './ViewerRacePage'

const api = vi.hoisted(() => ({
  getViewerFinalsRace: vi.fn()
}))

vi.mock('../../../api/client', () => api)

const publishedRace = {
  schema_version: 'viewer_finals_race_history.v1' as const,
  product_run_id: 'run alpha',
  viewer_branch_id: 'viewer-branch',
  latest_target_season_index: 4,
  publications: [
    {
      schema_version: 'viewer_finals_race_publication.v1' as const,
      product_run_id: 'run alpha',
      viewer_branch_id: 'viewer-branch',
      target_season_index: 4,
      cutoff_season_index: 4,
      cutoff_week: 55,
      best_n: 2,
      selection_published: true,
      finals_event_id: 'FINALS-2004',
      rows: [
        {
          rank: 1,
          player_id: 'P1',
          race_points: 125,
          tournaments_counted: 2,
          finals_selected: true,
          finals_seed: 1,
          qualification_source: 'race' as const,
          counted_results: [
            { event_id: 'E1', completed_season_index: 4, completed_week: 10, race_points: 100 },
            { event_id: 'E2', completed_season_index: 4, completed_week: 20, race_points: 25 }
          ]
        },
        {
          rank: 2,
          player_id: 'P2',
          race_points: 90,
          tournaments_counted: 1,
          finals_selected: false,
          finals_seed: null,
          qualification_source: null,
          counted_results: [
            { event_id: 'E1', completed_season_index: 4, completed_week: 10, race_points: 90 }
          ]
        },
        {
          rank: 3,
          player_id: 'P3',
          race_points: 80,
          tournaments_counted: 1,
          finals_selected: true,
          finals_seed: 2,
          qualification_source: 'direct_entry' as const,
          counted_results: [
            { event_id: 'E3', completed_season_index: 4, completed_week: 30, race_points: 80 }
          ]
        }
      ]
    }
  ]
}

describe('ViewerRacePage', () => {
  beforeEach(() => {
    clearViewerStorage()
    vi.clearAllMocks()
    api.getViewerFinalsRace.mockResolvedValue({
      schema_version: 'viewer_finals_race_history.v1',
      product_run_id: 'run alpha',
      viewer_branch_id: 'viewer-branch',
      latest_target_season_index: null,
      publications: []
    })
  })

  it('renders the no-Product-Run canonical landing without legacy Race reads', () => {
    renderWithViewerProviders(<ViewerRacePage />)

    expect(screen.getByRole('heading', { level: 2, name: 'Race to Finals' })).toBeInTheDocument()
    expect(screen.getByText('Select a Product Run before opening Race to Finals.')).toBeInTheDocument()
    expect(api.getViewerFinalsRace).not.toHaveBeenCalled()
    expectNoForbiddenViewerActions()
  })

  it('renders canonical saved Race standings and qualification markers', async () => {
    setViewerActiveProductRunId('run alpha')
    api.getViewerFinalsRace.mockResolvedValue(publishedRace)

    renderWithViewerProviders(<ViewerRacePage />)

    const table = await screen.findByRole('table', { name: 'Canonical Finals Race standings' })
    expect(api.getViewerFinalsRace).toHaveBeenCalledWith('run alpha')
    expect(table).toHaveTextContent('P1')
    expect(table).toHaveTextContent('125')
    expect(table).toHaveTextContent('Race qualified · seed 1')
    expect(table).toHaveTextContent('P2')
    expect(table).toHaveTextContent('Not selected')
    expect(table).toHaveTextContent('Direct entry · seed 2')
    expect(table).toHaveTextContent('E1: 100 pts (W10)')
    expect(screen.getByRole('list', { name: 'Canonical Finals Race publication history' })).toHaveTextContent('2004/05')
    expect(screen.getByRole('link', { name: 'Open run-scoped Race' })).toHaveAttribute(
      'href',
      '/viewer/runs/run%20alpha/race'
    )
    expect(screen.getByRole('link', { name: 'P1' })).toHaveAttribute(
      'href',
      '/viewer/runs/run%20alpha/players/P1/career'
    )
    expect(screen.queryByText(/snapshot sequence/i)).not.toBeInTheDocument()
    expectNoForbiddenViewerActions()
  })

  it('renders selection pending distinctly from a non-selected player', async () => {
    setViewerActiveProductRunId('run alpha')
    api.getViewerFinalsRace.mockResolvedValue({
      ...publishedRace,
      publications: [
        {
          ...publishedRace.publications[0],
          selection_published: false,
          finals_event_id: null,
          rows: publishedRace.publications[0].rows.map((row) => ({
            ...row,
            finals_selected: null,
            finals_seed: null,
            qualification_source: null
          }))
        }
      ]
    })

    renderWithViewerProviders(<ViewerRacePage />)

    const table = await screen.findByRole('table', { name: 'Canonical Finals Race standings' })
    expect(table).toHaveTextContent('Selection pending')
    expect(table).not.toHaveTextContent('Not selected')
  })

  it('uses the route Product Run for run-scoped canonical Race', async () => {
    api.getViewerFinalsRace.mockResolvedValue({
      ...publishedRace,
      product_run_id: 'run/one',
      publications: publishedRace.publications.map((publication) => ({
        ...publication,
        product_run_id: 'run/one'
      }))
    })

    renderWithViewerProviders(<ViewerRunRacePage />, {
      route: '/viewer/runs/run%2Fone/race'
    })

    expect(await screen.findByRole('table', { name: 'Canonical Finals Race standings' })).toBeInTheDocument()
    expect(api.getViewerFinalsRace).toHaveBeenCalledWith('run/one')
    expect(screen.queryByRole('link', { name: 'Open run-scoped Race' })).not.toBeInTheDocument()
    expectNoForbiddenViewerActions()
  })
})
