from __future__ import annotations

import pytest

from beta_engine.domain.rankings.command_audit import RankingCommandAudit
from beta_engine.domain.rankings.official import (
    OfficialRankingPolicy,
    RankingWeek,
)
from beta_engine.domain.rankings.transition_authority import RankingTransitionAuthority
from beta_engine.infrastructure.db.ranking_fork_remap import (
    RankingForkRemapUnsupportedError,
    _remap_transition_authorities,
)

pytestmark = pytest.mark.pr_critical


def _authority(*, branch_id: str, completed_week: int, command_id: str):
    return RankingTransitionAuthority(
        run_id="run-one",
        branch_id=branch_id,
        base_revision_id="revision-source",
        completed_week=RankingWeek(season_index=0, week=completed_week),
        target_week=RankingWeek(season_index=0, week=completed_week + 1),
        players=(),
        policy=OfficialRankingPolicy(policy_id="policy-one"),
        provenance="Canonical lifecycle-derived ranking transition",
        adopted_by_command_id=command_id,
        audit=RankingCommandAudit(
            actor_label="Admin",
            reason="Advance authoritative ranking week",
        ),
    )


def test_transition_authorities_rebind_branch_and_saved_revision_identity():
    source = (
        _authority(branch_id="branch-source", completed_week=1, command_id="week-2"),
        _authority(branch_id="branch-source", completed_week=2, command_id="week-3"),
    )

    remapped, by_source_fingerprint = _remap_transition_authorities(
        source,
        run_id="run-one",
        source_branch_id="branch-source",
        target_branch_id="branch-target",
        target_base_revision_id="revision-target-fork-root",
    )

    assert [item.target_week.week for item in remapped] == [2, 3]
    assert all(item.branch_id == "branch-target" for item in remapped)
    assert all(
        item.base_revision_id == "revision-target-fork-root" for item in remapped
    )
    assert [item.players for item in remapped] == [item.players for item in source]
    assert [item.policy for item in remapped] == [item.policy for item in source]
    assert [item.audit for item in remapped] == [item.audit for item in source]
    assert all(
        target.fingerprint != original.fingerprint
        for original, target in zip(source, remapped, strict=True)
    )
    assert {
        item.fingerprint for item in source
    } == set(by_source_fingerprint)
    assert by_source_fingerprint[source[0].fingerprint] == remapped[0]


def test_transition_authority_wrong_source_scope_fails_closed():
    source = (_authority(branch_id="other-branch", completed_week=1, command_id="week-2"),)

    with pytest.raises(
        RankingForkRemapUnsupportedError,
        match="scope does not match the source Branch",
    ):
        _remap_transition_authorities(
            source,
            run_id="run-one",
            source_branch_id="branch-source",
            target_branch_id="branch-target",
            target_base_revision_id="revision-target-fork-root",
        )


def test_transition_authority_noncanonical_order_fails_closed():
    source = (
        _authority(branch_id="branch-source", completed_week=2, command_id="week-3"),
        _authority(branch_id="branch-source", completed_week=1, command_id="week-2"),
    )

    with pytest.raises(
        RankingForkRemapUnsupportedError,
        match="canonical target-week order",
    ):
        _remap_transition_authorities(
            source,
            run_id="run-one",
            source_branch_id="branch-source",
            target_branch_id="branch-target",
            target_base_revision_id="revision-target-fork-root",
        )


def test_transition_authority_requires_target_revision_identity():
    source = (_authority(branch_id="branch-source", completed_week=1, command_id="week-2"),)

    with pytest.raises(
        RankingForkRemapUnsupportedError,
        match="target Saved Revision id",
    ):
        _remap_transition_authorities(
            source,
            run_id="run-one",
            source_branch_id="branch-source",
            target_branch_id="branch-target",
            target_base_revision_id=" ",
        )
