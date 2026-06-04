import { Link } from 'react-router-dom'

import type { RunPlayerListItem } from '../../../api/types'
import { ViewerActiveRunLinks, ViewerEmptyState, ViewerMetadataList, ViewerSampleList, ViewerSectionCard } from '../../../components/viewer/ViewerLandingComponents'
import { viewerPlannedEventPath, viewerPlayersPath, viewerTopH2HPath, viewerTopSearchPath, viewerTournamentDetailPath, viewerWeekDetailPath } from '../../../viewer/viewerRoutes'
import { renderLinkedCountry, renderLinkedPlayer, renderPlayerSampleMetadata } from '../people'
import { comparisonStatFields, formatComparisonDifference, type ViewerSearchTournamentResult, type ViewerSelectedComparisonPlayers } from './viewerComparisonDisplay'

export function buildPlayerSearchLink(player: RunPlayerListItem): string {
  return `${viewerTopSearchPath()}?q=${encodeURIComponent(player.player_id || player.name || '')}`
}

export function buildSelectedPlayerSearchLinks(players: RunPlayerListItem[]): { label: string; to: string }[] {
  return players
    .filter((player) => player.player_id || player.name)
    .map((player) => ({ label: `Search ${player.name || player.player_id}`, to: buildPlayerSearchLink(player) }))
}

export function buildSelectedH2HPath(selection: Pick<ViewerSelectedComparisonPlayers, 'playerA' | 'playerB'>): string {
  return selection.playerA && selection.playerB ? `${viewerTopH2HPath()}?playerA=${encodeURIComponent(selection.playerA.player_id)}&playerB=${encodeURIComponent(selection.playerB.player_id)}` : viewerTopH2HPath()
}

export function ViewerPlayerComparisonLinks({ activeRunId, players }: { activeRunId: string; players: RunPlayerListItem[] }): JSX.Element {
  return (
    <ViewerSectionCard title="Links" kicker="Read-only navigation">
      <ViewerActiveRunLinks
        links={[
          { label: 'Open active run players', to: viewerPlayersPath(activeRunId) },
          { label: 'Open Viewer search', to: viewerTopSearchPath() },
          ...buildSelectedPlayerSearchLinks(players)
        ]}
      />
    </ViewerSectionCard>
  )
}

export function ViewerComparisonPlayerCard({ activeRunId, title, player }: { activeRunId: string; title: string; player: RunPlayerListItem | null }): JSX.Element {
  return (
    <ViewerSectionCard title={title} kicker="Selected player">
      {player ? (
        <ViewerMetadataList
          ariaLabel={`${title} comparison fields`}
          items={[
            { label: 'Player', value: renderLinkedPlayer(activeRunId, player.player_id, player.name || player.player_id || '—') },
            { label: 'Player ID', value: renderLinkedPlayer(activeRunId, player.player_id, player.player_id || '—') },
            { label: 'Country', value: renderLinkedCountry(activeRunId, player.country_code) },
            { label: 'Age', value: player.age ?? '—' },
            { label: 'Power Rating', value: player.overall ?? '—' },
            { label: 'Technique', value: player.technique ?? '—' },
            { label: 'Movement', value: player.movement ?? '—' },
            { label: 'Physical', value: player.physical ?? '—' },
            { label: 'Mental', value: player.mental ?? '—' },
            { label: 'Quality band', value: player.quality_band ?? '—' }
          ]}
        />
      ) : (
        <ViewerEmptyState>Player data is not available for this run yet.</ViewerEmptyState>
      )}
    </ViewerSectionCard>
  )
}

export function ViewerComparisonSummary({ playerA, playerB, title = 'Comparison Summary' }: { playerA: RunPlayerListItem | null; playerB: RunPlayerListItem | null; title?: string }): JSX.Element {
  return (
    <ViewerSectionCard title={title} kicker="Numeric field differences">
      {playerA && playerB ? (
        <ViewerMetadataList
          ariaLabel={`${title} differences`}
          items={comparisonStatFields.map((field) => ({
            label: field.label,
            value: formatComparisonDifference(playerA, playerB, field.key)
          }))}
        />
      ) : (
        <ViewerEmptyState>This preview is not connected for this data shape yet.</ViewerEmptyState>
      )}
    </ViewerSectionCard>
  )
}

export function ViewerSamplePlayersList({ players, label, runId }: { players: RunPlayerListItem[]; label: string; runId?: string }): JSX.Element | null {
  return (
    <ViewerSampleList
      title="Sample players"
      label={label}
      items={players}
      getKey={(player) => player.player_id || player.name || 'unknown-player'}
      renderItem={(player) => renderPlayerSampleMetadata(player, runId)}
    />
  )
}

export function renderSearchTournamentMetadata(runId: string, event: ViewerSearchTournamentResult): JSX.Element {
  return (
    <ViewerMetadataList
      items={[
        { label: 'Event ID', value: event.hasPlannedEvent ? <Link to={viewerPlannedEventPath(runId, event.eventId)}>Planned Event: {event.eventId}</Link> : event.eventId },
        { label: 'Season', value: event.season ?? '—' },
        { label: 'Week', value: event.week ? <Link to={viewerWeekDetailPath(runId, event.week)}>Week Detail: W{event.week}</Link> : '—' },
        { label: 'Tour', value: event.tour ?? '—' },
        { label: 'Category', value: event.category ?? '—' },
        { label: 'Template', value: event.templateId ?? '—' },
        { label: 'Persisted availability', value: event.hasPersistedEvent ? 'Available' : 'Not available' },
        { label: 'Tournament detail', value: event.hasPersistedEvent ? <Link to={viewerTournamentDetailPath(runId, event.eventId)}>Tournament Detail: {event.eventId}</Link> : '—' }
      ]}
    />
  )
}
