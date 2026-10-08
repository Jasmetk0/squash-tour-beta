"""Deterministic, side-effect-free evidence remap for an eventual Week-4 fork."""

from copy import deepcopy
import json

import pytest

from beta_engine.application.authoritative_week_transition import (
    AuthoritativeWeekTransitionCommand,
    AuthoritativeWeekTransitionResult,
)
from beta_engine.domain.rankings.command_audit import RankingCommandAudit
from beta_engine.domain.rankings.official import RankingWeek
from beta_engine.infrastructure.db.authoritative_week_transition import _world_event_payload
from beta_engine.infrastructure.db.week_transition_fork_audit import (
    WeekTransitionForkAuditUnsupportedError,
    remap_event_free_week_transition_audit,
)

pytestmark = pytest.mark.pr_critical


def _fingerprint(n: int) -> str:
    return f"{n:064x}"


def _case():
    state = {"receipts": [], "events": []}
    maps = {
        "base_revision_ids": {},
        "ranking_authorities": {},
        "ranking_snapshots": {},
        "lifecycle_states": {},
        "sporting_states": {},
        "health_states": {},
    }
    for week in (1, 2):
        command = AuthoritativeWeekTransitionCommand(
            command_id=f"transition-{week}",
            run_id="run",
            branch_id="source",
            base_revision_id=f"saved-{week}",
            completed_week=RankingWeek(season_index=0, week=week),
            target_week=RankingWeek(season_index=0, week=week + 1),
            authority_fingerprint=_fingerprint(100 + week),
            audit=RankingCommandAudit(
                actor_label="Admin",
                reason="Deterministic empty-week transition",
            ),
        )
        result = AuthoritativeWeekTransitionResult(
            run_id="run",
            branch_id="source",
            command_id=command.command_id,
            completed_week=command.completed_week,
            target_week=command.target_week,
            official_ranking_fingerprint=_fingerprint(200 + week),
            player_lifecycle_fingerprint=_fingerprint(300 + week),
            player_sporting_fingerprint=_fingerprint(400 + week),
            player_health_fingerprint=(
                _fingerprint(500 + week) if week == 1 else None
            ),
        )
        state["receipts"].append({
            "run_id": "run",
            "branch_id": "source",
            "command_id": command.command_id,
            "request_fingerprint": command.fingerprint,
            "request_payload_json": command.canonical_request_json,
            "result_json": result.model_dump_json(),
        })
        state["events"].append({
            "run_id": "run",
            "branch_id": "source",
            "command_id": command.command_id,
            "week_ordinal": command.target_week.ordinal,
            "event_kind": "week_transition_completed",
            "payload_json": _world_event_payload(
                command,
                result.official_ranking_fingerprint,
                result.player_lifecycle_fingerprint,
                result.player_sporting_fingerprint,
                result.player_health_fingerprint,
            ),
        })
        maps["base_revision_ids"][command.base_revision_id] = f"target-saved-{week}"
        maps["ranking_authorities"][command.authority_fingerprint] = _fingerprint(600 + week)
        maps["ranking_snapshots"][result.official_ranking_fingerprint] = _fingerprint(700 + week)
        maps["lifecycle_states"][result.player_lifecycle_fingerprint] = _fingerprint(800 + week)
        maps["sporting_states"][result.player_sporting_fingerprint] = _fingerprint(900 + week)
        if result.player_health_fingerprint:
            maps["health_states"][result.player_health_fingerprint] = _fingerprint(1000 + week)
    return state, maps


def _remap(state, maps):
    return remap_event_free_week_transition_audit(
        state,
        run_id="run",
        source_branch_id="source",
        target_branch_id="fork",
        **maps,
    )


