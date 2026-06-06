import type {
  EventRecord,
  RaceSnapshot,
  RankingSnapshot,
  SeasonStateResponse,
} from "../../../api/types";
import {
  viewerPlannedEventPath,
  viewerRacePath,
  viewerRaceSnapshotPath,
  viewerRankingsPath,
  viewerRankingSnapshotPath,
  viewerRunsPath,
  viewerSeasonCalendarPath,
  viewerTournamentDetailPath,
  viewerTournamentsPath,
  viewerWeekDetailPath,
} from "../../../viewer/viewerRoutes";
import type {
  PlannedEventContext,
  ViewerEventDetailLink,
  ViewerEventMetadataItem,
} from "./viewerEventDetailDisplay";
import { resolvePlannedEventStatusLabel } from "./viewerPlannedEventDetailDisplay";

export type WeekSnapshotPublication = RankingSnapshot | RaceSnapshot;

export function parseViewerWeekParam(week: string | undefined): number | null {
  if (!week) return null;
  const parsedWeek = Number(week);
  if (!Number.isInteger(parsedWeek) || parsedWeek < 1) return null;
  return parsedWeek;
}

export function plannedEventsForWeek(
  seasonState: SeasonStateResponse["season_state"] | null | undefined,
  week: number | null,
): PlannedEventContext[] {
  if (week == null) return [];

  return (seasonState?.ordered_events ?? [])
    .map((event, planIndex) => ({ ...event, planIndex }))
    .filter((event) => event.week === week);
}

export function sourceEventIdsForWeek(
  plannedEvents: PlannedEventContext[] | null | undefined,
): Set<string> {
  return new Set((plannedEvents ?? []).map((event) => event.event_id));
}

export function persistedEventsForWeek(
  events: EventRecord[] | null | undefined,
  week: number | null,
  sourceEventIds: Set<string> = new Set(),
): EventRecord[] {
  if (week == null) return [];

  return (events ?? []).filter(
    (event) => event.week === week || sourceEventIds.has(event.event_id),
  );
}

export function persistedEventsByExactId(
  events: EventRecord[] | null | undefined,
): Map<string, EventRecord> {
  return new Map((events ?? []).map((event) => [event.event_id, event]));
}

export function snapshotsForWeekSourceEvents<T extends WeekSnapshotPublication>(
  snapshots: T[] | null | undefined,
  sourceEventIds: Set<string>,
): T[] {
  return (snapshots ?? []).filter((snapshot) =>
    Boolean(
      snapshot.source_event_id && sourceEventIds.has(snapshot.source_event_id),
    ),
  );
}

export function completedPlannedEventsForWeek(
  plannedEvents: PlannedEventContext[] | null | undefined,
  completedEventIds: Iterable<string> | null | undefined,
): PlannedEventContext[] {
  const completed = new Set(completedEventIds ?? []);
  return (plannedEvents ?? []).filter((event) => completed.has(event.event_id));
}

export function buildWeekDetailMetadataItems({
  runId,
  week,
  season,
  plannedEventCount,
  persistedEventCount,
  rankingPublicationCount,
  racePublicationCount,
  nextEventIndex,
  completedPlannedEventCount,
}: {
  runId: string;
  week: number;
  season?: number | null;
  plannedEventCount: number;
  persistedEventCount: number;
  rankingPublicationCount: number;
  racePublicationCount: number;
  nextEventIndex?: number | null;
  completedPlannedEventCount: number;
}): ViewerEventMetadataItem[] {
  return [
    { label: "Run ID", value: runId || "unknown" },
    { label: "Week number", value: week },
    { label: "Season", value: season ?? "—" },
    { label: "Planned events this week", value: plannedEventCount },
    { label: "Persisted events this week", value: persistedEventCount },
    { label: "Ranking publications this week", value: rankingPublicationCount },
    { label: "Race publications this week", value: racePublicationCount },
    { label: "Next event index", value: nextEventIndex ?? "—" },
    {
      label: "Completed planned events this week",
      value: completedPlannedEventCount,
    },
  ];
}

export function buildWeekPlannedEventMetadataItems({
  event,
  orderedEventCount,
  nextEventIndex,
  completedEventIds,
  persistedEvent,
}: {
  event: PlannedEventContext;
  orderedEventCount?: number;
  nextEventIndex: number;
  completedEventIds?: Iterable<string>;
  persistedEvent?: EventRecord | null;
}): ViewerEventMetadataItem[] {
  return [
    { label: "Event ID", value: event.event_id },
    { label: "Season", value: event.season },
    { label: "Week", value: `W${event.week}` },
    { label: "Tour", value: event.tour },
    { label: "Category", value: event.category },
    { label: "Template ID", value: event.template_id },
    { label: "Plan index", value: event.planIndex },
    {
      label: "Plan position",
      value:
        orderedEventCount == null
          ? event.planIndex + 1
          : `${event.planIndex + 1} of ${orderedEventCount}`,
    },
    {
      label: "Planned status",
      value: resolvePlannedEventStatusLabel({
        eventId: event.event_id,
        planIndex: event.planIndex,
        nextEventIndex,
        completedEventIds,
      }),
    },
    {
      label: "Persisted event record",
      value: persistedEvent ? "Available" : "Not available",
    },
  ];
}

export function buildWeekPersistedEventMetadataItems(
  event: EventRecord,
): ViewerEventMetadataItem[] {
  return [
    { label: "Event ID", value: event.event_id },
    { label: "Event sequence", value: event.event_sequence ?? "—" },
    { label: "Template ID", value: event.template_id ?? "—" },
  ];
}

export function buildWeekEventLinks({
  runId,
  eventId,
  hasPlanned,
  hasPersisted,
}: {
  runId: string;
  eventId: string;
  hasPlanned?: boolean;
  hasPersisted?: boolean;
}): ViewerEventDetailLink[] {
  const links: ViewerEventDetailLink[] = [];

  if (hasPlanned)
    links.push({
      label: "Open planned event",
      href: viewerPlannedEventPath(runId, eventId),
    });
  if (hasPersisted)
    links.push({
      label: "Open tournament detail",
      href: viewerTournamentDetailPath(runId, eventId),
    });

  return links;
}

export function buildWeekContextLinks({
  runId,
  week,
  rankingSnapshotSequences = [],
  raceSnapshotSequences = [],
}: {
  runId: string;
  week: number;
  rankingSnapshotSequences?: number[];
  raceSnapshotSequences?: number[];
}): ViewerEventDetailLink[] {
  return [
    { label: "Run browser", href: viewerRunsPath() },
    { label: "Season calendar", href: viewerSeasonCalendarPath(runId) },
    { label: "Tournament list", href: viewerTournamentsPath(runId) },
    { label: `Week W${week}`, href: viewerWeekDetailPath(runId, week) },
    { label: "Ranking snapshots", href: viewerRankingsPath(runId) },
    { label: "Race snapshots", href: viewerRacePath(runId) },
    ...rankingSnapshotSequences.map((sequence) => ({
      label: `Ranking publication #${sequence}`,
      href: viewerRankingSnapshotPath(runId, sequence),
    })),
    ...raceSnapshotSequences.map((sequence) => ({
      label: `Race publication #${sequence}`,
      href: viewerRaceSnapshotPath(runId, sequence),
    })),
  ];
}
