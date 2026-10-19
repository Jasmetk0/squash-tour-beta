"""Read-model contract/cost tests; context mocks are not integration evidence."""
from collections import Counter
from contextlib import nullcontext
from types import SimpleNamespace as NS

import pytest

from beta_engine.application.calendar_continuation_service import CalendarContinuationService
from beta_engine.application.calendar_opening_knockout_service import CalendarOpeningKnockoutService
from beta_engine.domain.calendar.run_calendar import RunCalendar
from beta_engine.domain.calendar.run_week_position import RunWeekPosition

pytestmark = pytest.mark.pr_critical


class Evidence:
    """Count digest evaluations independently of the production read model."""
    def __init__(self, key, **fields):
        self.key, self.calls = key, 0
        self.__dict__.update(fields)

    @property
    def fingerprint(self):
        self.calls += 1
        return self.key

    def model_dump(self, **_kwargs):
        return {"source": self.key}


def context_factory():
    session = NS(execute=lambda _statement: None)
    return NS(_session_factory=lambda: nullcontext(session))


def history(size):
    week = RunWeekPosition(calendar=RunCalendar(80, 80, 2030, 3), season_index=0, week=2)
    matches = tuple(Evidence(f"match-{i}", match_id=f"match-{i}", sequence=i + 1,
        week=week, input_context=NS(player_a=NS(player=NS(player_id="a")),
                                  player_b=NS(player=NS(player_id="b"))),
        result=NS(winner_player_id="a", rally_log=NS(events=(1, 2, 3)))) for i in range(size))
    tournaments = tuple(Evidence(f"tournament-{i}", tournament_id=f"tournament-{i}",
        command_id=f"play-{i}", week=week, entrant_ids=("a", "b", "c", "d"),
        matches=matches[:1], schema_version="calendar_followup_knockout.v3",
        scope="sporting_exhibition_knockout_not_official", prepared_policy=None,
        prepared_awards=()) for i in range(size))
    closures = tuple(Evidence(f"closure-{i}", command_id=f"close-{i}",
        tournament_id=f"tournament-{i}", champion_player_id="a", finalist_player_id="b",
        source_tournament_fingerprint=f"tournament-{i}", players=(), scope="result") for i in range(size))
    advances = tuple(Evidence(f"advance-{i}", command_id=f"advance-{i}",
        completed_week=week, target_week=week) for i in range(size))
    return Evidence("checkpoint", week=week, tournaments=tournaments, closures=closures,
        weekly_advances=advances, played_continuations=matches)


def all_sources(state):
    return (state, *state.tournaments, *state.closures,
            *state.weekly_advances, *state.played_continuations)


@pytest.mark.parametrize("size", [1, 20, 80])
@pytest.mark.parametrize("shared_objects", [False, True])
def test_each_authenticated_source_digest_is_evaluated_once_per_read(monkeypatch, size, shared_objects):
    state = history(size)
    saved = state if shared_objects else history(size)
    revision = NS(saved_head_revision_id="head", working_draft=NS(draft_version=2))
    world = NS(players=(NS(player_id="a"), NS(player_id="b")))
    calls = []

    def context(*_args, **kwargs):
        calls.append(kwargs)
        return state.week.calendar, revision, world, None, state, saved, None

    monkeypatch.setattr(CalendarContinuationService, "_context", context)
    reader = CalendarContinuationService(context_factory())
    response = reader.inspect(run_id="run", branch_id="branch")
    assert response["saved"] and response["can_play"]
    assert response["checkpoint_fingerprint"] == "checkpoint"
    assert all(row["saved"] for key in ("tournaments", "closures", "weekly_advances", "matches")
               for row in response[key])
    assert all(row["result_closed"] and row["result_closure_saved"] for row in response["tournaments"])
    assert len(response["matches"]) == size
    assert calls == [{"run_id": "run", "branch_id": "branch"}]
    unique = {id(source): source for source in (*all_sources(state), *all_sources(saved))}
    assert Counter(source.calls for source in unique.values()) == {1: len(unique)}
    # A later request must derive fresh digests; nothing is cached across reads.
    assert reader.inspect(run_id="run", branch_id="branch") == response
    assert Counter(source.calls for source in unique.values()) == {2: len(unique)}


def test_unsaved_identity_does_not_become_saved_and_match_membership_keeps_order(monkeypatch):
    state, saved = history(3), history(3)
    state.key = "unsaved-checkpoint"
    state.tournaments[1].key = "changed-event-with-same-tournament-id"
    state.closures[1].key = "unsaved-closure"
    state.weekly_advances[1].key = "unsaved-advance"
    state.played_continuations = tuple(reversed(state.played_continuations))
    revision = NS(saved_head_revision_id="head", working_draft=NS(draft_version=3))
    monkeypatch.setattr(CalendarContinuationService, "_context", lambda *_a, **_kw:
        (state.week.calendar, revision, NS(players=()), None, state, saved, None))
    result = CalendarContinuationService(context_factory()).inspect(run_id="run", branch_id="branch")
    assert not result["saved"] and not result["can_play"]
    for key in ("tournaments", "closures", "weekly_advances", "matches"):
        assert [row["saved"] for row in result[key]] == (
            [False, True, False] if key == "matches" else [True, False, True]
        )