def test_two_week_audit_rebinds_exact_verified_dependencies_without_mutation():
    state, maps = _case()
    source_copy = deepcopy(state)
    target = _remap(state, maps)

    assert target == _remap(state, maps)
    assert state == source_copy
    assert len(target["receipts"]) == len(target["events"]) == 2

    for source_row, target_row, target_event in zip(
        state["receipts"], target["receipts"], target["events"], strict=True
    ):
        source_command = AuthoritativeWeekTransitionCommand.model_validate_json(
            source_row["request_payload_json"]
        )
        source_result = AuthoritativeWeekTransitionResult.model_validate_json(
            source_row["result_json"]
        )
        command = AuthoritativeWeekTransitionCommand.model_validate_json(
            target_row["request_payload_json"]
        )
        result = AuthoritativeWeekTransitionResult.model_validate_json(
            target_row["result_json"]
        )
        assert command.branch_id == result.branch_id == "fork"
        assert command.base_revision_id == maps["base_revision_ids"][
            source_command.base_revision_id
        ]
        assert command.authority_fingerprint == maps["ranking_authorities"][
            source_command.authority_fingerprint
        ]
        assert command.fingerprint == target_row["request_fingerprint"]
        assert result.official_ranking_fingerprint == maps["ranking_snapshots"][
            source_result.official_ranking_fingerprint
        ]
        assert result.player_lifecycle_fingerprint == maps["lifecycle_states"][
            source_result.player_lifecycle_fingerprint
        ]
        assert result.player_sporting_fingerprint == maps["sporting_states"][
            source_result.player_sporting_fingerprint
        ]
        assert target_event["branch_id"] == "fork"
        assert target_event["payload_json"] == _world_event_payload(
            command, result.official_ranking_fingerprint,
            result.player_lifecycle_fingerprint,
            result.player_sporting_fingerprint,
            result.player_health_fingerprint,
        )
        assert target_event["payload_json"] != state["events"][
            int(source_command.completed_week.week) - 1
        ]["payload_json"]


@pytest.mark.parametrize(
    "corruption",
    [
        "receipt_hash", "receipt_payload", "result_scope", "event_payload",
        "event_scope", "missing_event", "extra_event", "duplicate_receipt",
        "duplicate_week", "missing_authority", "missing_revision",
        "missing_lifecycle", "missing_health", "missing_sporting",
    ],
)
def test_partial_or_tampered_transition_audit_fails_closed(corruption):
    state, maps = _case()
    if corruption == "receipt_hash":
        state["receipts"][0]["request_fingerprint"] = _fingerprint(12)
    elif corruption == "receipt_payload":
        state["receipts"][0]["request_payload_json"] += " "
    elif corruption == "result_scope":
        result = json.loads(state["receipts"][0]["result_json"])
        result["branch_id"] = "another"
        state["receipts"][0]["result_json"] = json.dumps(result)
    elif corruption == "event_payload":
        state["events"][0]["payload_json"] = "{}"
    elif corruption == "event_scope":
        state["events"][0]["branch_id"] = "other"
    elif corruption == "missing_event":
        state["events"].pop()
    elif corruption == "extra_event":
        state["events"].append({**state["events"][0], "command_id": "phantom"})
    elif corruption == "duplicate_receipt":
        state["receipts"].append(state["receipts"][0].copy())
    elif corruption == "duplicate_week":
        state["receipts"][1]["command_id"] = "other-week"
        state["events"][1]["command_id"] = "other-week"
        # The original canonical command id still remains in payload.
    elif corruption == "missing_authority":
        maps["ranking_authorities"].clear()
    elif corruption == "missing_revision":
        maps["base_revision_ids"].clear()
    elif corruption == "missing_lifecycle":
        maps["lifecycle_states"].clear()
    elif corruption == "missing_health":
        maps["health_states"].clear()
    elif corruption == "missing_sporting":
        maps["sporting_states"].clear()
    with pytest.raises(WeekTransitionForkAuditUnsupportedError):
        _remap(state, maps)


def test_mismatched_or_identical_branch_scope_cannot_be_remapped():
    state, maps = _case()
    with pytest.raises(WeekTransitionForkAuditUnsupportedError):
        remap_event_free_week_transition_audit(
            state, run_id="run",
            source_branch_id="source", target_branch_id="source", **maps,
        )
    with pytest.raises(WeekTransitionForkAuditUnsupportedError):
        remap_event_free_week_transition_audit(
            state, run_id="another-run",
            source_branch_id="source", target_branch_id="fork", **maps,
        )
