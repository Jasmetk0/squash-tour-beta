"""Real HTTP/SQLite: seasonal archive, world overview and honest season comparison.

Two genuine Signed Seasons are completed with twelve real MatchEngine rally logs (the
flow of ``test_native_overlapping_cross_season_signed``). The archive lists both, each
season is compared with the other in both directions, and the Run is then extended and
cold-restarted: the old summaries and their sources must not change. In the changed-
policy variant the next season is played under another ranking policy, which must be
reported as limited comparability with the exact differing values.
"""

import pytest

from beta_engine.domain.calendar.run_calendar import RunCalendar
from tests.api.test_calendar_sporting_horizon_extension import extend, extension
from tests.api.test_calendar_tour_flow import command, execute, inspect, save_tour, setup, tour_url
from tests.api.test_native_overlapping_cross_season_signed import (
    FIRST_WEEK,
    SECOND_WEEK,
    _advance,
    _plan,
    _play_week,
    _prepare_fields,
)
from tests.api.test_saved_revision_history_api import ApiServer, _request

pytestmark = pytest.mark.smoke


def get(server, path):
    code, body = _request("GET", tour_url(server) + path)
    assert code == 200, body
    return body


def complete_two_seasons(server, *, change_policy):
    repo, _ = setup(server, RunCalendar(4, 2, 2030, 3), count=8)
    if change_policy:
        view = inspect(server)
        execute(server, command(view, "policy", name="best1-from-s2", data={
            "effective_week": {**view["state"]["week"], "season_index": 1, "week": 1},
            "ranking": {"policy_id": "Best1fromS2", "best_n": 1},
        }))
        save_tour(server)
    _plan(server, FIRST_WEEK)
    _advance(server, "transition", "s1-open-announcement-w3", 0, 3)
    _plan(server, SECOND_WEEK)
    _advance(server, "transition", "s1-open-final-w4", 0, 4)
    _prepare_fields(server, FIRST_WEEK)
    _play_week(server, FIRST_WEEK, week=4)
    _advance(server, "season-transition", "s1-closure", 1, 1)
    _prepare_fields(server, SECOND_WEEK)
    _play_week(server, SECOND_WEEK, week=1)
    _advance(server, "transition", "s2-publish-w1", 1, 2)
    _advance(server, "transition", "s2-empty-w3", 1, 3)
    _advance(server, "transition", "s2-empty-w4", 1, 4)
    _advance(server, "season-transition", "s2-closure", 2, 1)
    return repo


def read_everything(server):
    archive = get(server, "/seasons")
    return {
        "archive": archive,
        "s0": get(server, "/seasons/0"),
        "s1": get(server, "/seasons/1"),
        "s1_vs_s0": get(server, "/seasons/1?compare_to=0"),
        "s0_vs_s1": get(server, "/seasons/0?compare_to=1"),
    }


