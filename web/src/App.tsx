import { Navigate, Route, Routes } from 'react-router-dom'

import { Layout } from './components/Layout'
import { BootstrapLineagePage } from './pages/BootstrapLineagePage'
import { ActivityPage } from './pages/ActivityPage'
import { DashboardPage } from './pages/DashboardPage'
import { CountriesPage } from './pages/CountriesPage'
import { EventDetailPage } from './pages/EventDetailPage'
import { EventsPage } from './pages/EventsPage'
import { FinalsPage } from './pages/FinalsPage'
import { FinalsQualificationDetailPage } from './pages/FinalsQualificationDetailPage'
import { FinalsResultDetailPage } from './pages/FinalsResultDetailPage'
import { RolloverPage } from './pages/RolloverPage'
import { RolloverSeasonDetailPage } from './pages/RolloverSeasonDetailPage'
import { RunDiagnosticsPage } from './pages/RunDiagnosticsPage'
import { RunPage } from './pages/RunPage'
import { RunsPage } from './pages/RunsPage'
import { PlannedEventDetailPage } from './pages/PlannedEventDetailPage'
import { PlayersPage } from './pages/PlayersPage'
import { SeasonCalendarPage } from './pages/SeasonCalendarPage'
import { SeasonChainPage } from './pages/SeasonChainPage'
import { SnapshotDetailPage } from './pages/SnapshotDetailPage'
import { SnapshotsPage } from './pages/SnapshotsPage'
import { TalentPreviewPage } from './pages/TalentPreviewPage'
import { ManualPlayerOverridesPage } from './pages/ManualPlayerOverridesPage'
import { WeekDetailPage } from './pages/WeekDetailPage'
import { WorldGenerationPage } from './pages/WorldGenerationPage'
import { NationsPage } from './pages/NationsPage'

export default function App(): JSX.Element {
  return (
    <Routes>
      <Route path="/" element={<Layout />}>
        <Route index element={<DashboardPage />} />
        <Route path="world/countries" element={<CountriesPage />} />
        <Route path="world/talent-preview" element={<TalentPreviewPage />} />
        <Route path="world/manual-player-overrides" element={<ManualPlayerOverridesPage />} />
        <Route path="runs" element={<RunsPage />} />
        <Route path="runs/:runId" element={<RunPage />} />
        <Route path="runs/:runId/events" element={<EventsPage />} />
        <Route path="runs/:runId/calendar" element={<SeasonCalendarPage />} />
        <Route path="runs/:runId/weeks/:week" element={<WeekDetailPage />} />
        <Route path="runs/:runId/calendar/:eventId" element={<PlannedEventDetailPage />} />
        <Route path="runs/:runId/activity" element={<ActivityPage />} />
        <Route path="runs/:runId/players" element={<PlayersPage />} />
        <Route path="runs/:runId/nations" element={<NationsPage />} />
        <Route path="runs/:runId/diagnostics" element={<RunDiagnosticsPage />} />
        <Route path="runs/:runId/world-generation" element={<WorldGenerationPage />} />
        <Route path="runs/:runId/events/:eventId" element={<EventDetailPage />} />
        <Route path="runs/:runId/finals" element={<FinalsPage />} />
        <Route path="runs/:runId/finals/qualification" element={<FinalsQualificationDetailPage />} />
        <Route path="runs/:runId/finals/result" element={<FinalsResultDetailPage />} />
        <Route path="runs/:runId/rollover" element={<RolloverPage />} />
        <Route path="runs/:runId/rollover/:toSeason" element={<RolloverSeasonDetailPage />} />
        <Route path="runs/:runId/bootstrap-lineage" element={<BootstrapLineagePage />} />
        <Route path="runs/:runId/season-chain" element={<SeasonChainPage />} />
        <Route path="runs/:runId/snapshots/ranking" element={<SnapshotsPage mode="ranking" />} />
        <Route path="runs/:runId/snapshots/ranking/:snapshotSequence" element={<SnapshotDetailPage mode="ranking" />} />
        <Route path="runs/:runId/snapshots/race" element={<SnapshotsPage mode="race" />} />
        <Route path="runs/:runId/snapshots/race/:snapshotSequence" element={<SnapshotDetailPage mode="race" />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  )
}
