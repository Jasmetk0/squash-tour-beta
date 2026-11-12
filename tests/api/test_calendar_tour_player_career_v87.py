"""Real HTTP/SQLite: native player career, milestones and historical (as-of) views.

A prospect turns pro in the pre-Tour exhibition week, plays a real Edition and the
winner's first recorded title appears with its exact source. A view as of an earlier
week contains neither the Edition nor its title. Saving and a cold restart return the
same view. The eager Turn Pro calibration is test-only and recorded like the default.
Not covered here: a forked Branch (isolation is structural: one Tour state per Branch).
"""

import pytest

from beta_engine.application import calendar_pre_tour_turn_pro as pre_tour
from beta_engine.domain.calendar.run_calendar import RunCalendar
from beta_engine.domain.players.turn_pro_model import default_turn_pro_model_policy
from tests.api import test_calendar_population_sporting_checkpoint as population
from tests.api.test_calendar_initial_world_adoption import request as population_request
from tests.api.test_calendar_tour_flow import command, execute, inspect, save_tour, setup, tour_url
from tests.api.test_calendar_tour_turn_pro_v87_flow import EAGER, V87, _opening_pros, _play_edition
from tests.api.test_player_generation_calendar_gate import _generation
from tests.api.test_saved_revision_history_api import ApiServer, _request

pytestmark = pytest.mark.smoke


def career(server, player_id, as_of=None):
    suffix = "" if as_of is None else f"?as_of_ordinal={as_of}"
    return _request("GET", tour_url(server) + f"/players/{player_id}/career{suffix}")


def test_first_recorded_title_and_turn_pro_have_exact_sources_and_no_future(tmp_path, monkeypatch):
    monkeypatch.setattr(
        population, "population_request",
        lambda server, **changes: population_request(server, **{**changes, "lifecycle_policy": V87}),
    )
    monkeypatch.setattr(
        population, "_generation",
        lambda **changes: _generation(**{**changes, "min_age": 15, "max_age": 19}),
    )
    monkeypatch.setattr(pre_tour, "default_turn_pro_model_policy", lambda: EAGER)
    db = f"sqlite:///{tmp_path / 'career.db'}"
    with ApiServer(database_url=db) as server:
        repo, _ = setup(server, RunCalendar(52, 35, 2030, 3), count=20)
        pros, everyone = _opening_pros(repo)
        view = inspect(server)
        record = view["state"]["pre_tour_turn_pro"]
        newcomers = sorted({d["player_id"] for w in record["weeks"] for d in w["decisions"]})
        assert len(newcomers) >= 2 and not set(newcomers) & pros
        monkeypatch.setattr(pre_tour, "default_turn_pro_model_policy", default_turn_pro_model_policy)

        # Create, announce and play a real four-player Edition two weeks later.
        week = view["state"]["week"]
        edition_week = week["week"] + 2
        data = {
            "edition_id": "first", "name": "Career Edition",
            "week": {**week, "week": edition_week},
            "announcement_week": {**week, "week": week["week"] + 1},
            "start_slot": 1, "main_entrant_count": 4, "ranked": True,
            "validity_weeks": week["calendar"]["weeks_per_year"],
            "point_table": {"champion": 100, "finalist": 60, "semifinal": 30},
        }
        execute(server, command(view, "create-edition", name="first:create", data=data))
        save_tour(server)
        for name in ("announce", "open-play-week"):
            execute(server, command(inspect(server), "transition", name=name))
            save_tour(server)
        field = [*newcomers[:2], *sorted(pros)[:2]]
        _play_edition(server, field)
        execute(server, command(inspect(server), "transition", name="after-first"))
        saved = save_tour(server)
        assert repo.verify_branch_saved_revision_hash(revision_id=saved["revision_id"])
        final = inspect(server)
        authority = next(a for a in final["state"]["editions"] if a["edition"]["edition_id"] == "first")
        edition_ordinal = edition_week - 1  # season 0, week n -> ordinal n - 1

        views = {}
        for pid in field:
            code, body = career(server, pid)
            assert code == 200, body
            views[pid] = body
        champions = [p for p, v in views.items() if v["overview"]["titles"] == 1]
        assert len(champions) == 1, {p: v["overview"] for p, v in views.items()}
        champion = champions[0]
        full = views[champion]
        title = next(m for m in full["milestones"] if m["kind"] == "first_recorded_title")
        assert title["source"]["fingerprint"] == authority["tournament_fingerprint"]
        assert title["effective_week"]["week"] == edition_week
        assert full["covered_period"]["note"].startswith("Coverage starts")
        assert "injury" in full["unsupported"]
        # Every participant has a result in the timeline with the same Edition source.
        for pid, v in views.items():
            results = [e for e in v["timeline"] if e["kind"] == "edition_result"]
            assert len(results) == 1 and results[0]["source"]["fingerprint"] == authority["tournament_fingerprint"]
            assert [e["effective_week"] for e in v["timeline"] if e["effective_week"]] == sorted(
                (e["effective_week"] for e in v["timeline"] if e["effective_week"]),
                key=lambda w: (w["season_index"], w["week"]),
            )
        if champion in newcomers:
            tp = next(m for m in full["milestones"] if m["kind"] == "turn_pro")
            assert tp["source"]["kind"] == "player_ai_decision" and tp["effective_week"]["week"] == 2
            assert tp["source"]["has_recorded_evidence"] is True

        # As of the week before the Edition: no title, no result; Turn Pro still shown.
        code, past = career(server, champion, edition_ordinal - 1)
        assert code == 200, past
        assert past["overview"]["titles"] == 0
        assert not [e for e in past["timeline"] if e["kind"] == "edition_result"]
        assert not [m for m in past["milestones"] if m["kind"] == "first_recorded_title"]
        # Before the Turn Pro week (ordinal 0) a newcomer is not yet a professional.
        code, opening = career(server, newcomers[0], 0)
        assert code == 200 and opening["overview"]["status"] == "not_professional"
        assert not [m for m in opening["milestones"] if m["kind"] == "turn_pro"]
        # Unknown player and future view are rejected without a guess.
        assert career(server, "nobody")[0] == 404
        assert career(server, champion, 10_000)[0] == 409
        # Reading creates no Save, draft change or sport.
        after = inspect(server)
        for field_name in ("saved_head_revision_id", "checkpoint_fingerprint", "tour_fingerprint", "draft_version"):
            assert after[field_name] == final[field_name]
        stored = {pid: career(server, pid)[1] for pid in field}

    # Cold restart with a different default model: the same views.
    monkeypatch.setattr(pre_tour, "default_turn_pro_model_policy", lambda: EAGER)
    with ApiServer(database_url=db) as restarted:
        for pid in field:
            assert career(restarted, pid) == (200, stored[pid])
        assert career(restarted, champion, edition_ordinal - 1) == (200, past)