@pytest.mark.parametrize("change_policy", [False, True], ids=["same-rules", "changed-ranking-policy"])
def test_archive_and_comparison_survive_extension_and_restart(tmp_path, change_policy):
    db = f"sqlite:///{tmp_path / 'season-archive.sqlite'}"
    with ApiServer(database_url=db) as server:
        complete_two_seasons(server, change_policy=change_policy)
        assert inspect(server)["saved_completed_seasons"] == [0, 1]
        before = read_everything(server)
        archive = before["archive"]
        assert [s["season_index"] for s in archive["seasons"]] == [0, 1]
        for season in archive["seasons"]:
            assert season["overview"]["completed_edition_count"] == 2
            assert season["overview"]["titles_awarded"] == 2
            assert season["leading_player"] is not None
            assert season["leading_country"]["titles"] >= 1
            ranks = season["overview"]["rankings"]
            assert len(ranks["week_w_published_fingerprint"]) == 64
            # The next season's Week-1 ranking is a different publication than Week W.
            if season["season_index"] == 0:
                assert ranks["next_season_week_1_fingerprint"] not in (
                    None, ranks["week_w_published_fingerprint"])
        # Debuts (historical rule: first application): all eight players in S1, nobody in S2.
        assert len(archive["seasons"][0]["overview"]["turned_pro"]) == 8
        assert archive["seasons"][1]["overview"]["turned_pro"] == []

        # Both directions are present, with presence-aware deltas.
        for key, (selected, other) in {"s1_vs_s0": (1, 0), "s0_vs_s1": (0, 1)}.items():
            detail = before[key]["detail"]
            assert (detail["selected_season_index"], detail["comparison_season_index"]) == (selected, other)
            for table in ("countries", "players"):
                for row in detail[table]:
                    # Absence is never a zero: a delta exists only when both seasons have the entity.
                    assert (row["delta"] is None) == (row["presence"] != "both")
                    if row["delta"] is not None:
                        for field, value in row["delta"].items():
                            assert value == row["selected"][field] - row["comparison"][field]
            assert detail["comparability"]["compared_fields"]
            assert {"edition_point_tables_fingerprint", "edition_formats_fingerprint"} <= set(
                detail["comparability"]["compared_fields"]
            )
            assert "point_tables" not in detail["comparability"]["not_compared"]
            assert "qualification_geometry" in detail["comparability"]["not_compared"]
            assert before[key]["overview"] == detail["selected_overview"]
        # The reverse comparison negates every delta.
        forward = {r["country_code"]: r for r in before["s1_vs_s0"]["detail"]["countries"]}
        for row in before["s0_vs_s1"]["detail"]["countries"]:
            if row["delta"] is not None:
                assert row["delta"] == {k: -v for k, v in forward[row["country_code"]]["delta"].items()}

        comparability = before["s1_vs_s0"]["detail"]["comparability"]
        assert before["s0_vs_s1"]["detail"]["comparability"]["comparable"] is comparability["comparable"]
        if change_policy:
            assert comparability["comparable"] is False
            fields = {d["field"]: d for d in comparability["differences"]}
            assert fields["ranking_best_n"] == {"field": "ranking_best_n", "selected": 1, "comparison": 15}
            assert fields["ranking_policy_id"]["selected"] == "Best1fromS2"
        else:
            assert comparability["comparable"] is True and comparability["differences"] == []

        # Continuing the Run (explicit horizon extension) must not touch closed seasons.
        status, review = extension(server, 4)
        assert status == 200 and review["can_save"], review
        status, receipt = extend(server, review, "extend-after-two-seasons")
        assert status == 200 and receipt["simulation_started"] is False, receipt
        assert inspect(server)["run_calendar"]["season_count"] == 4
        after_extension = read_everything(server)
        for key in ("s0", "s1", "s1_vs_s0", "s0_vs_s1"):
            assert after_extension[key]["selected"] == before[key]["selected"]
            assert after_extension[key]["detail" if "detail" in before[key] else "selected"] == (
                before[key]["detail" if "detail" in before[key] else "selected"])
        assert [s["season_index"] for s in after_extension["archive"]["seasons"]] == [0, 1]
        for old, new in zip(before["archive"]["seasons"], after_extension["archive"]["seasons"]):
            for field in ("overview", "rules", "leading_player", "leading_country", "boundary_command_id"):
                assert old[field] == new[field]
        assert inspect(server)["saved_completed_seasons"] == [0, 1]
        # A season that is not complete or not signed is rejected, not guessed.
        assert _request("GET", tour_url(server) + "/seasons/2")[0] == 409
        assert _request("GET", tour_url(server) + "/seasons/0?compare_to=2")[0] == 409
        stable = {k: v for k, v in after_extension.items() if k != "archive"}

    # Cold restart: identical reads; no extra Save, pause or duplicate closure.
    with ApiServer(database_url=db) as restarted:
        view = inspect(restarted)
        assert view["saved_completed_seasons"] == [0, 1]
        again = read_everything(restarted)
        for key, value in stable.items():
            assert again[key]["selected"] == value["selected"]
            assert again[key].get("detail") == value.get("detail")
        assert [s["season_index"] for s in again["archive"]["seasons"]] == [0, 1]
