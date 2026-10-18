"""Production HTTP/SQLite sporting-only weeks, persistence, real matches and recovery."""

import copy

import pytest

from beta_engine.domain.calendar.run_calendar import RunCalendar
from beta_engine.infrastructure.db.calendar_sporting_checkpoint import (
    COMPONENT_KEY,
    load_checkpoint,
)
from tests.api.test_calendar_continuation_flow import command, root, save_continuation
from tests.api.test_calendar_opening_knockout_flow import base
from tests.api.test_calendar_population_sporting_checkpoint import (
    play,
    prepare,
    restore,
    save,
)
from tests.api.test_player_generation_calendar_gate import _dump
from tests.api.test_saved_revision_history_api import ApiServer, _request

pytestmark = pytest.mark.pr_critical


def week_url(server):
    return base(server).replace("/calendar-opening-knockout", "/calendar-sporting-week")


def weekly_command(view, name="week-advance"):
    return {
        "command_id": name,
        "expected_saved_head": view["saved_head_revision_id"],
        "expected_checkpoint_fingerprint": view["checkpoint_fingerprint"],
        "seed": 431,
        "operator_label": "Admin",
        "audit_reason": "Prepare sporting week from exact completed player state",
    }


def advance(server, cmd):
    code, preview = _request("POST", week_url(server) + "/preview", cmd)
    assert code == 200, preview
    request = {
        "command": cmd,
        "expected_preview_fingerprint": preview["preview_fingerprint"],
        "explicit_confirmation": True,
    }
    code, result = _request("POST", week_url(server) + "/commit", request)
    assert code == 201, result
    assert result == preview
    return result, request


