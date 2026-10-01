import type { ReactNode } from 'react'
import { Link } from 'react-router-dom'

import { ViewerMetadataList } from '../../../components/viewer/ViewerLandingComponents'
import { viewerCountryProfilePath, viewerPlayerProfilePath } from '../../../viewer/viewerRoutes'

type PlayerSample = {
  player_id: string
  name: string
  country_code: string | null
  age: number | null
  overall?: number | null
  current_ovr?: number | null
  quality_band?: string | null
  status?: string | null
  identity_source?: string | null
}

type CountrySample = {
  country_code: string
  country_name?: string | null
  total_players?: number | null
  player_count?: number | null
  active_player_count?: number | null
  retired_player_count?: number | null
  average_overall?: number | null
  average_current_ovr?: number | null
  top_player_id?: string | null
  top_player_name?: string | null
  top_player_overall?: number | null
  top_player_current_ovr?: number | null
}

export function renderLinkedPlayer(runId: string, playerId: string | null | undefined, label: ReactNode): ReactNode {
  if (!playerId) return label || '—'
  return <Link to={viewerPlayerProfilePath(runId, playerId)}>{label || playerId}</Link>
}

export function renderLinkedCountry(runId: string, countryCode: string | null | undefined, label?: ReactNode): ReactNode {
  if (!countryCode) return label ?? '—'
  return <Link to={viewerCountryProfilePath(runId, countryCode)}>{label ?? countryCode}</Link>
}

export function renderPlayerSampleMetadata(player: PlayerSample, runId?: string, options: { includeQualityBand?: boolean } = {}): JSX.Element {
  const playerLabel = player.name || player.player_id || '—'
  const playerId = player.player_id || '—'
  const country = player.country_code || '—'
  const powerRating = player.current_ovr ?? player.overall ?? null

  const items = [
    { label: 'Player', value: runId ? renderLinkedPlayer(runId, player.player_id, playerLabel) : playerLabel },
    { label: 'Player ID', value: runId ? renderLinkedPlayer(runId, player.player_id, playerId) : playerId },
    { label: 'Country', value: runId ? renderLinkedCountry(runId, player.country_code) : country },
    { label: 'Age', value: player.age ?? '—' },
    { label: 'Power Rating', value: powerRating ?? '—' }
  ]

  if (options.includeQualityBand) {
    items.push({ label: 'Quality band', value: player.quality_band ?? '—' })
  }
  if (player.status) {
    items.push({ label: 'Status', value: player.status })
  }
  if (player.identity_source) {
    items.push({ label: 'Identity source', value: player.identity_source.replace(/_/g, ' ') })
  }

  return <ViewerMetadataList items={items} />
}

export function renderCountrySampleMetadata(nation: CountrySample, runId?: string): JSX.Element {
  const countryCode = nation.country_code || '—'
  const countryName = nation.country_name ?? nation.country_code ?? '—'
  const topPlayer = nation.top_player_name ?? nation.top_player_id ?? '—'
  const playerCount = nation.player_count ?? nation.total_players ?? null
  const averagePower = nation.average_current_ovr ?? nation.average_overall ?? null
  const topPower = nation.top_player_current_ovr ?? nation.top_player_overall ?? null

  return (
    <ViewerMetadataList
      items={[
        { label: 'Country code', value: runId ? renderLinkedCountry(runId, nation.country_code) : countryCode },
        { label: 'Country name', value: runId ? renderLinkedCountry(runId, nation.country_code, countryName) : countryName },
        { label: 'Player count', value: playerCount ?? '—' },
        { label: 'Active players', value: nation.active_player_count ?? '—' },
        { label: 'Retired players', value: nation.retired_player_count ?? '—' },
        { label: 'Average Power Rating', value: averagePower ?? '—' },
        { label: 'Top player', value: runId ? renderLinkedPlayer(runId, nation.top_player_id, topPlayer) : topPlayer },
        { label: 'Top player Power Rating', value: topPower ?? '—' }
      ]}
    />
  )
}
