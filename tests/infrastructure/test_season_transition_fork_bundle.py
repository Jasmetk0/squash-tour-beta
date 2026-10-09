"""Full 61-week ranking/audit chronology across one proven Season Transition.

Uses canonical ranking and Week Transition commands (not fabricated receipt hashes).
The production SQLite fork integration remains tested separately.
"""
from __future__ import annotations

import json

import pytest

from beta_engine.application.authoritative_week_transition import (
    AuthoritativeWeekTransitionCommand,
    AuthoritativeWeekTransitionResult,
)
from beta_engine.application.official_ranking_transition import RankingTransitionContext
from beta_engine.application.ranking_bootstrap_command import RankingBootstrapCommand
from beta_engine.application.ranking_week_command import RankingWeekCommand
from beta_engine.domain.rankings.command_audit import RankingCommandAudit
from beta_engine.domain.rankings.input_manifest import RankingInputManifest
from beta_engine.domain.rankings.official import (
    OfficialRankingPolicy,
    RankingWeek,
    calculate_official_ranking,
)
from beta_engine.domain.rankings.revision_state import (
    RankingRevisionEntry,
    RankingRevisionReceipt,
    RankingRevisionState,
)
from beta_engine.domain.rankings.season_closing import calculate_season_closing_ranking
from beta_engine.domain.rankings.transition_authority import RankingTransitionAuthority
from beta_engine.domain.season_closure import (
    bind_season_closure_marker, build_season_closure_package,
)
from beta_engine.infrastructure.db.authoritative_week_transition import _world_event_payload
from beta_engine.infrastructure.db.ranking_fork_remap import (
    remap_source_free_ranking_state_for_branch,
)
from beta_engine.infrastructure.db.saved_revision_season_closure import (
    install_saved_revision_season_closure,
    load_saved_revision_season_closure,
    rebind_cross_branch_season_closure,
)
from beta_engine.infrastructure.db.season_transition_fork_event import (
    rebind_verified_season_transition_event,
)
from beta_engine.infrastructure.db.week_transition_fork_bundle import (
    WeekTransitionForkAuditUnsupportedError,
    bind_event_free_transition_audit_to_ranking_fork,
)

pytestmark = pytest.mark.pr_critical


