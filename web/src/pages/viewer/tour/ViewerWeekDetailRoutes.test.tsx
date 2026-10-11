import { describe, expect, it } from "vitest";

import {
  viewerRaceSnapshotPath,
  viewerRankingSnapshotPath,
  viewerSeasonCalendarPath,
  viewerTournamentDetailPath,
  viewerTournamentsPath,
  viewerWeekDetailPath,
} from "../../../viewer/viewerRoutes";

describe("Viewer week detail route helpers", () => {
  it("keeps run-scoped week detail and related links encoded without changing route shape", () => {
    const runId = "run alpha/#1";
    const eventId = "EVENT/1";

    expect(viewerWeekDetailPath(runId, 5)).toBe(
      "/viewer/runs/run%20alpha%2F%231/weeks/5",
    );
    expect(viewerSeasonCalendarPath(runId)).toBe(
      "/viewer/runs/run%20alpha%2F%231/calendar",
    );
    expect(viewerTournamentsPath(runId)).toBe(
      "/viewer/runs/run%20alpha%2F%231/tournaments",
    );
    expect(viewerTournamentDetailPath(runId, eventId)).toBe(
      "/viewer/runs/run%20alpha%2F%231/tournaments/EVENT%2F1",
    );
    expect(viewerRankingSnapshotPath(runId, 3)).toBe(
      "/viewer/runs/run%20alpha%2F%231/rankings/3",
    );
    expect(viewerRaceSnapshotPath(runId, 9)).toBe(
      "/viewer/runs/run%20alpha%2F%231/race/9",
    );
  });
});
