import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { ActionStatusBlock, CurrentContextStrip, EmptyState, JsonPayloadBlock, MetadataList, PageIntro } from './RunScopedUi'

describe('RunScopedUi helpers', () => {
  it('renders error state ahead of success state for action status block', () => {
    render(<ActionStatusBlock errorText="Action failed" successText="Action succeeded" />)
    expect(screen.getByText('Action failed')).toHaveClass('error')
  })

  it('renders JSON payload and fallback empty state', () => {
    const { rerender } = render(<JsonPayloadBlock title="Payload" payload={{ ok: true }} emptyText="No data" />)
    expect(screen.getByText('Payload')).toBeInTheDocument()
    expect(screen.getByText(/"ok": true/)).toBeInTheDocument()

    rerender(<JsonPayloadBlock title="Payload" payload={null} emptyText="No data" />)
    expect(screen.getByText('No data')).toBeInTheDocument()
  })

  it('renders page intro and metadata list helpers', () => {
    render(
      <>
        <PageIntro title="Run detail" subtitle="Subtitle" meta="Run: run-a" />
        <MetadataList items={[{ label: 'Season', value: 2027 }]} />
        <EmptyState message="Nothing here yet" />
      </>
    )

    expect(screen.getByRole('heading', { name: 'Run detail' })).toBeInTheDocument()
    expect(screen.getByText('Subtitle')).toBeInTheDocument()
    expect(screen.getByText('Run: run-a')).toBeInTheDocument()
    expect(screen.getByText('Season')).toBeInTheDocument()
    expect(screen.getByText('2027')).toBeInTheDocument()
    expect(screen.getByText('Nothing here yet')).toBeInTheDocument()
  })

  it('renders compact current context strip values', () => {
    render(<CurrentContextStrip items={[{ label: 'Run', value: 'run-a' }, { label: 'Season', value: 2028 }]} />)

    expect(screen.getByRole('list', { name: 'Current context' })).toBeInTheDocument()
    expect(screen.getByText('Run')).toBeInTheDocument()
    expect(screen.getByText('run-a')).toBeInTheDocument()
    expect(screen.getByText('Season')).toBeInTheDocument()
    expect(screen.getByText('2028')).toBeInTheDocument()
  })
})
