const compactPattern = /^(\d{4})\/(\d{2})$/
const longPattern = /^(\d{4})\/(\d{4})$/

export function seasonLabelFromStartYear(startYear: number): string {
  if (!Number.isInteger(startYear) || startYear < 0) {
    throw new Error('startYear must be a non-negative integer')
  }
  return `${startYear}/${String((startYear + 1) % 100).padStart(2, '0')}`
}

export function toCompactSeasonLabel(label: string): string {
  const raw = label.trim()

  const compactMatch = compactPattern.exec(raw)
  if (compactMatch) {
    const startYear = Number(compactMatch[1])
    const endTwoDigits = Number(compactMatch[2])
    if (endTwoDigits !== (startYear + 1) % 100) {
      throw new Error('Invalid season label rollover')
    }
    return seasonLabelFromStartYear(startYear)
  }

  const longMatch = longPattern.exec(raw)
  if (longMatch) {
    const startYear = Number(longMatch[1])
    const endYear = Number(longMatch[2])
    if (endYear !== startYear + 1) {
      throw new Error('Invalid season label rollover')
    }
    return seasonLabelFromStartYear(startYear)
  }

  throw new Error('Season label must use YYYY/YY or YYYY/YYYY format')
}

export function toLongSeasonLabel(label: string): string {
  const compact = toCompactSeasonLabel(label)
  const startYear = Number(compact.split('/')[0])
  return `${startYear}/${startYear + 1}`
}
