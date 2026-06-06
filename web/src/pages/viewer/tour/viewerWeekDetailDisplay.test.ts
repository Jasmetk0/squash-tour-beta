import { describe, expect, it } from "vitest";

import type {
  EventRecord,
  RankingSnapshot,
  SeasonStateResponse,
} from "../../../api/types";
import {
  buildWeekContextLinks,
  buildWeekEventLinks,
  parseViewerWeekParam,
  persistedEventsForWeek,
  plannedEventsForWeek,
  snapshotsForWeekSourceEvents,
  sourceEventIdsForWeek,
} from "./viewerWeekDetailDisplay";

const seasonState: SeasonStateResponse["season_state"] = {
  season: 2028,
  next_event_index: 1,
  completed_event_ids: ["EVENT/1"],
  ordered_events: [
    {
      event_id: "EVENT/1",
      season: 2028,
      week: 5,
      tour: "World Tour",
      category: "Platinum",
      template_id: "WT-PLAT",
    },
    {
      event_id: "EVENT/10",
      season: 2028,
      week: 6,
      tour: "Elite Tour",
      category: "Gold",
      template_id: "ET-GOLD",
    },
  ],
};

const eventRecords: EventRecord[] = [
  {
    event_sequence: 7,
    event_id: "EVENT/1",
    season: 2028,
    week: 5,
    template_id: "WT-PLAT",
    tournament_result: {},
  },
  {
    event_sequence: 8,
    event_id: "EVENT/10",
    season: 2028,
    week: 6,
    template_id: "ET-GOLD",
    tournament_result: {},
  },
];

const snapshots: RankingSnapshot[] = [
  {
    snapshot_sequence: 3,
    snapshot_kind: "ranking",
    source_event_id: "EVENT/1",
    payload: {},
  },
  {
    snapshot_sequence: 4,
    snapshot_kind: "ranking",
    source_event_id: "EVENT/10",
    payload: {},
  },
  {
    snapshot_sequence: 5,
    snapshot_kind: "ranking",
    source_event_id: "EVENT",
    payload: {},
  },
  {
    snapshot_sequence: 6,
    snapshot_kind: "ranking",
    source_event_id: null,
    payload: {},
  },
];

describe("viewerWeekDetailDisplay helpers", () => {
  it("parses only positive whole-number week route params", () => {
    expect(parseViewerWeekParam("5")).toBe(5);
    expect(parseViewerWeekParam(undefined)).toBeNull();
    expect(parseViewerWeekParam("")).toBeNull();
    expect(parseViewerWeekParam("0")).toBeNull();
    expect(parseViewerWeekParam("1.5")).toBeNull();
    expect(parseViewerWeekParam("abc")).toBeNull();
  });

  it("filters planned and persisted events by exact week and exact event ids", () => {
    const planned = plannedEventsForWeek(seasonState, 5);
    const sourceIds = sourceEventIdsForWeek(planned);

    expect(planned.map((event) => event.event_id)).toEqual(["EVENT/1"]);
    expect(
      persistedEventsForWeek(eventRecords, 5, sourceIds).map(
        (event) => event.event_id,
      ),
    ).toEqual(["EVENT/1"]);
    expect(
      plannedEventsForWeek(
        {
          ...seasonState,
          ordered_events: undefined,
        } as unknown as SeasonStateResponse["season_state"],
        5,
      ),
    ).toEqual([]);
    expect(persistedEventsForWeek(undefined, 5, sourceIds)).toEqual([]);
  });

  it("matches snapshot source_event_id exactly and never by partial event id", () => {
    const matches = snapshotsForWeekSourceEvents(
      snapshots,
      new Set(["EVENT/1"]),
    );

    expect(matches.map((snapshot) => snapshot.snapshot_sequence)).toEqual([3]);
  });

  it("builds encoded stable context and event links with existing route helpers", () => {
    expect(
      buildWeekContextLinks({
        runId: "run alpha/#1",
        week: 5,
        rankingSnapshotSequences: [3],
        raceSnapshotSequences: [9],
      }),
    ).toEqual([
      { label: "Run browser", href: "/viewer/runs" },
      {
        label: "Season calendar",
        href: "/viewer/runs/run%20alpha%2F%231/calendar",
      },
      {
        label: "Tournament list",
        href: "/viewer/runs/run%20alpha%2F%231/tournaments",
      },
      { label: "Week W5", href: "/viewer/runs/run%20alpha%2F%231/weeks/5" },
      {
        label: "Ranking snapshots",
        href: "/viewer/runs/run%20alpha%2F%231/rankings",
      },
      { label: "Race snapshots", href: "/viewer/runs/run%20alpha%2F%231/race" },
      {
        label: "Ranking publication #3",
        href: "/viewer/runs/run%20alpha%2F%231/rankings/3",
      },
      {
        label: "Race publication #9",
        href: "/viewer/runs/run%20alpha%2F%231/race/9",
      },
    ]);
    expect(
      buildWeekEventLinks({
        runId: "run alpha/#1",
        eventId: "EVENT/1",
        hasPlanned: true,
        hasPersisted: true,
      }),
    ).toEqual([
      {
        label: "Open planned event",
        href: "/viewer/runs/run%20alpha%2F%231/calendar/EVENT%2F1",
      },
      {
        label: "Open tournament detail",
        href: "/viewer/runs/run%20alpha%2F%231/tournaments/EVENT%2F1",
      },
    ]);
  });
});
