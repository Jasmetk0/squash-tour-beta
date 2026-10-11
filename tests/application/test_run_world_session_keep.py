"""Session Keep recreates an exact reviewed Run source; no hidden persistent lock."""
from types import SimpleNamespace as NS

import pytest
from pydantic import ValidationError

from beta_engine.application.run_world_initial_pool_preview_service import (
    RunWorldInitialPoolPreviewRequest, RunWorldInitialPoolPreviewService,
)
from beta_engine.application.run_world_initial_world_service import (
    RunWorldInitialWorldAdoptionRequest, RunWorldInitialWorldService,
)
from tests.domain.initial_player_pool_contract_suite import country


pytestmark = pytest.mark.pr_critical


class Packages:
    def get(self, *, run_id, branch_id):
        return NS(fingerprint="a" * 64)


class Adapter:
    def project_countries(self, state, *, package_id):
        if package_id != "saved-world":
            raise ValueError(f"World '{package_id}' not found")
        return NS(
            countries=[
                country("BOG", population=12_000_000, system=3, popularity=3, tradition=3),
                country("GER", population=20_000_000, system=4, popularity=4, tradition=4),
            ],
            content_fingerprint="b" * 64,
        )

    def project_generation(self, state, *, package_id):
        return NS(identity_config=None, content_fingerprint="c" * 64)


def service():
    return RunWorldInitialPoolPreviewService(Packages(), Adapter())


def source_request():
    return RunWorldInitialPoolPreviewRequest(
        world_package_id="saved-world", season="2000/2001",
        seed=802, target_pool_size=32, min_age=18, max_age=25,
    )


def keep_request(original, ids, *, seed=803, **updates):
    return RunWorldInitialPoolPreviewRequest.model_validate({
        **original.request.model_dump(mode="json"),
        "seed": seed,
        "keep_from_seed": original.request.seed,
        "keep_from_preview_fingerprint": original.preview_fingerprint,
        "keep_player_ids": sorted(ids),
        **updates,
    })


def preview(request):
    return service().preview(run_id="run-one", branch_id="branch-one", request=request)


def test_keep_preserves_entire_real_source_player_objects_and_regenerates_remaining_slots():
    source = preview(source_request())
    retained_ids = [p.player_id for p in source.result.players[:3]]
    next_request = keep_request(source, retained_ids)
    first = preview(next_request)
    second = preview(next_request)
    assert first == second
    assert first.preview_fingerprint == second.preview_fingerprint
    assert first.preview_fingerprint != source.preview_fingerprint
    assert first.result.metadata.generated_count == 29
    assert first.result.metadata.preserved_locked_count == 3
    assert len(first.result.players) == len(source.result.players) == 32
    assert first.result.summary.locked_players == 0
    assert not any(p.locked for p in first.result.players)
    assert len({p.player_id for p in first.result.players}) == 32
    before = {p.player_id: p for p in source.result.players}
    after = {p.player_id: p for p in first.result.players}
    for player_id in retained_ids:
        assert after[player_id] == before[player_id]
    assert all(18 <= p.age_at_generation <= 25 for p in first.result.players)
    assert any(
        p.player_id not in retained_ids and
        (p.player_id not in before or p != before[p.player_id])
        for p in first.result.players
    )
    assert not any(p.locked for p in source.result.players)


def test_kept_players_survive_real_initial_world_adoption_as_unlocked():
    pool = preview(source_request())
    ids = sorted(p.player_id for p in pool.result.players[:4])
    request = RunWorldInitialWorldAdoptionRequest(
        command_id="test-session-keep",
        generation=keep_request(pool, ids),
        audit_label="Test keep",
        audit_reason="Verify original first-season players are retained",
        official_run=False, best_n=15, automatic_retirement_age=46,
    )
    service_instance = RunWorldInitialWorldService(service())
    a = service_instance.preview(
        run_id="run-one", branch_id="branch-one", request=request,
    )
    b = service_instance.preview(
        run_id="run-one", branch_id="branch-one", request=request,
    )
    assert a == b and len(a.players) == 32
    assert a.adoption_request_fingerprint == request.fingerprint_for_scope(
        run_id="run-one", branch_id="branch-one",
    )
    assert all(p.locked_from_initial_pool is False for p in a.players)
    previous = {p.player_id: p for p in pool.result.players}
    for player in a.players:
        if player.player_id in ids:
            original = previous[player.player_id]
            assert player.name == original.name
            assert player.current_ability == original.current_ability
            assert player.potential_ability == original.potential_ability
            assert player.source_generation_fingerprint == original.generation_fingerprint
    assert all(p.ranking_points == 0 for p in a.players)


@pytest.mark.parametrize("change,fragment", [
    ({"keep_from_preview_fingerprint": "f" * 64}, "source preview is stale"),
    ({"keep_player_ids": ["P-2000-ZZZ-0001"]}, "player IDs absent"),
    ({"world_package_id": "other-world"}, "other-world"),
    ({"country_code": "BOG"}, "source preview is stale"),
    ({"min_age": 21}, "source preview is stale"),
])
def test_tampered_keep_never_silently_imports_foreign_players(change, fragment):
    original = preview(source_request())
    valid = [original.result.players[0].player_id]
    req = keep_request(original, valid, **change)
    with pytest.raises((ValueError, AssertionError), match=fragment):
        preview(req)


