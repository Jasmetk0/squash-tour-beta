"""Exact whole-batch per-country quotas and weighted automatic remainder.

Real production generator/service, including Keep replay and preview provenance.
"""
from collections import Counter
from types import SimpleNamespace as NS

import pytest
from pydantic import ValidationError

from beta_engine.application.run_world_initial_pool_preview_service import (
    RunWorldExactCountryQuota, RunWorldInitialPoolPreviewRequest,
    RunWorldInitialPoolPreviewService,
)
from beta_engine.application.run_world_initial_world_service import (
    RunWorldInitialWorldAdoptionRequest, RunWorldInitialWorldService,
)
from beta_engine.domain.players.initial_pool import InitialPlayerPoolGenerator
from tests.application.test_run_world_session_keep import Packages, keep_request
from tests.domain.initial_player_pool_contract_suite import country

pytestmark = pytest.mark.pr_critical


class ThreeCountryAdapter:
    def project_countries(self, state, *, package_id):
        assert package_id == "saved-world"
        return NS(countries=[
            country("BOG", population=12_000_000, system=3, popularity=3, tradition=3),
            country("GER", population=20_000_000, system=4, popularity=4, tradition=4),
            country("ROU", population=16_000_000, system=3, popularity=3, tradition=3),
        ], content_fingerprint="b" * 64)

    def project_generation(self, state, *, package_id):
        assert package_id == "saved-world"
        return NS(identity_config=None, content_fingerprint="c" * 64)


def _preview(request):
    return RunWorldInitialPoolPreviewService(Packages(), ThreeCountryAdapter(), calendar_guard=lambda *_: None).preview(
        run_id="run-one", branch_id="branch-one", request=request,
    )


def _request(*quotas, count=50, seed=802):
    return RunWorldInitialPoolPreviewRequest(
        world_package_id="saved-world", seed=seed, target_pool_size=count,
        country_quotas=[RunWorldExactCountryQuota(country_code=code, count=n)
                        for code, n in quotas],
    )


def test_exact_country_quotas_and_automatic_remainder_are_deterministic():
    request = _request(("BOG", 10), ("GER", 15))
    one = _preview(request)
    two = _preview(request)
    assert one == two and one.preview_fingerprint == two.preview_fingerprint
    counts = Counter(p.country_code for p in one.result.players)
    assert counts == {"BOG": 10, "GER": 15, "ROU": 25}
    assert len({p.player_id for p in one.result.players}) == 50
    assert one.result.metadata.generated_count == 50
    diagnostics = {d.country_code: d for d in one.result.metadata.population_weighting_diagnostics}
    assert {code: diagnostics[code].final_country_count for code in counts} == counts
    assert one.request.fingerprint_payload()["country_quotas"] == [
        {"country_code": "BOG", "count": 10},
        {"country_code": "GER", "count": 15},
    ]


def test_zero_country_quota_excludes_country_and_remaining_is_auto():
    request = _request(("BOG", 0), count=30)
    result = _preview(request)
    assert len(result.result.players) == 30
    assert all(p.country_code != "BOG" for p in result.result.players)


def test_exact_all_country_quota_without_remainder_is_allowed():
    request = _request(("BOG", 15), ("GER", 15), ("ROU", 20))
    result = _preview(request)
    assert Counter(p.country_code for p in result.result.players) == {
        "BOG": 15, "GER": 15, "ROU": 20,
    }


def test_keep_reroll_preserves_identity_and_exact_country_quota():
    initial = _preview(_request(("BOG", 10), ("GER", 15)))
    keep_ids = [p.player_id for p in initial.result.players
                if p.country_code in ("BOG", "GER")][:6]
    changed = _preview(keep_request(initial, keep_ids, seed=803))
    assert changed == _preview(changed.request)
    assert Counter(p.country_code for p in changed.result.players) == {
        "BOG": 10, "GER": 15, "ROU": 25,
    }
    original = {p.player_id: p for p in initial.result.players}
    current = {p.player_id: p for p in changed.result.players}
    for pid in keep_ids:
        assert current[pid] == original[pid]
    assert not any(p.locked for p in changed.result.players)

    adopted = RunWorldInitialWorldService(
        RunWorldInitialPoolPreviewService(Packages(), ThreeCountryAdapter(), calendar_guard=lambda *_: None)
    ).preview(run_id="run-one", branch_id="branch-one",
              request=RunWorldInitialWorldAdoptionRequest(
                  command_id="country-quota-reviewed-adopt", generation=changed.request,
                  audit_label="Quota review", audit_reason="Verify exact reviewed cohort",
                  official_run=False, best_n=15, automatic_retirement_age=46,
              ))
    assert Counter(p.country_code for p in adopted.players) == {
        "BOG": 10, "GER": 15, "ROU": 25,
    }
    assert len(adopted.players) == 50


@pytest.mark.parametrize("quotas,count,fragment", [
    ((("BOG", 30), ("GER", 25)), 50, "exceed"),
    ((("BOG", 10), ("GER", 10), ("ROU", 10)), 50, "no eligible other countries"),
    ((("AAA", 10),), 50, "ineligible"),
])
def test_impossible_quotas_fail_closed(quotas, count, fragment):
    with pytest.raises(ValueError, match=fragment):
        _preview(_request(*quotas, count=count))


def test_kept_players_cannot_break_a_country_quota():
    source = _preview(_request(("BOG", 10)))
    kept = [p.model_copy(update={"locked": True}) for p in source.result.players
            if p.country_code == "BOG"][:2]
    countries = ThreeCountryAdapter().project_countries(None, package_id="saved-world").countries
    with pytest.raises(ValueError, match="Keep preserves"):
        InitialPlayerPoolGenerator().generate(
            countries=countries, season="2000/2001", seed=803, target_pool_size=50,
            existing_locked_players=kept, country_quotas={"BOG": 1}, dry_run=True,
        )


@pytest.mark.parametrize("data", [
    [{"country_code": "GER", "count": 1}, {"country_code": "BOG", "count": 2}],
    [{"country_code": "BOG", "count": 1}, {"country_code": "BOG", "count": 2}],
    [{"country_code": "BOG", "count": -1}],
    [{"country_code": "BOG", "count": True}],
    [{"country_code": "bog", "count": 1}],
])
def test_invalid_request_country_quotas_rejected(data):
    with pytest.raises(ValidationError):
        RunWorldInitialPoolPreviewRequest.model_validate({
            "world_package_id": "saved-world", "seed": 802, "target_pool_size": 50,
            "country_quotas": data,
        })


def test_absent_country_quota_preserves_historical_preview_fingerprint():
    request = _request(count=32)
    legacy = RunWorldInitialPoolPreviewRequest(
        world_package_id="saved-world", seed=802, target_pool_size=32,
    )
    assert request.fingerprint_payload() == legacy.fingerprint_payload()
    assert "country_quotas" not in request.fingerprint_payload()
