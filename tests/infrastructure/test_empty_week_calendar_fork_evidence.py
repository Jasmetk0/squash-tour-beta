"""An explicit empty week cites immutable Calendar *content*, not a tournament.

These tests exercise the fail-closed branch-boundary validation separately
from the slower real HTTP/SQLite Earth run integration acceptance.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from beta_engine.domain.players.sporting import CompletedWeekSportingContext
from beta_engine.domain.rankings.official import RankingWeek
from beta_engine.domain.simulation_slots import fingerprint
from beta_engine.infrastructure.db import player_slot_fork_remap as fork_module
from beta_engine.infrastructure.db.simulation_slot_fork_remap import (
    SimulationSlotForkRemapUnsupportedError,
)


pytestmark = pytest.mark.pr_critical


def _case(monkeypatch, *, target_authority="same-authority", events=()):
    class Calendar:
        def __init__(self, events):
            self.events = events

        def model_dump(self, *, mode):
            assert mode == "json"
            return {"season": "2000/2001", "events": []}

    week = RankingWeek(season_index=0, week=1)
    calendar = Calendar(events)
    expected = fingerprint(
        {
            "schema_version": "empty_week_calendar_evidence.v2",
            "season": "2000/2001",
            "week": week.model_dump(mode="json"),
            "calendar_authority_mode": "run_package",
            "calendar_authority_fingerprint": "same-authority",
            "calendar": calendar.model_dump(mode="json"),
        }
    )
    context = CompletedWeekSportingContext(
        run_id="run",
        branch_id="source",
        completed_week=week,
        competitive_match_counts=(),
        source_fingerprints=(expected,),
        provenance=fork_module._EMPTY_WEEK_PROVENANCE,
    )

    def load_saved(payload, *, run_id, branch_id):
        assert run_id == "run"
        assert branch_id == payload["branch"]
        return payload["branch"]

    def project_calendar(state, *, package_id):
        assert package_id == "calendar-2000-2001"
        return SimpleNamespace(
            season="2000/2001",
            content_fingerprint=(
                "same-authority" if state == "source" else target_authority
            ),
            calendar=calendar,
        )

    monkeypatch.setattr(fork_module, "load_saved_run_package_state", load_saved)
    monkeypatch.setattr(
        fork_module.CalendarPackageRunAdapter,
        "project_calendar",
        staticmethod(project_calendar),
    )
    return context, expected


def _verify(context, *, target_payload=None):
    return fork_module._verified_empty_week_calendar_evidence(
        {"branch": "source"},
        {"branch": "target"} if target_payload is None else target_payload,
        run_id="run",
        source_branch_id="source",
        target_branch_id="target",
        context=context,
    )


def test_empty_week_calendar_evidence_is_reused_only_after_two_independent_proofs(
    monkeypatch,
):
    context, expected = _case(monkeypatch)
    assert _verify(context) == expected


def test_empty_week_calendar_evidence_rejects_modified_target_authority(
    monkeypatch,
):
    context, _ = _case(monkeypatch, target_authority="changed")
    with pytest.raises(
        SimulationSlotForkRemapUnsupportedError, match="source/target Calendar evidence"
    ):
        _verify(context)


def test_empty_week_calendar_evidence_rejects_forged_context(monkeypatch):
    context, _ = _case(monkeypatch)
    forged = context.model_copy(update={"source_fingerprints": ("forged",)})
    with pytest.raises(
        SimulationSlotForkRemapUnsupportedError, match="source/target Calendar evidence"
    ):
        _verify(forged)


def test_empty_week_calendar_evidence_rejects_calendar_event(monkeypatch):
    event = SimpleNamespace(
        start_season_week=None,
        end_season_week=None,
        season_week=1,
    )
    context, _ = _case(monkeypatch, events=(event,))
    with pytest.raises(
        SimulationSlotForkRemapUnsupportedError, match="Calendar contains an event"
    ):
        _verify(context)
