/** Reformat a Lab editor buffer without coercing primitives into scenario objects. */
export function prettyLabJson(text: string): string {
  let parsed: unknown
  try {
    parsed = JSON.parse(text)
  } catch {
    throw new Error('Invalid JSON syntax. Check the scenario before formatting.')
  }
  if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) {
    throw new Error('A Lab scenario must be a JSON object.')
  }
  return JSON.stringify(parsed, null, 2)
}
