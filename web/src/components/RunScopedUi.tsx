type SectionCardProps = {
  title: string
  children: JSX.Element | JSX.Element[] | null
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

export function RunScopedHeader({ title, runId }: { title: string; runId: string }): JSX.Element {
  return (
    <>
      <h2>{title}</h2>
      <p className="status">Run: {runId || 'unknown'}</p>
    </>
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

export function ActionStatusBlock({ isLoading, loadingText, successText, errorText }: ActionStatusProps): JSX.Element | null {
  if (isLoading && loadingText) return <p className="status">{loadingText}</p>
  if (errorText) return <p className="error">{errorText}</p>
  if (successText) return <p className="status">{successText}</p>
  return null
}
