"""Unexpected faults at public simulation endpoints must not disclose internals."""
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from beta_engine.api.routers import admin_authoritative_simulation as auth
from beta_engine.api.routers import admin_calendar_tour as tour

pytestmark = pytest.mark.pr_critical


class FailingDriver:
    def simulate_next_season(self, command):
        raise RuntimeError("SECRET: database internals and stack trace")

    def simulate_full_simulation(self, command):
        raise RuntimeError("SECRET: database internals and stack trace")

    def inspect_full_simulation_boundary_options(self, **kwargs):
        raise RuntimeError("SECRET: database internals and stack trace")


@pytest.mark.parametrize("endpoint, request_type", [
    (auth.simulate_next_season, "AuthoritativeSeasonCommand"),
    (auth.simulate_full_simulation, "AuthoritativeFullSimulationCommand"),
])
def test_simulation_http_boundary_masks_unexpected_failures(monkeypatch, endpoint, request_type):
    monkeypatch.setattr(auth, "_driver", lambda *args: FailingDriver())
    monkeypatch.setattr(getattr(auth, request_type), "model_validate", lambda value: object())
    with pytest.raises(HTTPException) as caught:
        endpoint(
            run_id="run", branch_id="branch", payload={},
            runtime=object(), matches=object(), awards=object(),
        )
    assert caught.value.status_code == 500
    assert "SECRET" not in str(caught.value.detail)


def test_simulation_boundary_options_masks_unexpected_failures(monkeypatch):
    monkeypatch.setattr(auth, "_driver", lambda *args: FailingDriver())
    with pytest.raises(HTTPException) as caught:
        auth.inspect_full_simulation_target_options(
            run_id="run", branch_id="branch", command_id="cmd",
            runtime=object(), matches=object(), awards=object(),
        )
    assert caught.value.status_code == 500
    assert "SECRET" not in str(caught.value.detail)


def test_calendar_tour_transition_readiness_masks_unexpected_failures(monkeypatch):
    from beta_engine.application import calendar_native_transition_readiness
    def broken(*args, **kwargs):
        raise RuntimeError("SECRET: database internals and stack trace")
    monkeypatch.setattr(calendar_native_transition_readiness, "inspect_native_transition_readiness", broken)
    with pytest.raises(HTTPException) as caught:
        tour.native_transition_readiness(
            run_id="run", branch_id="branch",
            runtime=SimpleNamespace(repository=object()),
        )
    assert caught.value.status_code == 500
    assert "SECRET" not in str(caught.value.detail)
