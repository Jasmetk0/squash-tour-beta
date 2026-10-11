import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { ActionStatusBlock, CompactSummaryCard, CurrentContextStrip, EmptyState, JsonPayloadBlock, MetadataList, PageIntro, PreviewListCard } from './RunScopedUi'

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
        <CompactSummaryCard items={[{ label: 'Seed', value: 42 }, { label: 'Progress', value: '3 / 12' }]} />
        <EmptyState message="Nothing here yet" />
      </>
    )

    expect(screen.getByRole('heading', { name: 'Run detail' })).toBeInTheDocument()
    expect(screen.getByText('Subtitle')).toBeInTheDocument()
    expect(screen.getByText('Run: run-a')).toBeInTheDocument()
    expect(screen.getByText('Season')).toBeInTheDocument()
    expect(screen.getByText('2027')).toBeInTheDocument()
    expect(screen.getByText('Seed')).toBeInTheDocument()
    expect(screen.getByText('42')).toBeInTheDocument()
    expect(screen.getByText('3 / 12')).toBeInTheDocument()
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

  it('renders preview list card loading, items, and empty states', () => {
    const { rerender } = render(
      <PreviewListCard
        title="Recent events"
        isLoading
        loadingText="Loading recent events..."
        items={[]}
        emptyText="No events"
        listAriaLabel="Recent events preview"
        getKey={(item) => String(item)}
        renderItem={(item) => <span>{String(item)}</span>}
        viewAllLink={<a href="/runs/run-a/events">View all events</a>}
      />
    )

    expect(screen.getByText('Loading recent events...')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'View all events' })).toHaveAttribute('href', '/runs/run-a/events')

    rerender(
      <PreviewListCard
        title="Recent events"
        isLoading={false}
        loadingText="Loading recent events..."
        items={['E3', 'E1']}
        emptyText="No events"
        listAriaLabel="Recent events preview"
        getKey={(item) => item}
        renderItem={(item) => <span>{item}</span>}
        viewAllLink={<a href="/runs/run-a/events">View all events</a>}
      />
    )

    expect(screen.getByRole('list', { name: 'Recent events preview' })).toBeInTheDocument()
    expect(screen.getByText('E3')).toBeInTheDocument()
    expect(screen.getByText('E1')).toBeInTheDocument()

    rerender(
      <PreviewListCard
        title="Recent events"
        isLoading={false}
        loadingText="Loading recent events..."
        items={[]}
        emptyText="No events"
        listAriaLabel="Recent events preview"
        getKey={(item) => String(item)}
        renderItem={(item) => <span>{String(item)}</span>}
        viewAllLink={<a href="/runs/run-a/events">View all events</a>}
      />
    )

    expect(screen.getByText('No events')).toBeInTheDocument()
  })
})
