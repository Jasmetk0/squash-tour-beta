export type TournamentCategoryTourLevel = 'WORLD_TOUR' | 'ELITE_TOUR' | 'CHALLENGER_TOUR' | 'DEVELOPMENT_TOUR'

export type TournamentCategoryVisualTone =
  | 'world-championship'
  | 'world-finals'
  | 'diamond'
  | 'emerald'
  | 'platinium'
  | 'gold'
  | 'silver'
  | 'bronze'
  | 'copper'
  | 'cobalt'
  | 'iron'
  | 'nickel'
  | 'tin'
  | 'zinc'
  | 'challenger'
  | 'future'

export type TournamentCategoryCatalogEntry = {
  code: string
  name: string
  tourLevel: TournamentCategoryTourLevel
  tourLevelName: string
  sortOrder: number
  stickerLabel: string
  stickerSymbol: string
  visualTone: TournamentCategoryVisualTone
  shortDescription: string
}

export type TournamentCategoryTourLevelGroup = {
  tourLevel: TournamentCategoryTourLevel
  tourLevelName: string
  categories: TournamentCategoryCatalogEntry[]
}

const TOUR_LEVEL_NAMES: Record<TournamentCategoryTourLevel, string> = {
  WORLD_TOUR: 'World Tour',
  ELITE_TOUR: 'Elite Tour',
  CHALLENGER_TOUR: 'Challenger Tour',
  DEVELOPMENT_TOUR: 'Development Tour'
}

