import { describe, expect, it } from 'vitest'

import viewerRunSnapshotsPageSource from '../../ViewerRunSnapshotsPage.tsx?raw'
import viewerSnapshotPayloadDisplaySource from './viewerSnapshotPayloadDisplay.ts?raw'
import { parseRacePreviewPayload } from '../../../viewer/racePayload'
import { parseRankingPreviewPayload } from '../../../viewer/rankingPayload'
import { parseRaceSnapshotRows, parseRankingSnapshotRows } from './viewerSnapshotPayloadDisplay'

function detailPageSource(): string {
  const start = viewerRunSnapshotsPageSource.indexOf('export function ViewerRunSnapshotDetailPage')
  expect(start).toBeGreaterThanOrEqual(0)

  const rest = viewerRunSnapshotsPageSource.slice(start)
  const nextExport = rest.indexOf('\nexport ', 'export function ViewerRunSnapshotDetailPage'.length)
  return nextExport === -1 ? rest : rest.slice(0, nextExport)
}

describe('Viewer snapshot payload list/detail boundary', () => {
  it('keeps detail page payload rendering on the conservative audit path instead of preview-table inference', () => {
    const detailSource = detailPageSource()

    expect(detailSource).toContain('getSnapshotPayloadTableAuditStatus')
    expect(detailSource).not.toContain('RankingPreviewTable')
    expect(detailSource).not.toContain('RacePreviewTable')
    expect(detailSource).not.toContain('parseRankingPreviewPayload')
    expect(detailSource).not.toContain('parseRacePreviewPayload')
    expect(detailSource).not.toContain('Top 10 Ranking Preview')
    expect(detailSource).not.toContain('Top 10 Race Preview')
    expect(detailSource).not.toContain('Standings preview')
  })

  it('keeps list selected-publication previews intentionally separate from detail payload tables', () => {
    // List selected-publication previews are still allowed to use the typed preview parser/table path.
    // The detail source slice above is the boundary guard that prevents these heuristic previews
    // from being reintroduced into detail-page unknown-payload table rendering.
    expect(viewerRunSnapshotsPageSource).toContain('RankingPreviewTable')
    expect(viewerRunSnapshotsPageSource).toContain('RacePreviewTable')
    expect(viewerRunSnapshotsPageSource).toContain('parseRankingPreviewPayload')
    expect(viewerRunSnapshotsPageSource).toContain('parseRacePreviewPayload')

    expect(parseRankingPreviewPayload({ rankings: [{ rank: 1, player_id: 'p1', player_name: 'Preview Player', points: 100 }] }).rows).toHaveLength(1)
    expect(parseRacePreviewPayload({ race_to_finals: { rows: [{ position: 1, player_id: 'p2', player_name: 'Race Preview Player', race_points: 80 }] } }).rows).toHaveLength(1)
    expect(detailPageSource()).not.toContain('parseRankingPreviewPayload')
    expect(detailPageSource()).not.toContain('parseRacePreviewPayload')
  })

  it('keeps helper-level snapshot row parsing separate from preview payload parsers', () => {
    const plausibleRankingPayload = {
      ranking_table: { rows: [{ rank: 1, player_id: 'p_alpha', player_name: 'Plausible Ranking Player', ranking_points: 1200 }] }
    }
    const plausibleRacePayload = {
      race_table: { rows: [{ rank: 1, player_id: 'p_beta', player_name: 'Plausible Race Player', race_points: 900 }] }
    }

    expect(parseRankingSnapshotRows(plausibleRankingPayload)).toEqual([])
    expect(parseRaceSnapshotRows(plausibleRacePayload)).toEqual([])
    expect(viewerSnapshotPayloadDisplaySource).not.toContain("from '../../../viewer/rankingPayload'")
    expect(viewerSnapshotPayloadDisplaySource).not.toContain("from '../../../viewer/racePayload'")
    expect(viewerSnapshotPayloadDisplaySource).not.toContain("from '../viewer/rankingPayload'")
    expect(viewerSnapshotPayloadDisplaySource).not.toContain("from '../viewer/racePayload'")
    expect(viewerSnapshotPayloadDisplaySource).not.toContain('parseRankingPreviewPayload')
    expect(viewerSnapshotPayloadDisplaySource).not.toContain('parseRacePreviewPayload')
  })
})
