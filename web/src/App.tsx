import { Navigate, Route, Routes } from 'react-router-dom'

import { Layout } from './components/Layout'
import { BootstrapLineagePage } from './pages/BootstrapLineagePage'
import { DashboardPage } from './pages/DashboardPage'
import { EventsPage } from './pages/EventsPage'
import { FinalsPage } from './pages/FinalsPage'
import { RolloverPage } from './pages/RolloverPage'
import { RunPage } from './pages/RunPage'
import { SnapshotsPage } from './pages/SnapshotsPage'

export default function App(): JSX.Element {
  return (
    <Routes>
      <Route path="/" element={<Layout />}>
        <Route index element={<DashboardPage />} />
        <Route path="runs/:runId" element={<RunPage />} />
        <Route path="runs/:runId/events" element={<EventsPage />} />
        <Route path="runs/:runId/finals" element={<FinalsPage />} />
        <Route path="runs/:runId/rollover" element={<RolloverPage />} />
        <Route path="runs/:runId/bootstrap-lineage" element={<BootstrapLineagePage />} />
        <Route path="runs/:runId/snapshots/ranking" element={<SnapshotsPage mode="ranking" />} />
        <Route path="runs/:runId/snapshots/race" element={<SnapshotsPage mode="race" />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  )
}
