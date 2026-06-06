import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, within } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { expectNoForbiddenViewerActions } from "../../../test/viewerTestUtils";
import { ViewerRunWeekPage } from "../../ViewerRunCalendarPage";

const api = vi.hoisted(() => ({
  ApiError: class ApiError extends Error {
    status: number;

    constructor(message: string, status: number) {
      super(message);
      this.status = status;
    }
  },
  getRun: vi.fn(),
  listEvents: vi.fn(),
  listRankingSnapshots: vi.fn(),
  listRaceSnapshots: vi.fn(),
}));

vi.mock("../../../api/client", () => api);

function renderWeek(route = "/viewer/runs/run%20alpha/weeks/5"): void {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });

  render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[route]}>
        <Routes>
          <Route
            path="/viewer/runs/:runId/weeks/:week"
            element={<ViewerRunWeekPage />}
          />
          <Route path="/viewer/week-missing" element={<ViewerRunWeekPage />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

function persistedSection(): HTMLElement {
  const section = screen
    .getByRole("heading", { name: "Persisted tournament records this week" })
    .closest("article");
  expect(section).not.toBeNull();
  return section as HTMLElement;
}

function publicationsSection(): HTMLElement {
  const section = screen
    .getByRole("heading", { name: "Publications this week" })
    .closest("article");
  expect(section).not.toBeNull();
  return section as HTMLElement;
}

describe("ViewerRunWeekPage read model", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    api.getRun.mockResolvedValue({
      run: { run_id: "run alpha", season: 2028, seed: 42 },
      season_state: {
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
      },
    });
    api.listEvents.mockResolvedValue({ run_id: "run alpha", events: [] });
    api.listRankingSnapshots.mockResolvedValue({
      run_id: "run alpha",
      snapshots: [],
    });
    api.listRaceSnapshots.mockResolvedValue({
      run_id: "run alpha",
      snapshots: [],
    });
  });

  it("renders safe planned week metadata and planned event links only", async () => {
    renderWeek();

    expect(
      await screen.findByRole("heading", { name: "Week Detail" }),
    ).toBeInTheDocument();
    expect(screen.getAllByText("run alpha").length).toBeGreaterThan(0);
    expect((await screen.findAllByText("EVENT/1")).length).toBeGreaterThan(0);
    expect(screen.getAllByText("W5").length).toBeGreaterThan(0);
    expect(
      screen.getAllByText("Planned events this week").length,
    ).toBeGreaterThan(0);
    expect(screen.getAllByText("1").length).toBeGreaterThan(0);
    expect(screen.getByText("World Tour")).toBeInTheDocument();
    expect(screen.getByText("Platinum")).toBeInTheDocument();
    expect(screen.getByText("WT-PLAT")).toBeInTheDocument();
    expect(screen.getByText("Plan index")).toBeInTheDocument();
    expect(screen.getByText("Plan position")).toBeInTheDocument();
    expect(screen.getByText("Completed")).toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: "Open planned event" }),
    ).toHaveAttribute("href", "/viewer/runs/run%20alpha/calendar/EVENT%2F1");
    expect(
      screen.queryByRole("link", { name: "Open tournament detail" }),
    ).not.toBeInTheDocument();
    expect(screen.queryByText("EVENT/10")).not.toBeInTheDocument();
    expect(screen.queryByText(/champion/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/winner/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/draw/i)).not.toBeInTheDocument();
    expectNoForbiddenViewerActions();
  });

  it("shows the safe getRun error state without displaying unrelated fake read-model rows", async () => {
    api.getRun.mockRejectedValue(new Error("season state outage"));
    api.listEvents.mockResolvedValue({
      run_id: "run alpha",
      events: [
        {
          event_sequence: 700,
          event_id: "FAKE-PERSISTED",
          season: 2028,
          week: 5,
          template_id: "FAKE",
          tournament_result: {},
        },
      ],
    });
    api.listRankingSnapshots.mockResolvedValue({
      run_id: "run alpha",
      snapshots: [
        {
          snapshot_sequence: 70,
          snapshot_kind: "ranking",
          source_event_id: "FAKE-PERSISTED",
          payload: {},
        },
      ],
    });

    renderWeek();

    expect(
      await screen.findByRole("heading", { name: "Week Detail" }),
    ).toBeInTheDocument();
    expect(
      await screen.findByText(
        "Failed to load run season state: season state outage",
      ),
    ).toBeInTheDocument();
    expect(screen.queryByText("FAKE-PERSISTED")).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: /publication #70/i })).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Open planned event" })).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Open tournament detail" })).not.toBeInTheDocument();
    expectNoForbiddenViewerActions();
  });

  it("renders exact persisted tournament matches with encoded tournament links and event sequence", async () => {
    api.listEvents.mockResolvedValue({
      run_id: "run alpha",
      events: [
        {
          event_sequence: 7,
          event_id: "EVENT/1",
          season: 2028,
          week: 5,
          template_id: "WT-PLAT",
          tournament_result: {},
        },
      ],
    });

    renderWeek();

    expect(
      await screen.findByRole("heading", { name: "Week Detail" }),
    ).toBeInTheDocument();
    expect(await screen.findByText("Event sequence")).toBeInTheDocument();
    expect(
      screen.getAllByText("Persisted events this week").length,
    ).toBeGreaterThan(0);
    expect(within(persistedSection()).getByText("Event sequence")).toBeInTheDocument();
    expect(within(persistedSection()).getByText("7")).toBeInTheDocument();
    expect(within(persistedSection()).getByText("W5")).toBeInTheDocument();
    expect(
      within(persistedSection()).getByRole("link", {
        name: "Open tournament detail",
      }),
    ).toHaveAttribute("href", "/viewer/runs/run%20alpha/tournaments/EVENT%2F1");
    expectNoForbiddenViewerActions();
  });

  it("keeps planned events visible when persisted tournament records fail", async () => {
    api.listEvents.mockRejectedValue(new Error("tournament record outage"));

    renderWeek();

    expect((await screen.findAllByText("EVENT/1")).length).toBeGreaterThan(0);
    expect(
      await screen.findByText(
        "Failed to load tournament records: tournament record outage",
      ),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: "Open planned event" }),
    ).toHaveAttribute("href", "/viewer/runs/run%20alpha/calendar/EVENT%2F1");
    expect(
      screen.queryByRole("link", { name: "Open tournament detail" }),
    ).not.toBeInTheDocument();
    expectNoForbiddenViewerActions();
  });

  it("renders a same-week persisted-only event without a planned-event link", async () => {
    api.getRun.mockResolvedValue({
      run: { run_id: "run alpha", season: 2028, seed: 42 },
      season_state: {
        season: 2028,
        next_event_index: 0,
        completed_event_ids: [],
        ordered_events: [],
      },
    });
    api.listEvents.mockResolvedValue({
      run_id: "run alpha",
      events: [
        {
          event_sequence: 11,
          event_id: "PERSISTED-ONLY",
          season: 2028,
          week: 5,
          template_id: "WT-ONLY",
          tournament_result: {},
        },
      ],
    });

    renderWeek();

    expect((await screen.findAllByText("PERSISTED-ONLY")).length).toBeGreaterThan(0);
    expect(
      screen.getByText("No planned tournaments are available for this week."),
    ).toBeInTheDocument();
    expect(
      within(persistedSection()).getByRole("link", {
        name: "Open tournament detail",
      }),
    ).toHaveAttribute("href", "/viewer/runs/run%20alpha/tournaments/PERSISTED-ONLY");
    expect(
      within(persistedSection()).queryByRole("link", { name: "Open planned event" }),
    ).not.toBeInTheDocument();
    expectNoForbiddenViewerActions();
  });

  it("renders an exact planned-id persisted record from a different persisted week without result previews", async () => {
    api.listEvents.mockResolvedValue({
      run_id: "run alpha",
      events: [
        {
          event_sequence: 12,
          event_id: "EVENT/1",
          season: 2028,
          week: 6,
          template_id: "WT-PLAT",
          tournament_result: {
            champion: "Hidden Champion",
            winner: "Hidden Winner",
            draw: ["Hidden Draw"],
          },
        },
      ],
    });

    renderWeek();

    expect(
      await screen.findByRole("heading", { name: "Week Detail" }),
    ).toBeInTheDocument();
    expect((await within(persistedSection()).findAllByText("EVENT/1")).length).toBeGreaterThan(0);
    expect(await within(persistedSection()).findByText("W6")).toBeInTheDocument();
    expect(screen.queryByText("Hidden Champion")).not.toBeInTheDocument();
    expect(screen.queryByText("Hidden Winner")).not.toBeInTheDocument();
    expect(screen.queryByText("Hidden Draw")).not.toBeInTheDocument();
    expect(screen.queryByText(/champion/i)).not.toBeInTheDocument();
    expectNoForbiddenViewerActions();
  });

  it("renders source-matched ranking and race publications without partial event id matches", async () => {
    api.listRankingSnapshots.mockResolvedValue({
      run_id: "run alpha",
      snapshots: [
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
      ],
    });
    api.listRaceSnapshots.mockResolvedValue({
      run_id: "run alpha",
      snapshots: [
        {
          snapshot_sequence: 9,
          snapshot_kind: "race",
          source_event_id: "EVENT/1",
          payload: {},
        },
      ],
    });

    renderWeek();

    expect(
      await screen.findByRole("heading", { name: "Week Detail" }),
    ).toBeInTheDocument();
    expect(screen.getByText("Ranking publications count")).toBeInTheDocument();
    expect(screen.getByText("Race publications count")).toBeInTheDocument();
    expect(
      (await screen.findAllByRole("link", { name: "Ranking publication #3" }))
        .length,
    ).toBeGreaterThan(0);
    expect(
      (await screen.findAllByRole("link", { name: "Race publication #9" }))
        .length,
    ).toBeGreaterThan(0);
    expect(
      screen.queryByRole("link", { name: "Ranking publication #4" }),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole("link", { name: "Ranking publication #5" }),
    ).not.toBeInTheDocument();
    expectNoForbiddenViewerActions();
  });

  it("keeps race publication links visible when only ranking publications fail", async () => {
    api.listEvents.mockResolvedValue({
      run_id: "run alpha",
      events: [
        {
          event_sequence: 7,
          event_id: "EVENT/1",
          season: 2028,
          week: 5,
          template_id: "WT-PLAT",
          tournament_result: {},
        },
      ],
    });
    api.listRankingSnapshots.mockRejectedValue(new Error("ranking outage"));
    api.listRaceSnapshots.mockResolvedValue({
      run_id: "run alpha",
      snapshots: [
        {
          snapshot_sequence: 9,
          snapshot_kind: "race",
          source_event_id: "EVENT/1",
          payload: {},
        },
      ],
    });

    renderWeek();

    expect((await screen.findAllByText("EVENT/1")).length).toBeGreaterThan(0);
    expect(
      await screen.findByText("Failed to load ranking publications: ranking outage"),
    ).toBeInTheDocument();
    expect(
      screen.getAllByRole("link", { name: "Race publication #9" })[0],
    ).toHaveAttribute("href", "/viewer/runs/run%20alpha/race/9");
    expect(within(persistedSection()).getByText("Event sequence")).toBeInTheDocument();
    expectNoForbiddenViewerActions();
  });

  it("keeps ranking publication links visible when only race publications fail", async () => {
    api.listEvents.mockResolvedValue({
      run_id: "run alpha",
      events: [
        {
          event_sequence: 7,
          event_id: "EVENT/1",
          season: 2028,
          week: 5,
          template_id: "WT-PLAT",
          tournament_result: {},
        },
      ],
    });
    api.listRankingSnapshots.mockResolvedValue({
      run_id: "run alpha",
      snapshots: [
        {
          snapshot_sequence: 3,
          snapshot_kind: "ranking",
          source_event_id: "EVENT/1",
          payload: {},
        },
      ],
    });
    api.listRaceSnapshots.mockRejectedValue(new Error("race outage"));

    renderWeek();

    expect((await screen.findAllByText("EVENT/1")).length).toBeGreaterThan(0);
    expect(
      await screen.findByText("Failed to load race publications: race outage"),
    ).toBeInTheDocument();
    expect(
      screen.getAllByRole("link", { name: "Ranking publication #3" })[0],
    ).toHaveAttribute("href", "/viewer/runs/run%20alpha/rankings/3");
    expect(within(persistedSection()).getByText("Event sequence")).toBeInTheDocument();
    expectNoForbiddenViewerActions();
  });

  it("does not render snapshot publication links for partial source_event_id matches", async () => {
    api.listRankingSnapshots.mockResolvedValue({
      run_id: "run alpha",
      snapshots: [
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
      ],
    });
    api.listRaceSnapshots.mockResolvedValue({
      run_id: "run alpha",
      snapshots: [
        {
          snapshot_sequence: 8,
          snapshot_kind: "race",
          source_event_id: "EVENT",
          payload: {},
        },
      ],
    });

    renderWeek();

    expect(
      await within(publicationsSection()).findByText(
        "No ranking or race publications are source-matched to this week.",
      ),
    ).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Ranking publication #4" })).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Ranking publication #5" })).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Race publication #8" })).not.toBeInTheDocument();
    expectNoForbiddenViewerActions();
  });

  it("does not source-match snapshots through persisted-only event ids", async () => {
    api.getRun.mockResolvedValue({
      run: { run_id: "run alpha", season: 2028, seed: 42 },
      season_state: {
        season: 2028,
        next_event_index: 0,
        completed_event_ids: [],
        ordered_events: [],
      },
    });
    api.listEvents.mockResolvedValue({
      run_id: "run alpha",
      events: [
        {
          event_sequence: 11,
          event_id: "PERSISTED-ONLY",
          season: 2028,
          week: 5,
          template_id: "WT-ONLY",
          tournament_result: {},
        },
      ],
    });
    api.listRankingSnapshots.mockResolvedValue({
      run_id: "run alpha",
      snapshots: [
        {
          snapshot_sequence: 13,
          snapshot_kind: "ranking",
          source_event_id: "PERSISTED-ONLY",
          payload: {},
        },
      ],
    });

    renderWeek();

    expect((await screen.findAllByText("PERSISTED-ONLY")).length).toBeGreaterThan(0);
    expect(screen.queryByRole("link", { name: "Ranking publication #13" })).not.toBeInTheDocument();
    expectNoForbiddenViewerActions();
  });

  it("keeps week detail visible when snapshot publications fail", async () => {
    api.listRankingSnapshots.mockRejectedValue(new Error("ranking outage"));
    api.listRaceSnapshots.mockRejectedValue(new Error("race outage"));

    renderWeek();

    expect((await screen.findAllByText("EVENT/1")).length).toBeGreaterThan(0);
    expect(
      await screen.findByText(
        "Failed to load ranking publications: ranking outage",
      ),
    ).toBeInTheDocument();
    expect(
      await screen.findByText("Failed to load race publications: race outage"),
    ).toBeInTheDocument();
    expectNoForbiddenViewerActions();
  });

  it("renders safe empty state and does not call APIs for invalid or missing week context", async () => {
    renderWeek("/viewer/week-missing");

    expect(
      await screen.findByRole("heading", { name: "Week Detail" }),
    ).toBeInTheDocument();
    expect(
      screen.getByText("No run route context was provided."),
    ).toBeInTheDocument();
    expect(
      screen.getByText(
        "Week must be a positive whole number in the URL (for example /weeks/12).",
      ),
    ).toBeInTheDocument();
    expect(api.getRun).not.toHaveBeenCalled();
    expect(api.listEvents).not.toHaveBeenCalled();
    expect(api.listRankingSnapshots).not.toHaveBeenCalled();
    expect(api.listRaceSnapshots).not.toHaveBeenCalled();
    expectNoForbiddenViewerActions();
  });
});
