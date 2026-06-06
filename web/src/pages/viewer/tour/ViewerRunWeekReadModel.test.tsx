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
    const persistedSection = screen
      .getByRole("heading", { name: "Persisted tournament records this week" })
      .closest("article");
    expect(persistedSection).not.toBeNull();
    expect(
      within(persistedSection as HTMLElement).getByText("Event sequence"),
    ).toBeInTheDocument();
    expect(
      within(persistedSection as HTMLElement).getByText("7"),
    ).toBeInTheDocument();
    expect(
      within(persistedSection as HTMLElement).getByRole("link", {
        name: "Open tournament detail",
      }),
    ).toHaveAttribute("href", "/viewer/runs/run%20alpha/tournaments/EVENT%2F1");
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
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("link", { name: "Open tournament detail" }),
    ).not.toBeInTheDocument();
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
