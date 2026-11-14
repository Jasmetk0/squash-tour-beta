/** Run-level follows and derived follow alerts (Admin, read/preference only). */
export type FollowKind = 'player' | 'country'
export type FollowRow = { kind: FollowKind; subject_id: string; alerts_enabled: boolean }
export type FollowList = { schema_version: 'run_follows.v1'; run_id: string; follows: FollowRow[] }
export type AlertItem = {
  player_id: string; player_name: string; country_code: string; kind: string
  effective_week: { season_index: number; week: number }
  detail: Record<string, unknown>; source: { kind: string; fingerprint: string }; reasons: string[]
}
export type AlertCard = {
  notification_key: string; player_id: string; player_name: string; country_code: string
  first_week: { season_index: number; week: number }; last_week: { season_index: number; week: number }
  item_count: number; unread_items: number; reasons: string[]; items: AlertItem[]
  state: 'unread' | 'read' | 'hidden'
}
export type AlertList = {
  schema_version: 'native_tour_notifications.v1'; run_id: string; branch_id: string
  saved_head_revision_id: string; as_of_ordinal: number; unread_cards: number; cards: AlertCard[]
  criteria: { domestic_leaders: number; exceptional_rank: number; group_window_weeks: number; status: string }
}

const text = (v: unknown): v is string => typeof v === 'string' && v.length > 0
const count = (v: unknown): v is number => Number.isInteger(v) && (v as number) >= 0
const week = (w: AlertCard['first_week'] | undefined) =>
  Boolean(w) && count(w!.season_index) && Number.isInteger(w!.week) && w!.week >= 1

export function validFollowList(data: FollowList | null | undefined, runId: string): data is FollowList {
  if (!data || data.schema_version !== 'run_follows.v1' || data.run_id !== runId || !Array.isArray(data.follows)) return false
  const seen = new Set<string>()
  return data.follows.every(f => {
    const key = `${f.kind}:${f.subject_id}`
    if (!['player', 'country'].includes(f.kind) || !text(f.subject_id) ||
      typeof f.alerts_enabled !== 'boolean' || seen.has(key)) return false
    seen.add(key)
    return f.kind === 'player' || /^[A-Z]{3}$/.test(f.subject_id)
  })
}

/** Exact Run/Branch/Saved HEAD; each card must be backed by its items and a unique key. */
export function validAlertList(
  data: AlertList | null | undefined, scope: { runId: string; branchId: string; savedHead: string }
): data is AlertList {
  if (!data || data.schema_version !== 'native_tour_notifications.v1' ||
    data.run_id !== scope.runId || data.branch_id !== scope.branchId ||
    data.saved_head_revision_id !== scope.savedHead || !Array.isArray(data.cards)) return false
  const keys = new Set<string>()
  return data.cards.every(c => {
    if (!/^[0-9a-f]{64}$/.test(c.notification_key) || keys.has(c.notification_key)) return false
    keys.add(c.notification_key)
    if (!['unread', 'read', 'hidden'].includes(c.state) || !Array.isArray(c.items) || c.items.length === 0 ||
      c.item_count !== c.items.length || !count(c.unread_items) || c.unread_items > c.item_count ||
      !week(c.first_week) || !week(c.last_week)) return false
    return c.items.every(i => i.player_id === c.player_id && week(i.effective_week) &&
      text(i.kind) && text(i.source?.fingerprint) && text(i.source?.kind) && Array.isArray(i.reasons) && i.reasons.length > 0)
  })
}
