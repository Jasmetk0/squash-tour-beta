export const VIEWER_ACTIVE_RUN_STORAGE_KEY = 'beta_engine:viewer_active_run_id'
export const LAST_RUN_ID_STORAGE_KEY = 'beta_engine:last_run_id'
export const VIEWER_ACTIVE_RUN_CHANGED_EVENT = 'beta_engine:viewer_active_run_changed'

function notifyViewerActiveRunChanged(): void {
  if (typeof window === 'undefined') return
  window.dispatchEvent(new Event(VIEWER_ACTIVE_RUN_CHANGED_EVENT))
}

export function readViewerActiveRunId(): string | null {
  if (typeof window === 'undefined') return null

  try {
    return window.localStorage.getItem(VIEWER_ACTIVE_RUN_STORAGE_KEY)
  } catch {
    return null
  }
}

export function readLastRunId(): string | null {
  if (typeof window === 'undefined') return null

  try {
    return window.localStorage.getItem(LAST_RUN_ID_STORAGE_KEY)
  } catch {
    return null
  }
}

export function writeLastRunId(runId: string): void {
  if (typeof window === 'undefined') return
  const normalizedRunId = runId.trim()
  if (!normalizedRunId) return
  try {
    window.localStorage.setItem(LAST_RUN_ID_STORAGE_KEY, normalizedRunId)
  } catch {
    // Storage may be unavailable in restricted browser contexts; keep the app rendering.
  }
}

export function clearLastRunId(): void {
  if (typeof window === 'undefined') return

  try {
    window.localStorage.removeItem(LAST_RUN_ID_STORAGE_KEY)
  } catch {
    // Storage may be unavailable in restricted browser contexts; keep the app rendering.
  }
}

export function writeViewerActiveRunId(runId: string): void {
  if (typeof window === 'undefined') return
  const normalizedRunId = runId.trim()
  if (!normalizedRunId) {
    clearViewerActiveRunId()
    return
  }
  try {
    window.localStorage.setItem(VIEWER_ACTIVE_RUN_STORAGE_KEY, normalizedRunId)
  } catch {
    // Storage may be unavailable in restricted browser contexts; keep the app rendering.
  }
  notifyViewerActiveRunChanged()
}

export function clearViewerActiveRunId(): void {
  if (typeof window === 'undefined') return
  try {
    window.localStorage.removeItem(VIEWER_ACTIVE_RUN_STORAGE_KEY)
  } catch {
    // Storage may be unavailable in restricted browser contexts; keep the app rendering.
  }
  notifyViewerActiveRunChanged()
}
