"""Pure independent match reducers; SQLite tests prove actual source authority."""

from types import SimpleNamespace

import pytest

from beta_engine.application.calendar_continuation_service import (
    CalendarContinuationCommand,
)
from beta_engine.domain.native_fork_baseline import project_native_fork_baseline
from beta_engine.domain.native_fork_source import (
    NativeForkComponentSource,
    NativeForkSavedSource,
    NativeForkSourceBinding,
)
from beta_engine.domain.native_fork_sporting import (
    NativeForkSportingCheckpoint,
    NativeForkSportingSaveCandidate,
    play_native_fork_match,
    verify_native_fork_sporting,
)
from tests.domain.test_calendar_canonical_match import source
from tests.domain.test_calendar_native_sporting_checkpoint import prepared

pytestmark = pytest.mark.pr_critical


def fixture(width=52, offset=1):
    original, context = prepared(width, offset)
    binding = NativeForkSourceBinding(
        run_id=original.run_id,
        source=NativeForkSavedSource(
            revision_id="original-saved",
            branch_id=original.branch_id,
            content_hash="a" * 64,
        ),
        components=(
            NativeForkComponentSource(key="initial_world", content_hash="d" * 64),
        ),
        historical_sources=(
            NativeForkSavedSource(
                revision_id="pre-play",
                branch_id=original.branch_id,
                content_hash="e" * 64,
            ),
        ),
    )
    baseline = project_native_fork_baseline(
        binding=binding,
        selected_source_branch_id=original.branch_id,
        target_branch_id="fork",
        week=original.week,
        world_fingerprint=original.source_initial_world_fingerprint,
        lifecycle=context["lifecycle"][-1],
        health=context["health"][-1],
        checkpoint=original,
        tour=SimpleNamespace(
            run_id=original.run_id,
            branch_id=original.branch_id,
            week=original.week,
            lifecycle_fingerprint=context["lifecycle"][-1].fingerprint,
            checkpoint_fingerprint=original.fingerprint,
            fingerprint="b" * 64,
            rankings=(SimpleNamespace(fingerprint="c" * 64),),
            slot_cursor=4,
        ),
    )
    world = SimpleNamespace(
        run_id=original.run_id,
        branch_id=original.branch_id,
        fingerprint=original.source_initial_world_fingerprint,
        players=tuple(p.player for p in source().players),
    )
    return (
        NativeForkSportingCheckpoint(
            root_saved_revision_id="fork-root", baseline=baseline
        ),
        world,
        context["source"],
        original,
    )


def command(cp, *, number=1, first="newborn", second="a"):
    return CalendarContinuationCommand(
        command_id=f"match-{number}",
        match_id=f"match-{number}",
        expected_saved_head=cp.root_saved_revision_id,
        expected_checkpoint_fingerprint=cp.fingerprint,
        player_a_id=first,
        player_b_id=second,
        seed=number,
        operator_label="Admin",
        audit_reason="Pure independent native fork match",
    )


@pytest.mark.parametrize("width,offset", [(7, 1), (52, 35), (61, 37), (80, 80)])
def test_independent_matches_use_full_current_population_and_replay_after_roundtrip(
    width, offset
):
    cp, world, prospects, original = fixture(width, offset)
    original_bytes, baseline_bytes = (
        original.model_dump_json(),
        cp.baseline.model_dump_json(),
    )
    one = play_native_fork_match(
        cp, command(cp), draft_version=3, world=world, prospects=prospects
    )
    two = play_native_fork_match(
        one, command(one, number=2), draft_version=4, world=world, prospects=prospects
    )
    assert one == play_native_fork_match(
        cp, command(cp), draft_version=3, world=world, prospects=prospects
    )
    match = one.steps[0].match
    assert match.branch_id == "fork" and match.source_saved_head == "fork-root"
    assert match.source_health_fingerprint == cp.baseline.source_health_fingerprint
    assert (
        match.result.rally_log.events
        and match.result.timeline_log
        and match.result.stamina_log
    )
    assert match.result.rally_log.input_snapshot_hash == match.log_anchor_hash
    assert match.week == original.week == two.week
    originals = {p.player_id: p for p in cp.players}
    for projection in match.canonical_projections:
        assert len(projection.canonical_attributes) == 57
        assert (
            projection.canonical_attributes
            == originals[projection.player_id].attributes
        )
        assert projection.current_form == originals[projection.player_id].current_form
    newborn = match.canonical_projections[0]
    assert newborn.player_id == "newborn" and newborn.age == 15
    assert newborn.hidden_career_traits is None and newborn.play_style == "unspecified"
    after_one = {p.player_id: p for p in one.players}
    for projection in two.steps[-1].match.canonical_projections:
        assert projection.current_form == after_one[projection.player_id].current_form
        assert (
            projection.long_term_fatigue
            == after_one[projection.player_id].long_term_fatigue
        )
    for current in two.players:
        assert current.attributes == originals[current.player_id].attributes
        assert current.potential_ovr == originals[current.player_id].potential_ovr
        if current.player_id not in {"newborn", "a"}:
            assert current == originals[current.player_id]
    decoded = NativeForkSportingCheckpoint.model_validate_json(two.model_dump_json())
    assert (
        verify_native_fork_sporting(
            decoded,
            world=world,
            prospects=prospects,
            command_factory=CalendarContinuationCommand,
        )
        == two
    )
    assert original.model_dump_json() == original_bytes
    assert two.baseline.model_dump_json() == baseline_bytes


