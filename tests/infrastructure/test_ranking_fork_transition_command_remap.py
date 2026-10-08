from __future__ import annotations

import pytest

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
from beta_engine.domain.rankings.transition_authority import RankingTransitionAuthority
from beta_engine.infrastructure.db.ranking_fork_remap import (
    RankingForkRemapUnsupportedError,
    remap_source_free_ranking_state_for_branch,
)

pytestmark = pytest.mark.pr_critical


def _transition_backed_state() -> RankingRevisionState:
    policy = OfficialRankingPolicy(policy_id="policy")
    week1 = RankingWeek(season_index=0, week=1)
    week2 = RankingWeek(season_index=0, week=2)

    bootstrap = RankingBootstrapCommand(
        command_id="bootstrap",
        run_id="run",
        branch_id="source",
        target_week=week1,
        policy=policy,
        players=(),
        discipline="none",
    )
    snapshot1 = calculate_official_ranking(
        run_id="run",
        branch_id="source",
        week=week1,
        policy=policy,
        players=(),
        results=(),
        previous=None,
        disciplinary_zeros=(),
    )
    inputs1 = RankingInputManifest(
        players=(),
        results=(),
        command_request_fingerprint=bootstrap.fingerprint,
    )

    audit = RankingCommandAudit(
        actor_label="Admin",
        reason="Advance authoritative ranking week",
    )
    authority = RankingTransitionAuthority(
        run_id="run",
        branch_id="source",
        base_revision_id="source-revision",
        completed_week=week1,
        target_week=week2,
        players=(),
        policy=policy,
        provenance="Canonical lifecycle-derived ranking transition",
        adopted_by_command_id="week-2",
        audit=audit,
    )
    weekly = RankingWeekCommand(
        command_id="week-2",
        context=RankingTransitionContext(
            run_id="run",
            branch_id="source",
            completed_week=week1,
            target_week=week2,
            policy=policy,
            players=(),
            discipline="stored_zeros",
        ),
        tournaments=(),
        zero_versions=(),
        audit=audit,
        authority_fingerprint=authority.fingerprint,
    )
    snapshot2 = calculate_official_ranking(
        run_id="run",
        branch_id="source",
        week=week2,
        policy=policy,
        players=(),
        results=(),
        previous=snapshot1,
        disciplinary_zeros=(),
    )
    inputs2 = RankingInputManifest(
        players=(),
        results=(),
        zeros_from_history=True,
        command_request_fingerprint=weekly.fingerprint,
    )

    return RankingRevisionState(
        schema_version="ranking_revision_state.v4",
        run_id="run",
        branch_id="source",
        entries=(
            RankingRevisionEntry(
                snapshot=snapshot1,
                inputs=inputs1,
                receipts=(
                    RankingRevisionReceipt(
                        command_id=bootstrap.command_id,
                        request_fingerprint=bootstrap.fingerprint,
                        request_payload_json=bootstrap.canonical_request_json,
                    ),
                ),
            ),
            RankingRevisionEntry(
                snapshot=snapshot2,
                inputs=inputs2,
                receipts=(
                    RankingRevisionReceipt(
                        command_id=weekly.command_id,
                        request_fingerprint=weekly.fingerprint,
                        request_payload_json=weekly.canonical_request_json,
                    ),
                ),
            ),
        ),
        sources=(),
        transition_authorities=(authority,),
    )


def test_transition_backed_weekly_command_remaps_to_target_fork_root():
    source = _transition_backed_state()

    target = remap_source_free_ranking_state_for_branch(
        source,
        run_id="run",
        source_branch_id="source",
        target_branch_id="target",
        target_base_revision_id="target-materialized-root",
    )

    assert target.branch_id == "target"
    assert len(target.transition_authorities) == 1
    target_authority = target.transition_authorities[0]
    source_authority = source.transition_authorities[0]
    assert target_authority.branch_id == "target"
    assert target_authority.base_revision_id == "target-materialized-root"
    assert target_authority.fingerprint != source_authority.fingerprint
    assert target_authority.players == source_authority.players
    assert target_authority.policy == source_authority.policy
    assert target_authority.audit == source_authority.audit

    target_weekly = RankingWeekCommand.model_validate_json(
        target.entries[1].receipts[0].request_payload_json
    )
    assert target_weekly.context.branch_id == "target"
    assert target_weekly.audit == source_authority.audit
    assert target_weekly.authority_fingerprint == target_authority.fingerprint
    assert target.entries[1].receipts[0].request_fingerprint == target_weekly.fingerprint
    assert target.entries[1].snapshot.branch_id == "target"
    assert target.entries[1].snapshot.fingerprint != source.entries[1].snapshot.fingerprint


