import type { ReactNode } from 'react'
import { Link } from 'react-router-dom'

export type ViewerMetadataItem = {
  label: string
  value: ReactNode
}

export type ViewerLandingLink = {
  label: string
  to: string
}

export type ViewerDeferredFeature = {
  title: string
  description: ReactNode
}

type ViewerActiveRunCardProps = {
  ariaLabel?: string
  kicker?: string
  title: string
  children: ReactNode
}

export function ViewerActiveRunCard({ ariaLabel, kicker = 'Active Viewer run', title, children }: ViewerActiveRunCardProps): JSX.Element {
  return (
    <article className="viewer-active-run-card" aria-label={ariaLabel}>
      <span className="eyebrow">{kicker}</span>
      <h3>{title}</h3>
      {children}
    </article>
  )
}

type ViewerSectionCardProps = {
  kicker?: string
  title: string
  variant?: 'standard' | 'hero'
  children: ReactNode
}

export function ViewerSectionCard({ kicker, title, variant = 'standard', children }: ViewerSectionCardProps): JSX.Element {
  return (
    <article className={`viewer-home-card viewer-home-card--${variant}`}>
      {kicker ? <span className="eyebrow">{kicker}</span> : null}
      <h3>{title}</h3>
      {children}
    </article>
  )
}

export function ViewerLandingGrid({ children }: { children: ReactNode }): JSX.Element {
  return <div className="viewer-home-grid viewer-landing-grid">{children}</div>
}

type ViewerMetadataListProps = {
  items: ViewerMetadataItem[]
  ariaLabel?: string
  className?: string
}

export function ViewerMetadataList({ items, ariaLabel, className = 'metadata-list' }: ViewerMetadataListProps): JSX.Element {
  return (
    <dl className={className} aria-label={ariaLabel}>
      {items.map((item) => (
        <ViewerMetadataListItem key={item.label} label={item.label} value={item.value} />
      ))}
    </dl>
  )
}

export function ViewerMetadataListItem({ label, value }: ViewerMetadataItem): JSX.Element {
  return (
    <div>
      <dt>{label}</dt>
      <dd>{value}</dd>
    </div>
  )
}

type ViewerStatusMessageProps = {
  children: ReactNode
  tone?: 'status' | 'empty'
}

export function ViewerStatusMessage({ children, tone = 'status' }: ViewerStatusMessageProps): JSX.Element {
  return <p className={tone === 'empty' ? 'empty-state viewer-status-message viewer-status-message--empty' : 'status viewer-status-message'}>{children}</p>
}

export function ViewerEmptyState({ children }: { children: ReactNode }): JSX.Element {
  return <ViewerStatusMessage tone="empty">{children}</ViewerStatusMessage>
}

type ViewerActiveRunLinksProps = {
  links: ViewerLandingLink[]
  layout?: 'inline' | 'grid'
}

export function ViewerActiveRunLinks({ links, layout = 'inline' }: ViewerActiveRunLinksProps): JSX.Element | null {
  if (!links.length) return null

  if (layout === 'grid') {
    return (
      <div className="viewer-active-run-link-grid">
        {links.map((link) => (
          <Link key={`${link.label}:${link.to}`} className="viewer-active-run-link" to={link.to}>
            {link.label}
          </Link>
        ))}
      </div>
    )
  }

  return (
    <p className="viewer-active-run-actions">
      {links.map((link, index) => (
        <span key={`${link.label}:${link.to}`} className="viewer-active-run-action-item">
          {index > 0 ? ' ' : null}
          <Link className="viewer-active-run-link" to={link.to}>
            {link.label}
          </Link>
        </span>
      ))}
    </p>
  )
}

type ViewerDeferredFeatureListProps = {
  title?: string
  label: string
  features: ViewerDeferredFeature[]
}

export function ViewerDeferredFeatureList({ title, label, features }: ViewerDeferredFeatureListProps): JSX.Element | null {
  if (!features.length) return null

  return (
    <div className="viewer-deferred-feature-block">
      {title ? <h4>{title}</h4> : null}
      <ul className="viewer-home-list viewer-deferred-feature-list" aria-label={label}>
        {features.map((feature) => (
          <li key={feature.title}>
            <strong>{feature.title}</strong>: {feature.description}
          </li>
        ))}
      </ul>
    </div>
  )
}

type ViewerSampleListProps<T> = {
  title: string
  label: string
  items: T[]
  getKey: (item: T) => string
  renderItem: (item: T) => ReactNode
  limit?: number
}

export function ViewerSampleList<T>({ title, label, items, getKey, renderItem, limit = 5 }: ViewerSampleListProps<T>): JSX.Element | null {
  const sampleItems = items.slice(0, limit)
  if (!sampleItems.length) return null

  return (
    <div className="viewer-sample-list-block">
      <h4>{title}</h4>
      <ul className="viewer-home-list viewer-sample-list" aria-label={label}>
        {sampleItems.map((item) => (
          <li key={getKey(item)}>{renderItem(item)}</li>
        ))}
      </ul>
    </div>
  )
}
