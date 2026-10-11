/**
 * Synchronous safeguard for imperative Admin context changes.
 * BrowserRouter is not a data router; keep the guard at each authoritative
 * context transition rather than relying on a data-router-only blocker.
 */
type ContextKind = 'Run' | 'Branch'
type ApprovedLink = { runId: string; branchId: string; href: string }
let approvedLink: ApprovedLink | null = null

export function hasUnsavedRunChanges(): boolean {
  return document.querySelector('.app-shell--admin')?.getAttribute('data-run-form-edited') === 'true'
}

/** Called only after a genuine, confirmed internal link click. One transition only. */
export function allowConfirmedBranchLink(runId: string, url: URL): void {
  const branchId = url.searchParams.get('branch')
  if (!branchId || url.pathname !== '/admin/runs/' + encodeURIComponent(runId) &&
      !url.pathname.startsWith('/admin/runs/' + encodeURIComponent(runId) + '/')) return
  approvedLink = {runId, branchId, href: url.pathname + url.search}
}

export function confirmAdminContextChange(kind: ContextKind, runId?: string, branchId?: string): boolean {
  if (!hasUnsavedRunChanges()) {
    approvedLink = null
    return true
  }
  // A link which the Run guard already confirmed must not double-prompt when
  // the location's ?branch=... is resolved by AdminBranchProvider afterward.
  if (kind === 'Branch' && approvedLink &&
      approvedLink.runId === runId && approvedLink.branchId === branchId &&
      approvedLink.href === window.location.pathname + window.location.search) {
    approvedLink = null
    return true
  }
  approvedLink = null
  return window.confirm(
    'This Run has unapplied form edits or an unsaved Working Draft. Switch ' +
    kind + '? Save or discard your changes first.'
  )
}