def test_transition_backed_fork_requires_real_target_saved_revision_identity():
    source = _transition_backed_state()

    with pytest.raises(
        RankingForkRemapUnsupportedError,
        match="target materialized Saved Revision id",
    ):
        remap_source_free_ranking_state_for_branch(
            source,
            run_id="run",
            source_branch_id="source",
            target_branch_id="target",
        )


def test_detached_transition_authority_fails_closed():
    source = _transition_backed_state()
    extra = source.transition_authorities[0].model_copy(
        update={
            "target_week": RankingWeek(season_index=0, week=3),
            "completed_week": RankingWeek(season_index=0, week=2),
            "adopted_by_command_id": "week-3",
        }
    )
    source = source.model_copy(
        update={"transition_authorities": source.transition_authorities + (extra,)}
    )

    with pytest.raises(
        RankingForkRemapUnsupportedError,
        match="transition authorities are not completely owned",
    ):
        remap_source_free_ranking_state_for_branch(
            source,
            run_id="run",
            source_branch_id="source",
            target_branch_id="target",
            target_base_revision_id="target-materialized-root",
        )


def _with_publication_world(source: RankingRevisionState) -> RankingRevisionState:
    publications = [
        {
            "run_id": source.run_id,
            "branch_id": source.branch_id,
            "week_ordinal": entry.snapshot.week.ordinal,
            "snapshot_fingerprint": entry.snapshot.fingerprint,
            "payload_json": entry.snapshot.model_dump_json(),
        }
        for entry in source.entries
    ]
    world = {
        "run_id": source.run_id,
        "branch_id": source.branch_id,
        "current_ordinal": source.entries[-1].snapshot.week.ordinal,
        "ranking_fingerprint": source.entries[-1].snapshot.fingerprint,
    }
    return source.model_copy(
        update={
            "authoritative_transition_state": {
                "world": world,
                "publications": publications,
                "receipts": [],
                "events": [],
            }
        }
    )


def test_publications_and_world_head_remap_to_target_ranking_lineage():
    source = _with_publication_world(_transition_backed_state())

    target = remap_source_free_ranking_state_for_branch(
        source,
        run_id="run",
        source_branch_id="source",
        target_branch_id="target",
        target_base_revision_id="target-materialized-root",
    )

    transition = target.authoritative_transition_state
    assert transition is not None
    assert transition["receipts"] == []
    assert transition["events"] == []
    assert [row["week_ordinal"] for row in transition["publications"]] == [0, 1]
    for row, entry in zip(transition["publications"], target.entries, strict=True):
        assert row["run_id"] == "run"
        assert row["branch_id"] == "target"
        assert row["snapshot_fingerprint"] == entry.snapshot.fingerprint
        assert row["payload_json"] == entry.snapshot.model_dump_json()
    assert transition["world"] == {
        "run_id": "run",
        "branch_id": "target",
        "current_ordinal": 1,
        "ranking_fingerprint": target.entries[-1].snapshot.fingerprint,
    }
    assert (
        transition["world"]["ranking_fingerprint"]
        != source.authoritative_transition_state["world"]["ranking_fingerprint"]
    )


def test_publication_payload_mismatch_fails_closed():
    source = _transition_backed_state()
    broken_state = {
        "world": None,
        "publications": [
            {
                "run_id": "run",
                "branch_id": "source",
                "week_ordinal": 0,
                "snapshot_fingerprint": source.entries[0].snapshot.fingerprint,
                "payload_json": source.entries[1].snapshot.model_dump_json(),
            }
        ],
        "receipts": [],
        "events": [],
    }

    from beta_engine.infrastructure.db.ranking_fork_remap import (
        _remap_publication_world_state,
    )

    with pytest.raises(
        RankingForkRemapUnsupportedError,
        match="publication differs from frozen source ranking history",
    ):
        _remap_publication_world_state(
            broken_state,
            run_id="run",
            source_branch_id="source",
            target_branch_id="target",
            source_entries=source.entries,
            target_entries=source.entries,
        )


