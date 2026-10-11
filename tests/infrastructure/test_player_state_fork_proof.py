"""Guard materialized Branch player histories against plausible hash-only forks."""

from __future__ import annotations

import pytest

from beta_engine.domain.players.health import PlayerHealthWeekState
from beta_engine.domain.players.lifecycle import PlayerLifecycleWeekState
from beta_engine.domain.players.sporting import (
    CompletedWeekSportingContext,
    PlayerSportingWeekState,
)
from beta_engine.domain.rankings.official import RankingWeek
from beta_engine.infrastructure.db.player_state_fork_proof import (
    PlayerStateForkProofError,
    verify_fork_player_state_maps,
)

pytestmark = pytest.mark.pr_critical


def _pair():
    weeks = (
        RankingWeek(season_index=0, week=1),
        RankingWeek(season_index=0, week=2),
    )
    context = CompletedWeekSportingContext(
        run_id="run",
        branch_id="source",
        completed_week=weeks[0],
        competitive_match_counts=(),
        source_fingerprints=(),
        provenance="event-free, completed week",
    )
    target_context = CompletedWeekSportingContext.model_validate_json(
        context.model_copy(update={"branch_id": "target"}).model_dump_json()
    )

    def histories(branch, completed_context):
        lifecycle = []
        sporting = []
        health = []
        for i, week in enumerate(weeks):
            lifecycle.append(
                PlayerLifecycleWeekState(
                    run_id="run",
                    branch_id=branch,
                    week=week,
                    players=(),
                    source_initial_world_fingerprint="original-world",
                    predecessor_fingerprint=(
                        lifecycle[-1].fingerprint if lifecycle else None
                    ),
                )
            )
            sporting.append(
                PlayerSportingWeekState(
                    run_id="run",
                    branch_id=branch,
                    week=week,
                    players=(),
                    completed_context_fingerprint=(
                        "bootstrap:not-a-completed-week"
                        if i == 0 else completed_context.fingerprint
                    ),
                    source_initial_world_fingerprint="original-world",
                    predecessor_fingerprint=(
                        sporting[-1].fingerprint if sporting else None
                    ),
                    stage_provenance="unchanged source policy",
                )
            )
            health.append(
                PlayerHealthWeekState(
                    run_id="run",
                    branch_id=branch,
                    week=week,
                    players=(),
                    source_initial_world_fingerprint="original-world",
                    predecessor_fingerprint=(
                        health[-1].fingerprint if health else None
                    ),
                    stage_provenance="no invented health event",
                )
            )
        return tuple(lifecycle), tuple(sporting), tuple(health)

    sl, ss, sh = histories("source", context)
    tl, ts, th = histories("target", target_context)
    return {
        "run_id": "run",
        "source_branch_id": "source",
        "target_branch_id": "target",
        "source_lifecycle": sl,
        "target_lifecycle": tl,
        "source_sporting": ss,
        "target_sporting": ts,
        "source_health": sh,
        "target_health": th,
        "source_contexts": (context,),
        "target_contexts": (target_context,),
    }


def test_complete_week_2_player_histories_rebind_without_changing_facts():
    kwargs = _pair()
    proof = verify_fork_player_state_maps(**kwargs)
    assert len(proof.lifecycle) == len(proof.sporting) == len(proof.health) == 2
    assert len(proof.contexts) == 1
    assert proof.lifecycle == {
        source.fingerprint: target.fingerprint
        for source, target in zip(
            kwargs["source_lifecycle"], kwargs["target_lifecycle"], strict=True
        )
    }
    assert proof.sporting == {
        source.fingerprint: target.fingerprint
        for source, target in zip(
            kwargs["source_sporting"], kwargs["target_sporting"], strict=True
        )
    }
    assert proof.contexts[
        kwargs["source_contexts"][0].fingerprint
    ] == kwargs["target_contexts"][0].fingerprint
    assert verify_fork_player_state_maps(**kwargs) == proof


@pytest.mark.parametrize(
    "corruption",
    [
        "changed_lifecycle_truth",
        "changed_sporting_policy",
        "changed_health_truth",
        "changed_sporting_context",
        "bad_sporting_context_link",
        "different_run",
        "same_branch",
        "historical_gap",
        "missing_health_week",
        "foreign_target",
        "wrong_lifecycle_predecessor",
        "sporting_week_mismatch",
        "context_absent",
    ],
)
def test_false_or_incomplete_player_history_fork_fails_closed(corruption):
    kwargs = _pair()
    if corruption == "changed_lifecycle_truth":
        states = list(kwargs["target_lifecycle"])
        states[0] = states[0].model_copy(
            update={"source_initial_world_fingerprint": "fabricated-origin"}
        )
        kwargs["target_lifecycle"] = tuple(states)
    elif corruption == "changed_sporting_policy":
        states = list(kwargs["target_sporting"])
        states[1] = states[1].model_copy(
            update={"stage_provenance": "retroactively changed"}
        )
        kwargs["target_sporting"] = tuple(states)
    elif corruption == "changed_health_truth":
        states = list(kwargs["target_health"])
        states[1] = states[1].model_copy(
            update={"stage_provenance": "invented medical history"}
        )
        kwargs["target_health"] = tuple(states)
    elif corruption == "changed_sporting_context":
        source_context = kwargs["target_contexts"][0]
        kwargs["target_contexts"] = (
            source_context.model_copy(update={"provenance": "forged result"}),
        )
    elif corruption == "bad_sporting_context_link":
        states = list(kwargs["target_sporting"])
        states[1] = states[1].model_copy(
            update={"completed_context_fingerprint": "unmapped-context"}
        )
        kwargs["target_sporting"] = tuple(states)
    elif corruption == "different_run":
        kwargs["run_id"] = "another"
    elif corruption == "same_branch":
        kwargs["target_branch_id"] = "source"
    elif corruption == "historical_gap":
        states = list(kwargs["target_health"])
        states[1] = states[1].model_copy(
            update={"week": RankingWeek(season_index=0, week=4)}
        )
        kwargs["target_health"] = tuple(states)
    elif corruption == "missing_health_week":
        kwargs["target_health"] = kwargs["target_health"][:1]
    elif corruption == "foreign_target":
        states = list(kwargs["target_lifecycle"])
        states[1] = states[1].model_copy(update={"branch_id": "another"})
        kwargs["target_lifecycle"] = tuple(states)
    elif corruption == "wrong_lifecycle_predecessor":
        states = list(kwargs["target_lifecycle"])
        states[1] = states[1].model_copy(
            update={"predecessor_fingerprint": "wrong"}
        )
        kwargs["target_lifecycle"] = tuple(states)
    elif corruption == "sporting_week_mismatch":
        states = list(kwargs["target_sporting"])
        states[1] = states[1].model_copy(update={"week": RankingWeek(season_index=0, week=3)})
        kwargs["target_sporting"] = tuple(states)
    elif corruption == "context_absent":
        kwargs["target_contexts"] = ()
    with pytest.raises(PlayerStateForkProofError):
        verify_fork_player_state_maps(**kwargs)


def test_empty_pre_initial_world_fork_has_empty_verified_maps():
    proof = verify_fork_player_state_maps(
        run_id="run",
        source_branch_id="source",
        target_branch_id="target",
    )
    assert proof.lifecycle == {}
    assert proof.health == {}
    assert proof.sporting == {}
    assert proof.contexts == {}
