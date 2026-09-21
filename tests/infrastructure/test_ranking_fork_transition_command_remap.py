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
