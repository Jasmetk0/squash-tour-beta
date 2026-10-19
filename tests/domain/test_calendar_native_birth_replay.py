"""Exact read-only native birthday/first-application replay, including W boundaries."""
import json

import pytest

from beta_engine.domain.calendar.run_calendar import RunCalendar
from beta_engine.domain.calendar.run_week_position import RunWeekPosition
from beta_engine.domain.players.calendar_lifecycle import advance_calendar_lifecycle
from beta_engine.domain.players.calendar_prospect_birth import (
    advance_calendar_lifecycle_with_prospects, build_calendar_prospect_birth_event,
)
from beta_engine.domain.players.calendar_native_birth_replay import (
    CalendarNativeBirthReplayProof, verify_calendar_native_birth_history,
)
from beta_engine.domain.tournaments.application_submission_authority import (
    TournamentApplicationSubmissionAuthority,
)
from tests.domain.test_calendar_prospect_birth_event import (
    birth_row, lifecycle, source, week,
)

pytestmark = pytest.mark.pr_critical


def at(clock, ordinal):
    position = clock.position_at_ordinal(ordinal)
    return RunWeekPosition(
        calendar=clock, season_index=position.season_index,
        week=position.season_week,
    )


def history(clock, snapshot, *, last, entries=(), extra_v4=()):
    original = lifecycle(clock, at(clock, 0))
    states = [original]
    for ordinal in range(1, last + 1):
        previous = states[-1]
        next_week = at(clock, ordinal)
        event = build_calendar_prospect_birth_event(
            predecessor=previous, target=next_week,
            source=snapshot, world_package_id="world",
        )
        successor = (
            advance_calendar_lifecycle_with_prospects(previous, event, entries)
            if event.births or ordinal in extra_v4
            else advance_calendar_lifecycle(previous, next_week, entries)
        )
        states.append(successor)
    return tuple(states)


def submission(when, *, player_id="born", token="first-stable-token", run_id="r"):
    return TournamentApplicationSubmissionAuthority(
        schema_version="tournament_application_submission_authority.v2",
        application_id="application:" + player_id,
        run_id=run_id,
        branch_id="b", event_id="edition",
        player_id=player_id, entry_window="main",
        submission_week=when,
        decision_slot_ordinal=1,
        nr_tie_break_token=token,
        validation_authority_id="reviewed-entry-authority",
        validation_authority_fingerprint="a" * 64,
        provenance="Real reviewed valid submission",
    )


@pytest.mark.parametrize("w,offset", [
    (52, 1), (52, 35), (61, 37), (80, 15), (80, 80),
])
def test_every_signed_week_replays_native_15yo_birth_at_season_boundary(w, offset):
    clock = RunCalendar(w, offset, 2030, 3)
    target = at(clock, w)
    snapshot = source(
        birth_row(target, "born"),
        birth_row(at(clock, w + 2), "future"),
    )
    states = history(clock, snapshot, last=w + 1, extra_v4=(w + 1,))
    receipt = verify_calendar_native_birth_history(
        states=states, source=snapshot, world_package_id="world",
    )
    assert receipt.last_week.ordinal == w + 1
    assert receipt.admitted_player_ids == ("born",)
    assert receipt.birth_event_fingerprints[w - 1] is not None
    assert receipt.birth_event_fingerprints[w] is not None  # empty v4 event
    assert all(not fp for fp in receipt.birth_event_fingerprints[:w-1])
    assert len(states[w].players) == 2
    assert len(states[w + 1].players) == 2
    assert states[w].players[-1].tour_entry_week is None
    assert receipt == CalendarNativeBirthReplayProof.model_validate_json(
        receipt.model_dump_json()
    )
    assert receipt.fingerprint == verify_calendar_native_birth_history(
        states=states, source=snapshot, world_package_id="world",
    ).fingerprint
    assert states[0].fingerprint == lifecycle(clock, at(clock, 0)).fingerprint


def test_entry_is_only_sealed_on_week_after_real_post_birth_submission():
    clock = RunCalendar(52, 35, 2030, 3)
    snapshot = source(birth_row(at(clock, 1), "born"))
    first_entry = submission(at(clock, 1))
    states = history(clock, snapshot, last=2, entries=(first_entry,))
    review = verify_calendar_native_birth_history(
        states=states, source=snapshot, world_package_id="world",
        submissions=(first_entry,),
    )
    assert review.submission_fingerprints == (first_entry.fingerprint,)
    assert states[1].players[-1].tour_entry_week is None
    assert states[2].players[-1].tour_entry_week == at(clock, 1)
    assert states[2].players[-1].tie_break_token == "first-stable-token"
    assert review.admitted_player_ids == ("born",)

    forbidden = submission(at(clock, 0))
    with pytest.raises(ValueError, match="before birth"):
        verify_calendar_native_birth_history(
            states=states, source=snapshot, world_package_id="world",
            submissions=(forbidden,),
        )
    # Retrofitting an original Entry token into a birth-week Saved snapshot
    # is a forged event; first applications take effect the FOLLOWING week.
    forged = states[1].model_copy(update={
        "players": tuple(
            player.model_copy(update={
                "tour_entry_week": at(clock, 1), "tie_break_token": "retroactive"
            }) if player.player_id == "born" else player
            for player in states[1].players
        ),
    })
    with pytest.raises(ValueError, match="lifecycle differs"):
        verify_calendar_native_birth_history(
            states=(states[0], forged),
            source=snapshot, world_package_id="world",
        )


