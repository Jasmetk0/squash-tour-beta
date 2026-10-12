/** Pure, non-authoritative preview of a single bulk field operation. */
import {
  orderedPreviewFieldLocks, PREVIEW_FIELD_KEYS,
  type GeneratedPlayerFieldKey, type RunInitialWorldPlayer, type RunWorldPreviewFieldLock
} from '../api/runInitialWorldSetup'

export type GeneratedBulkChange = {
  playerId: string
  name: string
  before: number
  after: number
}

export type GeneratedBulkPlan = {
  selectedCount: number
  unchangedCount: number
  field: GeneratedPlayerFieldKey
  changes: GeneratedBulkChange[]
  nextLocks: RunWorldPreviewFieldLock[]
}

function observed(player: RunInitialWorldPlayer, field: GeneratedPlayerFieldKey): number | undefined {
  if (field === 'current_ability' || field === 'potential_ability') return player[field]
  return player.attributes?.[field.slice('attributes.'.length)]
}

/** Display-only plan; server owns the actual edit validation/replay and fingerprints.
 * Never infer absent attributes or accept client player objects as authority.
 */
export function prepareGeneratedBulkPlan(
  players: RunInitialWorldPlayer[], ids: string[], field: GeneratedPlayerFieldKey,
  value: number, verifiedLocks: RunWorldPreviewFieldLock[]
): GeneratedBulkPlan {
  if (!PREVIEW_FIELD_KEYS.includes(field))
    throw new Error('Bulk edits support only the nine real numeric source-model fields.')
  if (!Number.isSafeInteger(value) || value < 1 || value > 99)
    throw new Error('Bulk field value must be an integer from 1 to 99.')
  if (!ids.length || ids.length > 1000 || new Set(ids).size !== ids.length)
    throw new Error('Choose 1–1000 distinct players for the action.')
  const playersById = new Map(players.map(p => [p.player_id, p]))
  if (playersById.size !== players.length)
    throw new Error('Review contains duplicate player identities.')
  const changes: GeneratedBulkChange[] = []
  for (const id of [...ids].sort()) {
    const player = playersById.get(id)
    if (!player) throw new Error('Selected identity is not in the current verified preview.')
    const before = observed(player, field)
    if (!Number.isSafeInteger(before) || before! < 1 || before! > 99)
      throw new Error(`Selected player ${id} has no supported numeric ${field} value.`)
    // Basic impossible combinations are rejected before any backend preview.
    if ((field === 'current_ability' && value > player.potential_ability + 4) ||
        (field === 'potential_ability' && player.current_ability > value + 4))
      throw new Error(`Field value conflicts with current/potential ability for ${id}.`)
    if (before !== value) changes.push({playerId:id, name:player.name, before:before!, after:value})
  }
  const nextLocks = orderedPreviewFieldLocks([
    ...verifiedLocks.filter(lock => !changes.some(c =>
      lock.player_id === c.playerId && lock.field === field)),
    ...changes.map(change => ({player_id:change.playerId, field, value}))
  ])
  if (nextLocks.length > 2000 ||
      new Set(nextLocks.map(lock => lock.player_id+'|'+lock.field)).size !== nextLocks.length)
    throw new Error('Bulk edits exceed the supported lock budget or duplicate a field.')
  return {
    selectedCount: ids.length,
    unchangedCount: ids.length - changes.length,
    field, changes, nextLocks
  }
}
