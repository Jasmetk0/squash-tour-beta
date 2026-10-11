import type { RunActivityItem } from '../../../api/types'

export function selectLatestActivityItem(items: RunActivityItem[]): RunActivityItem | null {
  return [...items].sort((a, b) => (b.sequence ?? -1) - (a.sequence ?? -1))[0] ?? null
}
