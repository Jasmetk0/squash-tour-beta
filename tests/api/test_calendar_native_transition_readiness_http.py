"""Actual read-only readiness over birth, unsaved state, restart and Run end."""

import json

import pytest

from beta_engine.domain.calendar.run_calendar import RunCalendar
from tests.api.test_calendar_native_birth_week_execution import sign_prospects
from tests.api.test_calendar_tour_flow import (
    command,
    execute,
    inspect,
    save_tour,
    setup,
    tour_url,
)
from tests.api.test_player_generation_calendar_gate import _dump
from tests.api.test_saved_revision_history_api import ApiServer, _request

pytestmark = pytest.mark.smoke


def test_native_readiness_tracks_actual_writer_without_component_false_blockers(
    tmp_path,
):
    path = tmp_path / "readiness.db"
    database_url = f"sqlite:///{path}"
    clock = RunCalendar(2, 2, 2030, 2)
    with ApiServer(database_url=database_url) as server:
        repo, _ = setup(server, clock, 8)
        sign_prospects(server, repo, clock, target_week=1, target_season=1)
        url = tour_url(server) + "/prospect-intake/transition-readiness"
        before = _dump(path)
        code, view = _request("GET", url)
        assert code == 200, view
        assert view["schema_version"] == "native_tour_transition_readiness.v1"
        assert view["can_preview_transition"] and view["blockers"] == []
        assert view["action"] == "season-transition"
        assert (
            view["due_count"] == 1 and view["due"][0]["player_id"] == "born-native-15"
        )
        assert view["admitted_population_count"] == 0
        assert view["current_scope"] == "configured_tour"
        assert view["target_scope"] == "native_natural_transitions"
        assert (
            view["command_preview_required"] and view["explicit_confirmation_required"]
        )
        assert view["manual_save_required"] and not view["simulation_started"]
        assert len(json.dumps(view)) < 8000
        assert _request("GET", url) == (200, view)
        assert _dump(path) == before
        old = _request("GET", tour_url(server) + "/prospect-intake/preflight")
        assert (
            old[0] == 200
            and old[1]["blocked"]
            and not old[1]["native_activation_supported"]
        )
        result, _ = execute(
            server, command(inspect(server), view["action"], name="readiness-birth")
        )
        assert result["impact"]["target_week"] == view["target_week"]
        before = _dump(path)
        code, unsaved = _request("GET", url)
        assert code == 200, unsaved
        assert not unsaved["can_preview_transition"]
        assert unsaved["blockers"] == ["manual_save_required"]
        assert unsaved["admitted_population_count"] == 1 and unsaved["due_count"] == 0
        assert unsaved["source_problems"] == []
        assert unsaved["current_scope"] == "native_natural_transitions"
        assert not unsaved["post_birth_competition_supported"]
        assert not unsaved["source_epoch_changes_supported"]
        assert _dump(path) == before
        saved = save_tour(server)
        code, signed = _request("GET", url)
        assert code == 200 and signed["can_preview_transition"], signed
        assert signed["saved_head_revision_id"] == saved["revision_id"]
        assert signed["action"] == "transition"
        assert (
            _request("GET", url.replace("branches/branch/", "branches/foreign/"))[0]
            == 409
        )
        assert _request("GET", url.replace("runs/run/", "runs/foreign/"))[0] == 409
    with ApiServer(database_url=database_url) as restarted:
        url = tour_url(restarted) + "/prospect-intake/transition-readiness"
        assert _request("GET", url) == (200, signed)
        execute(
            restarted,
            command(inspect(restarted), "transition", name="readiness-terminal"),
        )
        save_tour(restarted)
        before = _dump(path)
        code, terminal = _request("GET", url)
        assert code == 200, terminal
        assert (
            not terminal["can_preview_transition"] and terminal["target_week"] is None
        )
        assert terminal["blockers"] == [
            "run_horizon_exhausted",
            "season_transition_horizon_exhausted",
        ]
        assert terminal["due"] == [] and terminal["admitted_population_count"] == 1
        assert _dump(path) == before
