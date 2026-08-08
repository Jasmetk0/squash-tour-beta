export type AppShellMode = 'admin' | 'viewer' | 'landing'

export type AdminScope =
  | { kind: 'global' }
  | { kind: 'run'; runId: string }

export function readAppShellMode(pathname: string): AppShellMode {
  if (pathname.startsWith('/admin')) return 'admin'
  if (pathname.startsWith('/viewer')) return 'viewer'
  return 'landing'
}

export function readAppShellRunId(pathname: string, paramRunId?: string): string | undefined {
  if (paramRunId) return paramRunId
  const match = pathname.match(/^\/(?:admin|viewer)\/runs\/([^/]+)/)
  if (match?.[1] === 'new') return undefined
  return match?.[1]
}

export function resolveAdminScope(pathname: string): AdminScope {
  const match = pathname.match(/^\/admin\/runs\/([^/]+)(?:\/|$)/)
  if (!match || match[1] === 'new') return { kind: 'global' }
  return { kind: 'run', runId: match[1] }
}

export function appShellTitleForMode(mode: AppShellMode): string {
  return mode === 'viewer' ? 'MSA Squash' : 'Squash Tour Beta Engine'
}

export function appShellSubtitleForMode(mode: AppShellMode): string {
  if (mode === 'admin') return 'Admin / Engine Mode'
  if (mode === 'viewer') return 'Viewer / MSA Website Mode'
  return 'Mode selection'
}

export function appShellClassNameForMode(mode: AppShellMode): string {
  return `app-shell app-shell--${mode}`
}
