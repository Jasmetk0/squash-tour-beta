import { render, screen, within } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it } from 'vitest'

import { RankingPreviewTable } from './RankingPreviewTable'
import type { RankingPreviewRow } from './rankingPayload'

const forbiddenLabels = /Simulate|Generate|Persist|Apply|Execute|Delete|Edit|Import|Rollover|Rebuild|Override|Save changes|Commit|Regenerate|Repair|Merge|Overwrite/i

function renderTable(rows: RankingPreviewRow[], runId = 'viewer-run-1'): void {
  render(
    <MemoryRouter>
      <RankingPreviewTable rows={rows} runId={runId} />
    </MemoryRouter>
  )
}

describe('RankingPreviewTable', () => {
  it('renders provided safe rows as a read-only Viewer table', () => {
    renderTable([
      {
        rank: 1,
        playerId: 'P1',
        playerName: 'Ali Farag',
        country: 'EGY',
        points: 12000,
        tournamentsCounted: 12,
        movement: '+1',
        previousRank: null
      }
    ])

    const table = screen.getByRole('table', { name: 'Top 10 ranking preview table' })
    expect(within(table).getByText('Rank')).toBeInTheDocument()
    expect(within(table).getByText('1')).toBeInTheDocument()
    expect(within(table).getByRole('link', { name: 'Ali Farag' })).toHaveAttribute('href', '/viewer/runs/viewer-run-1/players/P1/career')
    expect(within(table).getByRole('link', { name: 'EGY' })).toHaveAttribute('href', '/viewer/runs/viewer-run-1/countries/EGY')
    expect(within(table).getByText('12000')).toBeInTheDocument()
    expect(within(table).getByText('12')).toBeInTheDocument()
    expect(within(table).getByText('+1')).toBeInTheDocument()
    expect(screen.queryByRole('button')).not.toBeInTheDocument()
    expect(screen.queryByRole('link', { name: forbiddenLabels })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: forbiddenLabels })).not.toBeInTheDocument()
    screen.getAllByRole('link').forEach((link) => expect(link).toHaveAttribute('href', expect.stringMatching(/^\/viewer\//)))
  })

  it('encodes slash, hash, and space player/country IDs as Viewer-only links', () => {
    renderTable(
      [
        {
          rank: 1,
          playerId: 'P/1 #A',
          playerName: 'Encoded Player',
          country: 'CO/DE #1',
          points: 100,
          tournamentsCounted: 1,
          movement: null,
          previousRank: null
        }
      ],
      'run/alpha #1'
    )

    const playerHref = screen.getByRole('link', { name: 'Encoded Player' }).getAttribute('href')
    const countryHref = screen.getByRole('link', { name: 'CO/DE #1' }).getAttribute('href')

    expect(playerHref).toBe('/viewer/runs/run%2Falpha%20%231/players/P%2F1%20%23A/career')
    expect(countryHref).toBe('/viewer/runs/run%2Falpha%20%231/countries/CO%2FDE%20%231')
    for (const href of [playerHref, countryHref]) {
      expect(href).toMatch(/^\/viewer\//)
      expect(href).not.toMatch(/^\/admin(?:\/|$)/)
      expect(href).not.toContain('run/alpha #1')
      expect(href).not.toContain('#')
    }
    expect(playerHref).not.toContain('P/1 #A')
    expect(countryHref).not.toContain('CO/DE #1')
  })

  it('does not expose Admin links or mutation controls', () => {
    renderTable([{ rank: 1, playerId: 'P1', playerName: 'Safe Player', country: null, points: 100, tournamentsCounted: null, movement: null, previousRank: null }])

    expect(screen.queryByRole('link', { name: /Admin/i })).not.toBeInTheDocument()
    expect(screen.queryByRole('link', { name: forbiddenLabels })).not.toBeInTheDocument()
    expect(screen.queryByRole('button')).not.toBeInTheDocument()
  })

  it('does not create links or render [object Object] for object-derived player/country IDs', () => {
    renderTable([
      {
        rank: { value: 1 },
        playerId: { value: 'P1' },
        playerName: { label: 'Unsafe Player' },
        country: { code: 'EGY' },
        points: { value: 100 },
        tournamentsCounted: { value: 12 },
        movement: { label: '+1' },
        previousRank: { value: 2 }
      } as unknown as RankingPreviewRow
    ])

    expect(screen.queryByText('[object Object]')).not.toBeInTheDocument()
    expect(screen.getAllByText('—').length).toBeGreaterThan(0)
    expect(screen.queryByRole('link')).not.toBeInTheDocument()
  })

  it('handles empty rows with an empty table body so the parent can own empty state copy', () => {
    renderTable([])

    const table = screen.getByRole('table', { name: 'Top 10 ranking preview table' })
    expect(within(table).getAllByRole('row')).toHaveLength(1)
    expect(screen.queryByText('[object Object]')).not.toBeInTheDocument()
  })
})
