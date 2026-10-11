"""Authenticated v2 session edits after repeated legacy Keep; read-only Run scope."""
import pytest
from pydantic import ValidationError

from beta_engine.application.run_world_initial_pool_preview_service import (
    RunWorldInitialPoolPreviewRequest, RunWorldVerifiedSessionStep,
    RunWorldPreviewFieldLock,
)
from beta_engine.application.run_world_initial_world_service import (
    RunWorldInitialWorldAdoptionRequest, RunWorldInitialWorldService,
)
from tests.application.test_run_world_session_keep import (
    keep_request, preview, service, source_request,
)

pytestmark = pytest.mark.pr_critical
VERSION = "run_world_generation_session.v2"


def _after_two_keeps():
    base = preview(source_request())
    retained = sorted(p.player_id for p in base.result.players[:2])
    first = preview(keep_request(base, retained, seed=803))
    second_ids = sorted([retained[0], next(
        p.player_id for p in first.result.players if p.player_id not in retained
    )])
    from beta_engine.application.run_world_initial_pool_preview_service import RunWorldKeepStep
    history = [RunWorldKeepStep(
        seed=first.request.seed,
        keep_from_seed=first.request.keep_from_seed,
        keep_from_preview_fingerprint=first.request.keep_from_preview_fingerprint,
        keep_player_ids=first.request.keep_player_ids,
    )]
    second = preview(keep_request(
        first, second_ids, seed=804, keep_history=history,
    ))
    return base, first, second


def _step(before, *, kind="edit", seed=None, ids=(), locks=()):
    return RunWorldVerifiedSessionStep(
        kind=kind,
        source_preview_fingerprint=before.preview_fingerprint,
        seed=before.request.seed if seed is None else seed,
        keep_player_ids=sorted(ids),
        field_locks=sorted(locks, key=lambda lock: (lock.player_id, lock.field)),
    )


def _v2(origin, steps):
    return RunWorldInitialPoolPreviewRequest.model_validate({
        **origin.request.model_dump(mode="json"),
        "seed": steps[-1].seed,
        "field_locks": [lock.model_dump(mode="json") for lock in steps[-1].field_locks],
        "session_schema_version": VERSION,
        "session_origin_request": origin.request.model_dump(mode="json"),
        "session_origin_fingerprint": origin.preview_fingerprint,
        "session_steps": [step.model_dump(mode="json") for step in steps],
    })


def _continue(existing, step):
    return RunWorldInitialPoolPreviewRequest.model_validate({
        **existing.request.model_dump(mode="json"),
        "seed": step.seed,
        "field_locks": [lock.model_dump(mode="json") for lock in step.field_locks],
        "session_steps": [
            *[old.model_dump(mode="json") for old in existing.request.session_steps],
            step.model_dump(mode="json"),
        ],
    })


def test_edits_after_two_legacy_keeps_are_auditable_and_isolated():
    original, first, second = _after_two_keeps()
    assert original == preview(original.request)
    assert first == preview(first.request)
    assert second == preview(second.request)
    player = second.result.players[0]
    value = 91 if player.attributes.technique != 91 else 90
    lock = RunWorldPreviewFieldLock(
        player_id=player.player_id, field="attributes.technique", value=value,
    )
    edited = preview(_v2(second, [_step(second, locks=[lock])]))
    assert edited == preview(edited.request)
    after = {item.player_id: item for item in edited.result.players}
    before = {item.player_id: item for item in second.result.players}
    assert after[player.player_id].attributes.technique == value
    assert all(after[pid] == item for pid, item in before.items() if pid != player.player_id)
    assert [p.player_id for p in edited.result.players] == [
        p.player_id for p in second.result.players
    ]
    assert second == preview(second.request)  # neither request nor old digest mutates
    assert second.preview_fingerprint == preview(second.request).preview_fingerprint
    assert all(not p.locked for p in edited.result.players)


