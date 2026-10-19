"""Actual Saved lifecycle v4 decoder and full authenticated birthday/Entry replay.

No SQLite writer or synthetic saved-hash bypass: this exercises the production
load_saved_lifecycle parser, source-component digest and native Tour model.
The isolated World fixture supplies only the InitialWorld fields needed to
validate the existing signed population.
"""
import hashlib
import json
from types import SimpleNamespace

import pytest

from beta_engine.domain.calendar.run_calendar import RunCalendar
from beta_engine.domain.calendar.run_week_position import RunWeekPosition
from beta_engine.domain.players.calendar_prospect_birth import (
    CalendarTourLifecycleIntakeState,
    advance_calendar_lifecycle_with_prospects,
    build_calendar_prospect_birth_event,
)
from beta_engine.domain.rankings.calendar_official import (
    calculate_calendar_official_ranking,
)
from beta_engine.domain.rankings.official import OfficialRankingPolicy
from beta_engine.domain.tournaments.calendar_tour import (
    CalendarTourState, CalendarTourPolicy, CalendarTourTransition, ranking_week,
)
from beta_engine.infrastructure.db.player_lifecycle_state import (
    _parse_lifecycle_json, load_saved_lifecycle, remap_saved_lifecycle_component,
)
from beta_engine.infrastructure.db.run_prospect_source_state import (
    RUN_PROSPECT_SOURCE_SCHEMA, _fingerprint,
    RunProspectSourceSnapshot,
)
from tests.domain.test_calendar_prospect_birth_event import (
    birth_row, lifecycle, week,
)

pytestmark = pytest.mark.pr_critical