@pytest.mark.parametrize("changes", [
    {"keep_from_seed": 123, "keep_from_preview_fingerprint": None,
     "keep_player_ids": ["x"]},
    {"keep_from_seed": 123, "keep_from_preview_fingerprint": "a" * 64,
     "keep_player_ids": []},
    {"keep_from_seed": 123, "keep_from_preview_fingerprint": "a" * 64,
     "keep_player_ids": ["x", "x"]},
    {"keep_from_seed": 123, "keep_from_preview_fingerprint": "a" * 64,
     "keep_player_ids": ["z", "a"]},
    {"keep_from_seed": 802, "keep_from_preview_fingerprint": "a" * 64,
     "keep_player_ids": ("x",)},
])
def test_keep_request_requires_valid_one_pass_reviewed_subset(changes):
    with pytest.raises(ValidationError):
        RunWorldInitialPoolPreviewRequest(
            **{**source_request().model_dump(), **changes},
        )



def test_multiple_keep_steps_replay_exactly_and_allow_growing_selection():
    base = preview(source_request())
    base_id = base.result.players[0].player_id
    first = preview(keep_request(base, [base_id], seed=803))
    added = next(p.player_id for p in first.result.players if p.player_id != base_id)
    from beta_engine.application.run_world_initial_pool_preview_service import (
        RunWorldKeepStep,
    )
    history = [RunWorldKeepStep(
        seed=first.request.seed,
        keep_from_seed=first.request.keep_from_seed,
        keep_from_preview_fingerprint=first.request.keep_from_preview_fingerprint,
        keep_player_ids=first.request.keep_player_ids,
    )]
    second_req = keep_request(
        first, [base_id, added], seed=804, keep_history=history,
    )
    second = preview(second_req)
    assert second == preview(second_req)
    assert second.preview_fingerprint != first.preview_fingerprint
    assert {p.player_id for p in second.result.players} >= {base_id, added}
    a = {p.player_id:p for p in first.result.players}
    b = {p.player_id:p for p in second.result.players}
    assert b[base_id] == a[base_id]
    assert b[added] == a[added]
    assert not any(p.locked for p in second.result.players)
    assert len({p.player_id for p in second.result.players}) == 32

    second_step = RunWorldKeepStep(
        seed=second.request.seed,
        keep_from_seed=second.request.keep_from_seed,
        keep_from_preview_fingerprint=second.request.keep_from_preview_fingerprint,
        keep_player_ids=second.request.keep_player_ids,
    )
    third_req = keep_request(
        second, [base_id, added], seed=805,
        keep_history=[*history, second_step],
    )
    third = preview(third_req)
    assert third == preview(third_req)
    c = {p.player_id: p for p in third.result.players}
    assert c[base_id] == b[base_id] and c[added] == b[added]
    assert third.result.summary.locked_players == 0
    adopted = RunWorldInitialWorldService(service()).preview(
        run_id="run-one", branch_id="branch-one",
        request=RunWorldInitialWorldAdoptionRequest(
            command_id="multi-keep-adopt", generation=third_req,
            audit_label="Three repeatable Keep passes",
            audit_reason="Keep original identities through repeated session rolls",
            official_run=False, best_n=15, automatic_retirement_age=46,
        ),
    )
    assert len(adopted.players) == 32
    assert all(not p.locked_from_initial_pool for p in adopted.players)
    assert {p.player_id for p in adopted.players} >= {base_id, added}


def test_keep_lineage_rejects_forged_fingerprint_and_broken_ancestry():
    from beta_engine.application.run_world_initial_pool_preview_service import (
        RunWorldKeepStep,
    )
    base = preview(source_request())
    first = preview(keep_request(base, [base.result.players[0].player_id]))
    keep_id = first.result.players[0].player_id
    step = RunWorldKeepStep(
        seed=first.request.seed,
        keep_from_seed=base.request.seed,
        keep_from_preview_fingerprint="f" * 64,
        keep_player_ids=first.request.keep_player_ids,
    )
    forged = keep_request(
        first, [keep_id], seed=805, keep_history=[step],
    )
    with pytest.raises(ValueError, match="source preview is stale"):
        preview(forged)
    with pytest.raises(ValidationError, match="broken seed ancestry"):
        keep_request(
            first, [keep_id], seed=805, keep_history=[
                step, RunWorldKeepStep(
                    seed=804, keep_from_seed=810,
                    keep_from_preview_fingerprint=first.preview_fingerprint,
                    keep_player_ids=[keep_id],
                )
            ],
        )
    with pytest.raises(ValidationError, match="entire batch"):
        keep_request(
            first, [keep_id], seed=805, keep_history=[
                step.model_copy(update={"keep_player_ids": sorted(
                    p.player_id for p in base.result.players
                )}),
            ],
        )


def test_unmodified_one_pass_fingerprint_is_backwards_compatible():
    origin = preview(source_request())
    first_req = keep_request(origin, [origin.result.players[0].player_id])
    assert "keep_history" not in first_req.fingerprint_payload()
    assert first_req.fingerprint_payload() == {
        key: value for key, value in first_req.model_dump(mode="json").items()
        if key != "keep_history"
    }
    assert preview(first_req).preview_fingerprint == preview(first_req).preview_fingerprint
