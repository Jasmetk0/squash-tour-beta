import { describe, expect, it } from 'vitest'

import viewerRunSnapshotsPageSource from '../../ViewerRunSnapshotsPage.tsx?raw'

const detailExportName = 'export function ViewerRunSnapshotDetailPage'

function detailPageSource(): string {
  const start = viewerRunSnapshotsPageSource.indexOf(detailExportName)
  expect(start).toBeGreaterThanOrEqual(0)

  const rest = viewerRunSnapshotsPageSource.slice(start)
  const nextExport = rest.indexOf('\nexport ', detailExportName.length)
  return nextExport === -1 ? rest : rest.slice(0, nextExport)
}

describe('Viewer snapshot module final source guard', () => {
  it('keeps detail pages on the conservative payload boundary path', () => {
    const detailSource = detailPageSource()

    expect(detailSource).toContain('getSnapshotPayloadRows')
    expect(detailSource).toContain('getSnapshotPayloadTableAuditStatus')
    expect(detailSource).toContain('normalizeSourceEventId')
    expect(detailSource).toContain('normalizeSnapshots')

    expect(detailSource).not.toContain('RankingPreviewTable')
    expect(detailSource).not.toContain('RacePreviewTable')
    expect(detailSource).not.toContain('parseRankingPreviewPayload')
    expect(detailSource).not.toContain('parseRacePreviewPayload')
    expect(detailSource).not.toContain('Top 10 Ranking Preview')
    expect(detailSource).not.toContain('Top 10 Race Preview')
    expect(detailSource).not.toContain('Standings preview')
  })

  it('allows preview parser/table usage only outside the detail page source slice', () => {
    const detailSource = detailPageSource()

    // List selected-publication previews intentionally remain on the preview parser/table path.
    // Detail payload rendering is intentionally separate and remains conservative for unknown payloads.
    expect(viewerRunSnapshotsPageSource).toContain('RankingPreviewTable')
    expect(viewerRunSnapshotsPageSource).toContain('RacePreviewTable')
    expect(viewerRunSnapshotsPageSource).toContain('parseRankingPreviewPayload')
    expect(viewerRunSnapshotsPageSource).toContain('parseRacePreviewPayload')

    expect(detailSource).not.toContain('RankingPreviewTable')
    expect(detailSource).not.toContain('RacePreviewTable')
    expect(detailSource).not.toContain('parseRankingPreviewPayload')
    expect(detailSource).not.toContain('parseRacePreviewPayload')
  })

  it('keeps list and detail snapshot sequence parsing strict', () => {
    const detailSource = detailPageSource()

    expect(viewerRunSnapshotsPageSource).toMatch(
      /requestedSequenceParam\s*&&\s*\/\^\\d\+\$\/\.test\(requestedSequenceParam\)[\s\S]*Number\.parseInt\(requestedSequenceParam, 10\)/
    )
    expect(viewerRunSnapshotsPageSource).toMatch(
      /hasRequestedSequence\s*=\s*Number\.isInteger\(requestedSequence\)\s*&&\s*requestedSequence\s*>\s*0/
    )
    expect(detailSource).toMatch(/\/\^\\d\+\$\/\.test\(snapshotSequence\)[\s\S]*Number\.isSafeInteger\(parsedSequence\)[\s\S]*parsedSequence\s*>\s*0/)
    expect(detailSource).not.toContain('Number.parseInt(snapshotSequence')
    expect(detailSource).not.toContain('parseInt(snapshotSequence')
  })

  it('keeps unsafe snapshot-list normalization before navigation consumers use list items', () => {
    expect(viewerRunSnapshotsPageSource).toContain('isSnapshotListItem')
    expect(viewerRunSnapshotsPageSource).toContain('normalizeSnapshots')
    expect(viewerRunSnapshotsPageSource).toMatch(/typeof value === 'object'[\s\S]*value !== null[\s\S]*!Array\.isArray\(value\)/)
    expect(viewerRunSnapshotsPageSource).toMatch(/snapshot_sequence[\s\S]*Number\.is(?:Safe)?Integer\(sequence\)[\s\S]*sequence <= 0/)
    expect(viewerRunSnapshotsPageSource).toMatch(/typeof value\.snapshot_kind !== 'string'/)
    expect(viewerRunSnapshotsPageSource).toMatch(/hasOwnProperty\.call\(value, 'payload'\)/)
    expect(viewerRunSnapshotsPageSource).toMatch(/Array\.isArray\(data\?\.snapshots\)[\s\S]*filter\(isSnapshotListItem\)/)
  })

  it('keeps the snapshot module Viewer-only and free of obvious mutating labels', () => {
    expect(viewerRunSnapshotsPageSource).not.toContain('/admin')

    const mutationLabels = [
      'Simulate',
      'Generate',
      'Persist',
      'Apply',
      'Execute',
      'Delete',
      'Edit',
      'Import',
      'Rollover',
      'Rebuild',
      'Override',
      'Save changes',
      'Commit',
      'Regenerate',
      'Repair',
      'Merge',
      'Overwrite'
    ]

    for (const label of mutationLabels) {
      expect(viewerRunSnapshotsPageSource).not.toMatch(new RegExp(`\\b${label.replace(/ /g, '\\s+')}\\b`))
    }
  })
})
