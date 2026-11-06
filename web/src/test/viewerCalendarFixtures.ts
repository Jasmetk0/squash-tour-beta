// Typed mock HTTP responses for component contracts, not real sporting evidence.
import type {
  ViewerCalendarEvent, ViewerRunCalendar, ViewerTournamentHistory,
  ViewerTournamentHistoryItem, ViewerOfficialRankingHistory,
  ViewerOfficialRankingHistoryItem, ViewerFinalsRaceHistory,
  ViewerFinalsRacePublication,
} from '../api/types'

export const CALENDAR_RUN = 'run alpha'
export const CALENDAR_BRANCH = 'viewer-branch'

export function calendarEvent(overrides: Partial<ViewerCalendarEvent> = {}): ViewerCalendarEvent {
  const week = overrides.season_week ?? 5
  return {
    event_id: 'EVENT/1', season: '2028/2029', season_week: week,
    calendar_year: 2028, year_week: week, template_id: 'WT-PLAT',
    event_name: 'Source Open', category: 'PLATINUM', tour_level: 'WORLD_TOUR',
    host_country: 'EGY', host_city: 'Cairo', region: 'AFRICA',
    duration_in_season_weeks: 1, start_season_week: week, end_season_week: week,
    status: 'planned', main_draw_size: 32, qualification_draw_size: 16,
    seeds_count: 8, qualifier_spots: 4, wild_cards: 2, byes: 0, prestige: 9,
    ...overrides,
  }
}

export function savedCalendar(events = [calendarEvent()], run = CALENDAR_RUN): ViewerRunCalendar {
  const seasons = [...new Set(events.map(e => String(e.season)))].map(season => {
    const selected = events.filter(e => String(e.season) === season)
    return { season, event_count: selected.length, events: selected }
  })
  return {
    schema_version: 'viewer_run_calendar.v1', product_run_id: run,
    viewer_branch_id: CALENDAR_BRANCH, season_count: seasons.length,
    event_count: events.length, seasons,
  }
}

export function historyEvent(event = calendarEvent(), overrides: Partial<ViewerTournamentHistoryItem> = {}): ViewerTournamentHistoryItem {
  return {
    event_id: event.event_id, season: String(event.season), season_week: event.season_week,
    event_name: event.event_name, template_id: event.template_id,
    category: event.category, tour_level: event.tour_level, host_country: event.host_country,
    host_city: event.host_city, region: event.region, main_draw_size: event.main_draw_size,
    qualification_draw_size: event.qualification_draw_size, seeds_count: event.seeds_count,
    qualifier_spots: event.qualifier_spots, wild_cards: event.wild_cards, byes: event.byes,
    ranking_status: 'ranked', result_published: false,
    champion_player_id: null, finalist_player_id: null, ...overrides,
  }
}

export function savedHistory(tournaments: ViewerTournamentHistoryItem[] = [], run = CALENDAR_RUN): ViewerTournamentHistory {
  return {
    schema_version: 'viewer_tournament_history.v1', product_run_id: run,
    viewer_branch_id: CALENDAR_BRANCH, tournament_count: tournaments.length,
    published_result_count: tournaments.filter(t => t.result_published).length, tournaments,
  }
}

export function rankingPublication(week = 5): ViewerOfficialRankingHistoryItem {
  return {
    season_index: 28, week, week_ordinal: 28 * 61 + week - 1,
    snapshot_fingerprint: 'a'.repeat(64), policy_id: 'best-15', best_n: 15, row_count: 0,
  }
}

export function savedRankings(publications: ViewerOfficialRankingHistoryItem[] = []): ViewerOfficialRankingHistory {
  return {
    schema_version: 'viewer_official_ranking_history.v1', product_run_id: CALENDAR_RUN,
    viewer_branch_id: CALENDAR_BRANCH, public_head_ordinal: 28 * 61 + 60,
    publication_count: publications.length, publications,
  }
}

export function racePublication(week = 5): ViewerFinalsRacePublication {
  return {
    schema_version: 'viewer_finals_race_publication.v1', product_run_id: CALENDAR_RUN,
    viewer_branch_id: CALENDAR_BRANCH, target_season_index: 28,
    cutoff_season_index: 28, cutoff_week: week, best_n: 8,
    selection_published: false, finals_event_id: null, rows: [],
  }
}

export function savedRace(publications: ViewerFinalsRacePublication[] = []): ViewerFinalsRaceHistory {
  return {
    schema_version: 'viewer_finals_race_history.v1', product_run_id: CALENDAR_RUN,
    viewer_branch_id: CALENDAR_BRANCH,
    latest_target_season_index: publications.length ? publications[publications.length - 1].target_season_index : null,
    publications,
  }
}
