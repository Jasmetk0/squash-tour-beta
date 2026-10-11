"""Adversarial identity/provenance tests for saved Season Transition World Events."""

from __future__ import annotations

import json
from copy import deepcopy
from types import SimpleNamespace

import pytest

from test_season_closing_fork_proof import _case

from beta_engine.domain.rankings.official import RankingWeek, calculate_official_ranking
from beta_engine.domain.season_closure import (
    bind_season_closure_marker,
    build_season_closure_package,
)
from beta_engine.infrastructure.db.saved_revision_season_closure import (
    install_saved_revision_season_closure,
    load_saved_revision_season_closure,
    rebind_cross_branch_season_closure,
)
from beta_engine.infrastructure.db.season_closing_fork_proof import (
    rebind_verified_season_closing_ranking,
)
from beta_engine.infrastructure.db.season_transition_fork_event import (
    SeasonTransitionForkEventError,
    rebind_verified_season_transition_event,
)


pytestmark = pytest.mark.pr_critical


def _case_with_event():
    closing, proof = _case()
    target_closing = rebind_verified_season_closing_ranking(closing, **proof)
    source_pkg = build_season_closure_package(closing_ranking=closing)
    source_marker = bind_season_closure_marker(
        source_pkg.marker, final_saved_revision_id="source-revision",
    )
    source_payload = {"content": {}}
    install_saved_revision_season_closure(
        source_payload, package=source_pkg, marker=source_marker,
    )
    target_payload = {"content": {}}
    target_closure = rebind_cross_branch_season_closure(
        source_payload, target_payload,
        run_id="run", source_branch_id="source",
        target_branch_id="target", source_revision_id="source-revision",
        target_revision_id="fork-root",
        source_closing=closing, target_closing=target_closing,
    )
    source_closure = load_saved_revision_season_closure(
        source_payload, run_id="run", branch_id="source",
        revision_id="source-revision",
    )
    boundary = RankingWeek(season_index=1, week=1)
    source_week = calculate_official_ranking(
        run_id="run", branch_id="source",
        week=boundary, policy=closing.policy,
        players=proof["source_players"],
        results=proof["source_results"],
        previous=proof["source_predecessor"],
        disciplinary_zeros=proof["source_zeros"],
    )
    target_week = calculate_official_ranking(
        run_id="run", branch_id="target",
        week=boundary, policy=closing.policy,
        players=proof["target_players"],
        results=proof["target_results"],
        previous=proof["target_predecessor"],
        disciplinary_zeros=proof["target_zeros"],
    )
    event = {
        "schema_version": "season_transition_world_event.v1",
        "command_id": "season-transition",
        "completed_week": closing.completed_week.model_dump(mode="json"),
        "target_week": boundary.model_dump(mode="json"),
        "saved_revision_id": "source-revision",
        "configuration_fingerprint": "a" * 64,
        "closing_ranking_fingerprint": closing.fingerprint,
        "season_summary_fingerprint": source_pkg.summary.fingerprint,
        "closure_marker_fingerprint": source_marker.fingerprint,
        "player_sporting_fingerprint": "b" * 64,
        "player_lifecycle_fingerprint": "c" * 64,
        "player_health_fingerprint": "d" * 64,
        "official_ranking_fingerprint": source_week.fingerprint,
    }
    row = {
        "run_id": "run", "branch_id": "source",
        "command_id": "season-transition",
        "week_ordinal": boundary.ordinal,
        "event_kind": "season_transition_completed",
        "payload_json": json.dumps(event, sort_keys=True, separators=(",", ":")),
    }
    args = dict(
        run_id="run", source_branch_id="source",
        target_branch_id="target",
        source_revision_id="source-revision",
        target_revision_id="fork-root",
        source_closure=source_closure,
        target_closure=target_closure,
        source_ranking=SimpleNamespace(
            run_id="run", branch_id="source",
            entries=(SimpleNamespace(snapshot=source_week),),
        ),
        target_ranking=SimpleNamespace(
            run_id="run", branch_id="target",
            entries=(SimpleNamespace(snapshot=target_week),),
        ),
        lifecycle_fingerprint_map={"c" * 64: "e" * 64},
        sporting_fingerprint_map={"b" * 64: "f" * 64},
        health_fingerprint_map={"d" * 64: "1" * 64},
    )
    return row, args


def test_cross_branch_season_event_rebinds_rankings_closure_and_player_outputs():
    row, args = _case_with_event()
    original = deepcopy(row)
    new = rebind_verified_season_transition_event(row, **args)
    payload = json.loads(new["payload_json"])
    assert row == original
    assert (new["run_id"], new["branch_id"], new["week_ordinal"]) == (
        "run", "target", RankingWeek(season_index=1, week=1).ordinal
    )
    assert payload["saved_revision_id"] == "fork-root"
    assert payload["official_ranking_fingerprint"] == (
        args["target_ranking"].entries[0].snapshot.fingerprint
    )
    assert payload["closing_ranking_fingerprint"] == (
        args["target_closure"].parsed_summary.closing_ranking_fingerprint
    )
    assert payload["season_summary_fingerprint"] == args["target_closure"].parsed_summary.fingerprint
    assert payload["closure_marker_fingerprint"] == args["target_closure"].parsed_marker.fingerprint
    assert payload["player_lifecycle_fingerprint"] == "e" * 64
    assert payload["player_sporting_fingerprint"] == "f" * 64
    assert payload["player_health_fingerprint"] == "1" * 64
    assert payload["configuration_fingerprint"] == "a" * 64
    assert rebind_verified_season_transition_event(row, **args) == new


@pytest.mark.parametrize("tamper", [
    "source_revision", "closing_hash", "source_ranking", "missing_sporting",
    "target_revision", "wrong_week", "bad_configuration", "foreign_branch",
])
def test_cross_branch_season_event_fails_closed_on_forged_authority(tamper):
    row, args = _case_with_event()
    original = deepcopy(row)
    args = dict(args)
    payload = json.loads(row["payload_json"])
    if tamper == "source_revision":
        payload["saved_revision_id"] = "foreign-source"
    elif tamper == "closing_hash":
        payload["closing_ranking_fingerprint"] = "0" * 64
    elif tamper == "source_ranking":
        payload["official_ranking_fingerprint"] = "0" * 64
    elif tamper == "missing_sporting":
        args["sporting_fingerprint_map"] = {}
    elif tamper == "target_revision":
        args["target_revision_id"] = "wrong-fork"
    elif tamper == "wrong_week":
        row["week_ordinal"] = 64
    elif tamper == "bad_configuration":
        payload["configuration_fingerprint"] = "not-verified"
    else:
        row["branch_id"] = "foreign"
    row["payload_json"] = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    with pytest.raises(SeasonTransitionForkEventError):
        rebind_verified_season_transition_event(row, **args)
    assert args["source_closure"].parsed_marker.final_saved_revision_id == "source-revision"
    assert original["branch_id"] == "source"
