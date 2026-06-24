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
import { LandingPage } from './pages/LandingPage'
import {
  AdminHomePage,
  AdminPlayersDatabasePage,
  AdminPlayersPage,
  AdminSeasonsPage,
  AdminSettingsPage,
  AdminTourSeasonsPage,
  AdminTournamentTemplatesPage,
  AdminWorldPage
} from './pages/admin'
import { ViewerHomePage } from './pages/viewer/ViewerHomePage'
import { ViewerRunBrowserPage } from './pages/viewer/ViewerRunBrowserPage'
import {
  ViewerRankingSnapshotDetailPage,
  ViewerRankingsPage,
  ViewerRacePage,
  ViewerRaceSnapshotDetailPage
} from './pages/viewer/rankings'
import { ViewerSeasonHubPage, ViewerTourCalendarPage, ViewerCurrentWeekPage, ViewerTournamentsPage } from './pages/viewer/tour'
import { ViewerPlayersPage, ViewerCountriesPage } from './pages/viewer/people'
import { ViewerSearchPage, ViewerH2HPage, ViewerPlayerComparisonPage, ViewerMatchPredictorPage } from './pages/viewer/explore'
import { ViewerHistoryPage } from './pages/viewer/history'
import { ViewerRecordsPage, ViewerStatsPage } from './pages/viewer/stats'
import {
  ViewerCountriesDeferredPage,
  ViewerCountryRankingPage,
  ViewerH2HSubroutePage,
  ViewerPredictionDeferredPage,
  ViewerPlayersDeferredPage,
  ViewerRankingDeferredPage,
  ViewerStatsDeferredPage,
  ViewerTourDeferredPage
} from './pages/viewer/deferred'
import { AdminTourSeasonsComparePage } from './pages/CalendarComparePage'
import { AdminTourSeasonsValidationPage } from './pages/CalendarValidationPage'
import { AdminTourSeasonsCategoriesPage } from './pages/CategoriesPage'
import { AdminTourSeasonsCategoryDetailPage } from './pages/CategoryDetailPage'
import { AdminTourSeasonsTournamentsPage } from './pages/TournamentsPage'
import { AdminTourSeasonsTournamentDetailPage } from './pages/TournamentDetailPage'
import { AdminTourSeasonsSeasonTemplatesPage } from './pages/SeasonTemplatesPage'
import { SeasonTemplateDraftSandboxPage } from './pages/SeasonTemplateDraftSandboxPage'
import { AdminTourSeasonsSeasonTemplateDetailPage } from './pages/SeasonTemplateDetailPage'
import { AdminCalendarTemplateDetailPage } from './pages/CalendarTemplateDetailPage'
import { AdminCalendarTemplateNewPage } from './pages/CalendarTemplateNewPage'
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
import { ViewerRunSnapshotListPage } from './pages/ViewerRunSnapshotsPage'
import { ViewerRunTournamentDetailPage, ViewerRunTournamentsPage } from './pages/ViewerRunTournamentsPage'
import {
  ViewerRunCountriesPage,
  ViewerRunCountryDetailPage,
  ViewerRunPlayerCareerPage,
  ViewerRunPlayersPage
} from './pages/ViewerRunPlayersCountriesPage'
import { TalentPreviewPage } from './pages/TalentPreviewPage'
import { TalentIntakePage } from './pages/TalentIntakePage'
import { ManualPlayerOverridesPage } from './pages/ManualPlayerOverridesPage'
import { WeekDetailPage } from './pages/WeekDetailPage'
import { ViewerRunCalendarPage, ViewerRunPlannedEventPage, ViewerRunWeekPage } from './pages/ViewerRunCalendarPage'
import {
  ViewerRunFinalsPage,
  ViewerRunFinalsQualificationPage,
  ViewerRunFinalsResultPage,
  ViewerRunHistoryPage
} from './pages/ViewerRunHistoryFinalsPage'
import { WorldGenerationPage } from './pages/WorldGenerationPage'
import { NationsPage } from './pages/NationsPage'
import { WorldPackagePage } from './pages/WorldPackagePage'
import { CountryMomentumPage } from './pages/CountryMomentumPage'
import { AdminSeasonDetailPage } from './pages/SeasonDetailPage'
import { AdminSeasonBuilderPage } from './pages/SeasonBuilderPage'

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
        <Route path="admin/tour-seasons/season-templates/draft-sandbox" element={<SeasonTemplateDraftSandboxPage />} />
        <Route path="admin/tour-seasons/season-templates/new" element={<AdminCalendarTemplateNewPage />} />
        <Route path="admin/tour-seasons/season-templates/calendar/:templateId" element={<AdminCalendarTemplateDetailPage />} />
        <Route path="admin/tour-seasons/season-templates/:templateId" element={<AdminTourSeasonsSeasonTemplateDetailPage />} />
        <Route path="admin/tour-seasons/season-registry" element={<AdminTourSeasonsSeasonRegistryPage />} />
        <Route path="admin/tour-seasons/compare" element={<AdminTourSeasonsComparePage />} />
        <Route path="admin/tour-seasons/validation" element={<AdminTourSeasonsValidationPage />} />
        <Route path="admin/tour-seasons" element={<AdminTourSeasonsPage />} />
        <Route path="admin/tournament-templates" element={<AdminTournamentTemplatesPage />} />
        <Route path="admin/seasons" element={<AdminSeasonsPage />} />
        <Route path="admin/seasons/build" element={<AdminSeasonBuilderPage />} />
        <Route path="admin/seasons/detail/:seasonLabel" element={<AdminSeasonDetailPage />} />
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
        <Route path="viewer/rankings/race" element={<ViewerRacePage />} />
        <Route path="viewer/rankings/next-gen" element={<ViewerRankingDeferredPage kind="next-gen" />} />
        <Route path="viewer/rankings/elo" element={<ViewerRankingDeferredPage kind="elo" />} />
        <Route path="viewer/rankings/power" element={<ViewerRankingDeferredPage kind="power" />} />
        <Route path="viewer/rankings/form" element={<ViewerRankingDeferredPage kind="form" />} />
        <Route path="viewer/rankings/no1-history" element={<ViewerRankingDeferredPage kind="no1-history" />} />
        <Route path="viewer/tour" element={<ViewerSeasonHubPage />} />
        <Route path="viewer/tour/calendar" element={<ViewerTourCalendarPage />} />
        <Route path="viewer/tour/current-week" element={<ViewerCurrentWeekPage />} />
        <Route path="viewer/tour/tournaments" element={<ViewerTournamentsPage />} />
        <Route path="viewer/tour/matches" element={<ViewerTourDeferredPage kind="matches" />} />
        <Route path="viewer/tour/categories" element={<ViewerTourDeferredPage kind="categories" />} />
        <Route path="viewer/tour/champions" element={<ViewerTourDeferredPage kind="champions" />} />
        <Route path="viewer/tournaments" element={<ViewerTournamentsPage />} />
        <Route path="viewer/players" element={<ViewerPlayersPage />} />
        <Route path="viewer/players/all" element={<ViewerPlayersDeferredPage kind="all" />} />
        <Route path="viewer/players/active" element={<ViewerPlayersDeferredPage kind="active" />} />
        <Route path="viewer/players/next-gen" element={<ViewerPlayersDeferredPage kind="next-gen" />} />
        <Route path="viewer/players/retired" element={<ViewerPlayersDeferredPage kind="retired" />} />
        <Route path="viewer/players/compare" element={<ViewerPlayerComparisonPage />} />
        <Route path="viewer/countries" element={<ViewerCountriesPage />} />
        <Route path="viewer/countries/ranking" element={<ViewerCountryRankingPage />} />
        <Route path="viewer/countries/all" element={<ViewerCountriesDeferredPage kind="all" />} />
        <Route path="viewer/countries/hosting" element={<ViewerCountriesDeferredPage kind="hosting" />} />
        <Route path="viewer/countries/talent-pipeline" element={<ViewerCountriesDeferredPage kind="talent-pipeline" />} />
        <Route path="viewer/countries/records" element={<ViewerCountriesDeferredPage kind="records" />} />
        <Route path="viewer/h2h" element={<ViewerH2HPage />} />
        <Route path="viewer/h2h/rivalries" element={<ViewerH2HSubroutePage kind="rivalries" />} />
        <Route path="viewer/h2h/most-played" element={<ViewerH2HSubroutePage kind="most-played" />} />
        <Route path="viewer/h2h/finals-rivalries" element={<ViewerH2HSubroutePage kind="finals-rivalries" />} />
        <Route path="viewer/stats" element={<ViewerStatsPage />} />
        <Route path="viewer/stats/title-leaders" element={<ViewerStatsDeferredPage kind="title-leaders" />} />
        <Route path="viewer/stats/no1-weeks" element={<ViewerStatsDeferredPage kind="no1-weeks" />} />
        <Route path="viewer/stats/streaks" element={<ViewerStatsDeferredPage kind="streaks" />} />
        <Route path="viewer/stats/upsets" element={<ViewerStatsDeferredPage kind="upsets" />} />
        <Route path="viewer/stats/best-seasons" element={<ViewerStatsDeferredPage kind="best-seasons" />} />
        <Route path="viewer/stats/player-stats" element={<ViewerStatsDeferredPage kind="player-stats" />} />
        <Route path="viewer/stats/tournament-stats" element={<ViewerStatsDeferredPage kind="tournament-stats" />} />
        <Route path="viewer/stats/country-stats" element={<ViewerStatsDeferredPage kind="country-stats" />} />
        <Route path="viewer/stats/awards" element={<ViewerStatsDeferredPage kind="awards" />} />
        <Route path="viewer/stats/hall-of-fame" element={<ViewerStatsDeferredPage kind="hall-of-fame" />} />
        <Route path="viewer/stats/era-rankings" element={<ViewerStatsDeferredPage kind="era-rankings" />} />
        <Route path="viewer/records" element={<ViewerRecordsPage />} />
        <Route path="viewer/predictions" element={<ViewerMatchPredictorPage />} />
        <Route path="viewer/predictions/match-predictor" element={<ViewerMatchPredictorPage />} />
        <Route path="viewer/predictions/match-odds" element={<ViewerPredictionDeferredPage kind="match-odds" />} />
        <Route path="viewer/predictions/tournament-odds" element={<ViewerPredictionDeferredPage kind="tournament-odds" />} />
        <Route path="viewer/predictions/finals-qualification" element={<ViewerPredictionDeferredPage kind="finals-qualification" />} />
        <Route path="viewer/predictions/season-end-no1" element={<ViewerPredictionDeferredPage kind="season-end-no1" />} />
        <Route path="viewer/predictions/upset-watch" element={<ViewerPredictionDeferredPage kind="upset-watch" />} />
        <Route path="viewer/predictions/futures" element={<ViewerPredictionDeferredPage kind="futures" />} />
        <Route path="viewer/search" element={<ViewerSearchPage />} />
        <Route path="viewer/history" element={<ViewerHistoryPage />} />
        <Route path="viewer/runs" element={<ViewerRunBrowserPage />} />
        <Route path="viewer/runs/:runId/rankings" element={<ViewerRunSnapshotListPage mode="ranking" />} />
        <Route path="viewer/runs/:runId/rankings/:snapshotSequence" element={<ViewerRankingSnapshotDetailPage />} />
        <Route path="viewer/runs/:runId/race" element={<ViewerRunSnapshotListPage mode="race" />} />
        <Route path="viewer/runs/:runId/race/:snapshotSequence" element={<ViewerRaceSnapshotDetailPage />} />
        <Route path="viewer/runs/:runId/tournaments" element={<ViewerRunTournamentsPage />} />
        <Route path="viewer/runs/:runId/tournaments/:eventId" element={<ViewerRunTournamentDetailPage />} />
        <Route path="viewer/runs/:runId/calendar" element={<ViewerRunCalendarPage />} />
        <Route path="viewer/runs/:runId/calendar/:eventId" element={<ViewerRunPlannedEventPage />} />
        <Route path="viewer/runs/:runId/weeks/:week" element={<ViewerRunWeekPage />} />
        <Route path="viewer/runs/:runId/players" element={<ViewerRunPlayersPage />} />
        <Route path="viewer/runs/:runId/players/:playerId/career" element={<ViewerRunPlayerCareerPage />} />
        <Route path="viewer/runs/:runId/countries" element={<ViewerRunCountriesPage />} />
        <Route path="viewer/runs/:runId/countries/:countryCode" element={<ViewerRunCountryDetailPage />} />
        <Route path="viewer/runs/:runId/history" element={<ViewerRunHistoryPage />} />
        <Route path="viewer/runs/:runId/finals" element={<ViewerRunFinalsPage />} />
        <Route path="viewer/runs/:runId/finals/qualification" element={<ViewerRunFinalsQualificationPage />} />
        <Route path="viewer/runs/:runId/finals/result" element={<ViewerRunFinalsResultPage />} />

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
