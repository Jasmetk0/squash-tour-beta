import type { RunContainer } from '../../api/types'

export const RUN_BROWSER_PAGE_SIZE = 25

// Filter only the already fetched public Run catalog. Display names are
// catalog metadata, never a claim that a Saved branch was revalidated.
export function filterViewerRuns(runs: readonly RunContainer[], text: string): RunContainer[] {
  const words = text.trim().toLocaleLowerCase().split(/\s+/).filter(Boolean)
  if (!words.length) return [...runs]
  return runs.filter(run => {
    const displayName = typeof run.display_name === 'string' ? run.display_name : ''
    const haystack = [run.run_id, displayName].join(' ').toLocaleLowerCase()
    return words.every(word => haystack.includes(word))
  })
}

// Keep malformed and out-of-range deep links visibly invalid instead of
// silently showing a different page and misleading the user.
export function parseViewerRunPage(raw: string | null, pageCount: number): number | null {
  if (raw === null) return 1
  if (!/^[1-9][0-9]*$/.test(raw)) return null
  const value = Number(raw)
  return Number.isSafeInteger(value) && value <= pageCount ? value : null
}
