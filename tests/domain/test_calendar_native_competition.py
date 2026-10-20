"""Pure v12/v6 reducer tests; genuine World/Saved authority is tested over HTTP."""

from types import SimpleNamespace

import pytest

from beta_engine.application.calendar_tour_service import CalendarTourCommand
from beta_engine.domain.players.calendar_native_competition import (
    competition_checkpoint,
    native_projections,
    play_native_tournament,
)
from beta_engine.infrastructure.db.calendar_sporting_checkpoint import (
    parse_checkpoint_json,
)
from tests.domain.test_calendar_canonical_match import source
from tests.domain.test_calendar_native_sporting_checkpoint import prepared

pytestmark = pytest.mark.pr_critical


def fixture():
    cp, ctx = prepared(52, 1)
    world = SimpleNamespace(players=tuple(p.player for p in source().players))
    ids = ("newborn", "a", "b", "c")
    authority = SimpleNamespace(
        draw=SimpleNamespace(
            main=SimpleNamespace(
                slots=tuple(SimpleNamespace(player_id=pid) for pid in ids)
            )
        ),
        edition=SimpleNamespace(
            edition_id="native-event",
            start_slot=1,
            main_entrant_count=4,
            validity_weeks=52,
            point_table={"champion": 100, "finalist": 60, "semifinal": 30},
        ),
        execution_fingerprint="e" * 64,
    )
    command = CalendarTourCommand(
        command_id="play-native",
        action="play",
        edition_id="native-event",
        expected_saved_head="actual-saved-origin",
        expected_checkpoint_fingerprint=cp.fingerprint,
        seed=12,
        operator_label="Admin",
        audit_reason="Pure deterministic reducer fixture",
    )
    return cp, {
        "checkpoint": cp,
        "world": world,
        "lifecycle": ctx["lifecycle"][-1],
        "health": ctx["health"][-1],
        "source": ctx["source"],
        "clock": cp.week.calendar,
        "authority": authority,
        "command": command,
    }


def test_actual_matches_share_round_inputs_and_feed_winners_and_terminal_state():
    cp, inputs = fixture()
    old_bytes = cp.model_dump_json()
    old_hash = cp.fingerprint
    event, successor = play_native_tournament(**inputs)
    assert event.schema_version == "calendar_followup_knockout.v6"
    assert successor.schema_version == "calendar_sporting_checkpoint.v12"
    assert successor.competition_root.model_dump_json() == old_bytes
    assert successor.competition_root.fingerprint == old_hash
    one, two, final = event.matches
    assert one.source_checkpoint_fingerprint == two.source_checkpoint_fingerprint
    assert one.source_checkpoint_fingerprint != final.source_checkpoint_fingerprint
    records = {p.player_id: p for p in cp.players}
    for m in (one, two):
        for projection in m.canonical_projections:
            assert (
                projection.canonical_attributes
                == records[projection.player_id].attributes
            )
            assert projection.current_form == records[projection.player_id].current_form
    new = next(p for p in one.canonical_projections if p.player_id == "newborn")
    assert new.age == 15 and new.hidden_career_traits is None
    assert new.play_style == new.archetype == "unspecified"
    assert {p.player_id for p in final.canonical_projections} == {
        one.result.winner_player_id,
        two.result.winner_player_id,
    }
    effects = {e.player_id: e for m in (one, two) for e in m.effects}
    for p in final.canonical_projections:
        assert (p.current_form, p.match_sharpness, p.long_term_fatigue) == (
            effects[p.player_id].form_after,
            effects[p.player_id].sharpness_after,
            effects[p.player_id].fatigue_after,
        )
    assert next(p for p in successor.players if p.player_id == "d") == records["d"]
    assert parse_checkpoint_json(successor.model_dump_json()) == successor
    replay, replayed = play_native_tournament(**inputs)
    assert replay == event and replayed == successor


def test_future_or_retired_identity_cannot_enter_native_match_projection():
    cp, inputs = fixture()
    with pytest.raises(ValueError, match="not admitted"):
        native_projections(
            cp,
            inputs["world"],
            inputs["lifecycle"],
            inputs["source"],
            ("newborn", "future"),
        )
    life = inputs["lifecycle"].model_copy(
        update={
            "players": tuple(
                p.model_copy(update={"status": "retired"})
                if p.player_id == "newborn"
                else p
                for p in inputs["lifecycle"].players
            )
        }
    )
    with pytest.raises(ValueError, match="Retired"):
        native_projections(
            cp, inputs["world"], life, inputs["source"], ("newborn", "a")
        )
    assert competition_checkpoint(cp).competition_root is cp