@pytest.mark.parametrize(
    "clock", [RunCalendar(52, 52, 2030, 3), RunCalendar(80, 80, 2100, 3)]
)
def test_real_sporting_weeks_consume_terminal_state_then_drive_new_matches_and_restore(
    tmp_path, clock, monkeypatch
):
    path = tmp_path / "weekly.db"
    db = f"sqlite:///{path}"
    with ApiServer(database_url=db) as server:
        repo, head = prepare(server, clock)
        knockout, _ = play(server, head)
        opening = save(server, knockout)
        _, view = _request("GET", root(server))
        cmd = weekly_command(view)
        with repo._session_factory() as session:
            previous = load_checkpoint(session, run_id="run", branch_id="branch")
        before = _dump(path)
        code, preview = _request("POST", week_url(server) + "/preview", cmd)
        assert code == 200, preview
        assert _dump(path) == before
        assert _request("POST", week_url(server) + "/preview", cmd) == (200, preview)
        event = preview["advance"]
        assert (
            event["completed_week"]["week"] == 1 and event["target_week"]["week"] == 2
        )
        assert (
            event["completed_week"]["calendar"]["weeks_per_year"]
            == clock.weeks_per_year
        )
        assert event["scope"] == "sporting_only_exhibition_timeline"
        assert sum(n for _, n in event["played_counts"]) == 6
        request = {
            "command": cmd,
            "expected_preview_fingerprint": preview["preview_fingerprint"],
            "explicit_confirmation": True,
        }
        assert (
            _request(
                "POST",
                week_url(server) + "/commit",
                {**request, "explicit_confirmation": False},
            )[0]
            == 409
        )
        assert (
            _request(
                "POST",
                week_url(server) + "/commit",
                {**request, "expected_preview_fingerprint": "f" * 64},
            )[0]
            == 409
        )
        from beta_engine.application import calendar_sporting_week_service as svc

        original = svc.replace_checkpoint

        def fail(*args, **kwargs):
            original(*args, **kwargs)
            raise ValueError("Injected after complete weekly replacement")

        monkeypatch.setattr(svc, "replace_checkpoint", fail)
        assert _request("POST", week_url(server) + "/commit", request)[0] == 409
        assert _dump(path) == before
        monkeypatch.setattr(svc, "replace_checkpoint", original)
        from concurrent.futures import ThreadPoolExecutor

        with ThreadPoolExecutor(max_workers=2) as pool:
            outcomes = list(
                pool.map(
                    lambda _: _request("POST", week_url(server) + "/commit", request),
                    range(2),
                )
            )
        assert outcomes == [(201, preview), (201, preview)]
        _, v = _request("GET", root(server))
        assert not v["saved"] and not v["can_play"]
        assert v["sporting_week"]["week"] == 2
        assert (
            _request(
                "POST", week_url(server) + "/preview", weekly_command(v, "blocked")
            )[0]
            == 409
        )
        saved_week = save_continuation(server, preview)
        state = saved_week["payload"]["content"][COMPONENT_KEY]["state"]
        assert state["schema_version"] == "calendar_sporting_checkpoint.v3"
        assert state["annual_development_applied"]
        assert (
            saved_week["payload"]["content"]["calendar_standalone_match"]
            == opening["payload"]["content"]["calendar_standalone_match"]
        )
        with repo._session_factory() as session:
            current = load_checkpoint(session, run_id="run", branch_id="branch")
        counts = dict(event["played_counts"])
        for old, new in zip(previous.players, current.players):
            assert new.long_term_fatigue == max(0, old.long_term_fatigue - 8)
            assert new.match_sharpness == max(
                0, old.match_sharpness - (2 if counts[old.player_id] == 0 else 0)
            )
            assert abs(new.current_form - new.long_term_form_norm) <= abs(
                old.current_form - old.long_term_form_norm
            )
            assert new.potential_identity == old.potential_identity
            assert new.potential_provenance == old.potential_provenance
            assert new.potential_ovr == old.potential_ovr
        _, v = _request("GET", root(server))
        ids = v["player_ids"][:2]
        code, match = _request(
            "POST", root(server) + "/simulate", command(v, *ids, "week-two-match")
        )
        assert code == 201, match
        assert match["match"]["schema_version"] == "calendar_continuation_match.v2"
        assert match["match"]["week"]["week"] == 2
        for projection in match["match"]["canonical_projections"]:
            player = next(
                p for p in current.players if p.player_id == projection["player_id"]
            )
            assert projection["canonical_attributes"] == [
                list(a) for a in player.attributes
            ]
            assert projection["long_term_fatigue"] == player.long_term_fatigue
        save_continuation(server, match)
        assert _request("GET", root(server) + "/week-two-match/replay")[1][
            "exact_replay"
        ]
        assert _request("POST", week_url(server) + "/commit", request) == (201, preview)
        _, v = _request("GET", root(server))
        third, _ = advance(server, weekly_command(v, "third-week"))
        assert sum(n for _, n in third["advance"]["played_counts"]) == 2
        save_continuation(server, third)
        _, v = _request("GET", root(server))
        fourth, _ = advance(server, weekly_command(v, "empty-third-week"))
        assert sum(n for _, n in fourth["advance"]["played_counts"]) == 0
        final = save_continuation(server, fourth)
        from beta_engine.domain.run_packages import canonical_hash
        from beta_engine.infrastructure.db.calendar_standalone_match_state import (
            load_saved_calendar_match,
        )

        for damage in (
            "delete",
            "reverse",
            "players",
            "rate",
            "counts",
            "week",
            "downgrade",
        ):
            changed = copy.deepcopy(final["payload"])
            component = changed["content"][COMPONENT_KEY]
            raw = component["state"]
            if damage == "delete":
                raw["week_events"].pop(0)
            elif damage == "reverse":
                raw["week_events"].reverse()
            elif damage == "players":
                raw["players"][0]["long_term_fatigue"] = 99
            elif damage == "rate":
                raw["week_events"][0]["policy"]["annual_change_basis_points"] = 10000
            elif damage == "counts":
                raw["week_events"][0]["played_counts"][0][1] += 1
            elif damage == "week":
                raw["week"]["week"] += 1
            elif damage == "downgrade":
                raw["schema_version"] = "calendar_sporting_checkpoint.v2"
            component["fingerprint"] = canonical_hash(raw)
            with pytest.raises(ValueError):
                load_saved_calendar_match(changed, run_id="run", branch_id="branch")
        assert repo.verify_branch_saved_revision_hash(
            revision_id=opening["revision_id"]
        )
    with ApiServer(database_url=db) as restarted:
        assert _request("GET", root(restarted))[1]["sporting_week"]["week"] == 4
        assert _request("GET", root(restarted) + "/week-two-match/replay")[1][
            "exact_replay"
        ]
        back = restore(restarted, opening["revision_id"])
        assert (
            back["payload"]["content"][COMPONENT_KEY]
            == opening["payload"]["content"][COMPONENT_KEY]
        )
        assert _request("GET", root(restarted))[1]["sporting_week"]["week"] == 1
        forward = restore(restarted, final["revision_id"])
        assert (
            forward["payload"]["content"][COMPONENT_KEY]
            == final["payload"]["content"][COMPONENT_KEY]
        )
        assert _request("POST", week_url(restarted) + "/commit", request) == (
            201,
            preview,
        )
        # Extension preserves past weekly facts; later sporting weeks consume the new horizon.
        from tests.api.test_calendar_sporting_horizon_extension import extend, extension

        code, checked = extension(restarted, 4)
        assert code == 200 and checked["can_save"], checked
        assert extend(restarted, checked)[0] == 200
        _, v = _request("GET", root(restarted))
        fifth, _ = advance(restarted, weekly_command(v, "extended-fifth"))
        assert fifth["advance"]["target_week"]["calendar"]["season_count"] == 4
        save_continuation(restarted, fifth)
        assert _request("POST", week_url(restarted) + "/commit", request) == (
            201,
            preview,
        )