def _digest(states):
    body = [state.model_dump(mode="json") for state in states]
    return hashlib.sha256(json.dumps(body, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _signed_fixture(monkeypatch, width=52, offset=35):
    clock = RunCalendar(width, offset, 2030, 3)
    initial = lifecycle(clock, week(clock, 0, 1))
    target = week(clock, 0, 2)
    raw = birth_row(target, pid="born")
    source = RunProspectSourceSnapshot(
        schema_version=RUN_PROSPECT_SOURCE_SCHEMA,
        run_id="r", records=(raw,),
        fingerprint=_fingerprint(run_id="r", records=(raw,)),
    )
    event = build_calendar_prospect_birth_event(
        predecessor=initial, target=target, source=source,
        world_package_id="world",
    )
    second = advance_calendar_lifecycle_with_prospects(initial, event)
    policy = OfficialRankingPolicy(policy_id="stored-ranking", best_n=15)
    rank1 = calculate_calendar_official_ranking(
        run_id="r", branch_id="b", run_calendar=clock,
        week=ranking_week(initial.week), policy=policy, players=(), results=(),
    )
    rank2 = calculate_calendar_official_ranking(
        run_id="r", branch_id="b", run_calendar=clock,
        week=ranking_week(second.week), policy=policy, players=(), results=(),
        previous=rank1,
    )
    tour = CalendarTourState(
        run_id="r", branch_id="b", week=second.week,
        checkpoint_fingerprint="c" * 64,
        lifecycle_fingerprint=second.fingerprint,
        policies=(CalendarTourPolicy(effective_week=initial.week, ranking=policy),),
        rankings=(rank1, rank2),
        transitions=(CalendarTourTransition(
            command_id="week-transition",
            completed_week=initial.week, target_week=second.week,
            sporting_advance_fingerprint="d" * 64,
            ranking_fingerprint=rank2.fingerprint,
            health_fingerprint="e" * 64,
            ages=tuple((p.player_id, p.age) for p in second.players),
            retired_player_ids=(),
            public_event={"kind": "week_transition_completed"},
        ),),
    )
    world = SimpleNamespace(
        schema_version="initial_world_state.v2",
        run_calendar=clock, world_package_id="world",
        fingerprint=initial.source_initial_world_fingerprint,
        lifecycle_policy=initial.policy,
        players=tuple(
            SimpleNamespace(
                player_id=p.player_id, birth_year=p.birth_year,
                birth_year_week=p.birth_year_week,
                age_years_at_season_start=p.age,
                source_generation_fingerprint=p.source_generation_fingerprint,
            )
            for p in initial.players
        ),
    )
    from beta_engine.infrastructure.db import initial_world_state

    monkeypatch.setattr(
        initial_world_state, "load_saved_initial_world",
        lambda payload, *, run_id, branch_id: world,
    )
    states = (initial, second)
    payload = {
        "content": {
            "player_lifecycle": {
                "fingerprint": _digest(states),
                "states": [s.model_dump(mode="json") for s in states],
            },
            "run_prospect_source": {
                "schema_version": source.schema_version,
                "run_id": source.run_id,
                "records": list(source.records),
                "fingerprint": source.fingerprint,
            },
            "calendar_tour_authority": {
                "state": tour.model_dump(mode="json"),
            },
        },
    }
    return payload, states, event


@pytest.mark.parametrize("w,o", [
    (52, 1), (52, 35), (61, 37), (80, 15), (80, 80),
])
def test_saved_v4_roundtrip_exact_verified_source_and_tour_w_clock(monkeypatch, w, o):
    payload, states, event = _signed_fixture(monkeypatch, w, o)
    assert _parse_lifecycle_json(states[-1].model_dump_json()) == states[-1]
    assert load_saved_lifecycle(payload, run_id="r", branch_id="b") == states
    assert load_saved_lifecycle(payload, run_id="r", branch_id="b")[-1].birth_event == event
    before = json.dumps(payload, sort_keys=True)
    with pytest.raises(ValueError, match="full source/Entry/event re-signing"):
        remap_saved_lifecycle_component(
            payload, run_id="r", source_branch_id="b",
            target_branch_id="fork",
        )
    assert json.dumps(payload, sort_keys=True) == before


@pytest.mark.parametrize("attack,reason", [
    ("source_absent", "requires Signed Run prospect source"),
    ("source_bad_hash", "fingerprint mismatch"),
    ("source_replaced", "cannot be regenerated"),
    ("source_extra_due", "birth event differs"),
    ("tour_wrong_head", "head differs"),
    ("component_bad_hash", "identity or fingerprint mismatch"),
    ("foreign_branch", "foreign scope|identity or fingerprint mismatch"),
    ("v4_wrong_birth", "signed birth"),
])
def test_saved_lifecycle_v4_rejects_tampered_source_event_or_tour(
    monkeypatch, attack, reason,
):
    payload, states, _ = _signed_fixture(monkeypatch)
    content = payload["content"]
    if attack == "source_absent":
        del content["run_prospect_source"]
    elif attack == "source_bad_hash":
        content["run_prospect_source"]["fingerprint"] = "0" * 64
    elif attack == "source_replaced":
        item = content["run_prospect_source"]["records"][0]
        item["profile_seed"] = "tampered"
        content["run_prospect_source"]["fingerprint"] = _fingerprint(
            run_id="r", records=tuple(content["run_prospect_source"]["records"]),
        )
    elif attack == "source_extra_due":
        raw = birth_row(states[-1].week, pid="z-extra")
        content["run_prospect_source"]["records"].append(raw)
        content["run_prospect_source"]["fingerprint"] = _fingerprint(
            run_id="r", records=tuple(content["run_prospect_source"]["records"]),
        )
    elif attack == "tour_wrong_head":
        content["calendar_tour_authority"]["state"]["lifecycle_fingerprint"] = "f" * 64
    elif attack == "component_bad_hash":
        content["player_lifecycle"]["fingerprint"] = "f" * 64
    elif attack == "foreign_branch":
        content["player_lifecycle"]["states"][-1]["branch_id"] = "foreign"
    elif attack == "v4_wrong_birth":
        birth = next(
            person for person in content["player_lifecycle"]["states"][-1]["players"]
            if person["player_id"] == "born"
        )
        birth["source_generation_fingerprint"] = "0" * 64
    if attack in {"foreign_branch", "v4_wrong_birth"}:
        content["player_lifecycle"]["fingerprint"] = hashlib.sha256(json.dumps(
            content["player_lifecycle"]["states"], sort_keys=True, separators=(",", ":"),
        ).encode()).hexdigest()
    with pytest.raises(ValueError, match=reason):
        load_saved_lifecycle(payload, run_id="r", branch_id="b")


def test_existing_legacy_v3_and_unknown_version_are_not_silently_promoted(monkeypatch):
    payload, states, _ = _signed_fixture(monkeypatch)
    from beta_engine.domain.players.calendar_lifecycle import advance_calendar_lifecycle

    target = states[-1].week
    predecessor = states[0]
    downgraded = advance_calendar_lifecycle(predecessor, target)
    payload["content"]["player_lifecycle"] = {
        "fingerprint": _digest((predecessor, downgraded)),
        "states": [
            predecessor.model_dump(mode="json"),
            downgraded.model_dump(mode="json"),
        ],
    }
    # Even if a Signed prospect source exists, the unchanged historical v3
    # reader remains historically strict and refuses a forged Tour head.
    with pytest.raises(ValueError, match="head differs"):
        load_saved_lifecycle(payload, run_id="r", branch_id="b")
    raw = states[-1].model_dump(mode="json")
    raw["schema_version"] = "player_lifecycle_calendar_state.v999"
    with pytest.raises(ValueError):
        _parse_lifecycle_json(json.dumps(raw))