def test_update_automatic_new_keep_seed_and_adoption_without_career_lock():
    _, _, second = _after_two_keeps()
    player = second.result.players[0]
    original_value = player.attributes.clutch
    chosen = 99 if original_value != 99 else 98
    lock = RunWorldPreviewFieldLock(
        player_id=player.player_id, field="attributes.clutch", value=chosen,
    )
    edit1 = preview(_v2(second, [_step(second, locks=[lock])]))
    edit2 = preview(_continue(edit1, _step(edit1, locks=[])))
    assert next(p for p in edit2.result.players if p.player_id == player.player_id).attributes.clutch == original_value
    assert edit2.preview_fingerprint != edit1.preview_fingerprint
    edit3 = preview(_continue(edit2, _step(edit2, locks=[lock])))
    retained = [player.player_id]
    kept = preview(_continue(
        edit3, _step(edit3, kind="keep", seed=805, ids=retained, locks=[lock]),
    ))
    assert kept == preview(kept.request)
    assert next(p for p in kept.result.players if p.player_id == player.player_id).attributes.clutch == chosen
    adopted = RunWorldInitialWorldService(service()).preview(
        run_id="run-one", branch_id="branch-one",
        request=RunWorldInitialWorldAdoptionRequest(
            command_id="v2-keep-adopt", generation=kept.request,
            audit_label="Reviewed v2 session", audit_reason="Keep remains preview-only",
            official_run=False, best_n=15, automatic_retirement_age=46,
        ),
    )
    assert len(adopted.players) == 32
    assert all(not p.locked_from_initial_pool for p in adopted.players)


def test_restore_exact_serialized_request_without_trusting_player_objects():
    _, _, second = _after_two_keeps()
    player = second.result.players[0]
    lock = RunWorldPreviewFieldLock(
        player_id=player.player_id, field="attributes.mental", value=80,
    )
    request = _v2(second, [_step(second, locks=[lock])])
    restored = RunWorldInitialPoolPreviewRequest.model_validate(
        request.model_dump(mode="json")
    )
    assert preview(restored) == preview(request)
    assert "session_origin_request" in restored.fingerprint_payload()
    assert "session_origin_request" not in second.request.fingerprint_payload()


@pytest.mark.parametrize("alter", [
    lambda p: p.update({"session_origin_fingerprint": "f" * 64}),
    lambda p: p["session_steps"][0].update({"source_preview_fingerprint": "a" * 64}),
    lambda p: p.update({"country_code": "BOG"}),
    lambda p: p.update({"min_age": 20}),
    lambda p: p["session_steps"][0].update({"seed": 999}),
    lambda p: p["session_steps"][0]["field_locks"][0].update({"player_id": "fake-id"}),
])
def test_forged_origin_step_seed_world_constraints_and_player_ids_fail(alter):
    _, _, second = _after_two_keeps()
    player = second.result.players[0]
    lock = RunWorldPreviewFieldLock(
        player_id=player.player_id, field="attributes.technique", value=85,
    )
    data = _v2(second, [_step(second, locks=[lock])]).model_dump(mode="json")
    alter(data)
    with pytest.raises((ValueError, ValidationError, KeyError)):
        preview(RunWorldInitialPoolPreviewRequest.model_validate(data))


def test_legacy_hashes_omit_all_v2_fields_and_bad_steps_do_not_pass():
    _, first, second = _after_two_keeps()
    assert first.request.fingerprint_payload().get("session_steps") is None
    assert first.request.fingerprint_payload().get("session_schema_version") is None
    assert second == preview(second.request)
    with pytest.raises(ValidationError, match="[Ss]ession"):
        RunWorldInitialPoolPreviewRequest.model_validate({
            **source_request().model_dump(mode="json"),
            "session_steps": [{
                "kind":"edit", "source_preview_fingerprint":"a"*64,
                "seed":802, "keep_player_ids":[], "field_locks":[],
            }],
        })
