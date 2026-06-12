import { render, screen, within } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it } from 'vitest'

import { RacePreviewTable } from './RacePreviewTable'
import type { RacePreviewRow } from './racePayload'

const forbiddenLabels = /Simulate|Generate|Persist|Apply|Execute|Delete|Edit|Import|Rollover|Rebuild|Override|Save changes|Commit|Regenerate|Repair|Merge|Overwrite/i

function renderTable(rows: RacePreviewRow[], runId = 'viewer-run-1'): void {
  render(
    <MemoryRouter>
      <RacePreviewTable rows={rows} runId={runId} />
    </MemoryRouter>
  )
}

describe('RacePreviewTable', () => {
  it('renders provided safe rows as a read-only Viewer table', () => {
    renderTable([
      {
        rank: 1,
        playerId: 'R1',
        playerName: 'Mostafa Asal',
        country: 'EGY',
        racePoints: 9000,
        tournamentsCounted: 8,
        qualificationStatus: 'Qualified',
        nextMaxPoints: 1200
      }
    ])

    const table = screen.getByRole('table', { name: 'Top 10 race preview table' })
    expect(within(table).getByText('Rank')).toBeInTheDocument()
    expect(within(table).getByText('1')).toBeInTheDocument()
    expect(within(table).getByRole('link', { name: 'Mostafa Asal' })).toHaveAttribute('href', '/viewer/runs/viewer-run-1/players/R1/career')
    expect(within(table).getByRole('link', { name: 'EGY' })).toHaveAttribute('href', '/viewer/runs/viewer-run-1/countries/EGY')
    expect(within(table).getByText('9000')).toBeInTheDocument()
    expect(within(table).getByText('8')).toBeInTheDocument()
    expect(within(table).getByText('Qualified')).toBeInTheDocument()
    expect(within(table).getByText('1200')).toBeInTheDocument()
    expect(screen.queryByRole('button')).not.toBeInTheDocument()
    expect(screen.queryByRole('link', { name: forbiddenLabels })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: forbiddenLabels })).not.toBeInTheDocument()
    screen.getAllByRole('link').forEach((link) => expect(link).toHaveAttribute('href', expect.stringMatching(/^\/viewer\//)))
  })

  it('does not expose Admin links or mutation controls', () => {
    renderTable([{ rank: 1, playerId: 'R1', playerName: 'Safe Race Player', country: null, racePoints: 100, tournamentsCounted: null, qualificationStatus: null, nextMaxPoints: null }])

    expect(screen.queryByRole('link', { name: /Admin/i })).not.toBeInTheDocument()
    expect(screen.queryByRole('link', { name: forbiddenLabels })).not.toBeInTheDocument()
    expect(screen.queryByRole('button')).not.toBeInTheDocument()
  })

  it('does not render object values as [object Object]', () => {
    renderTable([
      {
        rank: { value: 1 },
        playerId: { value: 'R1' },
        playerName: { label: 'Unsafe Race Player' },
        country: { code: 'EGY' },
        racePoints: { value: 100 },
        tournamentsCounted: { value: 8 },
        qualificationStatus: { label: 'Qualified' },
        nextMaxPoints: { value: 1200 }
      } as unknown as RacePreviewRow
    ])

    expect(screen.queryByText('[object Object]')).not.toBeInTheDocument()
    expect(screen.getAllByText('—').length).toBeGreaterThan(0)
    expect(screen.queryByRole('link')).not.toBeInTheDocument()
  })

  it('handles empty rows with an empty table body so the parent can own empty state copy', () => {
    renderTable([])

    const table = screen.getByRole('table', { name: 'Top 10 race preview table' })
    expect(within(table).getAllByRole('row')).toHaveLength(1)
    expect(screen.queryByText('[object Object]')).not.toBeInTheDocument()
  })
})