@pytest.mark.parametrize(
    "case",
    [
        "head",
        "checkpoint",
        "retired",
        "unknown",
        "same",
        "foreign_world",
        "health",
        "version",
        "collision",
    ],
)
def test_fork_match_rejects_stale_foreign_or_unsupported_inputs(case):
    cp, world, prospects, _ = fixture()
    cmd = command(cp)
    version = 0
    if case == "head":
        cmd = cmd.model_copy(update={"expected_saved_head": "original-saved"})
    elif case == "checkpoint":
        cmd = cmd.model_copy(update={"expected_checkpoint_fingerprint": "0" * 64})
    elif case in {"retired", "health"}:
        if case == "retired":
            life = tuple(
                p.model_copy(update={"status": "retired"})
                if p.player_id == "newborn"
                else p
                for p in cp.baseline.lifecycle_players
            )
            baseline = cp.baseline.model_copy(update={"lifecycle_players": life})
        else:
            from beta_engine.domain.players.calendar_health import CalendarHealthRecord

            health = tuple(
                p.model_copy(
                    update={
                        "records": (
                            CalendarHealthRecord(
                                record_id="injury",
                                kind="Injury",
                                condition_key="input",
                                lifecycle="Active",
                                severity=10,
                                affected_domains=("movement",),
                                onset_week=cp.baseline.source_health_week,
                                provenance="Explicit test fact",
                            ),
                        )
                    }
                )
                if p.player_id == "newborn"
                else p
                for p in cp.baseline.health_players
            )
            baseline = cp.baseline.model_copy(update={"health_players": health})
        cp = cp.model_copy(update={"baseline": baseline})
        cmd = command(cp)
    elif case == "unknown":
        cmd = cmd.model_copy(update={"player_a_id": "unknown"})
    elif case == "same":
        cmd = cmd.model_copy(update={"player_a_id": "a"})
    elif case == "foreign_world":
        world.branch_id = "foreign"
    elif case in {"version", "collision"}:
        cp = play_native_fork_match(
            cp, cmd, draft_version=0, world=world, prospects=prospects
        )
        cmd = command(cp, number=2 if case == "version" else 1)
        version = 2 if case == "version" else 1
    with pytest.raises(ValueError):
        play_native_fork_match(
            cp, cmd, draft_version=version, world=world, prospects=prospects
        )


def test_fork_save_candidate_binds_exact_played_head_draft_and_roundtrips():
    cp, world, prospects, _ = fixture()
    played = play_native_fork_match(
        cp, command(cp), draft_version=3, world=world, prospects=prospects
    )
    candidate = NativeForkSportingSaveCandidate(
        run_id=cp.run_id,
        branch_id=cp.branch_id,
        parent_saved_revision_id=cp.root_saved_revision_id,
        draft_id="fork-draft",
        draft_version=4,
        checkpoint=played,
    )
    assert candidate.checkpoint == played
    assert candidate.fingerprint == NativeForkSportingSaveCandidate.model_validate_json(
        candidate.model_dump_json()
    ).fingerprint
    assert len(candidate.fingerprint) == 64
    assert candidate.fingerprint != candidate.model_copy(
        update={"draft_id": "other-draft"}
    ).fingerprint
    original = candidate.model_dump(mode="json")
    for changed in (
        {"run_id": "foreign-run"},
        {"branch_id": "foreign-branch"},
        {"parent_saved_revision_id": "foreign-root"},
        {"draft_version": 5},
        {"checkpoint": cp.model_dump(mode="json")},
    ):
        with pytest.raises(ValueError, match="exact played target root and draft"):
            NativeForkSportingSaveCandidate.model_validate(original | changed)
