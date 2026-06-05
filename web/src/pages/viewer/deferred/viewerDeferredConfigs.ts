export type ViewerRankingDeferredKind =
  | 'next-gen'
  | 'elo'
  | 'power'
  | 'form'
  | 'no1-history'

export type ViewerDeferredConfig = {
  title: string
  deferredCopy: string
}

export const viewerRankingDeferredConfigs: Record<
  ViewerRankingDeferredKind,
  ViewerDeferredConfig
> = {
  'next-gen': {
    title: 'Next Gen Race',
    deferredCopy:
      'No Next Gen ranking table is shown until a real Next Gen ranking read model exists.',
  },
  elo: {
    title: 'Elo Ranking',
    deferredCopy:
      'No Elo ranking table is shown until a real Elo ranking read model exists.',
  },
  power: {
    title: 'Power Rating',
    deferredCopy:
      'No Power Rating table is shown until a real Power Rating read model exists.',
  },
  form: {
    title: 'Form Ranking',
    deferredCopy:
      'No form ranking table is shown until a real form ranking read model exists.',
  },
  'no1-history': {
    title: 'No.1 History',
    deferredCopy:
      'No No.1 history table is shown until a real ranking history read model exists.',
  },
}

export type ViewerPlayersDeferredKind =
  | 'all'
  | 'active'
  | 'next-gen'
  | 'retired'

export const viewerPlayersDeferredConfigs: Record<
  ViewerPlayersDeferredKind,
  ViewerDeferredConfig
> = {
  all: {
    title: 'All Players',
    deferredCopy:
      'No full player directory is shown until a real player directory read model exists.',
  },
  active: {
    title: 'Active Players',
    deferredCopy:
      'No active-player list is shown until a real player status read model exists.',
  },
  'next-gen': {
    title: 'Prospects / Next Gen',
    deferredCopy:
      'No prospects list is shown until a real Next Gen player read model exists.',
  },
  retired: {
    title: 'Retired Players',
    deferredCopy:
      'No retired-player list is shown until a real player career-status read model exists.',
  },
}

export type ViewerCountriesDeferredKind =
  | 'ranking'
  | 'all'
  | 'hosting'
  | 'talent-pipeline'
  | 'records'

export const viewerCountriesDeferredConfigs: Record<
  ViewerCountriesDeferredKind,
  ViewerDeferredConfig
> = {
  ranking: {
    title: 'Country Ranking',
    deferredCopy:
      'No country ranking table is shown until a real country ranking read model exists.',
  },
  all: {
    title: 'All Countries',
    deferredCopy:
      'No full country directory is shown until a real country directory read model exists.',
  },
  hosting: {
    title: 'Hosting Nations',
    deferredCopy:
      'No hosting nation table is shown until a real hosting read model exists.',
  },
  'talent-pipeline': {
    title: 'Talent Pipeline',
    deferredCopy:
      'No talent pipeline table is shown until a real country talent read model exists.',
  },
  records: {
    title: 'Country Records',
    deferredCopy:
      'No country records table is shown until a real country records read model exists.',
  },
}

export type ViewerStatsDeferredKind =
  | 'title-leaders'
  | 'no1-weeks'
  | 'streaks'
  | 'upsets'
  | 'best-seasons'
  | 'player-stats'
  | 'tournament-stats'
  | 'country-stats'
  | 'awards'
  | 'hall-of-fame'
  | 'era-rankings'

export const viewerStatsDeferredConfigs: Record<
  ViewerStatsDeferredKind,
  ViewerDeferredConfig