def test_missing_birth_and_rehashed_forged_state_fail_closed():
    clock = RunCalendar(61, 37, 2030, 3)
    snapshot = source(birth_row(at(clock, 1), "born"))
    states = history(clock, snapshot, last=2)
    with pytest.raises(ValueError, match="silently omitted"):
        verify_calendar_native_birth_history(
            states=(states[0], advance_calendar_lifecycle(states[0], at(clock, 1))),
            source=snapshot, world_package_id="world",
        )
    forged = states[1].model_copy(update={
        "birth_event": states[1].birth_event.model_copy(update={
            "source_run_prospect_fingerprint": "0" * 64,
        })
    })
    with pytest.raises(ValueError, match="birth event differs"):
        verify_calendar_native_birth_history(
            states=(states[0], forged),
            source=snapshot, world_package_id="world",
        )
    changed = source(birth_row(at(clock, 1), "born"))
    changed.fingerprint = "1" * 64
    with pytest.raises(ValueError, match="birth event differs"):
        verify_calendar_native_birth_history(
            states=states, source=changed, world_package_id="world",
        )
    with pytest.raises(ValueError, match="foreign Run/Branch"):
        verify_calendar_native_birth_history(
            states=(states[0], states[1].model_copy(update={"branch_id": "other"})),
            source=snapshot, world_package_id="world",
        )


def test_distinct_real_tour_entrants_must_have_distinct_tokens_and_identity():
    clock = RunCalendar(80, 15, 2030, 3)
    snapshot = source(birth_row(at(clock, 1), "born"))
    states = history(clock, snapshot, last=2)
    same_token = (
        submission(at(clock, 1), player_id="born", token="collision"),
        submission(at(clock, 1), player_id="existing", token="collision"),
    )
    with pytest.raises(ValueError, match="duplicate first Entry"):
        verify_calendar_native_birth_history(
            states=states, source=snapshot, world_package_id="world",
            submissions=same_token,
        )
    with pytest.raises(ValueError, match="scoped"):
        verify_calendar_native_birth_history(
            states=states, source=snapshot, world_package_id="world",
            submissions=(submission(at(clock, 1), run_id="other"),),
        )
    with pytest.raises(ValueError, match="before birth"):
        verify_calendar_native_birth_history(
            states=states, source=snapshot, world_package_id="world",
            submissions=(submission(at(clock, 0), player_id="future"),),
        )


def test_horizon_extension_preserves_old_native_birthday_event_and_lineage():
    old = RunCalendar(52, 35, 2030, 3)
    full = RunCalendar(52, 35, 2030, 5)
    snapshot = source(birth_row(at(old, 1), "born"))
    historical = history(old, snapshot, last=2)
    fresh_target = RunWeekPosition(calendar=full, season_index=0, week=4)
    extension = advance_calendar_lifecycle(
        historical[-1], fresh_target,
    )
    receipt = verify_calendar_native_birth_history(
        states=historical + (extension,),
        source=snapshot, world_package_id="world",
    )
    original = verify_calendar_native_birth_history(
        states=historical, source=snapshot, world_package_id="world",
    )
    assert receipt.lifecycle_fingerprints[:3] == original.lifecycle_fingerprints
    assert receipt.birth_event_fingerprints[:2] == original.birth_event_fingerprints
    assert receipt.last_week.calendar.season_count == 5
    assert historical[-1].fingerprint == original.lifecycle_fingerprints[-1]


def test_corrupted_history_gap_and_noncanonical_proof_are_rejected():
    clock = RunCalendar(52, 1, 2030, 3)
    snapshot = source(birth_row(at(clock, 1), "born"))
    states = history(clock, snapshot, last=3)
    with pytest.raises(ValueError, match="contiguous"):
        verify_calendar_native_birth_history(
            states=(states[0], states[2], states[3]),
            source=snapshot, world_package_id="world",
        )
    signed = verify_calendar_native_birth_history(
        states=states, source=snapshot, world_package_id="world",
    )
    payload = json.loads(signed.model_dump_json())
    payload["birth_event_fingerprints"] = []
    with pytest.raises(ValueError, match="incomplete"):
        CalendarNativeBirthReplayProof.model_validate_json(json.dumps(payload))