def _full_transition():
    """Build every ranking week, an authenticated receipt/event for each W1->W61."""
    policy = OfficialRankingPolicy(policy_id="policy", best_n=15)
    audit = RankingCommandAudit(actor_label="Admin", reason="Advance ranking")
    entries = []
    authorities = []
    receipts = []
    events = []
    publications = []
    predecessor = None
    for ordinal in range(62):
        current = RankingWeek(season_index=ordinal // 61, week=ordinal % 61 + 1)
        if ordinal == 0:
            command = RankingBootstrapCommand(
                command_id="ranking-bootstrap", run_id="run",
                branch_id="source", target_week=current, policy=policy,
                players=(), discipline="stored_zeros",
            )
        elif ordinal == 61:
            command = RankingWeekCommand(
                command_id="ranking-season-1",
                context=RankingTransitionContext(
                    run_id="run", branch_id="source",
                    completed_week=predecessor.week,
                    target_week=current, policy=policy, players=(),
                    discipline="stored_zeros",
                ),
                tournaments=(),
            )
        else:
            authority = RankingTransitionAuthority(
                run_id="run", branch_id="source", base_revision_id="source-root",
                completed_week=predecessor.week, target_week=current,
                players=(), policy=policy, audit=audit,
                provenance="Complete 61-week test evidence",
                adopted_by_command_id=f"ranking-week-{ordinal}",
            )
            authorities.append(authority)
            command = RankingWeekCommand(
                command_id=f"ranking-week-{ordinal}",
                context=RankingTransitionContext(
                    run_id="run", branch_id="source",
                    completed_week=predecessor.week, target_week=current,
                    policy=policy, players=(), discipline="stored_zeros",
                ),
                tournaments=(), audit=audit,
                authority_fingerprint=authority.fingerprint,
            )
        snapshot = calculate_official_ranking(
            run_id="run", branch_id="source", week=current,
            policy=policy, players=(), results=(), previous=predecessor,
        )
        entries.append(RankingRevisionEntry(
            snapshot=snapshot,
            inputs=RankingInputManifest(
                players=(), results=(), zeros_from_history=True,
                command_request_fingerprint=command.fingerprint,
            ),
            receipts=(RankingRevisionReceipt(
                command_id=command.command_id,
                request_fingerprint=command.fingerprint,
                request_payload_json=command.canonical_request_json,
            ),),
        ))
        publications.append({
            "run_id": "run", "branch_id": "source",
            "week_ordinal": ordinal,
            "snapshot_fingerprint": snapshot.fingerprint,
            "payload_json": snapshot.model_dump_json(),
        })
        if 0 < ordinal < 61:
            official_command = AuthoritativeWeekTransitionCommand(
                command_id=f"advance-week-{ordinal:02d}",
                run_id="run", branch_id="source",
                base_revision_id="source-root",
                completed_week=predecessor.week, target_week=current,
                authority_fingerprint=authorities[-1].fingerprint,
                audit=audit,
            )
            result = AuthoritativeWeekTransitionResult(
                run_id="run", branch_id="source",
                command_id=official_command.command_id,
                completed_week=official_command.completed_week,
                target_week=official_command.target_week,
                official_ranking_fingerprint=snapshot.fingerprint,
                player_lifecycle_fingerprint="1" * 64,
                player_sporting_fingerprint="2" * 64,
                player_health_fingerprint="3" * 64,
            )
            receipts.append({
                "run_id": "run", "branch_id": "source",
                "command_id": official_command.command_id,
                "request_fingerprint": official_command.fingerprint,
                "request_payload_json": official_command.canonical_request_json,
                "result_json": result.model_dump_json(),
            })
            events.append({
                "run_id": "run", "branch_id": "source",
                "command_id": official_command.command_id,
                "week_ordinal": ordinal,
                "event_kind": "week_transition_completed",
                "payload_json": _world_event_payload(
                    official_command, result.official_ranking_fingerprint,
                    result.player_lifecycle_fingerprint,
                    result.player_sporting_fingerprint,
                    result.player_health_fingerprint,
                ),
            })
        predecessor = snapshot

    closing = calculate_season_closing_ranking(
        run_id="run", branch_id="source",
        completed_week=RankingWeek(season_index=0, week=61),
        policy=policy, players=(), results=(),
        predecessor=entries[60].snapshot,
    )
    package = build_season_closure_package(closing_ranking=closing)
    marker = bind_season_closure_marker(
        package.marker, final_saved_revision_id="source-season-revision",
    )
    source_payload = {"content": {}}
    install_saved_revision_season_closure(
        source_payload, package=package, marker=marker,
    )
    event_payload = {
        "schema_version": "season_transition_world_event.v1",
        "command_id": "advance-season",
        "completed_week": closing.completed_week.model_dump(mode="json"),
        "target_week": RankingWeek(season_index=1, week=1).model_dump(mode="json"),
        "saved_revision_id": "source-season-revision",
        "configuration_fingerprint": "a" * 64,
        "closing_ranking_fingerprint": closing.fingerprint,
        "season_summary_fingerprint": package.summary.fingerprint,
        "closure_marker_fingerprint": marker.fingerprint,
        "player_sporting_fingerprint": "2" * 64,
        "player_lifecycle_fingerprint": "1" * 64,
        "player_health_fingerprint": "3" * 64,
        "official_ranking_fingerprint": entries[-1].snapshot.fingerprint,
    }
    events.append({
        "run_id": "run", "branch_id": "source",
        "command_id": "advance-season", "week_ordinal": 61,
        "event_kind": "season_transition_completed",
        "payload_json": json.dumps(
            event_payload, sort_keys=True, separators=(",", ":")
        ),
    })
    transition = {
        "world": {
            "run_id": "run", "branch_id": "source",
            "current_ordinal": 61,
            "ranking_fingerprint": entries[-1].snapshot.fingerprint,
        },
        "publications": publications,
        "receipts": sorted(receipts, key=lambda row: row["command_id"]),
        "events": sorted(events, key=lambda row: row["command_id"]),
    }
    source = RankingRevisionState(
        schema_version="ranking_revision_state.v7",
        run_id="run", branch_id="source",
        entries=tuple(entries), sources=(), zero_sources=(),
        transition_authorities=tuple(authorities),
        season_closing_rankings=(closing,),
        authoritative_transition_state=transition,
    )
    stripped = source.model_copy(update={
        "authoritative_transition_state": {**transition, "receipts": [], "events": []},
    })
    target = remap_source_free_ranking_state_for_branch(
        stripped,
        run_id="run", source_branch_id="source",
        target_branch_id="target", target_base_revision_id="fork-root",
    )
    target_payload = {"content": {}}
    target_closure = rebind_cross_branch_season_closure(
        source_payload, target_payload,
        run_id="run", source_branch_id="source",
        source_revision_id="source-season-revision",
        target_branch_id="target", target_revision_id="fork-root",
        source_closing=closing,
        target_closing=target.season_closing_rankings[0],
    )
    maps = dict(
        lifecycle_fingerprint_map={"1" * 64: "4" * 64},
        sporting_fingerprint_map={"2" * 64: "5" * 64},
        health_fingerprint_map={"3" * 64: "6" * 64},
    )
    rebounded_event = rebind_verified_season_transition_event(
        events[-1],
        run_id="run", source_branch_id="source",
        target_branch_id="target",
        source_revision_id="source-season-revision",
        target_revision_id="fork-root",
        source_closure=load_saved_revision_season_closure(
            source_payload, run_id="run", branch_id="source",
            revision_id="source-season-revision",
        ),
        target_closure=target_closure,
        source_ranking=source, target_ranking=target,
        **maps,
    )
    return source, target, rebounded_event, maps


def _bind(source, target, event, maps):
    return bind_event_free_transition_audit_to_ranking_fork(
        source=source, target=target,
        run_id="run", source_branch_id="source", target_branch_id="target",
        verified_season_event=event,
        valid_source_revision_ids=frozenset({"source-root", "source-season-revision"}),
        **maps,
    )


def test_week61_to_next_season_week1_rebinds_complete_61_week_history():
    source, target, event, maps = _full_transition()
    rebound = _bind(source, target, event, maps)
    audit = rebound.authoritative_transition_state
    assert len(audit["publications"]) == 62
    assert len(audit["receipts"]) == 60
    assert len(audit["events"]) == 61
    assert len(rebound.season_closing_rankings) == 1
    assert [row["event_kind"] for row in audit["events"]].count(
        "season_transition_completed"
    ) == 1
    assert [row["week_ordinal"] for row in audit["events"]].count(61) == 1
    assert audit["world"]["current_ordinal"] == 61
    assert audit["world"]["ranking_fingerprint"] == rebound.entries[-1].snapshot.fingerprint
    assert source.authoritative_transition_state["events"][-1]["branch_id"] == "source"
    assert source.entries[-1].snapshot.fingerprint != rebound.entries[-1].snapshot.fingerprint
    assert RankingRevisionState.model_validate_json(rebound.model_dump_json()) == rebound
    assert _bind(source, target, event, maps) == rebound


@pytest.mark.parametrize("mutation", ["omit_week_event", "omit_season_event", "duplicate_season", "fake_target_event"])
def test_incomplete_or_spoofed_season_history_is_rejected(mutation):
    source, target, event, maps = _full_transition()
    rows = list(source.authoritative_transition_state["events"])
    if mutation == "omit_week_event":
        rows = [row for row in rows if row["command_id"] != "advance-week-25"]
    elif mutation == "omit_season_event":
        rows = [row for row in rows if row["event_kind"] != "season_transition_completed"]
    elif mutation == "duplicate_season":
        rows.append({**rows[0], "event_kind": "season_transition_completed"})
    else:
        event = {**event, "branch_id": "foreign"}
    if mutation != "fake_target_event":
        revised = dict(source.authoritative_transition_state)
        revised["events"] = rows
        source = source.model_copy(update={"authoritative_transition_state": revised})
    with pytest.raises((WeekTransitionForkAuditUnsupportedError, ValueError)):
        _bind(source, target, event, maps)
