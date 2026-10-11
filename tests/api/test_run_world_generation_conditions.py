"""Country/region constraints use only the exact saved Run World and are binding."""
from types import SimpleNamespace as Obj

from fastapi import HTTPException
import pytest

from beta_engine.api.routers import admin_players
from beta_engine.application.run_world_initial_pool_preview_service import (
    RunWorldInitialPoolPreviewRequest, RunWorldInitialPoolPreviewService,
)
import beta_engine.application.run_world_initial_pool_preview_service as preview_module
from tests.api.test_reviewed_player_generation_context import FakePackages, FakeRepo


pytestmark = pytest.mark.pr_critical
SHA = "a" * 64


def _country(code: str, name: str, region: str, travel: str):
    return Obj(code=code, name=name, region=region, effective_travel_region=travel)


COUNTRIES = (
    _country("CZE", "Czechia", "EUROPE", "CENTRAL_EUROPE"),
    _country("SVK", "Slovakia", "EUROPE", "CENTRAL_EUROPE"),
    _country("USA", "United States", "NORTH_AMERICA", "NORTH_AMERICA"),
)


class FakeAdapter:
    def project_countries(self, state, *, package_id):
        if package_id != "saved-earth":
            raise ValueError("World not found")
        return Obj(countries=COUNTRIES)

    def project_generation(self, state, *, package_id):
        return Obj(identity_config=None)


def _opts(repo, package, **overrides):
    args = dict(
        run_id="run-a", branch_id="branch-a", world_package_id="saved-earth",
        expected_head="head-a", expected_draft_version=3,
        expected_package_fingerprint=SHA, package_service=package,
        world_adapter=FakeAdapter(), runtime=Obj(repository=repo),
    )
    args.update(overrides)
    return admin_players.get_run_world_generation_options(**args)


def test_generation_options_read_only_and_bound_to_saved_revision(monkeypatch):
    repo, package = FakeRepo(), FakePackages()
    monkeypatch.setattr(admin_players, "load_saved_run_package_state",
                        lambda *_a, **_kw: Obj(fingerprint=SHA))
    result = _opts(repo, package)
    assert result.schema_version == "run_world_generation_options.v1"
    assert (result.run_id, result.branch_id, result.saved_revision_id) == (
        "run-a", "branch-a", "head-a")
    assert [c.code for c in result.countries] == ["CZE", "SVK", "USA"]
    assert result.regions == ("CENTRAL_EUROPE", "EUROPE", "NORTH_AMERICA")
    assert result.run_package_fingerprint == SHA


@pytest.mark.parametrize("change", ["head", "draft", "source", "protected"])
def test_options_refuse_stale_or_protected_source(monkeypatch, change):
    repo, package = FakeRepo(), FakePackages()
    monkeypatch.setattr(admin_players, "load_saved_run_package_state",
                        lambda *_a, **_kw: Obj(fingerprint=SHA))
    if change == "head":
        repo.branch.saved_head_revision_id = "another-head"
    elif change == "draft":
        repo.state.working_draft.draft_version = 4
    elif change == "source":
        package.current.fingerprint = "b" * 64
    else:
        repo.run.read_only = True
    with pytest.raises(HTTPException) as error:
        _opts(repo, package)
    assert error.value.status_code == 409
    assert error.value.detail["code"] == "run_world_generation_options_unavailable"


@pytest.mark.parametrize("country,region,fragment", [
    ("ZZZ", None, "Country condition 'ZZZ' is unavailable"),
    (None, "MARS", "Region condition 'MARS' has no eligible countries"),
    ("CZE", "NORTH_AMERICA", "Conflicting generation conditions"),
])
def test_impossible_country_region_diagnosed_before_any_rng(country, region, fragment):
    request = RunWorldInitialPoolPreviewRequest(
        world_package_id="saved-earth", season="2000/2001",
        seed=42, target_pool_size=30, country_code=country, region=region,
    )
    service = RunWorldInitialPoolPreviewService(FakePackages(), FakeAdapter())
    with pytest.raises(ValueError, match=fragment):
        service.preview(run_id="run-a", branch_id="branch-a", request=request)


def test_compatible_conditions_reach_the_existing_production_generator(monkeypatch):
    called = []

    class SpyProductionGenerator:
        def __init__(self, *, identity_config):
            assert identity_config is None

        def generate(self, **kwargs):
            called.append(kwargs)
            raise RuntimeError("production generator invoked")

    monkeypatch.setattr(preview_module, "InitialPlayerPoolGenerator", SpyProductionGenerator)
    service = RunWorldInitialPoolPreviewService(FakePackages(), FakeAdapter())
    request = RunWorldInitialPoolPreviewRequest(
        world_package_id="saved-earth", season="2000/2001",
        seed=4201, target_pool_size=30, country_code="CZE",
        region="CENTRAL_EUROPE",
    )
    with pytest.raises(RuntimeError, match="production generator invoked"):
        service.preview(run_id="run-a", branch_id="branch-a", request=request)
    assert len(called) == 1
    assert called[0]["countries"] == list(COUNTRIES)
    assert called[0]["country_code"] == "CZE"
    assert called[0]["region"] == "CENTRAL_EUROPE"
    assert called[0]["target_pool_size"] == 30 and called[0]["seed"] == 4201
    assert called[0]["dry_run"] is True
