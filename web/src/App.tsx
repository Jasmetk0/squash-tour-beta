import { Navigate, Route, Routes, useParams } from 'react-router-dom'

import { Layout } from './components/Layout'
import { BootstrapLineagePage } from './pages/BootstrapLineagePage'
import { ActivityPage } from './pages/ActivityPage'
import { DashboardPage } from './pages/DashboardPage'
import { CountriesPage } from './pages/CountriesPage'
import { CountryDetailPage } from './pages/CountryDetailPage'
import { EventDetailPage } from './pages/EventDetailPage'
import { EventsPage } from './pages/EventsPage'
import { FinalsPage } from './pages/FinalsPage'
import { FinalsQualificationDetailPage } from './pages/FinalsQualificationDetailPage'
import { FinalsResultDetailPage } from './pages/FinalsResultDetailPage'
import {
  AdminHomePage,
  AdminPlayersDatabasePage,
  AdminPlayersPage,
  AdminSeasonsPage,
  AdminSettingsPage,
  AdminTourSeasonsPage,
  AdminTournamentTemplatesPage,
  AdminWorldPage,
  LandingPage,
  ViewerCountriesPage,
  ViewerHistoryPage,
  ViewerHomePage,
  ViewerPlayersPage,
  ViewerRankingsPage,
  ViewerRecordsPage,
  ViewerTournamentsPage
} from './pages/ModePages'
import { AdminTourSeasonsComparePage, AdminTourSeasonsValidationPage } from './pages/TourSeasonsShellPages'
import { AdminTourSeasonsCategoriesPage } from './pages/CategoriesPage'
import { AdminTourSeasonsCategoryDetailPage } from './pages/CategoryDetailPage'
import { AdminTourSeasonsTournamentsPage } from './pages/TournamentsPage'
import { AdminTourSeasonsTournamentDetailPage } from './pages/TournamentDetailPage'
import { AdminTourSeasonsSeasonTemplatesPage } from './pages/SeasonTemplatesPage'
import { AdminTourSeasonsSeasonTemplateDetailPage } from './pages/SeasonTemplateDetailPage'
import { AdminTourSeasonsSeasonRegistryPage } from './pages/SeasonRegistryPage'
import { AdminSimulatePage } from './pages/AdminSimulatePage'
import { AdminDiagnosticsPage } from './pages/AdminDiagnosticsPage'
import { RolloverPage } from './pages/RolloverPage'
import { RolloverSeasonDetailPage } from './pages/RolloverSeasonDetailPage'
import { RunDiagnosticsPage } from './pages/RunDiagnosticsPage'
import { RunPage } from './pages/RunPage'
import { RunsPage } from './pages/RunsPage'
import { PlannedEventDetailPage } from './pages/PlannedEventDetailPage'
import { PlayersPage } from './pages/PlayersPage'
import { PlayerCareerPage } from './pages/PlayerCareerPage'
import { SeasonCalendarPage } from './pages/SeasonCalendarPage'
import { SeasonChainPage } from './pages/SeasonChainPage'
import { SnapshotDetailPage } from './pages/SnapshotDetailPage'
import { SnapshotsPage } from './pages/SnapshotsPage'
import { TalentPreviewPage } from './pages/TalentPreviewPage'
import { TalentIntakePage } from './pages/TalentIntakePage'
import { ManualPlayerOverridesPage } from './pages/ManualPlayerOverridesPage'
import { WeekDetailPage } from './pages/WeekDetailPage'
import { WorldGenerationPage } from './pages/WorldGenerationPage'
import { NationsPage } from './pages/NationsPage'
import { WorldPackagePage } from './pages/WorldPackagePage'
import { CountryMomentumPage } from './pages/CountryMomentumPage'

function LegacyRunRedirect(): JSX.Element {
  const { runId = '', '*': suffix = '' } = useParams()
  return <Navigate to={`/admin/runs/${runId}${suffix ? `/${suffix}` : ''}`} replace />
}

