import { Link } from 'react-router-dom'

import { useLanguage, type Language } from '../../../i18n/LanguageContext'
import type { RunPlayerListItem, ViewerPlayer } from '../../../api/types'
import { ViewerActiveRunLinks, ViewerEmptyState, ViewerMetadataList, ViewerSampleList, ViewerSectionCard } from '../../../components/viewer/ViewerLandingComponents'
import { viewerPlannedEventPath, viewerPlayersPath, viewerTopH2HPath, viewerTopSearchPath, viewerTournamentDetailPath, viewerWeekDetailPath } from '../../../viewer/viewerRoutes'
import { renderLinkedCountry, renderLinkedPlayer, renderPlayerSampleMetadata } from '../people'
import { comparisonStatFields, formatComparisonDifference, type ViewerSearchTournamentResult, type ViewerSelectedComparisonPlayers } from './viewerComparisonDisplay'


// Translate interface labels only. Stored names, IDs and quality values stay intact.
const czechComparisonLabels: Record<string, string> = {
  'Links': 'Odkazy', 'Read-only navigation': 'Čtecí navigace',
  'Open active run players': 'Otevřít hráče aktivního Runu',
  'Open Viewer search': 'Otevřít vyhledávání Vieweru',
  'Selected player': 'Vybraný hráč', 'Player': 'Hráč', 'Player ID': 'ID hráče',
  'Country': 'Země', 'Age': 'Věk', 'Power Rating': 'Herní síla',
  'Technique': 'Technika', 'Movement': 'Pohyb', 'Physical': 'Fyzická složka',
  'Mental': 'Mentální složka', 'Quality band': 'Pásmo kvality',
  'Player data is not available for this run yet.': 'Pro tento Run zatím nejsou dostupná data hráče.',
  'Comparison Summary': 'Souhrn porovnání', 'Numeric field differences': 'Rozdíly číselných atributů',
  'Power Rating difference': 'Rozdíl herní síly', 'Technique difference': 'Rozdíl techniky',
  'Movement difference': 'Rozdíl pohybu', 'Physical difference': 'Rozdíl fyzické složky',
  'Mental difference': 'Rozdíl mentální složky', 'Age difference': 'Rozdíl věku',
  'This preview is not connected for this data shape yet.': 'Pro tento formát dat zatím není náhled dostupný.'
}
function comparisonLabel(label: string, language: Language): string {
  return language === 'cs' ? czechComparisonLabels[label] ?? label : label
}

export function buildPlayerSearchLink(player: RunPlayerListItem): string {
  return `${viewerTopSearchPath()}?q=${encodeURIComponent(player.player_id || player.name || '')}`
}

export function buildSelectedPlayerSearchLinks(players: RunPlayerListItem[], language: Language = 'en'): { label: string; to: string }[] {
  return players
    .filter((player) => player.player_id || player.name)
    .map((player) => ({ label: `${language === 'cs' ? 'Vyhledat' : 'Search'} ${player.name || player.player_id}`, to: buildPlayerSearchLink(player) }))
}

export function buildSelectedH2HPath(selection: Pick<ViewerSelectedComparisonPlayers, 'playerA' | 'playerB'>): string {
  return selection.playerA && selection.playerB ? `${viewerTopH2HPath()}?playerA=${encodeURIComponent(selection.playerA.player_id)}&playerB=${encodeURIComponent(selection.playerB.player_id)}` : viewerTopH2HPath()
}

export function ViewerPlayerComparisonLinks({ activeRunId, players }: { activeRunId: string; players: RunPlayerListItem[] }): JSX.Element {
  const { language } = useLanguage()
  const label = (text: string) => comparisonLabel(text, language)
  return (
    <ViewerSectionCard title={label('Links')} kicker={label('Read-only navigation')}>
      <ViewerActiveRunLinks
        links={[
          { label: label('Open active run players'), to: viewerPlayersPath(activeRunId) },
          { label: label('Open Viewer search'), to: viewerTopSearchPath() },
          ...buildSelectedPlayerSearchLinks(players, language)
        ]}
      />
    </ViewerSectionCard>
  )
}

export function ViewerComparisonPlayerCard({ activeRunId, title, player }: { activeRunId: string; title: string; player: RunPlayerListItem | null }): JSX.Element {
  const { language } = useLanguage()
  const label = (text: string) => comparisonLabel(text, language)
  return (
    <ViewerSectionCard title={title} kicker={label('Selected player')}>
      {player ? (
        <ViewerMetadataList
          ariaLabel={language === 'cs' ? `${title} – porovnávané atributy` : `${title} comparison fields`}
          items={[
            { label: label('Player'), value: renderLinkedPlayer(activeRunId, player.player_id, player.name || player.player_id || '—') },
            { label: label('Player ID'), value: renderLinkedPlayer(activeRunId, player.player_id, player.player_id || '—') },
            { label: label('Country'), value: renderLinkedCountry(activeRunId, player.country_code) },
            { label: label('Age'), value: player.age ?? '—' },
            { label: label('Power Rating'), value: player.overall ?? '—' },
            { label: label('Technique'), value: player.technique ?? '—' },
            { label: label('Movement'), value: player.movement ?? '—' },
            { label: label('Physical'), value: player.physical ?? '—' },
            { label: label('Mental'), value: player.mental ?? '—' },
            { label: label('Quality band'), value: player.quality_band ?? '—' }
          ]}
        />
      ) : (
        <ViewerEmptyState>{label('Player data is not available for this run yet.')}</ViewerEmptyState>
      )}
    </ViewerSectionCard>
  )
}

export function ViewerComparisonSummary({ playerA, playerB, title = 'Comparison Summary' }: { playerA: RunPlayerListItem | null; playerB: RunPlayerListItem | null; title?: string }): JSX.Element {
  const { language } = useLanguage()
  const label = (text: string) => comparisonLabel(text, language)
  return (
    <ViewerSectionCard title={label(title)} kicker={label('Numeric field differences')}>
      {playerA && playerB ? (
        <ViewerMetadataList
          ariaLabel={language === 'cs' ? `${label(title)} – rozdíly` : `${title} differences`}
          items={comparisonStatFields.map((field) => ({
            label: label(field.label),
            value: formatComparisonDifference(playerA, playerB, field.key)
          }))}
        />
      ) : (
        <ViewerEmptyState>{label('This preview is not connected for this data shape yet.')}</ViewerEmptyState>
      )}
    </ViewerSectionCard>
  )
}

export function ViewerSamplePlayersList({ players, label, runId }: { players: Array<RunPlayerListItem | ViewerPlayer>; label: string; runId?: string }): JSX.Element | null {
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