export const tournamentCategoryCatalog: TournamentCategoryCatalogEntry[] = [
  {
    code: 'WORLD_CHAMPIONSHIP',
    name: 'World Championship',
    tourLevel: 'WORLD_TOUR',
    tourLevelName: TOUR_LEVEL_NAMES.WORLD_TOUR,
    sortOrder: 10,
    stickerLabel: 'WC',
    stickerSymbol: '🌍',
    visualTone: 'world-championship',
    shortDescription: 'Stable identity for the world title category.'
  },
  {
    code: 'WORLD_TOUR_FINALS',
    name: 'World Tour Finals',
    tourLevel: 'WORLD_TOUR',
    tourLevelName: TOUR_LEVEL_NAMES.WORLD_TOUR,
    sortOrder: 20,
    stickerLabel: 'Finals',
    stickerSymbol: '🏆',
    visualTone: 'world-finals',
    shortDescription: 'Stable identity for the season-ending finals category.'
  },
  {
    code: 'DIAMOND',
    name: 'Diamond',
    tourLevel: 'WORLD_TOUR',
    tourLevelName: TOUR_LEVEL_NAMES.WORLD_TOUR,
    sortOrder: 30,
    stickerLabel: 'Diamond',
    stickerSymbol: '💎',
    visualTone: 'diamond',
    shortDescription: 'Stable identity for Diamond-tier World Tour events.'
  },
  {
    code: 'EMERALD',
    name: 'Emerald',
    tourLevel: 'WORLD_TOUR',
    tourLevelName: TOUR_LEVEL_NAMES.WORLD_TOUR,
    sortOrder: 40,
    stickerLabel: 'Emerald',
    stickerSymbol: '✳',
    visualTone: 'emerald',
    shortDescription: 'Stable identity for Emerald-tier World Tour events.'
  },
  {
    code: 'PLATINIUM',
    name: 'Platinium',
    tourLevel: 'WORLD_TOUR',
    tourLevelName: TOUR_LEVEL_NAMES.WORLD_TOUR,
    sortOrder: 50,
    stickerLabel: 'Platinium',
    stickerSymbol: '🛡',
    visualTone: 'platinium',
    shortDescription: 'Stable identity for Platinium-tier World Tour events.'
  },
  {
    code: 'GOLD',
    name: 'Gold',
    tourLevel: 'WORLD_TOUR',
    tourLevelName: TOUR_LEVEL_NAMES.WORLD_TOUR,
    sortOrder: 60,
    stickerLabel: 'Gold',
    stickerSymbol: '🥇',
    visualTone: 'gold',
    shortDescription: 'Stable identity for Gold-tier World Tour events.'
  },
  {
    code: 'SILVER',
    name: 'Silver',
    tourLevel: 'WORLD_TOUR',
    tourLevelName: TOUR_LEVEL_NAMES.WORLD_TOUR,
    sortOrder: 70,
    stickerLabel: 'Silver',
    stickerSymbol: '🥈',
    visualTone: 'silver',
    shortDescription: 'Stable identity for Silver-tier World Tour events.'
  },
  {
    code: 'BRONZE',
    name: 'Bronze',
    tourLevel: 'WORLD_TOUR',
    tourLevelName: TOUR_LEVEL_NAMES.WORLD_TOUR,
    sortOrder: 80,
    stickerLabel: 'Bronze',
    stickerSymbol: '🥉',
    visualTone: 'bronze',
    shortDescription: 'Stable identity for Bronze-tier World Tour events.'
  },
  {
    code: 'COPPER',
    name: 'Copper',
    tourLevel: 'ELITE_TOUR',
    tourLevelName: TOUR_LEVEL_NAMES.ELITE_TOUR,
    sortOrder: 110,
    stickerLabel: 'Copper',
    stickerSymbol: '◈',
    visualTone: 'copper',
    shortDescription: 'Stable identity for Copper-tier Elite Tour events.'
  },
  {
    code: 'COBALT',
    name: 'Cobalt',
    tourLevel: 'ELITE_TOUR',
    tourLevelName: TOUR_LEVEL_NAMES.ELITE_TOUR,
    sortOrder: 120,
    stickerLabel: 'Cobalt',
    stickerSymbol: '◆',
    visualTone: 'cobalt',
    shortDescription: 'Stable identity for Cobalt-tier Elite Tour events.'
  },
  {
    code: 'IRON',
    name: 'Iron',
    tourLevel: 'ELITE_TOUR',
    tourLevelName: TOUR_LEVEL_NAMES.ELITE_TOUR,
    sortOrder: 130,
    stickerLabel: 'Iron',
    stickerSymbol: '⚙',
    visualTone: 'iron',
    shortDescription: 'Stable identity for Iron-tier Elite Tour events.'
  },
  {
    code: 'NICKEL',
    name: 'Nickel',
    tourLevel: 'ELITE_TOUR',
    tourLevelName: TOUR_LEVEL_NAMES.ELITE_TOUR,
    sortOrder: 140,
    stickerLabel: 'Nickel',
    stickerSymbol: '◇',
    visualTone: 'nickel',
    shortDescription: 'Stable identity for Nickel-tier Elite Tour events.'
  },
  {
    code: 'TIN',
    name: 'Tin',
    tourLevel: 'ELITE_TOUR',
    tourLevelName: TOUR_LEVEL_NAMES.ELITE_TOUR,
    sortOrder: 150,
    stickerLabel: 'Tin',
    stickerSymbol: '▣',
    visualTone: 'tin',
    shortDescription: 'Stable identity for Tin-tier Elite Tour events.'
  },
  {
    code: 'ZINC',
    name: 'Zinc',
    tourLevel: 'ELITE_TOUR',
    tourLevelName: TOUR_LEVEL_NAMES.ELITE_TOUR,
    sortOrder: 160,
    stickerLabel: 'Zinc',
    stickerSymbol: '✦',
    visualTone: 'zinc',
    shortDescription: 'Stable identity for Zinc-tier Elite Tour events.'
  },
  {
    code: 'CHALLENGER_100',
    name: 'Challenger 100',
    tourLevel: 'CHALLENGER_TOUR',
    tourLevelName: TOUR_LEVEL_NAMES.CHALLENGER_TOUR,
    sortOrder: 210,
    stickerLabel: 'C100',
    stickerSymbol: '',
    visualTone: 'challenger',
    shortDescription: 'Stable identity for Challenger 100 events.'
  },
  {
    code: 'CHALLENGER_80',
    name: 'Challenger 80',
    tourLevel: 'CHALLENGER_TOUR',
    tourLevelName: TOUR_LEVEL_NAMES.CHALLENGER_TOUR,
    sortOrder: 220,
    stickerLabel: 'C80',
    stickerSymbol: '',
    visualTone: 'challenger',
    shortDescription: 'Stable identity for Challenger 80 events.'
  },
  {
    code: 'CHALLENGER_60',
    name: 'Challenger 60',
    tourLevel: 'CHALLENGER_TOUR',
    tourLevelName: TOUR_LEVEL_NAMES.CHALLENGER_TOUR,
    sortOrder: 230,
    stickerLabel: 'C60',
    stickerSymbol: '',
    visualTone: 'challenger',
    shortDescription: 'Stable identity for Challenger 60 events.'
  },
  {
    code: 'CHALLENGER_40',
    name: 'Challenger 40',
    tourLevel: 'CHALLENGER_TOUR',
    tourLevelName: TOUR_LEVEL_NAMES.CHALLENGER_TOUR,
    sortOrder: 240,
    stickerLabel: 'C40',
    stickerSymbol: '',
    visualTone: 'challenger',
    shortDescription: 'Stable identity for Challenger 40 events.'
  },
  {
    code: 'FUTURE_25',
    name: 'Future 25',
    tourLevel: 'DEVELOPMENT_TOUR',
    tourLevelName: TOUR_LEVEL_NAMES.DEVELOPMENT_TOUR,
    sortOrder: 310,
    stickerLabel: 'F25',
    stickerSymbol: '',
    visualTone: 'future',
    shortDescription: 'Stable identity for Future 25 development events.'
  },
  {
    code: 'FUTURE_15',
    name: 'Future 15',
    tourLevel: 'DEVELOPMENT_TOUR',
    tourLevelName: TOUR_LEVEL_NAMES.DEVELOPMENT_TOUR,
    sortOrder: 320,
    stickerLabel: 'F15',
    stickerSymbol: '',
    visualTone: 'future',
    shortDescription: 'Stable identity for Future 15 development events.'
  },
  {
    code: 'FUTURE_10',
    name: 'Future 10',
    tourLevel: 'DEVELOPMENT_TOUR',
    tourLevelName: TOUR_LEVEL_NAMES.DEVELOPMENT_TOUR,
    sortOrder: 330,
    stickerLabel: 'F10',
    stickerSymbol: '',
    visualTone: 'future',
    shortDescription: 'Stable identity for Future 10 development events.'
  },
  {
    code: 'FUTURE_5',
    name: 'Future 5',
    tourLevel: 'DEVELOPMENT_TOUR',
    tourLevelName: TOUR_LEVEL_NAMES.DEVELOPMENT_TOUR,
    sortOrder: 340,
    stickerLabel: 'F5',
    stickerSymbol: '',
    visualTone: 'future',
    shortDescription: 'Stable identity for Future 5 development events.'
  }
]

const tourLevelOrder: TournamentCategoryTourLevel[] = ['WORLD_TOUR', 'ELITE_TOUR', 'CHALLENGER_TOUR', 'DEVELOPMENT_TOUR']

export const tournamentCategoryGroups: TournamentCategoryTourLevelGroup[] = tourLevelOrder.map((tourLevel) => ({
  tourLevel,
  tourLevelName: TOUR_LEVEL_NAMES[tourLevel],
  categories: tournamentCategoryCatalog
    .filter((category) => category.tourLevel === tourLevel)
    .sort((left, right) => left.sortOrder - right.sortOrder)
}))
