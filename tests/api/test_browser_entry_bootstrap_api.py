"""Real HTTP/SQLite regression for the browser's first unmaterialized Entry slot.

All player state is generated/adopted by production commands. Source preparation
uses the same disposable four-player Calendar as the browser acceptance script.
"""

from pathlib import Path

import pytest

from scripts.admin_first_tournament_smoke import create_smoke_app
from tests.api.test_initial_world_ranking_integration import _post_headers
from tests.api.test_saved_revision_history_api import ApiServer, _create_run, _request

pytestmark = pytest.mark.pr_critical


def ok(method, url, payload=None):
    status, body = _request(method, url, payload)
    assert status in (200, 201), body
    return body


@pytest.fixture
def generated_run(tmp_path):
    root = tmp_path / "isolated"
    server = ApiServer(database_url=f"sqlite:///{tmp_path}/unused.sqlite")
    server.app = create_smoke_app(root)
    server.server.config.app = server.app
    with server:
        run, branch, _ = _create_run(
            server, display_name="Actual Entry bootstrap regression"
        )
        base = f"{server.base_url}/admin/runs/{run}/branches/{branch}"
        for kind, source in [
            ("world", "official_fax_world"),
            ("calendar", "2000-2001"),
        ]:
            url = base + f"/packages/source-{kind}/{source}"
            preview = ok("POST", url + "/preview")
            applied = ok(
                "POST",
                url + "/confirm",
                {
                    "command_id": f"copy-{kind}",
                    "expected_head_revision_id": preview["saved_head_revision_id"],
                    "expected_draft_version": preview["draft_version"],
                    "expected_state_fingerprint": preview["current_state_fingerprint"],
                    "expected_preview_fingerprint": preview["preview_fingerprint"],
                    "conflict_resolutions": {},
                },
            )
            ok(
                "POST",
                f"{server.base_url}/run-containers/{run}/branches/{branch}/working-draft/save",
                {"expected_draft_version": applied["draft_version"]},
            )
        world = f"{server.base_url}/admin/players/runs/{run}/branches/{branch}/initial-world"
        intent = {
            "command_id": "generate-regression",
            "generation": {
                "world_package_id": "official_fax_world",
                "season": "2000/2001",
                "seed": 4201,
                "target_pool_size": 64,
            },
            "audit_label": "API regression",
            "audit_reason": "Generate real owned players",
            "official_run": False,
            "best_n": 15,
            "automatic_retirement_age": 46,
        }
        preview = ok("POST", world + "/world-package/preview", intent)
        assert (
            _post_headers(
                world + "/world-package",
                intent,
                {"X-Initial-World-Preview-Fingerprint": preview["fingerprint"]},
            )[0]
            == 201
        )
        save = ok("GET", world + "/save/preview")
        assert save["has_unsaved_changes"] and save["can_save"]
        ok(
            "POST",
            world + "/save",
            {
                "expected_draft_version": save["draft_version"],
                "expected_initial_world_fingerprint": save["initial_world_fingerprint"],
            },
        )
        ranking = base + "/ranking-candidates"
        intent = {
            "command_id": "derived-ranking",
            "audit": {
                "actor_label": "API regression",
                "reason": "Initial ranking from actual generated players",
            },
        }
        preview = ok("POST", ranking + "/prepare/initial/derived/preview", intent)
        candidate = _post_headers(
            ranking + "/prepare/initial/derived",
            intent,
            {
                "X-Ranking-Preview-Fingerprint": preview["candidate"]["fingerprint"],
                "X-Ranking-Preview-Request": preview["request_fingerprint"],
            },
        )[1]
        for publish in [False, True]:
            if publish:
                ok(
                    "POST",
                    ranking + "/publish-initial",
                    {"expected_ranking_fingerprint": candidate["fingerprint"]},
                )
            save = ok("GET", ranking + "/save/preview")
            ok(
                "POST",
                ranking + "/save",
                {
                    "expected_draft_version": save["draft_version"],
                    "expected_ranking_fingerprint": save["ranking_fingerprint"],
                },
            )
        yield server, base, run, branch, root


