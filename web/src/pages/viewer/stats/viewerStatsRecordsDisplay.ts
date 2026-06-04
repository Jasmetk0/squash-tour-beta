export type ViewerRecordsLandingKind = 'records' | 'stats'

export type ViewerDeferredStatsRecordsGroup = {
  title: string
  description: string
}

export type ViewerStatsRecordsLandingConfig = {
  title: string
  shellDescription: string
  activeShellDescription: string
  overviewTitle: string
  overviewDescription: string
  deferredGroupsTitle: string
  deferredGroupsLabel: string
}

export const deferredRecordGroups: ViewerDeferredStatsRecordsGroup[] = [
  { title: 'Title Leaders', description: 'needs dedicated records read model.' },
  { title: 'Weeks at No.1', description: 'needs dedicated records read model.' },
  { title: 'Streaks', description: 'needs dedicated records read model.' },
  { title: 'Biggest Upsets', description: 'needs match/prediction read model.' },
  { title: 'Best Seasons', description: 'needs historical stats read model.' }
]

export const deferredStatsGroups: ViewerDeferredStatsRecordsGroup[] = [
  { title: 'Player Stats', description: 'needs dedicated player statistics read model.' },
  { title: 'Tournament Stats', description: 'needs dedicated tournament statistics read model.' },
  { title: 'Country Stats', description: 'needs dedicated country statistics read model.' },
  { title: 'Awards', description: 'needs dedicated awards read model.' },
  { title: 'Hall of Fame', description: 'needs dedicated Hall of Fame read model.' },
  { title: 'Era Rankings', description: 'needs dedicated era comparison read model.' }
]

export function getStatsRecordsLandingConfig(kind: ViewerRecordsLandingKind): ViewerStatsRecordsLandingConfig {
  const isStats = kind === 'stats'

  return {
    title: isStats ? 'Stats' : 'Records',
    shellDescription: isStats
      ? 'Stats library destination prepared for connected run-scoped statistical read models.'
      : 'Record book destination prepared for statistics, milestones, and historical achievements.',
    activeShellDescription: isStats
      ? 'Conservative Stats landing using existing active-run metadata only.'
      : 'Conservative Records landing using existing active-run metadata only.',
    overviewTitle: isStats ? 'Stats Overview' : 'Records Overview',
    overviewDescription: isStats
      ? 'Read-only statistics landing showing only available active-run source metadata until real stat read models exist.'
      : 'Read-only record book landing showing only available active-run source metadata until real record read models exist.',
    deferredGroupsTitle: isStats ? 'Deferred stat groups' : 'Deferred record groups',
    deferredGroupsLabel: isStats ? 'Deferred stat groups' : 'Deferred record groups'
  }
}

export function getStatsRecordsDeferredGroups(kind: ViewerRecordsLandingKind): ViewerDeferredStatsRecordsGroup[] {
  return kind === 'stats' ? deferredStatsGroups : deferredRecordGroups
}

export function buildStatsRecordsSourceLinks(args: {
  activeRunId: string
  viewerRunsPath: () => string
  viewerTournamentsPath: (runId: string) => string
  viewerRankingsPath: (runId: string) => string
  viewerRacePath: (runId: string) => string
  viewerFinalsPath: (runId: string) => string
}): { label: string; to: string }[] {
  return [
    { label: 'Open run browser', to: args.viewerRunsPath() },
    { label: 'Open active run tournaments', to: args.viewerTournamentsPath(args.activeRunId) },
    { label: 'Open active run rankings', to: args.viewerRankingsPath(args.activeRunId) },
    { label: 'Open active run race', to: args.viewerRacePath(args.activeRunId) },
    { label: 'Open active run finals', to: args.viewerFinalsPath(args.activeRunId) }
  ]
}
