/** Personal Run-list presentation preferences only. No Run/Branch data is stored. */
export const RUN_LIST_VIEWS_KEY = 'squash-run-list-views.v1'
export const RUN_LIST_VIEWS_LIMIT = 24
const VERSION = 'run_list_views.v1'
const MAX_STORE_LENGTH = 16000

export type RunListVisibility = 'all' | 'editable' | 'protected'
export type SavedRunListView = {
  name: string
  query: string
  visibility: RunListVisibility
  hidden: boolean
}
export type RunListViewsRead = {
  status: 'ok' | 'invalid' | 'unsupported' | 'unavailable'
  items: SavedRunListView[]
}

export function isValidRunListView(value: unknown): value is SavedRunListView {
  if (!value || typeof value !== 'object' || Array.isArray(value)) return false
  const v = value as Record<string, unknown>
  return typeof v.name === 'string' && v.name.length > 0 && v.name.length <= 64
    && v.name.trim() === v.name && !/[\u0000-\u001f\u007f]/.test(v.name)
    && typeof v.query === 'string' && v.query.length <= 250
    && (v.visibility === 'all' || v.visibility === 'editable' || v.visibility === 'protected')
    && typeof v.hidden === 'boolean'
}

function validItems(items: unknown): items is SavedRunListView[] {
  return Array.isArray(items) && items.length <= RUN_LIST_VIEWS_LIMIT
    && items.every(isValidRunListView)
    && new Set(items.map((item: SavedRunListView) => item.name.toLocaleLowerCase())).size === items.length
}

/** A bad or future schema is never auto-repaired/overwritten. */
export function decodeRunListViews(raw: string | null): RunListViewsRead {
  if (raw === null) return { status: 'ok', items: [] }
  if (raw.length > MAX_STORE_LENGTH) return { status: 'invalid', items: [] }
  try {
    const parsed: unknown = JSON.parse(raw)
    if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) return { status: 'invalid', items: [] }
    const data = parsed as Record<string, unknown>
    if (typeof data.schema_version !== 'string') return { status: 'invalid', items: [] }
    if (data.schema_version !== VERSION) return { status: 'unsupported', items: [] }
    if (!validItems(data.items)) return { status: 'invalid', items: [] }
    return { status: 'ok', items: data.items }
  } catch {
    return { status: 'invalid', items: [] }
  }
}

export function readRunListViews(): RunListViewsRead {
  if (typeof window === 'undefined') return { status: 'unavailable', items: [] }
  try {
    return decodeRunListViews(window.localStorage.getItem(RUN_LIST_VIEWS_KEY))
  } catch {
    return { status: 'unavailable', items: [] }
  }
}

/** Only explicit user actions call this; a failed write never changes UI state. */
export function writeRunListViews(items: readonly SavedRunListView[]): boolean {
  if (typeof window === 'undefined' || !validItems(items)) return false
  const serialized = JSON.stringify({ schema_version: VERSION, items })
  if (serialized.length > MAX_STORE_LENGTH) return false
  try {
    window.localStorage.setItem(RUN_LIST_VIEWS_KEY, serialized)
    return true
  } catch {
    return false
  }
}
