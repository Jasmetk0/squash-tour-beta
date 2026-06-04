import type { ReactNode } from 'react'
import { Link } from 'react-router-dom'

import type { RunNationSummaryItem, RunPlayerListItem } from '../../../api/types'
import { ViewerMetadataList } from '../../../components/viewer/ViewerLandingComponents'
import { viewerCountryProfilePath, viewerPlayerProfilePath } from '../../../viewer/viewerRoutes'

export function renderLinkedPlayer(runId: string, playerId: string | null | undefined, label: ReactNode): ReactNode {
  if (!playerId) return label || '—'
  return <Link to={viewerPlayerProfilePath(runId, playerId)}>{label || playerId}</Link>
}

export function renderLinkedCountry(runId: string, countryCode: string | null | undefined, label?: ReactNode): ReactNode {
  if (!countryCode) return label ?? '—'
  return <Link to={viewerCountryProfilePath(runId, countryCode)}>{label ?? countryCode}</Link>
}

export function renderPlayerSampleMetadata(player: RunPlayerListItem, runId?: string, options: { includeQualityBand?: boolean } = {}): JSX.Element {
  const playerLabel = player.name || player.player_id || '—'
  const playerId = player.player_id || '—'
  const country = player.country_code || '—'

  const items = [
    { label: 'Player', value: runId ? renderLinkedPlayer(runId, player.player_id, playerLabel) : playerLabel },
    { label: 'Player ID', value: runId ? renderLinkedPlayer(runId, player.player_id, playerId) : playerId },
    { label: 'Country', value: runId ? renderLinkedCountry(runId, player.country_code) : country },
    { label: 'Age', value: player.age ?? '—' },
    { label: 'Power Rating', value: player.overall ?? '—' }
  ]

  if (options.includeQualityBand) {
    items.push({ label: 'Quality band', value: player.quality_band ?? '—' })
  }

  return <ViewerMetadataList items={items} />
}

export function renderCountrySampleMetadata(nation: RunNationSummaryItem, runId?: string): JSX.Element {
  const countryCode = nation.country_code || '—'
  const countryName = nation.country_name ?? nation.country_code ?? '—'
  const topPlayer = nation.top_player_name ?? nation.top_player_id ?? '—'

  return (
    <ViewerMetadataList
      items={[
        { label: 'Country code', value: runId ? renderLinkedCountry(runId, nation.country_code) : countryCode },
        { label: 'Country name', value: runId ? renderLinkedCountry(runId, nation.country_code, countryName) : countryName },
        { label: 'Player count', value: nation.total_players ?? '—' },
        { label: 'Average Power Rating', value: nation.average_overall ?? '—' },
        { label: 'Top player', value: runId ? renderLinkedPlayer(runId, nation.top_player_id, topPlayer) : topPlayer },
        { label: 'Top player Power Rating', value: nation.top_player_overall ?? '—' }
      ]}
    />
  )
}
