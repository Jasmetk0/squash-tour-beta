"""History-derived Automatic after legacy Keep; exact fingerprints remain durable."""
import pytest
from pydantic import ValidationError

from beta_engine.application.run_world_initial_pool_preview_service import (
    RunWorldKeepStep, RunWorldInitialPoolPreviewRequest,
    RunWorldPreviewFieldLock, RunWorldPreviewAutomaticField,
    RunWorldVerifiedSessionStep,
)
from beta_engine.application.run_world_initial_world_service import (
    RunWorldInitialWorldAdoptionRequest, RunWorldInitialWorldService,
)
from tests.application.test_run_world_session_keep import (
    keep_request, preview, service, source_request,
)
from tests.application.test_run_world_verified_session_edits import _v2, _continue, _step

pytestmark = pytest.mark.pr_critical


def _manually_edited_twice_kept():
    generated = preview(source_request())
    chosen = generated.result.players[0]
    sampled = chosen.attributes.technique
    changed = sampled + 1 if sampled < 99 else sampled - 1
    lock = RunWorldPreviewFieldLock(
        player_id=chosen.player_id, field="attributes.technique", value=changed,
    )
    edited = preview(RunWorldInitialPoolPreviewRequest.model_validate({
        **source_request().model_dump(mode="json"),
        "field_locks": [lock.model_dump(mode="json")],
    }))
    first = preview(keep_request(edited, [chosen.player_id], seed=803))
    history = [RunWorldKeepStep(
        seed=first.request.seed, keep_from_seed=first.request.keep_from_seed,
        keep_from_preview_fingerprint=first.request.keep_from_preview_fingerprint,
        keep_player_ids=first.request.keep_player_ids,
    )]
    second = preview(keep_request(
        first, [chosen.player_id], seed=804, keep_history=history,
    ))
    assert next(p for p in second.result.players if p.player_id == chosen.player_id).attributes.technique == changed
    return generated, edited, first, second, chosen.player_id, sampled, changed


def _automatic_after(second, player_id, *, locks=(), fields=None):
    step = RunWorldVerifiedSessionStep(
        kind="edit", seed=second.request.seed,
        source_preview_fingerprint=second.preview_fingerprint,
        keep_player_ids=[], field_locks=list(locks),
        automatic_fields=fields if fields is not None else [
            RunWorldPreviewAutomaticField(
                player_id=player_id, field="attributes.technique",
            ),
        ],
    )
    return _v2(second, [step])


def test_automatic_resolves_earliest_source_through_two_legacy_keeps():
    generated, edited, first, second, pid, sampled, changed = _manually_edited_twice_kept()
    old_fingerprints = [p.preview_fingerprint for p in (generated, edited, first, second)]
    automatic = preview(_automatic_after(second, pid))
    assert automatic == preview(automatic.request)
    before = {p.player_id: p for p in second.result.players}
    after = {p.player_id: p for p in automatic.result.players}
    assert after[pid].attributes.technique == sampled != changed
    assert after[pid].player_id == before[pid].player_id
    assert after[pid].name == before[pid].name
    assert after[pid].country_code == before[pid].country_code
    assert after[pid].potential_ability == before[pid].potential_ability
    assert after[pid].attributes.mental == before[pid].attributes.mental
    assert all(after[key] == player for key, player in before.items() if key != pid)
    assert all(not player.locked for player in automatic.result.players)
    assert [preview(p.request).preview_fingerprint for p in (
        generated, edited, first, second,
    )] == old_fingerprints
    assert automatic.request.fingerprint_payload()["session_steps"][0]["automatic_fields"] == [
        {"player_id": pid, "field": "attributes.technique"},
    ]


def test_reset_survives_following_edit_new_seed_keep_and_adoption():
    _, _, _, second, pid, sampled, _ = _manually_edited_twice_kept()
    automatic = preview(_automatic_after(second, pid))
    further = preview(_continue(automatic, _step(automatic, locks=[])))
    assert next(p for p in further.result.players if p.player_id == pid).attributes.technique == sampled
    next_kept = preview(_continue(
        further, _step(further, kind="keep", seed=805, ids=[pid], locks=[]),
    ))
    assert next_kept == preview(next_kept.request)
    assert next(p for p in next_kept.result.players if p.player_id == pid).attributes.technique == sampled
    adopted = RunWorldInitialWorldService(service()).preview(
        run_id="run-one", branch_id="branch-one",
        request=RunWorldInitialWorldAdoptionRequest(
            command_id="automatic-after-keep",
            generation=next_kept.request,
            audit_label="Reviewed source Automatic",
            audit_reason="Restore sampled source without lifetime career lock",
            official_run=False, best_n=15, automatic_retirement_age=46,
        ),
    )
    restored = next(p for p in adopted.players if p.player_id == pid)
    assert restored.attributes.technique == sampled
    assert not restored.locked_from_initial_pool


def test_serialized_saved_v2_automatic_request_replays_identically():
    _, _, _, second, pid, _, _ = _manually_edited_twice_kept()
    original = _automatic_after(second, pid)
    saved = original.model_dump(mode="json")
    parsed = RunWorldInitialPoolPreviewRequest.model_validate(saved)
    assert preview(parsed) == preview(original)
    assert preview(parsed).preview_fingerprint == preview(original).preview_fingerprint
    # A V2 session created before Automatic existed retains its old hash bytes.
    legacy_v2 = _v2(second, [_step(second, locks=second.request.field_locks)])
    assert "automatic_fields" not in legacy_v2.fingerprint_payload()["session_steps"][0]
    assert preview(legacy_v2).preview_fingerprint == preview(legacy_v2).preview_fingerprint


@pytest.mark.parametrize("bad", ["missing", "duplicate", "overlap", "keep", "forged"])
def test_automatic_tampering_fails_closed(bad):
    _, _, _, second, pid, _, _ = _manually_edited_twice_kept()
    payload = _automatic_after(second, pid).model_dump(mode="json")
    step = payload["session_steps"][0]
    if bad == "missing":
        step["automatic_fields"][0]["player_id"] = "forged-player"
    elif bad == "duplicate":
        step["automatic_fields"].append(dict(step["automatic_fields"][0]))
    elif bad == "overlap":
        step["field_locks"] = [{"player_id": pid, "field": "attributes.technique", "value": 90}]
        payload["field_locks"] = list(step["field_locks"])
    elif bad == "keep":
        step["kind"] = "keep"
        step["keep_player_ids"] = [pid]
        step["seed"] = 805
        payload["seed"] = 805
    else:
        step["source_preview_fingerprint"] = "e" * 64
    with pytest.raises((ValueError, ValidationError)):
        preview(RunWorldInitialPoolPreviewRequest.model_validate(payload))


def test_changing_world_or_hard_country_quota_cannot_rewrite_saved_origin():
    _, _, _, second, pid, _, _ = _manually_edited_twice_kept()
    payload = _automatic_after(second, pid).model_dump(mode="json")
    payload["country_code"] = "GER"
    with pytest.raises(ValueError, match="cannot silently alter"):
        preview(RunWorldInitialPoolPreviewRequest.model_validate(payload))
