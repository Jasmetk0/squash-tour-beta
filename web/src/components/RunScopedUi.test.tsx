import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { ActionStatusBlock, JsonPayloadBlock } from './RunScopedUi'

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
})
