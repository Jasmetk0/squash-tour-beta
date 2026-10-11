import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'

import { SelectableHistoryList } from './SelectableHistoryList'

describe('SelectableHistoryList', () => {
  it('renders labels in provided order and updates selected state by callback', async () => {
    const user = userEvent.setup()
    const onSelect = vi.fn()
    const items = [
      { id: 'A', title: '2. A', meta: 'S2027 / W2' },
      { id: 'B', title: '1. B', meta: 'S2027 / W1' }
    ]

    const { rerender } = render(
      <SelectableHistoryList
        items={items}
        getKey={(item) => item.id}
        getLabel={(item) => item.title}
        getSubLabel={(item) => item.meta}
        isSelected={(item) => item.id === 'A'}
        onSelect={onSelect}
        ariaLabel="History test list"
      />
    )

    const rows = screen.getAllByRole('button')
    expect(rows[0]).toHaveTextContent('2. A')
    expect(rows[1]).toHaveTextContent('1. B')
    expect(rows[0]).toHaveClass('is-selected')

    await user.click(rows[1])
    expect(onSelect).toHaveBeenCalledWith(items[1])

    rerender(
      <SelectableHistoryList
        items={items}
        getKey={(item) => item.id}
        getLabel={(item) => item.title}
        getSubLabel={(item) => item.meta}
        isSelected={(item) => item.id === 'B'}
        onSelect={onSelect}
        ariaLabel="History test list"
      />
    )

    expect(screen.getByRole('button', { name: /1\. B/i })).toHaveClass('is-selected')
    expect(screen.getByRole('button', { name: /2\. A/i })).not.toHaveClass('is-selected')
  })
})
