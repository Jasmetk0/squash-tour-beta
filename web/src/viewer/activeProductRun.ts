export const VIEWER_ACTIVE_PRODUCT_RUN_STORAGE_KEY = 'beta_engine:viewer_active_product_run_id'
export const VIEWER_ACTIVE_PRODUCT_RUN_CHANGED_EVENT = 'beta_engine:viewer_active_product_run_changed'

function notify(): void {
  if (typeof window !== 'undefined') window.dispatchEvent(new Event(VIEWER_ACTIVE_PRODUCT_RUN_CHANGED_EVENT))
}

export function readViewerActiveProductRunId(): string | null {
  if (typeof window === 'undefined') return null
  try {
    const value = window.localStorage.getItem(VIEWER_ACTIVE_PRODUCT_RUN_STORAGE_KEY)?.trim()
    return value || null
  } catch { return null }
}

export function writeViewerActiveProductRunId(productRunId: string): void {
  if (typeof window === 'undefined') return
  const value = productRunId.trim()
  if (!value) return clearViewerActiveProductRunId()
  try { window.localStorage.setItem(VIEWER_ACTIVE_PRODUCT_RUN_STORAGE_KEY, value) } catch { /* storage is optional */ }
  notify()
}

export function clearViewerActiveProductRunId(): void {
  if (typeof window === 'undefined') return
  try { window.localStorage.removeItem(VIEWER_ACTIVE_PRODUCT_RUN_STORAGE_KEY) } catch { /* storage is optional */ }
  notify()
}