def test_first_entry_preview_read_only_and_position_cas_inside_real_transaction(
    generated_run,
):
    _server, base, run, branch, root = generated_run
    sim = base + "/authoritative-simulation"
    preparation = ok("GET", base + "/tournaments/EVT-2000-W01-browser_cup/preparation")
    from beta_engine.domain.simulation_slots import fingerprint

    wire_fingerprint = preparation.pop("preparation_fingerprint")
    assert wire_fingerprint == fingerprint(preparation)
    position = ok("GET", sim + "/position")
    assert position["current_slot_kind"] is None
    assert (
        _request("GET", sim + "/match-reconstruction/state?group_id=missing")[0] == 409
    )
    preview = ok("GET", sim + "/pre-alpha/fax-current-entry/preview")
    assert preview["decision_slot_ordinal"] == 1
    assert preview["decision_count"] == 41
    assert not preview["persisted"]
    assert _request("GET", sim + "/entry-decision-slot/1")[0] == 409
    # A stale reviewed Position must fail in the production DB transaction and
    # leave the Entry store unchanged, even with all other proposal hashes valid.
    stale = {
        "command_id": "stale-entry",
        "run_id": run,
        "branch_id": branch,
        "expected_week": preview["current_week"],
        "expected_revision_id": preview["expected_revision_id"],
        "expected_position_fingerprint": "0" * 64,
        "decision_slot_ordinal": 1,
        "event_ids": preview["event_ids"],
        "seed": preview["seed"],
        "expected_entry_batch_fingerprint": preview["entry_batch_fingerprint"],
        "expected_slot_fingerprint": preview["slot_fingerprint"],
    }
    assert _request("POST", sim + "/entry-decision-slot/commit", stale)[0] == 409
    assert _request("GET", sim + "/entry-decision-slot/1")[0] == 409
    applied = ok(
        "POST",
        sim + "/pre-alpha/fax-current-entry/apply",
        {
            "command_id": "actual-entry",
            "expected_preview_fingerprint": preview["preview_fingerprint"],
        },
    )
    assert applied["decision_count"] == 41
    assert applied["validation_required"]
    persisted = ok("GET", sim + "/entry-decision-slot/1")
    assert not persisted["validation_resolved"]
    assert ok("GET", sim + "/position")["current_slot_kind"] == "entry"
    assert (root / "entry_tuning.json").read_bytes() == Path(
        "config/balance/entry_tuning.json"
    ).read_bytes()


def test_roster_fingerprints_are_computed_once_without_changing_projection(
    generated_run, monkeypatch
):
    server, _base, run, branch, _ = generated_run
    from beta_engine.application.run_owned_entry_roster import (
        RunOwnedEntryRosterService,
    )
    from beta_engine.domain.rankings.official import RankingWeek
    from beta_engine.infrastructure.db.initial_world_state import get_initial_world
    from beta_engine.infrastructure.db.player_lifecycle_state import get_lifecycle
    from beta_engine.infrastructure.db.player_sporting_state import get_sporting

    factory = server.app.state.runtime.repository._session_factory
    week = RankingWeek(season_index=0, week=1)
    with factory() as session:
        service = RunOwnedEntryRosterService(session, run, branch, week)
        expected = service.get_active_players(season="2000/2001").model_dump(
            mode="json"
        )
        states = [
            get_initial_world(session, run_id=run, branch_id=branch),
            get_lifecycle(session, run_id=run, branch_id=branch, week=week),
            get_sporting(session, run_id=run, branch_id=branch, week=week),
        ]
        counts = {}
        for state in states:
            cls = type(state)
            original = cls.fingerprint.fget
            counts[cls] = 0

            def counted(value, cls=cls, original=original):
                counts[cls] += 1
                return original(value)

            monkeypatch.setattr(cls, "fingerprint", property(counted))
        assert (
            service.get_active_players(season="2000/2001").model_dump(mode="json")
            == expected
        )
        # One persisted-state integrity check plus one shared projection hash;
        # the count must be constant for all 64 players.
        assert list(counts.values()) == [2, 2, 2]