def test_transition_receipts_events_stay_fail_closed_until_player_state_remap():
    source = _transition_backed_state()
    raw_state = {
        "world": None,
        "publications": [],
        "receipts": [{"command_id": "week-2"}],
        "events": [],
    }

    from beta_engine.infrastructure.db.ranking_fork_remap import (
        _remap_publication_world_state,
    )

    with pytest.raises(
        RankingForkRemapUnsupportedError,
        match="lifecycle/sporting remapping first",
    ):
        _remap_publication_world_state(
            raw_state,
            run_id="run",
            source_branch_id="source",
            target_branch_id="target",
            source_entries=source.entries,
            target_entries=source.entries,
        )


def _paired_completed_transition():
    """A real ranking lineage plus one fully frozen empty-week transition."""
    from beta_engine.application.authoritative_week_transition import (
        AuthoritativeWeekTransitionCommand,
        AuthoritativeWeekTransitionResult,
    )
    from beta_engine.infrastructure.db.authoritative_week_transition import (
        _world_event_payload,
    )

    source = _with_publication_world(_transition_backed_state())
    authority = source.transition_authorities[0]
    week_command = AuthoritativeWeekTransitionCommand(
        command_id="advance-week-1",
        run_id="run",
        branch_id="source",
        base_revision_id=authority.base_revision_id,
        completed_week=authority.completed_week,
        target_week=authority.target_week,
        authority_fingerprint=authority.fingerprint,
        audit=authority.audit,
    )
    result = AuthoritativeWeekTransitionResult(
        run_id="run",
        branch_id="source",
        command_id=week_command.command_id,
        completed_week=week_command.completed_week,
        target_week=week_command.target_week,
        official_ranking_fingerprint=source.entries[1].snapshot.fingerprint,
        player_lifecycle_fingerprint="1" * 64,
        player_sporting_fingerprint="2" * 64,
        player_health_fingerprint="3" * 64,
    )
    source_state = {
        **source.authoritative_transition_state,
        "receipts": [{
            "run_id": "run",
            "branch_id": "source",
            "command_id": week_command.command_id,
            "request_fingerprint": week_command.fingerprint,
            "request_payload_json": week_command.canonical_request_json,
            "result_json": result.model_dump_json(),
        }],
        "events": [{
            "run_id": "run",
            "branch_id": "source",
            "command_id": week_command.command_id,
            "week_ordinal": week_command.target_week.ordinal,
            "event_kind": "week_transition_completed",
            "payload_json": _world_event_payload(
                week_command,
                result.official_ranking_fingerprint,
                result.player_lifecycle_fingerprint,
                result.player_sporting_fingerprint,
                result.player_health_fingerprint,
            ),
        }],
    }
    source = RankingRevisionState.model_validate_json(
        source.model_copy(
            update={"authoritative_transition_state": source_state}
        ).model_dump_json()
    )
    # Preparation is in memory only. Production must not install an
    # audit-stripped bundle; the helper will rebind the complete evidence.
    source_without_audit = source.model_copy(
        update={
            "authoritative_transition_state": {
                **source_state, "receipts": [], "events": [],
            }
        }
    )
    target = remap_source_free_ranking_state_for_branch(
        source_without_audit,
        run_id="run",
        source_branch_id="source",
        target_branch_id="target",
        target_base_revision_id="target-materialized-root",
    )
    return source, target


def _bind_pair(source, target, **overrides):
    from beta_engine.infrastructure.db.week_transition_fork_bundle import (
        bind_event_free_transition_audit_to_ranking_fork,
    )
    args = {
        "source": source,
        "target": target,
        "run_id": "run",
        "source_branch_id": "source",
        "target_branch_id": "target",
        "lifecycle_fingerprint_map": {"1" * 64: "4" * 64},
        "sporting_fingerprint_map": {"2" * 64: "5" * 64},
        "health_fingerprint_map": {"3" * 64: "6" * 64},
    }
    args.update(overrides)
    return bind_event_free_transition_audit_to_ranking_fork(**args)