def test_empty_inspection_and_context_rejection_have_no_fallback(monkeypatch):
    clock = RunCalendar.earth_default()
    revision = NS(saved_head_revision_id="head", working_draft=NS(draft_version=0))
    monkeypatch.setattr(CalendarContinuationService, "_context", lambda *_a, **_kw:
        (clock, revision, NS(players=()), None, None, None, None))
    result = CalendarContinuationService(context_factory()).inspect(run_id="run", branch_id="branch")
    assert result["checkpoint_fingerprint"] is None
    assert not result["saved"] and not result["can_play"]
    assert not any(result[key] for key in ("tournaments", "closures", "weekly_advances", "matches"))

    def reject(*_a, **_kw):
        raise ValueError("actual live bytes differ from Saved authority")

    for cls in (CalendarContinuationService, CalendarOpeningKnockoutService):
        monkeypatch.setattr(cls, "_context", reject)
        with pytest.raises(ValueError, match="actual live bytes"):
            cls(context_factory()).inspect(run_id="run", branch_id="branch")


@pytest.mark.parametrize("variant", ["empty", "unsaved", "saved", "prepared", "saved_prepared", "mismatch"])
def test_opening_signed_and_prepared_flags_use_the_same_authenticated_sources(monkeypatch, variant):
    from beta_engine.application import calendar_opening_knockout_service as opening
    from beta_engine.infrastructure.db.calendar_knockout_awards_state import (
        CalendarKnockoutPointPolicy, CalendarScoredOpeningKnockout,
        derive_knockout_prepared_awards,
    )
    from tests.domain.test_calendar_canonical_match import canonical_bracket

    knockout = canonical_bracket()
    row = None if variant == "empty" else knockout
    saved = knockout if variant in {"saved", "prepared", "mismatch"} else None
    if variant in {"prepared", "saved_prepared"}:
        policy = CalendarKnockoutPointPolicy(category_label="Reviewed", champion=100,
            finalist=60, semifinal=30, validity_weeks=knockout.week.calendar.weeks_per_year)
        row = CalendarScoredOpeningKnockout(
            run_id=knockout.run_id, branch_id=knockout.branch_id,
            match_id=knockout.match_id, command_id="prepare", request_fingerprint="a" * 64,
            source_saved_head=knockout.source_saved_head,
            source_initial_world_fingerprint=knockout.source_initial_world_fingerprint,
            week=knockout.week, knockout=knockout, knockout_fingerprint=knockout.fingerprint,
            policy=policy, first_publication_week=knockout.week.model_copy(update={"week": 2}),
            awards=derive_knockout_prepared_awards(knockout, policy),
            operator_label="Admin", audit_reason="Prepared points remain separate from Save")
        if variant == "saved_prepared":
            saved = row
    if variant == "mismatch":
        row = knockout.model_copy(update={"audit_reason": "different live root"})
    revision = NS(saved_head_revision_id="head", working_draft=NS(draft_version=3),
        saved_revision=NS(payload={"content": {}}))
    world = NS(fingerprint=knockout.source_initial_world_fingerprint,
        players=tuple(NS(player_id=p) for p in knockout.entrant_ids))

    def context(*_args, **kwargs):
        assert kwargs["_include_sporting_sources"] is True
        return knockout.week.calendar, revision, world, None, None, (() if row is None else (row,)), None, saved

    def duplicate(*_args, **_kwargs):
        raise AssertionError("Must not re-read already authenticated sources in this transaction")

    monkeypatch.setattr(CalendarOpeningKnockoutService, "_context", context)
    monkeypatch.setattr(opening, "load_match_rows", duplicate)
    reader = CalendarOpeningKnockoutService(context_factory())
    if variant == "mismatch":
        with pytest.raises(ValueError, match="Saved knockout differs"):
            reader.inspect(run_id=knockout.run_id, branch_id=knockout.branch_id)
        return
    result = reader.inspect(run_id=knockout.run_id, branch_id=knockout.branch_id)
    assert result["saved"] is (variant in {"saved", "saved_prepared"})
    assert result["knockout"] == (knockout.model_dump(mode="json") if row else None)
    assert result["knockout_fingerprint"] == (row.fingerprint if row else None)
    if variant in {"prepared", "saved_prepared"}:
        assert result["prepared_points"]["publication_status"] == "prepared_not_official"
        assert result["prepared_points"]["scored_fingerprint"] == row.fingerprint
    else:
        assert result["prepared_points"] is None
