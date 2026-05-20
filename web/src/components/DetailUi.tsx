import type { ReactNode } from 'react'

type DetailFieldProps = {
  label: string
  value: ReactNode
}

type DetailFieldGridProps = {
  fields: DetailFieldProps[]
  emptyFallback?: ReactNode
}

type DetailListProps = {
  items: ReactNode[]
  emptyLabel: string
}

export function DetailField({ label, value }: DetailFieldProps): JSX.Element {
  return (
    <li>
      {label}: {value}
    </li>
  )
}

export function DetailFieldGrid({ fields, emptyFallback = '—' }: DetailFieldGridProps): JSX.Element {
  return (
    <ul className="dashboard-help-list">
      {fields.length > 0
        ? fields.map((field) => <DetailField key={field.label} label={field.label} value={field.value} />)
        : <li>{emptyFallback}</li>}
    </ul>
  )
}

export function DetailList({ items, emptyLabel }: DetailListProps): JSX.Element {
  return (
    <ul className="dashboard-help-list">
      {items.length > 0 ? items.map((item, index) => <li key={`detail-item-${index}`}>{item}</li>) : <li>{emptyLabel}</li>}
    </ul>
  )
}
