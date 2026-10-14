export type AdminNavItem = {
  to: string
  label: string
  children?: AdminNavItem[]
}

export const globalAdminNav: AdminNavItem[] = [
  { to: '/admin', label: 'Home' },
  { to: '/admin/runs', label: 'Runs', children: [
    { to: '/admin/runs', label: 'Run inventory' },
    { to: '/admin/operations', label: 'Simulation Task Center' }
  ] },
  { to: '/admin/packages', label: 'Packages' },
  { to: '/admin/labs', label: 'Test Lab' },
]
export const globalAdminBottomNav: AdminNavItem[] = [
  { to: '/admin/settings', label: 'Settings' }
]

export function runAdminNavFor(runId: string): AdminNavItem[] {
  const base = '/admin/runs/' + encodeURIComponent(runId)
  return [
    { to: base, label: 'Home' },
    { to: base + '/world', label: 'World', children: [
      { to: base + '/world', label: 'World overview' },
      { to: base + '/nations', label: 'Country strength diagnostics' },
      { to: base + '/world-generation', label: 'World Generation' }
    ] },
    { to: base + '/players', label: 'Players', children: [
      { to: base + '/players', label: 'Player list' },
      { to: base + '/players/intake', label: 'Talent Intake' }
    ] },
    { to: base + '/calendar', label: 'Tour', children: [
      { to: base + '/tour/calendar', label: 'Saved Tour Calendar' },
      { to: base + '/calendar', label: 'Season Calendar' },
      { to: base + '/finals', label: 'World Tour Finals' },
      { to: base + '/rollover', label: 'Season Rollover' }
    ] },
    { to: base + '/snapshots/ranking', label: 'Rankings & Analytics', children: [
      { to: base + '/snapshots/ranking', label: 'Ranking Snapshots' },
      { to: base + '/snapshots/race', label: 'Race Snapshots' },
    ] },
    { to: base + '/simulate', label: 'Simulation', children: [
      { to: base + '/simulate', label: 'Simulation controls' },
      { to: base + '/diagnostics', label: 'Run diagnostics' }
    ] },
    { to: base + '/branches', label: 'History & Branches', children: [
      { to: base + '/branches', label: 'Branches & revisions' },
      { to: base + '/bootstrap-lineage', label: 'Bootstrap / Lineage' },
      { to: base + '/season-chain', label: 'Season Chain' },
      { to: base + '/activity', label: 'Activity' },
      { to: base + '/events', label: 'Events' }
    ] }
  ]
}

export function runAdminBottomNavFor(runId: string): AdminNavItem[] {
  return [{ to: '/admin/runs/' + encodeURIComponent(runId) + '/manage', label: 'Run Management' }]
}