function LegacyWorldRedirect(): JSX.Element {
  const { '*': suffix = '' } = useParams()
  return <Navigate to={`/admin/world${suffix ? `/${suffix}` : ''}`} replace />
}

export default function App(): JSX.Element {
  return (
    <Routes>
      <Route path="/" element={<Layout />}>
        <Route index element={<LandingPage />} />

        <Route path="admin" element={<AdminHomePage />} />
        <Route path="admin/world" element={<AdminWorldPage />} />
        <Route path="admin/world/countries" element={<CountriesPage />} />
        <Route path="admin/world/countries/:countryCode" element={<CountryDetailPage />} />
        <Route path="admin/world/talent-preview" element={<TalentPreviewPage />} />
        <Route path="admin/world/country-momentum" element={<CountryMomentumPage />} />
        <Route path="admin/world/manual-player-overrides" element={<ManualPlayerOverridesPage />} />
        <Route path="admin/world/package" element={<WorldPackagePage />} />
        <Route path="admin/tour-seasons/categories" element={<AdminTourSeasonsCategoriesPage />} />
        <Route path="admin/tour-seasons/categories/:categoryId" element={<AdminTourSeasonsCategoryDetailPage />} />
        <Route path="admin/tour-seasons/tournaments" element={<AdminTourSeasonsTournamentsPage />} />
        <Route path="admin/tour-seasons/tournaments/:tournamentId" element={<AdminTourSeasonsTournamentDetailPage />} />
        <Route path="admin/tour-seasons/season-templates" element={<AdminTourSeasonsSeasonTemplatesPage />} />
        <Route path="admin/tour-seasons/season-templates/:templateId" element={<AdminTourSeasonsSeasonTemplateDetailPage />} />
        <Route path="admin/tour-seasons/season-registry" element={<AdminTourSeasonsSeasonRegistryPage />} />
        <Route path="admin/tour-seasons/compare" element={<AdminTourSeasonsComparePage />} />
        <Route path="admin/tour-seasons/validation" element={<AdminTourSeasonsValidationPage />} />
        <Route path="admin/tour-seasons" element={<AdminTourSeasonsPage />} />
        <Route path="admin/tournament-templates" element={<AdminTournamentTemplatesPage />} />
        <Route path="admin/seasons" element={<AdminSeasonsPage />} />
        <Route path="admin/players" element={<AdminPlayersPage />} />
        <Route path="admin/players/database" element={<AdminPlayersDatabasePage />} />
        <Route path="admin/players/intake" element={<TalentIntakePage />} />
        <Route path="admin/simulate" element={<AdminSimulatePage />} />
        <Route path="admin/runs/new" element={<DashboardPage />} />
        <Route path="admin/runs" element={<RunsPage />} />
        <Route path="admin/runs/:runId" element={<RunPage />} />
        <Route path="admin/runs/:runId/events" element={<EventsPage />} />
        <Route path="admin/runs/:runId/calendar" element={<SeasonCalendarPage />} />
        <Route path="admin/runs/:runId/weeks/:week" element={<WeekDetailPage />} />
        <Route path="admin/runs/:runId/calendar/:eventId" element={<PlannedEventDetailPage />} />
        <Route path="admin/runs/:runId/activity" element={<ActivityPage />} />
        <Route path="admin/runs/:runId/players" element={<PlayersPage />} />
        <Route path="admin/runs/:runId/players/:playerId/career" element={<PlayerCareerPage />} />
        <Route path="admin/runs/:runId/nations" element={<NationsPage />} />
        <Route path="admin/runs/:runId/diagnostics" element={<RunDiagnosticsPage />} />
        <Route path="admin/runs/:runId/world-generation" element={<WorldGenerationPage />} />
        <Route path="admin/runs/:runId/events/:eventId" element={<EventDetailPage />} />
        <Route path="admin/runs/:runId/finals" element={<FinalsPage />} />
        <Route path="admin/runs/:runId/finals/qualification" element={<FinalsQualificationDetailPage />} />
        <Route path="admin/runs/:runId/finals/result" element={<FinalsResultDetailPage />} />
        <Route path="admin/runs/:runId/rollover" element={<RolloverPage />} />
        <Route path="admin/runs/:runId/rollover/:toSeason" element={<RolloverSeasonDetailPage />} />
        <Route path="admin/runs/:runId/bootstrap-lineage" element={<BootstrapLineagePage />} />
        <Route path="admin/runs/:runId/season-chain" element={<SeasonChainPage />} />
        <Route path="admin/runs/:runId/snapshots/ranking" element={<SnapshotsPage mode="ranking" />} />
        <Route path="admin/runs/:runId/snapshots/ranking/:snapshotSequence" element={<SnapshotDetailPage mode="ranking" />} />
        <Route path="admin/runs/:runId/snapshots/race" element={<SnapshotsPage mode="race" />} />
        <Route path="admin/runs/:runId/snapshots/race/:snapshotSequence" element={<SnapshotDetailPage mode="race" />} />
        <Route path="admin/diagnostics" element={<AdminDiagnosticsPage />} />
        <Route path="admin/settings" element={<AdminSettingsPage />} />

        <Route path="viewer" element={<ViewerHomePage />} />
        <Route path="viewer/rankings" element={<ViewerRankingsPage />} />
        <Route path="viewer/tournaments" element={<ViewerTournamentsPage />} />
        <Route path="viewer/players" element={<ViewerPlayersPage />} />
        <Route path="viewer/countries" element={<ViewerCountriesPage />} />
        <Route path="viewer/history" element={<ViewerHistoryPage />} />
        <Route path="viewer/records" element={<ViewerRecordsPage />} />
        <Route path="viewer/runs/:runId/rankings" element={<SnapshotsPage mode="ranking" />} />
        <Route path="viewer/runs/:runId/rankings/:snapshotSequence" element={<SnapshotDetailPage mode="ranking" />} />
        <Route path="viewer/runs/:runId/race" element={<SnapshotsPage mode="race" />} />
        <Route path="viewer/runs/:runId/race/:snapshotSequence" element={<SnapshotDetailPage mode="race" />} />
        <Route path="viewer/runs/:runId/tournaments" element={<EventsPage />} />
        <Route path="viewer/runs/:runId/tournaments/:eventId" element={<EventDetailPage />} />
        <Route path="viewer/runs/:runId/calendar" element={<SeasonCalendarPage />} />
        <Route path="viewer/runs/:runId/calendar/:eventId" element={<PlannedEventDetailPage />} />
        <Route path="viewer/runs/:runId/weeks/:week" element={<WeekDetailPage />} />
        <Route path="viewer/runs/:runId/players" element={<PlayersPage />} />
        <Route path="viewer/runs/:runId/players/:playerId/career" element={<PlayerCareerPage />} />
        <Route path="viewer/runs/:runId/countries" element={<NationsPage />} />
        <Route path="viewer/runs/:runId/history" element={<ActivityPage />} />
        <Route path="viewer/runs/:runId/finals" element={<FinalsPage />} />
        <Route path="viewer/runs/:runId/finals/qualification" element={<FinalsQualificationDetailPage />} />
        <Route path="viewer/runs/:runId/finals/result" element={<FinalsResultDetailPage />} />

        <Route path="runs" element={<Navigate to="/admin/runs" replace />} />
        <Route path="runs/:runId" element={<LegacyRunRedirect />} />
        <Route path="runs/:runId/*" element={<LegacyRunRedirect />} />
        <Route path="world" element={<Navigate to="/admin/world" replace />} />
        <Route path="world/*" element={<LegacyWorldRedirect />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  )
}
