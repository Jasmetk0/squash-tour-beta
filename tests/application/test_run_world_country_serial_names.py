"""F79-03: versioned country + serial display names with old replay untouched."""
import pytest
from pydantic import ValidationError

from beta_engine.application.run_world_initial_pool_preview_service import (
    RunWorldInitialPoolPreviewRequest, RunWorldKeepStep, RunWorldPreviewFieldLock,
    RunWorldVerifiedSessionStep,
)
from beta_engine.application.run_world_initial_world_service import (
    RunWorldInitialWorldAdoptionRequest, RunWorldInitialWorldService,
)
from beta_engine.domain.players.initial_pool import InitialPlayerPoolGenerator
from tests.application.test_run_world_session_keep import (
    keep_request, preview, service, source_request,
)
from tests.application.test_run_world_verified_session_edits import _v2
from tests.domain.initial_player_pool_contract_suite import country

pytestmark = pytest.mark.pr_critical
POLICY = "country_serial.v1"


def _named_request(*, seed=802, **updates):
    return RunWorldInitialPoolPreviewRequest.model_validate({
        **source_request().model_dump(mode="json"),
        "seed": seed, "naming_policy": POLICY, **updates,
    })


def test_opt_in_names_are_deterministic_country_sequence_without_changing_other_player_facts():
    legacy = preview(source_request())
    named = preview(_named_request())
    assert named == preview(named.request)
    assert named.preview_fingerprint != legacy.preview_fingerprint
    assert len(named.result.players) == len(legacy.result.players)
    before = {p.player_id: p for p in legacy.result.players}
    after = {p.player_id: p for p in named.result.players}
    assert after.keys() == before.keys()
    assert all(old.generation_fingerprint == after[pid].generation_fingerprint
               for pid, old in before.items())
    for pid, fresh in after.items():
        assert fresh.model_copy(update={"name": before[pid].name}) == before[pid]
        assert fresh.name == f"{fresh.country_code} {int(pid.rsplit('-', 1)[-1])}"
    assert len(set(p.name for p in named.result.players)) == len(after)
    assert not any(p.locked or p.manual_override for p in named.result.players)


def test_legacy_requests_and_old_v2_request_hash_payload_omit_policy():
    old = source_request()
    assert old.naming_policy is None
    assert "naming_policy" not in old.fingerprint_payload()
    assert "naming_policy" not in RunWorldInitialPoolPreviewRequest.model_validate(
        old.model_dump(mode="json", exclude={"naming_policy"}),
    ).fingerprint_payload()
    assert preview(old).preview_fingerprint == preview(
        RunWorldInitialPoolPreviewRequest.model_validate(
            old.model_dump(mode="json", exclude={"naming_policy"}),
        )
    ).preview_fingerprint
    assert preview(old).result.players[0].name != (
        f"{preview(old).result.players[0].country_code} "
        f"{int(preview(old).result.players[0].player_id.rsplit('-',1)[-1])}"
    )


def test_named_legacy_keep_twice_and_v2_edit_preserve_kept_identity_and_name():
    first = preview(_named_request())
    keep_id = first.result.players[0].player_id
    kept = preview(keep_request(first, [keep_id], seed=803))
    first_id = next(p for p in first.result.players if p.player_id == keep_id)
    assert next(p for p in kept.result.players if p.player_id == keep_id).name == first_id.name
    history = [RunWorldKeepStep(
        seed=kept.request.seed,
        keep_from_seed=kept.request.keep_from_seed,
        keep_from_preview_fingerprint=kept.request.keep_from_preview_fingerprint,
        keep_player_ids=kept.request.keep_player_ids,
    )]
    second = preview(keep_request(
        kept, [keep_id], seed=804, keep_history=history,
    ))
    assert second == preview(second.request)
    selected = next(p for p in second.result.players if p.player_id == keep_id)
    assert selected == first_id
    field = RunWorldPreviewFieldLock(
        player_id=keep_id, field="attributes.technique",
        value=selected.attributes.technique,
    )
    edit = RunWorldVerifiedSessionStep(
        kind="edit", source_preview_fingerprint=second.preview_fingerprint,
        seed=second.request.seed, keep_player_ids=[], field_locks=[field],
    )
    after_edit = preview(_v2(second, [edit]))
    assert next(p for p in after_edit.result.players if p.player_id == keep_id).name == first_id.name
    assert after_edit == preview(after_edit.request)
    adopted = RunWorldInitialWorldService(service()).preview(
        run_id="run-one", branch_id="branch-one",
        request=RunWorldInitialWorldAdoptionRequest(
            command_id="country-serial-adopt",
            generation=after_edit.request,
            audit_label="Country serial source names",
            audit_reason="InitialWorld country serial names survive Keep and V2 edit",
            official_run=False, best_n=15, automatic_retirement_age=46,
        ),
    )
    assert next(p for p in adopted.players if p.player_id == keep_id).name == first_id.name


def test_country_serial_continues_from_preserved_profiles_in_expanded_cohort():
    source_country = country(
        "AAA", population=12_000_000, system=3, popularity=3, tradition=3,
    )
    generator = InitialPlayerPoolGenerator()
    first = generator.generate(
        countries=[source_country], seed=17, target_pool_size=3,
        naming_policy=POLICY,
    )
    assert [p.name for p in first.players] == ["AAA 1", "AAA 2", "AAA 3"]
    locked = [p.model_copy(update={"locked": True}) for p in first.players]
    grown = generator.generate(
        countries=[source_country], seed=18, target_pool_size=5,
        existing_locked_players=locked, naming_policy=POLICY,
    )
    by_id = {p.player_id: p for p in grown.players}
    assert [p.name for p in grown.players] == [
        "AAA 1", "AAA 2", "AAA 3", "AAA 4", "AAA 5",
    ]
    for original in first.players:
        assert by_id[original.player_id].name == original.name
        assert by_id[original.player_id].locked is True
    assert len({p.player_id for p in grown.players}) == 5


def test_cross_world_country_names_derive_from_authoritative_saved_world_label():
    c = country(
        "AAA", population=12_000_000, system=3, popularity=3, tradition=3,
    ).model_copy(update={"name": "Česko"})
    generated = InitialPlayerPoolGenerator().generate(
        countries=[c], seed=1234, target_pool_size=2, naming_policy=POLICY,
    )
    assert [p.name for p in generated.players] == ["Česko 1", "Česko 2"]


def test_invalid_policy_is_rejected_not_silently_interpreted():
    with pytest.raises(ValidationError):
        _named_request(naming_policy="fantasy_person.v1")
    with pytest.raises(ValueError, match="Unsupported initial-pool naming policy"):
        InitialPlayerPoolGenerator().generate(
            countries=[country("AAA",population=12_000_000,system=3,popularity=3,tradition=3)],
            seed=12, target_pool_size=1, naming_policy="unknown",
        )


def test_quota_names_are_bound_to_each_country_sequence_not_ui_row_order():
    req = _named_request(
        target_pool_size=12,
        country_quotas=[{"country_code":"BOG","count":5}],
    )
    generated = preview(req)
    assert generated == preview(req)
    assert sum(p.country_code == "BOG" for p in generated.result.players) == 5
    assert all(
        p.name.endswith(f" {int(p.player_id.rsplit('-',1)[-1])}")
        for p in generated.result.players
    )
    assert [p.name for p in generated.result.players if p.country_code=="BOG"] == [
        f"BOG {n}" for n in range(1,6)
    ]
