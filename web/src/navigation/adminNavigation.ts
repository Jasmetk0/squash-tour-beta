export type AdminNavItem = {
  to: string
  label: string
}

export const globalAdminNav: AdminNavItem[] = [
  { to: '/admin', label: 'Dashboard' },
  { to: '/admin/world', label: 'World' },
  { to: '/admin/players', label: 'Players' },
  { to: '/admin/tour-seasons', label: 'Tour & Seasons' },
  { to: '/admin/runs', label: 'Runs' },
  { to: '/admin/simulate', label: 'Simulate' },
  { to: '/admin/diagnostics', label: 'Diagnostics' },
  { to: '/admin/settings', label: 'Settings' }
]

export function runAdminNavFor(runId: string): AdminNavItem[] {
  return [
    { to: `/admin/runs/${runId}`, label: 'Home' },
    { to: `/admin/runs/${runId}/events`, label: 'Events' },
    { to: `/admin/runs/${runId}/calendar`, label: 'Season Calendar' },
    { to: `/admin/runs/${runId}/activity`, label: 'Activity' },
    { to: `/admin/runs/${runId}/players`, label: 'Players' },
    { to: `/admin/runs/${runId}/nations`, label: 'Nations' },
    { to: `/admin/runs/${runId}/diagnostics`, label: 'Diagnostics' },
    { to: `/admin/runs/${runId}/world-generation`, label: 'World Generation' },
    { to: `/admin/runs/${runId}/finals`, label: 'World Tour Finals' },
    { to: `/admin/runs/${runId}/rollover`, label: 'Season Rollover' },
    { to: `/admin/runs/${runId}/bootstrap-lineage`, label: 'Bootstrap / Lineage' },
    { to: `/admin/runs/${runId}/season-chain`, label: 'Season Chain' },
    { to: `/admin/runs/${runId}/snapshots/ranking`, label: 'Ranking Snapshots' },
    { to: `/admin/runs/${runId}/snapshots/race`, label: 'Race Snapshots' }
  ]
}
