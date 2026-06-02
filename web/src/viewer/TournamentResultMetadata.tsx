import type { ReactNode } from 'react'
import { Link } from 'react-router-dom'

import { MetadataList } from '../components/RunScopedUi'
import { parseTournamentResultPayload } from './tournamentResultPayload'
import type { TournamentPlayerSummary, TournamentResultSummary } from './tournamentResultPayload'
import { viewerPlayerProfilePath } from './viewerRoutes'

type TournamentResultMetadataItem = {
  label: string
  value: ReactNode
}

type TournamentResultMatchMode = 'combined' | 'matchCount' | 'completedMatchCount'

type TournamentPlayerLabelMode = 'identity' | 'identityWithCountry'

type TournamentResultMetadataItemOptions = {
  runId: string
  includeChampion?: boolean
  includeFinalist?: boolean
  includeResultStatus?: boolean
  matches?: TournamentResultMatchMode | false
  includeEmptyValues?: boolean
  emptyValue?: ReactNode
  labels?: Partial<Record<'champion' | 'finalist' | 'resultStatus' | 'matches', string>>
  playerLabelMode?: TournamentPlayerLabelMode
}

type TournamentResultMetadataListProps = TournamentResultMetadataItemOptions & {
  payload?: unknown
  summary?: TournamentResultSummary | null
}

function displayValue(value: ReactNode, includeEmptyValues: boolean, emptyValue: ReactNode): ReactNode | null {
  if (value === null || value === undefined || value === '') return includeEmptyValues ? emptyValue : null
  return value
}

function tournamentPlayerLabel(player: TournamentPlayerSummary | null, mode: TournamentPlayerLabelMode): string | null {
  const identity = player?.name ?? player?.playerId ?? player?.country
  if (!player || !identity) return null
  if (mode === 'identityWithCountry' && player.country) return `${identity} (${player.country})`
  return identity
}

export function tournamentPlayerProfileValue(
  runId: string,
  player: TournamentPlayerSummary | null,
  mode: TournamentPlayerLabelMode = 'identity'
): JSX.Element | string | null {
  const label = tournamentPlayerLabel(player, mode)
  if (!player || !label) return null
  if (!player.playerId) return label

  return <Link to={viewerPlayerProfilePath(runId, player.playerId)}>{label}</Link>
}

export function tournamentResultMatchesValue(summary: TournamentResultSummary, mode: TournamentResultMatchMode): string | number | null {
  if (mode === 'matchCount') return summary.matchCount
  if (mode === 'completedMatchCount') return summary.completedMatchCount
  if (summary.completedMatchCount !== null && summary.matchCount !== null) return `${summary.completedMatchCount} of ${summary.matchCount}`
  return summary.matchCount ?? summary.completedMatchCount
}

export function tournamentResultMetadataItems(
  summary: TournamentResultSummary | null,
  {
    runId,
    includeChampion = true,
    includeFinalist = false,
    includeResultStatus = true,
    matches = 'combined',
    includeEmptyValues = false,
    emptyValue = '—',
    labels = {},
    playerLabelMode = 'identity'
  }: TournamentResultMetadataItemOptions
): TournamentResultMetadataItem[] {
  if (!summary) return []

  const items: TournamentResultMetadataItem[] = []

  if (includeChampion) {
    const value = displayValue(tournamentPlayerProfileValue(runId, summary.champion, playerLabelMode), includeEmptyValues, emptyValue)
    if (value !== null) items.push({ label: labels.champion ?? 'Champion', value })
  }

  if (includeFinalist) {
    const value = displayValue(tournamentPlayerProfileValue(runId, summary.finalist, playerLabelMode), includeEmptyValues, emptyValue)
    if (value !== null) items.push({ label: labels.finalist ?? 'Finalist', value })
  }

  if (includeResultStatus) {
    const value = displayValue(summary.resultStatus, includeEmptyValues, emptyValue)
    if (value !== null) items.push({ label: labels.resultStatus ?? 'Result status', value })
  }

  if (matches) {
    const value = displayValue(tournamentResultMatchesValue(summary, matches), includeEmptyValues, emptyValue)
    if (value !== null) items.push({ label: labels.matches ?? 'Matches', value })
  }

  return items
}

export function tournamentResultPayloadMetadataItems(
  payload: unknown,
  options: TournamentResultMetadataItemOptions
): TournamentResultMetadataItem[] {
  return tournamentResultMetadataItems(parseTournamentResultPayload(payload).summary, options)
}

export function TournamentResultMetadataList({ payload, summary, ...options }: TournamentResultMetadataListProps): JSX.Element | null {
  const resultSummary = summary ?? parseTournamentResultPayload(payload).summary
  const items = tournamentResultMetadataItems(resultSummary, options)

  return items.length > 0 ? <MetadataList items={items} /> : null
}