> = {
  'title-leaders': {
    title: 'Title Leaders',
    deferredCopy:
      'No title leader table is shown until a real records read model exists.',
  },
  'no1-weeks': {
    title: 'Weeks at No.1',
    deferredCopy:
      'No weeks-at-No.1 table is shown until a real ranking history read model exists.',
  },
  streaks: {
    title: 'Streaks',
    deferredCopy:
      'No streak table is shown until a real streak records read model exists.',
  },
  upsets: {
    title: 'Biggest Upsets',
    deferredCopy:
      'No upset table is shown until real match and ranking history read models exist.',
  },
  'best-seasons': {
    title: 'Best Seasons',
    deferredCopy:
      'No best-season table is shown until a real season statistics read model exists.',
  },
  'player-stats': {
    title: 'Player Stats',
    deferredCopy:
      'No player statistics table is shown until a real player statistics read model exists.',
  },
  'tournament-stats': {
    title: 'Tournament Stats',
    deferredCopy:
      'No tournament statistics table is shown until a real tournament statistics read model exists.',
  },
  'country-stats': {
    title: 'Country Stats',
    deferredCopy:
      'No country statistics table is shown until a real country statistics read model exists.',
  },
  awards: {
    title: 'Awards',
    deferredCopy: 'No awards are shown until a real awards read model exists.',
  },
  'hall-of-fame': {
    title: 'Hall of Fame',
    deferredCopy:
      'No Hall of Fame entries are shown until a real Hall of Fame read model exists.',
  },
  'era-rankings': {
    title: 'Era Rankings',
    deferredCopy:
      'No era rankings are shown until a real era comparison read model exists.',
  },
}

export type ViewerTourDeferredKind = 'matches' | 'categories' | 'champions'

export const viewerTourDeferredConfigs: Record<
  ViewerTourDeferredKind,
  ViewerDeferredConfig
> = {
  matches: {
    title: 'Match Center',
    deferredCopy:
      'No match list is shown until a real match read model exists.',
  },
  categories: {
    title: 'Tournament Categories',
    deferredCopy:
      'No connected category breakdown is shown until a real category read model exists.',
  },
  champions: {
    title: 'Past Champions',
    deferredCopy:
      'No champions index is shown until a real champions read model exists.',
  },
}

export type ViewerH2HSubrouteKind =
  | 'rivalries'
  | 'most-played'
  | 'finals-rivalries'

export type ViewerH2HSubrouteContent = {
  title: string
  note: string
}

export const viewerH2HSubrouteContent: Record<
  ViewerH2HSubrouteKind,
  ViewerH2HSubrouteContent
> = {
  rivalries: {
    title: 'Rivalries',
    note: 'No rivalry list is shown until direct match records are available.',
  },
  'most-played': {
    title: 'Most Played Matchups',
    note: 'No matchup list is shown until completed match counts are available.',
  },
  'finals-rivalries': {
    title: 'Finals Rivalries',
    note: 'No finals rivalry list is shown until final-round match records are available.',
  },
}

export type ViewerPredictionDeferredKind =
  | 'match-odds'
  | 'tournament-odds'
  | 'finals-qualification'
  | 'season-end-no1'
  | 'upset-watch'
  | 'futures'

export const viewerPredictionDeferredConfigs: Record<
  ViewerPredictionDeferredKind,
  ViewerDeferredConfig
> = {
  'match-odds': {
    title: 'Match Odds',
    deferredCopy: 'No odds are shown until a real odds read model exists.',
  },
  'tournament-odds': {
    title: 'Tournament Odds',
    deferredCopy:
      'No tournament odds are shown until a real tournament odds read model exists.',
  },
  'finals-qualification': {
    title: 'Finals Qualification',
    deferredCopy:
      'No finals qualification probability is shown until a real qualification probability read model exists.',
  },
  'season-end-no1': {
    title: 'Season-End No.1',
    deferredCopy:
      'No season-end No.1 probability is shown until a real season projection read model exists.',
  },
  'upset-watch': {
    title: 'Upset Watch',
    deferredCopy: 'No upset chance is shown until a real upset model exists.',
  },
  futures: {
    title: 'Futures',
    deferredCopy:
      'No futures markets are shown until a real futures read model exists.',
  },
}
