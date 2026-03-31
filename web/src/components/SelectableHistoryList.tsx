import type { ReactNode } from 'react'

type SelectableHistoryListProps<T> = {
  items: readonly T[]
  getKey: (item: T) => string
  getLabel: (item: T) => ReactNode
  getSubLabel?: (item: T) => ReactNode
  isSelected: (item: T) => boolean
  onSelect: (item: T) => void
  ariaLabel: string
}

export function SelectableHistoryList<T>({
  items,
  getKey,
  getLabel,
  getSubLabel,
  isSelected,
  onSelect,
  ariaLabel
}: SelectableHistoryListProps<T>): JSX.Element {
  return (
    <ul className="history-list" aria-label={ariaLabel}>
      {items.map((item) => {
        const selected = isSelected(item)
        const subLabel = getSubLabel?.(item)

        return (
          <li key={getKey(item)}>
            <button
              type="button"
              className={`history-list-item${selected ? ' is-selected' : ''}`}
              aria-current={selected ? 'true' : undefined}
              onClick={() => onSelect(item)}
            >
              <span className="history-list-item__title">{getLabel(item)}</span>
              {subLabel ? <span className="history-list-item__meta">{subLabel}</span> : null}
            </button>
          </li>
        )
      })}
    </ul>
  )
}