def test_verified_week_transition_audit_rebinds_into_complete_ranking_bundle():
    from beta_engine.application.authoritative_week_transition import (
        AuthoritativeWeekTransitionCommand,
        AuthoritativeWeekTransitionResult,
    )

    source, target = _paired_completed_transition()
    rebound = _bind_pair(source, target)
    assert rebound.authoritative_transition_state["world"] == (
        target.authoritative_transition_state["world"]
    )
    audit = rebound.authoritative_transition_state
    assert len(audit["receipts"]) == len(audit["events"]) == 1
    command = AuthoritativeWeekTransitionCommand.model_validate_json(
        audit["receipts"][0]["request_payload_json"]
    )
    result = AuthoritativeWeekTransitionResult.model_validate_json(
        audit["receipts"][0]["result_json"]
    )
    assert command.branch_id == result.branch_id == "target"
    assert command.base_revision_id == "target-materialized-root"
    assert command.authority_fingerprint == rebound.transition_authorities[0].fingerprint
    assert result.official_ranking_fingerprint == rebound.entries[1].snapshot.fingerprint
    assert result.player_lifecycle_fingerprint == "4" * 64
    assert result.player_sporting_fingerprint == "5" * 64
    assert result.player_health_fingerprint == "6" * 64
    assert source.authoritative_transition_state["receipts"][0]["branch_id"] == "source"
    assert target.authoritative_transition_state["receipts"] == []
    assert RankingRevisionState.model_validate_json(rebound.model_dump_json()) == rebound
    assert _bind_pair(source, target).fingerprint == rebound.fingerprint


def test_rank_transition_bundle_rejects_corrupted_snapshot_link_even_with_matching_event():
    from beta_engine.application.authoritative_week_transition import (
        AuthoritativeWeekTransitionCommand,
        AuthoritativeWeekTransitionResult,
    )
    from beta_engine.infrastructure.db.authoritative_week_transition import (
        _world_event_payload,
    )

    source, target = _paired_completed_transition()
    state = source.authoritative_transition_state
    receipt = state["receipts"][0].copy()
    result = AuthoritativeWeekTransitionResult.model_validate_json(receipt["result_json"])
    forged_result = result.model_copy(update={"official_ranking_fingerprint": "f" * 64})
    receipt["result_json"] = forged_result.model_dump_json()
    command = AuthoritativeWeekTransitionCommand.model_validate_json(
        receipt["request_payload_json"]
    )
    forged_event = {
        **state["events"][0],
        "payload_json": _world_event_payload(
            command, forged_result.official_ranking_fingerprint,
            forged_result.player_lifecycle_fingerprint,
            forged_result.player_sporting_fingerprint,
            forged_result.player_health_fingerprint,
        ),
    }
    corrupted = source.model_copy(
        update={"authoritative_transition_state": {
            **state, "receipts": [receipt], "events": [forged_event],
        }}
    )
    from beta_engine.infrastructure.db.week_transition_fork_audit import (
        WeekTransitionForkAuditUnsupportedError,
    )
    with pytest.raises(
        WeekTransitionForkAuditUnsupportedError,
        match="Saved Week Transition receipt differs from frozen ranking authority",
    ):
        _bind_pair(corrupted, target)


@pytest.mark.parametrize(
    "change",
    [
        "missing_lifecycle", "missing_sporting", "missing_health",
        "branch_mismatch", "audit_already_installed", "authority_mismatch",
    ],
)
def test_rank_transition_bundle_rejects_missing_mappings_or_wrong_target(change):
    from beta_engine.infrastructure.db.week_transition_fork_audit import (
        WeekTransitionForkAuditUnsupportedError,
    )

    source, target = _paired_completed_transition()
    overrides = {}
    if change == "missing_lifecycle":
        overrides["lifecycle_fingerprint_map"] = {}
    elif change == "missing_sporting":
        overrides["sporting_fingerprint_map"] = {}
    elif change == "missing_health":
        overrides["health_fingerprint_map"] = {}
    elif change == "branch_mismatch":
        overrides["target_branch_id"] = "wrong"
    elif change == "audit_already_installed":
        target = target.model_copy(
            update={"authoritative_transition_state": {
                **target.authoritative_transition_state,
                "receipts": source.authoritative_transition_state["receipts"],
            }}
        )
    elif change == "authority_mismatch":
        target = target.model_copy(
            update={"transition_authorities": ()}
        )
    with pytest.raises(WeekTransitionForkAuditUnsupportedError):
        _bind_pair(source, target, **overrides)
