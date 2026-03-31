import type { ReactNode } from 'react'

type SectionCardProps = {
  title: string
  children: ReactNode
}

type MetadataField = {
  label: string
  value: ReactNode
}

type SummaryItem = {
  label: string
  value: ReactNode
}

type ContextItem = {
  label: string
  value: ReactNode
}

type JsonPayloadProps = {
  title: string
  emptyText: string
  payload: unknown
}

type ActionStatusProps = {
  loadingText?: string
  successText?: string
  errorText?: string
  isLoading?: boolean
}

export function PageIntro({
  title,
  subtitle,
  meta
}: {
  title: string
  subtitle?: string
  meta?: string
}): JSX.Element {
  return (
    <header className="page-intro">
      <h2>{title}</h2>
      {subtitle ? <p className="subtitle">{subtitle}</p> : null}
      {meta ? <p className="status">{meta}</p> : null}
    </header>
  )
}

export function RunScopedHeader({ title, runId, subtitle }: { title: string; runId: string; subtitle?: string }): JSX.Element {
  return <PageIntro title={title} subtitle={subtitle} meta={`Run: ${runId || 'unknown'}`} />
}

export function CurrentContextStrip({ items }: { items: ContextItem[] }): JSX.Element | null {
  if (items.length === 0) return null

  return (
    <ul className="context-strip" aria-label="Current context">
      {items.map((item) => (
        <li key={item.label} className="context-strip__item">
          <span className="context-strip__label">{item.label}</span>
          <strong className="context-strip__value">{item.value}</strong>
        </li>
      ))}
    </ul>
  )
}

export function MetadataList({ items }: { items: MetadataField[] }): JSX.Element {
  return (
    <dl className="kv-grid">
      {items.map((item) => (
        <div key={item.label}>
          <dt>{item.label}</dt>
          <dd>{item.value}</dd>
        </div>
      ))}
    </dl>
  )
}

export function SummaryPills({ items }: { items: SummaryItem[] }): JSX.Element {
  return (
    <ul className="summary-pill-list" aria-label="Summary highlights">
      {items.map((item) => (
        <li key={item.label} className="summary-pill">
          <span className="summary-pill__label">{item.label}</span>
          <strong className="summary-pill__value">{item.value}</strong>
        </li>
      ))}
    </ul>
  )
}

export function SectionCard({ title, children }: SectionCardProps): JSX.Element {
  return (
    <article className="panel nested-panel">
      <h3>{title}</h3>
      {children}
    </article>
  )
}

export function JsonPayloadBlock({ title, emptyText, payload }: JsonPayloadProps): JSX.Element {
  return (
    <>
      <h4>{title}</h4>
      {payload ? <pre className="json-block">{JSON.stringify(payload, null, 2)}</pre> : <p className="status">{emptyText}</p>}
    </>
  )
}

export function EmptyState({ message }: { message: string }): JSX.Element {
  return <p className="status">{message}</p>
}

export function ActionStatusBlock({ isLoading, loadingText, successText, errorText }: ActionStatusProps): JSX.Element | null {
  if (isLoading && loadingText) return <p className="status">{loadingText}</p>
  if (errorText) return <p className="error">{errorText}</p>
  if (successText) return <p className="status">{successText}</p>
  return null
}
